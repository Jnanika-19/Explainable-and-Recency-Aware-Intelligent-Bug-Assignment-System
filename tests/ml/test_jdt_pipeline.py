import numpy as np
import pandas as pd
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

from ml_model.evaluate_jdt_phase3 import evaluate_ranked_cohort
from ml_model.generate_jdt_phase3_features import (
    _make_labeled_candidate_dataset,
    build_partition_candidate_features,
)
from ml_model.jdt_dataset import (
    build_temporal_expertise,
    chronological_split,
    clean_bug_text,
    normalize_developer_id,
)
from ml_model.jdt_recommendation import (
    build_temporal_candidate_features,
    explain_candidate,
    rank_candidate_features,
    recommend_bug,
)


def _known_rows():
    return pd.DataFrame([
        {
            "bug_id": 1,
            "created_at": pd.Timestamp("2020-01-01T00:00:00Z"),
            "assignment_time": pd.Timestamp("2020-01-02T00:00:00Z"),
            "developer_id": "Dev-A",
            "component": "Core",
            "label_type": "known_entry",
        },
        {
            "bug_id": 2,
            "created_at": pd.Timestamp("2020-01-03T00:00:00Z"),
            "assignment_time": pd.Timestamp("2020-01-04T00:00:00Z"),
            "developer_id": "Dev-A",
            "component": "Core",
            "label_type": "known_entry",
        },
        {
            "bug_id": 3,
            "created_at": pd.Timestamp("2020-01-05T00:00:00Z"),
            "assignment_time": pd.Timestamp("2020-01-09T00:00:00Z"),
            "developer_id": "Dev-B",
            "component": "UI",
            "label_type": "known_entry",
        },
        {
            "bug_id": 4,
            "created_at": pd.Timestamp("2020-01-07T00:00:00Z"),
            "assignment_time": pd.Timestamp("2020-01-08T00:00:00Z"),
            "developer_id": "Dev-A",
            "component": "Core",
            "label_type": "known_entry",
        },
        {
            "bug_id": 5,
            "created_at": pd.Timestamp("2020-01-09T00:00:00Z"),
            "assignment_time": pd.Timestamp("2020-01-10T00:00:00Z"),
            "developer_id": "Dev-B",
            "component": "Core",
            "label_type": "known_entry",
        },
    ])


def test_developer_ids_are_trimmed_and_unicode_normalized_without_casefolding():
    assert normalize_developer_id("  Dev-A  ") == "Dev-A"
    assert normalize_developer_id("Lars.Vogel@example.org") != normalize_developer_id(
        "lars.vogel@example.org"
    )


def test_cleaner_restores_escaped_newlines_before_removing_stack_trace_lines():
    stack_line = "at org.eclipse.sample." + "x" * 350 + "(Sample.java:1)"
    cleaned = clean_bug_text("Useful report.\\\\n" + stack_line)
    assert "useful report" in cleaned
    assert "Sample.java" not in cleaned
    assert clean_bug_text(r"C:\temp\new-project") == r"c:\temp\new-project"


def test_chronological_split_excludes_pre_cutoff_labels_not_yet_known():
    known = _known_rows()
    train, test, cutoff, excluded = chronological_split(known, test_fraction=0.4)
    assert cutoff == pd.Timestamp("2020-01-07T00:00:00Z")
    assert train["bug_id"].tolist() == [1, 2]
    assert test["bug_id"].tolist() == [4, 5]
    assert excluded["bug_id"].tolist() == [3]
    assert (train["assignment_time"] < cutoff).all()


def test_temporal_expertise_does_not_count_current_or_future_assignments():
    known = _known_rows()
    test = known.loc[known["bug_id"].isin([4, 5])].copy()
    snapshots = build_temporal_expertise(known, test, ["Dev-A", "Dev-B"])
    row = snapshots.loc[
        (snapshots["prediction_bug_id"] == 4)
        & (snapshots["candidate_developer_id"] == "Dev-A")
    ].iloc[0]
    assert row["prior_known_assignment_count"] == 2
    assert row["prior_component_assignment_count"] == 2
    assert row["last_prior_assignment_utc"] == "2020-01-04T00:00:00Z"
    later_row = snapshots.loc[
        (snapshots["prediction_bug_id"] == 5)
        & (snapshots["candidate_developer_id"] == "Dev-A")
    ].iloc[0]
    assert later_row["prior_known_assignment_count"] == 3
    assert snapshots["prediction_bug_id"].nunique() == 2


def test_ranking_metrics_penalize_unseen_developers_and_compute_top_k():
    metrics = evaluate_ranked_cohort(
        actual=["Dev-B", "Unseen"],
        rankings=[["Dev-B", "Dev-A"], ["Dev-A", "Dev-B"]],
    )
    assert metrics["top1_accuracy"] == 0.5
    assert metrics["top3_accuracy"] == 0.5
    assert metrics["precision_at_3"] == 0.25
    assert metrics["recall_at_5"] == 0.5
    assert metrics["mean_reciprocal_rank"] == 0.5
    cold_start = evaluate_ranked_cohort(
        actual=["Unseen"],
        rankings=[["Dev-A", "Dev-B"]],
    )
    assert cold_start["top5_accuracy"] == 0.0
    assert cold_start["mean_reciprocal_rank"] == 0.0


