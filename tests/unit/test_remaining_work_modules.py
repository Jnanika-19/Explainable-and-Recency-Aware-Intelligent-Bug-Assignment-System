from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from bug_similarity.retrieval.point_in_time import (
    BugRelationshipClassifier,
    BugDocument,
    DuplicateTrainingPair,
    PointInTimeBugRetriever,
    RelationshipTrainingPair,
)
from ml_model.feature_selection.adaptive import (
    FeatureSignal,
    score_features,
    validate_feature_columns,
)
from ml_model.ranking.top_k import (
    RankedDeveloper,
    rank_developers,
    ranking_metrics,
)
from scoring_engine.cold_start.policy import (
    ColdStartStatus,
    assess_cold_start,
)
from scoring_engine.confidence.prediction_confidence import (
    CalibrationExample,
    IsotonicConfidenceCalibrator,
    summarize_prediction_evidence,
)
from scoring_engine.final_scoring.explainability import explain_recommendation
from scoring_engine.recency.point_in_time import recency_decay_score
from scoring_engine.workload.point_in_time import (
    AssignmentEvent,
    calculate_workload,
)


UTC = timezone.utc
NOW = datetime(2025, 1, 10, tzinfo=UTC)


class RemainingWorkModuleTests(unittest.TestCase):
    def test_cold_start_does_not_promote_git_commits_to_assignment_history(self):
        result = assess_cold_start(
            assignment_count=0,
            git_commit_count=100,
            identity_verified=False,
        )
        self.assertEqual(result.status, ColdStartStatus.UNMATCHED_GIT_CONTRIBUTOR)
        self.assertFalse(result.eligible_for_history_model)

    def test_cold_start_conflicts_require_manual_review(self):
        result = assess_cold_start(
            assignment_count=10,
            identity_verified=True,
            identity_conflict=True,
        )
        self.assertEqual(result.status, ColdStartStatus.MANUAL_REVIEW)
        self.assertFalse(result.eligible_for_history_model)

    def test_explicit_new_developer_requires_verified_identity(self):
        result = assess_cold_start(
            assignment_count=0,
            explicitly_confirmed_new=True,
            identity_verified=False,
        )
        self.assertEqual(result.status, ColdStartStatus.MANUAL_REVIEW)

    def test_cold_start_validated_history_threshold(self):
        result = assess_cold_start(
            assignment_count=2,
            identity_verified=True,
            minimum_assignments=2,
        )
        self.assertEqual(result.status, ColdStartStatus.ELIGIBLE_WITH_HISTORY)

    def test_adaptive_feature_selection_omits_missing_feature(self):
        result = score_features(
            weights={"expertise": 0.6, "recency": 0.4},
            signals={
                "expertise": FeatureSignal(0.8, evidence_quality=0.5),
                "recency": FeatureSignal(None),
            },
            mode="adaptive",
        )
        self.assertAlmostEqual(result.score, 0.8)
        self.assertEqual(result.used_features, ("expertise",))
        self.assertEqual(result.omitted_features, ("recency",))
        self.assertEqual(result.normalized_weights, {"expertise": 1.0})

    def test_fixed_and_adaptive_weights_differ_by_quality_adjustment(self):
        signals = {
            "expertise": FeatureSignal(1.0, evidence_quality=0.25),
            "text": FeatureSignal(0.0, evidence_quality=1.0),
        }
        fixed = score_features(
            weights={"expertise": 0.5, "text": 0.5},
            signals=signals,
            mode="fixed",
        )
        adaptive = score_features(
            weights={"expertise": 0.5, "text": 0.5},
            signals=signals,
            mode="adaptive",
        )
        self.assertAlmostEqual(fixed.score, 0.5)
        self.assertAlmostEqual(adaptive.score, 0.2)

    def test_target_columns_rejected_from_model_features(self):
        with self.assertRaisesRegex(ValueError, "Target/outcome"):
            validate_feature_columns(("expertise", "developer_label"))

    def test_no_available_adaptive_feature_returns_no_score(self):
        result = score_features(
            weights={"workload": 1.0},
            signals={"workload": FeatureSignal(None)},
        )
        self.assertIsNone(result.score)
        self.assertEqual(result.evidence_coverage, 0)

    def test_evidence_summary_is_not_a_probability(self):
        summary = summarize_prediction_evidence([1.0, 0.8, 0.0])
        self.assertIsNone(summary.calibrated_probability)
        self.assertEqual(summary.calibration_status, "uncalibrated")
        self.assertEqual(summary.available_signals, 2)

    def test_evidence_conflict_downgrades_summary(self):
        summary = summarize_prediction_evidence([1.0, 1.0], conflicting=True)
        self.assertEqual(summary.level, "insufficient_or_conflicting")

    def test_calibrator_requires_held_out_calibration_examples(self):
        calibrator = IsotonicConfidenceCalibrator(minimum_examples=2)
        examples = [
            CalibrationExample(
                0.5, 1, "b1", NOW, NOW + timedelta(days=1), "test"
            ),
            CalibrationExample(
                0.6, 0, "b2", NOW, NOW + timedelta(days=1), "calibration"
            ),
        ]
        with self.assertRaisesRegex(ValueError, "calibration split"):
            calibrator.fit(examples)

    def test_calibrator_fit_and_predict_after_validation(self):
        calibrator = IsotonicConfidenceCalibrator(minimum_examples=4)
        examples = [
            CalibrationExample(
                score,
                outcome,
                f"bug-{index}",
                NOW,
                NOW + timedelta(days=1),
                "calibration",
            )
            for index, (score, outcome) in enumerate(
                [(0.1, 0), (0.2, 0), (0.7, 1), (0.9, 1)]
            )
        ]
        calibrator.fit(examples)
        self.assertGreaterEqual(calibrator.predict_probability(0.5), 0)
        self.assertLessEqual(calibrator.predict_probability(0.5), 1)

    def test_calibrator_rejects_naive_timestamps(self):
        examples = [
            CalibrationExample(
                score,
                outcome,
                f"bug-{index}",
                datetime(2025, 1, 10),
                NOW + timedelta(days=1),
                "calibration",
            )
            for index, (score, outcome) in enumerate(
                [(0.1, 0), (0.2, 0), (0.7, 1), (0.9, 1)]
            )
        ]
        with self.assertRaisesRegex(ValueError, "timezone"):
            IsotonicConfidenceCalibrator(minimum_examples=4).fit(examples)

    def test_explanation_uses_provided_values_and_contributions(self):
        score = score_features(
            weights={"expertise": 1.0, "workload": 1.0},
            signals={
                "expertise": FeatureSignal(0.8),
                "workload": FeatureSignal(None),
            },
        )
        explanation = explain_recommendation(
            developer_id="repo:key",
            score=score,
            values={"expertise": 0.8, "workload": None},
            evidence={"expertise": ("2 historical assignments in this component",)},
        )
        self.assertAlmostEqual(explanation.score, 0.8)
        self.assertTrue(explanation.features[0].evidence)
        self.assertTrue(any(
            item.status == "missing_or_unavailable"
            for item in explanation.features
        ))

    def test_explanation_rejects_contributions_that_do_not_sum_to_score(self):
        score = score_features(
            weights={"expertise": 1.0},
            signals={"expertise": FeatureSignal(0.8)},
        )
        inconsistent_score = replace(score, score=0.7)
        with self.assertRaisesRegex(ValueError, "contributions.*feature score"):
            explain_recommendation(
                developer_id="repo:key",
                score=inconsistent_score,
                values={"expertise": 0.8},
                evidence={},
            )

    def test_ranking_is_stable_and_truncates(self):
        candidates = [
            RankedDeveloper("z", 0.8, {"expertise": 0.8}, True),
            RankedDeveloper("a", 0.8, {"expertise": 0.8}, True),
            RankedDeveloper("b", 0.4, {"expertise": 0.4}, True),
        ]
        self.assertEqual(
            [item.developer_id for item in rank_developers(candidates, k=2)],
            ["a", "z"],
        )

    def test_ranking_rejects_duplicate_candidate_ids(self):
        candidate = RankedDeveloper("same", 1.0, {}, True)
        with self.assertRaisesRegex(ValueError, "unique"):
            rank_developers([candidate, candidate])

    def test_ranking_metrics_known_small_example(self):
        metrics = ranking_metrics(
            ["d1", "d2", "d3", "d4", "d5"],
            {"d2", "d4"},
            ks=(1, 3, 5),
        )
        self.assertAlmostEqual(metrics["precision_at_3"], 1 / 3)
        self.assertAlmostEqual(metrics["recall_at_3"], 0.5)
        self.assertAlmostEqual(metrics["mrr"], 0.5)

    def test_ranking_rejects_ineligible_developer(self):
        candidate = RankedDeveloper("unverified", 1.0, {}, False)
        with self.assertRaisesRegex(ValueError, "not eligible"):
            rank_developers([candidate])

    def test_ranking_metrics_undefined_when_no_relevant_labels(self):
        metrics = ranking_metrics(["d1"], set(), ks=(1,))
        self.assertIsNone(metrics["recall_at_1"])
        self.assertIsNone(metrics["mrr"])

    def test_point_in_time_retrieval_excludes_cutoff_and_future_bugs(self):
        retriever = PointInTimeBugRetriever().fit(
            [
                BugDocument(
                    "old", NOW - timedelta(days=1), "parser crash",
                    NOW - timedelta(days=1),
                ),
                BugDocument("at-cutoff", NOW, "parser failure", NOW),
                BugDocument(
                    "future", NOW + timedelta(days=1), "parser crash",
                    NOW + timedelta(days=1),
                ),
            ],
            cutoff=NOW,
            query_bug_id="query",
        )
        matches = retriever.search(
            query_bug_id="query",
            query_text="parser crash",
            query_text_available_at=NOW - timedelta(minutes=1),
            top_k=10,
        )
        self.assertEqual([match.bug_id for match in matches], ["old"])
        self.assertLess(matches[0].created_at, NOW)

    def test_point_in_time_retrieval_rejects_naive_timestamps(self):
        with self.assertRaisesRegex(ValueError, "timezone"):
            PointInTimeBugRetriever().fit(
                [BugDocument(
                    "old",
                    datetime(2025, 1, 1),
                    "text",
                    datetime(2025, 1, 1),
                )],
                cutoff=NOW,
                query_bug_id="query",
            )

    def test_point_in_time_retrieval_excludes_text_updated_at_cutoff(self):
        retriever = PointInTimeBugRetriever().fit(
            [
                BugDocument(
                    "edited-after-cutoff",
                    NOW - timedelta(days=2),
                    "future edited description",
                    NOW,
                )
            ],
            cutoff=NOW,
            query_bug_id="query",
        )
        self.assertEqual(
            retriever.search(
                query_bug_id="query",
                query_text="future",
                query_text_available_at=NOW - timedelta(minutes=1),
                top_k=5,
            ),
            (),
        )

    def test_point_in_time_retrieval_requires_query_text_before_cutoff(self):
        retriever = PointInTimeBugRetriever().fit(
            [
                BugDocument(
                    "old",
                    NOW - timedelta(days=1),
                    "parser crash",
                    NOW - timedelta(days=1),
                )
            ],
            cutoff=NOW,
            query_bug_id="query",
        )
        with self.assertRaisesRegex(ValueError, "query text.*before.*cutoff"):
            retriever.search(
                query_bug_id="query",
                query_text="parser crash",
                query_text_available_at=NOW,
            )

    def test_point_in_time_retrieval_excludes_query_from_fitted_corpus(self):
        retriever = PointInTimeBugRetriever().fit(
            [
                BugDocument(
                    "query",
                    NOW - timedelta(days=1),
                    "uniqueselftoken",
                    NOW - timedelta(days=1),
                ),
                BugDocument(
                    "old",
                    NOW - timedelta(days=2),
                    "parser crash",
                    NOW - timedelta(days=2),
                ),
            ],
            cutoff=NOW,
            query_bug_id="query",
        )
        self.assertNotIn("query", [doc.bug_id for doc in retriever._documents])
        self.assertNotIn("uniqueselftoken", retriever._vectorizer.vocabulary_)

    def test_duplicate_pair_keeps_target_out_of_model_features(self):
        pair = DuplicateTrainingPair(
            "query", "old", NOW - timedelta(days=1), NOW, 0.75, 1
        )
        self.assertEqual(
            pair.model_features(), {"tfidf_cosine_similarity": 0.75}
        )
        self.assertEqual(pair.target(), 1)
        self.assertNotIn("duplicate_label", pair.model_features())

    def test_duplicate_pair_rejects_future_candidate(self):
        with self.assertRaisesRegex(ValueError, "predate"):
            DuplicateTrainingPair(
                "query", "future", NOW + timedelta(seconds=1), NOW, 0.8, 1
            )

    def test_relationship_classifier_keeps_targets_out_of_features(self):
        examples = [
            RelationshipTrainingPair(
                f"query-{index}",
                f"candidate-{index}",
                NOW - timedelta(days=1),
                NOW,
                similarity,
                label,
            )
            for index, (similarity, label) in enumerate(
                [(0.1, "unrelated"), (0.2, "unrelated"),
                 (0.8, "duplicate"), (0.9, "duplicate")]
            )
        ]
        self.assertEqual(
            examples[0].model_features(),
            {"tfidf_cosine_similarity": 0.1},
        )
        classifier = BugRelationshipClassifier().fit(examples)
        prediction, probabilities = classifier.predict(0.85)
        self.assertEqual(prediction, "duplicate")
        self.assertAlmostEqual(sum(probabilities.values()), 1.0)

    def test_workload_replay_assignment_reassignment_close(self):
        events = [
            AssignmentEvent(
                "1", "bug-1", NOW - timedelta(days=3), "assign", "dev-a", "major"
            ),
            AssignmentEvent(
                "2", "bug-1", NOW - timedelta(days=2), "reassign", "dev-b", "major"
            ),
            AssignmentEvent(
                "3", "bug-2", NOW - timedelta(days=1), "assign", "dev-b", "minor"
            ),
            AssignmentEvent(
                "4", "bug-2", NOW - timedelta(seconds=1), "close", None, "minor"
            ),
        ]
        snapshot = calculate_workload(
            events,
            developer_id="dev-b",
            cutoff=NOW,
            history_complete=True,
            severity_weights={"major": 2.0, "minor": 1.0},
        )
        self.assertEqual(snapshot.active_bug_count, 1)
        self.assertEqual(snapshot.active_bug_ids, ("bug-1",))
        self.assertEqual(snapshot.severity_weighted_count, 2.0)
        self.assertEqual(snapshot.status, "complete_as_of_cutoff")

    def test_workload_requires_chronological_events(self):
        events = [
            AssignmentEvent("1", "bug-1", NOW, "assign", "dev-a"),
            AssignmentEvent(
                "2", "bug-2", NOW - timedelta(days=1), "assign", "dev-a"
            ),
        ]
        with self.assertRaisesRegex(ValueError, "chronologically"):
            calculate_workload(
                events,
                developer_id="dev-a",
                cutoff=NOW + timedelta(days=1),
                history_complete=False,
            )

    def test_incomplete_workload_history_is_not_reported_complete(self):
        snapshot = calculate_workload(
            [AssignmentEvent(
                "1", "bug-1", NOW - timedelta(days=1), "assign", "dev-a"
            )],
            developer_id="dev-a",
            cutoff=NOW,
            history_complete=False,
        )
        self.assertEqual(snapshot.active_bug_count, 1)
        self.assertEqual(snapshot.status, "incomplete_history_manual_review")

    def test_reassignment_without_severity_preserves_known_severity(self):
        snapshot = calculate_workload(
            [
                AssignmentEvent(
                    "1", "bug-1", NOW - timedelta(days=2), "assign", "dev-a", "major"
                ),
                AssignmentEvent(
                    "2", "bug-1", NOW - timedelta(days=1), "reassign", "dev-b"
                ),
            ],
            developer_id="dev-b",
            cutoff=NOW,
            history_complete=True,
            severity_weights={"major": 2.0},
        )
        self.assertEqual(snapshot.active_bug_count, 1)
        self.assertEqual(snapshot.severity_weighted_count, 2.0)

    def test_workload_excludes_events_at_the_cutoff(self):
        snapshot = calculate_workload(
            [
                AssignmentEvent(
                    "1", "bug-1", NOW - timedelta(days=1), "assign", "dev-a"
                ),
                AssignmentEvent("2", "bug-1", NOW, "close"),
            ],
            developer_id="dev-a",
            cutoff=NOW,
            history_complete=True,
        )
        self.assertEqual(snapshot.active_bug_count, 1)

    def test_recency_score_orders_newer_evidence_higher(self):
        recent = recency_decay_score(
            NOW - timedelta(days=10),
            prediction_cutoff=NOW,
        )
        older = recency_decay_score(
            NOW - timedelta(days=20),
            prediction_cutoff=NOW,
        )
        self.assertGreater(recent, older)
        self.assertAlmostEqual(
            recency_decay_score(
                NOW - timedelta(days=90),
                prediction_cutoff=NOW,
            ),
            0.5,
        )

    def test_recency_score_requires_evidence_strictly_before_cutoff(self):
        for timestamp in (NOW, NOW + timedelta(seconds=1)):
            with self.subTest(timestamp=timestamp):
                with self.assertRaisesRegex(ValueError, "strictly before"):
                    recency_decay_score(
                        timestamp,
                        prediction_cutoff=NOW,
                    )

    def test_recency_score_returns_missing_for_missing_evidence_timestamp(self):
        self.assertIsNone(
            recency_decay_score(None, prediction_cutoff=NOW)
        )
        with self.assertRaisesRegex(ValueError, "timezone"):
            recency_decay_score(
                datetime(2025, 1, 1),
                prediction_cutoff=NOW,
            )


if __name__ == "__main__":
    unittest.main()
