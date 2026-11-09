import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

from ml_model.developer_recommender import recommend_developers
from ml_model.jdt_recommendation import build_temporal_candidate_features
from ml_model.train_jdt_phase4 import _fit_transformers


class _FixedMarginModel:
    def __init__(self, scores):
        self.scores = np.asarray(scores, dtype=float)

    def decision_function(self, matrix):
        if matrix.shape[0] != len(self.scores):
            raise AssertionError("Unexpected candidate count in inference matrix.")
        return self.scores


def _resources(scores=None, history=None, candidates=None):
    history = history if history is not None else pd.DataFrame([
        {
            "bug_id": 1,
            "created_at": "2020-01-01T00:00:00Z",
            "assignment_time": "2020-01-02T00:00:00Z",
            "developer_id": "Dev-A",
            "component": "Core",
            "title": "null pointer",
            "description": "null pointer in editor",
            "product": "JDT",
            "severity": "major",
            "priority": "P1",
            "label_type": "known_entry",
        },
        {
            "bug_id": 2,
            "created_at": "2020-01-03T00:00:00Z",
            "assignment_time": "2020-01-04T00:00:00Z",
            "developer_id": "Dev-B",
            "component": "Core",
            "title": "layout problem",
            "description": "editor layout issue",
            "product": "JDT",
            "severity": "minor",
            "priority": "P2",
            "label_type": "known_entry",
        },
    ])
    candidates = candidates if candidates is not None else [
        "Dev-A",
        "Dev-B",
        "Cold-1",
        "Cold-2",
        "Cold-3",
    ]
    query = pd.DataFrame([{
        "bug_id": 0,
        "created_at": "2020-01-10T00:00:00Z",
        "component": "Core",
        "title": "null pointer",
        "description": "pointer bug in editor",
    }])
    vectorizer = TfidfVectorizer().fit(
        history["title"].tolist()
        + history["description"].tolist()
        + ["null pointer bug in editor"]
    )
    candidate_features = build_temporal_candidate_features(
        history,
        query,
        candidates,
        vectorizer,
    )
    bug_record = pd.DataFrame([{
        "bug_id": 0,
        "title": "null pointer",
        "description": "pointer bug in editor",
        "product": "JDT",
        "component": "Core",
        "severity": "major",
        "priority": "P1",
    }])
    transformers = _fit_transformers(bug_record, candidate_features)
    if scores is None:
        scores = list(np.arange(len(candidates), 0, -1, dtype=float))
    artifact = {
        "classifier": _FixedMarginModel(scores),
        "transformers": transformers,
        "candidate_developer_ids": candidates,
    }
    return artifact, history, vectorizer


def _bug_report(**overrides):
    fixture_path = (
        Path(__file__).parents[1]
        / "fixtures"
        / "member2_bug_report.json"
    )
    bug = json.loads(fixture_path.read_text(encoding="utf-8"))["bug_report"]
    bug.update(overrides)
    return bug


def _recommend(bug=None, top_k=3, *, candidates=None, scores=None, history=None):
    artifact, training_history, vectorizer = _resources(
        scores=scores,
        history=history,
        candidates=candidates,
    )
    return recommend_developers(
        _bug_report() if bug is None else bug,
        top_k=top_k,
        candidates=candidates,
        model_artifact=artifact,
        history=training_history,
        similarity_vectorizer=vectorizer,
    )


def test_valid_report_returns_documented_ranked_recommendation_schema():
    result = _recommend()
    assert result["bug_id"] == "BUG-001"
    assert len(result["recommendations"]) == 3
    first = result["recommendations"][0]
    assert first["developer_id"] == "Dev-A"
    assert first["rank"] == 1
    assert isinstance(first["ml_score"], float)
    assert first["ml_score_type"].startswith("uncalibrated")
    assert 0.0 <= first["expertise_score"] <= 1.0
    assert 0.0 <= first["recency_score"] <= 1.0
    assert 0.0 <= first["component_relevance"] <= 1.0
    assert 0.0 <= first["similar_bug_experience_score"] <= 1.0
    assert first["evidence"]["verified_component_assignment_count"] == 1
    assert first["explanations"]


@pytest.mark.parametrize("missing", ["title", "description"])
def test_missing_title_or_description_is_handled_as_empty_text(missing):
    bug = _bug_report()
    bug.pop(missing)
    result = _recommend(bug)
    assert result["recommendations"]