class _FixedSVM:
    classes_ = np.asarray(["Dev-A", "Dev-B"])

    def decision_function(self, matrix):
        return np.asarray([[0.9, 0.1]])


def _expertise_fixture():
    history = pd.DataFrame([
        {
            "bug_id": 1,
            "created_at": "2020-01-01T00:00:00Z",
            "assignment_time": "2020-01-02T00:00:00Z",
            "developer_id": "Dev-A",
            "component": "Core",
            "title": "null pointer",
            "description": "null pointer in core editor",
            "label_type": "known_entry",
        },
        {
            "bug_id": 2,
            "created_at": "2020-01-03T00:00:00Z",
            "assignment_time": "2020-01-08T00:00:00Z",
            "developer_id": "Dev-B",
            "component": "Core",
            "title": "unrelated",
            "description": "different text",
            "label_type": "known_entry",
        },
        {
            "bug_id": 3,
            "created_at": "2020-01-04T00:00:00Z",
            "assignment_time": "2020-01-05T00:00:00Z",
            "developer_id": "Provisional",
            "component": "Core",
            "title": "null pointer",
            "description": "provisional text",
            "label_type": "provisional",
        },
    ])
    vectorizer = TfidfVectorizer().fit([
        "null pointer in core editor",
        "different text",
        "new null pointer core issue",
    ])
    prediction = pd.DataFrame([{
        "bug_id": 4,
        "created_at": "2020-01-06T00:00:00Z",
        "component": "Core",
        "title": "null pointer",
        "description": "new null pointer core issue",
    }])
    return history, prediction, vectorizer


def test_temporal_features_exclude_future_and_provisional_history():
    history, prediction, vectorizer = _expertise_fixture()
    same_time = history.iloc[[0]].copy()
    same_time["bug_id"] = 10
    same_time["assignment_time"] = prediction.iloc[0]["created_at"]
    history = pd.concat([history, same_time], ignore_index=True)
    features = build_temporal_candidate_features(
        history, prediction, ["Dev-A", "Dev-B", "No-History"], vectorizer
    ).set_index("candidate_developer_id")
    assert features.loc["Dev-A", "historical_bug_count"] == 1
    assert features.loc["Dev-A", "component_experience_count"] == 1
    assert features.loc["Dev-A", "component_experience_share"] == 1.0
    assert features.loc["Dev-A", "recent_component_count_365d"] == 1
    assert features.loc["Dev-A", "recent_activity_count_30d"] == 1
    assert features.loc["Dev-A", "recent_activity_count_90d"] == 1
    assert features.loc["Dev-A", "recent_component_count_30d"] == 1
    assert features.loc["Dev-A", "recent_component_count_90d"] == 1
    assert features.loc["Dev-A", "historical_active_days"] == 1
    assert features.loc["Dev-A", "days_since_last_component"] == 4.0
    assert features.loc["Dev-A", "similar_bug_count"] == 1
    assert features.loc["Dev-B", "historical_bug_count"] == 0
    assert features.loc["Dev-B", "similar_bug_count"] == 0
    assert features.loc["No-History", "component_recency_score"] == 0.0


def test_recent_30_and_90_day_activity_use_inclusive_lower_boundary():
    prediction_time = pd.Timestamp("2020-04-01T00:00:00Z")
    offsets = (30, 31, 90, 91)
    history = pd.DataFrame([
        {
            "bug_id": index,
            "created_at": prediction_time - pd.Timedelta(days=days, hours=1),
            "assignment_time": prediction_time - pd.Timedelta(days=days),
            "developer_id": "Dev-A",
            "component": "Core",
            "title": f"report {index}",
            "description": "shared failure",
            "label_type": "known_entry",
        }
        for index, days in enumerate(offsets, start=1)
    ])
    vectorizer = TfidfVectorizer().fit(["shared failure new report"])
    prediction = pd.DataFrame([{
        "bug_id": 5,
        "created_at": prediction_time,
        "component": "Core",
        "title": "new report",
        "description": "shared failure",
    }])
    features = build_temporal_candidate_features(
        history, prediction, ["Dev-A"], vectorizer
    ).iloc[0]
    assert features["historical_bug_count"] == 4
    assert features["historical_active_days"] == 4
    assert features["recent_activity_count_30d"] == 1
    assert features["recent_activity_count_90d"] == 3
    assert features["recent_activity_count_365d"] == 4
    assert features["component_experience_count"] == 4
    assert features["recent_component_count_30d"] == 1
    assert features["recent_component_count_90d"] == 3
    assert features["recent_component_count_365d"] == 4
    assert features["days_since_last_activity"] == 30.0
    assert features["days_since_last_component"] == 30.0


def test_missing_prediction_or_history_timestamps_fail_explicitly():
    history, prediction, vectorizer = _expertise_fixture()
    prediction.loc[0, "created_at"] = ""
    with pytest.raises(ValueError, match="invalid creation timestamp"):
        build_temporal_candidate_features(
            history, prediction, ["Dev-A"], vectorizer
        )

    history, prediction, vectorizer = _expertise_fixture()
    history.loc[0, "assignment_time"] = ""
    with pytest.raises(ValueError, match="invalid timestamp"):
        build_temporal_candidate_features(
            history, prediction, ["Dev-A"], vectorizer
        )


def test_labeled_feature_table_keeps_ids_as_labels_not_numeric_features():
    history, prediction, vectorizer = _expertise_fixture()
    raw_features = build_temporal_candidate_features(
        history, prediction, ["Dev-A"], vectorizer
    )
    prediction = prediction.assign(developer_id="Dev-A")
    output = _make_labeled_candidate_dataset(raw_features, prediction)
    assert output.loc[0, "is_ground_truth_candidate"]
    assert output.loc[0, "candidate_developer_id"] == "Dev-A"
    assert output.loc[0, "target_developer_id"] == "Dev-A"
    assert "candidate_developer_id" not in {
        column for column in output.select_dtypes(include=np.number).columns
    }
    assert "target_developer_id" not in {
        column for column in output.select_dtypes(include=np.number).columns
    }


def test_evaluation_labels_never_enter_expertise_history():
    train = pd.DataFrame([{
        "bug_id": 1,
        "created_at": "2020-01-01T00:00:00Z",
        "assignment_time": "2020-01-02T00:00:00Z",
        "developer_id": "Dev-A",
        "component": "Core",
        "title": "alpha failure",
        "description": "shared test terms",
        "label_type": "known_entry",
    }])
    evaluation = pd.DataFrame([
        {
            "bug_id": 2,
            "created_at": "2020-01-03T00:00:00Z",
            "assignment_time": "2020-01-04T00:00:00Z",
            "developer_id": "Dev-A",
            "component": "Core",
            "title": "beta failure",
            "description": "shared test terms",
            "label_type": "known_entry",
        },
        {
            "bug_id": 3,
            "created_at": "2020-01-05T00:00:00Z",
            "assignment_time": "2020-01-06T00:00:00Z",
            "developer_id": "Dev-A",
            "component": "Core",
            "title": "gamma failure",
            "description": "shared test terms",
            "label_type": "known_entry",
        },
    ])
    vectorizer = TfidfVectorizer().fit(["alpha failure shared test terms"])
    _, evaluation_features = build_partition_candidate_features(
        train, evaluation, ["Dev-A"], vectorizer
    )
    assert evaluation_features["historical_bug_count"].tolist() == [1, 1]


def test_explanation_reasons_are_grounded_in_feature_values():
    history, prediction, vectorizer = _expertise_fixture()
    features = build_temporal_candidate_features(
        history, prediction, ["Dev-A", "No-History"], vectorizer
    ).set_index("candidate_developer_id")
    reasons = explain_candidate(features.loc["Dev-A"])
    assert any("1 verified prior assignment" in reason for reason in reasons)
    assert any("prior bug(s) exceeded" in reason for reason in reasons)
    assert any("4.0 days ago" in reason for reason in reasons)
    cold_reasons = explain_candidate(features.loc["No-History"])
    assert any("No prior verified assignment history" in reason for reason in cold_reasons)


def test_recommendation_output_contains_candidate_ids_numeric_evidence_and_reasons():
    history, _, vectorizer = _expertise_fixture()
    recommendations = recommend_bug(
        {
            "bug_id": 10,
            "created_at": "2020-01-06T00:00:00Z",
            "component": "Core",
            "title": "null pointer",
            "description": "new null pointer core issue",
        },
        history,
        ["Dev-A", "Dev-B"],
        vectorizer,
        _FixedSVM(),
        top_k=2,
    )
    assert [row["developer_id"] for row in recommendations] == ["Dev-A", "Dev-B"]
    assert recommendations[0]["evidence"]["component_experience_count"] == 1
    assert recommendations[0]["evidence"]["similar_bug_count"] == 1
    assert recommendations[0]["evidence"]["recent_activity_count_30d"] == 1
    assert recommendations[0]["evidence"]["recent_component_count_90d"] == 1
    assert recommendations[0]["reasons"]
    assert all(
        isinstance(value, (int, float))
        for value in recommendations[0]["evidence"].values()
        if value is not None
    )


def test_ranker_keeps_tied_candidates_equally_scored_before_id_tiebreak():
    history, prediction, vectorizer = _expertise_fixture()
    features = build_temporal_candidate_features(
        history, prediction, ["Dev-A", "Dev-B"], vectorizer
    )
    tied = features.copy()
    for column in (
        "component_experience_count",
        "component_experience_share",
        "recent_component_count_365d",
        "component_recency_score",
        "similar_bug_count",
        "similar_bug_similarity_sum",
        "max_similar_bug_similarity",
        "historical_bug_count",
        "recent_activity_count_365d",
        "expertise_score",
        "similarity_score",
    ):
        tied[column] = 0
    ranked = rank_candidate_features(tied, {"Dev-A": 0.0, "Dev-B": 0.0})
    assert ranked["linear_svm_baseline"]["recommendation_score"].nunique() == 1