def test_missing_component_is_rejected():
    bug = _bug_report()
    bug.pop("component")
    with pytest.raises(ValueError, match="component or module"):
        _recommend(bug)


def test_empty_candidate_list_is_rejected():
    artifact, history, vectorizer = _resources()
    with pytest.raises(ValueError, match="No candidate developers"):
        recommend_developers(
            _bug_report(),
            candidates=[],
            model_artifact=artifact,
            history=history,
            similarity_vectorizer=vectorizer,
        )


def test_invalid_empty_model_artifact_is_not_replaced_by_default():
    _, history, vectorizer = _resources()
    with pytest.raises(ValueError, match="missing classifier"):
        recommend_developers(
            _bug_report(),
            model_artifact={},
            history=history,
            similarity_vectorizer=vectorizer,
        )


def test_one_eligible_developer_returns_one_recommendation():
    result = _recommend(top_k=5, candidates=["Dev-A"])
    assert len(result["recommendations"]) == 1
    assert result["recommendations"][0]["developer_id"] == "Dev-A"


def test_top3_and_top5_are_capped_by_available_candidates():
    top3 = _recommend(top_k=3)
    top5 = _recommend(top_k=5)
    assert len(top3["recommendations"]) == 3
    assert len(top5["recommendations"]) == 5


def test_external_unseen_candidate_is_returned_as_explicit_cold_start():
    result = _recommend(top_k=1, candidates=["External-Dev"])
    recommendation = result["recommendations"][0]
    assert recommendation["developer_id"] == "External-Dev"
    assert recommendation["cold_start"] is True
    assert recommendation["evidence"]["historical_verified_bug_count"] == 0
    assert any("No prior verified assignment history" in reason
               for reason in recommendation["explanations"])


def test_missing_historical_expertise_does_not_exclude_candidate():
    result = _recommend(top_k=5)
    cold_candidates = [
        row for row in result["recommendations"]
        if row["developer_id"].startswith("Cold-")
    ]
    assert cold_candidates
    assert all(row["cold_start"] for row in cold_candidates)


def test_prediction_time_cutoff_excludes_equal_time_and_future_events():
    history = pd.DataFrame([
        {
            "bug_id": 1,
            "created_at": "2020-01-01T00:00:00Z",
            "assignment_time": "2020-01-10T00:00:00Z",
            "developer_id": "Dev-A",
            "component": "Core",
            "title": "null pointer",
            "description": "editor failure",
            "product": "JDT",
            "severity": "major",
            "priority": "P1",
            "label_type": "known_entry",
        },
        {
            "bug_id": 2,
            "created_at": "2020-01-01T00:00:00Z",
            "assignment_time": "2020-01-11T00:00:00Z",
            "developer_id": "Dev-B",
            "component": "Core",
            "title": "null pointer",
            "description": "editor failure",
            "product": "JDT",
            "severity": "major",
            "priority": "P1",
            "label_type": "known_entry",
        },
    ])
    result = _recommend(
        top_k=2,
        candidates=["Dev-A", "Dev-B"],
        history=history,
    )
    assert all(row["cold_start"] for row in result["recommendations"])
    assert all(
        row["evidence"]["historical_verified_bug_count"] == 0
        for row in result["recommendations"]
    )


def test_equal_ml_margins_use_stable_developer_id_order():
    result = _recommend(
        top_k=5,
        scores=[0.0] * 5,
        candidates=["Dev-B", "Dev-A", "Cold-3", "Cold-2", "Cold-1"],
    )
    ids = [row["developer_id"] for row in result["recommendations"]]
    assert ids == sorted(ids)
    assert [row["rank"] for row in result["recommendations"]] == [1, 2, 3, 4, 5]


@pytest.mark.parametrize("timestamp", [None, "not-a-timestamp"])
def test_invalid_or_missing_prediction_timestamp_is_rejected(timestamp):
    bug = _bug_report(prediction_timestamp=timestamp)
    with pytest.raises(ValueError, match="prediction_timestamp"):
        _recommend(bug)


def test_nonverified_history_is_rejected():
    artifact, history, vectorizer = _resources()
    history.loc[0, "label_type"] = "provisional"
    with pytest.raises(ValueError, match="only verified known_entry"):
        recommend_developers(
            _bug_report(),
            model_artifact=artifact,
            history=history,
            similarity_vectorizer=vectorizer,
        )
