import numpy as np
import pytest
from scipy import sparse
from sklearn.svm import LinearSVC

from ml_model.explainability import (
    explain_recommendations,
    linear_svm_feature_contributions,
)


class _VectorizerSchema:
    def __init__(self, width):
        self.vocabulary_ = {str(index): index for index in range(width)}


class _MetadataSchema:
    categories_ = [["component"]]


def _recommendation_result():
    return {
        "bug_id": "BUG-001",
        "recommendations": [
            {
                "developer_id": "Dev-A",
                "rank": 1,
                "ml_score": 5.0,
                "ml_score_type": "uncalibrated Phase 4 LinearSVC decision margin",
                "expertise_score": 1 / 3,
                "recency_score": float(np.exp(-8 / 365)),
                "component_relevance": 1.0,
                "similar_bug_experience_score": 0.9658006190156911,
                "cold_start": False,
                "evidence": {
                    "component": "Core",
                    "historical_verified_bug_count": 1,
                    "verified_component_assignment_count": 1,
                    "component_experience_share": 1.0,
                    "similar_bug_count": 1,
                    "similar_bug_similarity_sum": 0.9658006190156911,
                    "max_similar_bug_cosine_similarity": 0.9658006190156911,
                    "recent_activity_count_30d": 1,
                    "recent_activity_count_90d": 1,
                    "recent_component_count_30d": 1,
                    "recent_component_count_90d": 1,
                    "days_since_last_component": 8.0,
                },
                "model_contribution": None,
            },
        ],
    }


def test_explanation_contains_main_text_and_structured_computed_evidence():
    recommendation = explain_recommendations(
        _recommendation_result()
    )["recommendations"][0]
    assert "main_explanation" in recommendation
    assert "Dev-A" in recommendation["main_explanation"]
    assert "1 verified prior assignment(s) in Core" in recommendation["main_explanation"]
    assert recommendation["component_experience"] == {
        "component": "Core",
        "verified_assignment_count": 1,
        "share_of_verified_history": 1.0,
    }
    assert recommendation["similar_bug_evidence"][
        "similar_bug_count_at_or_above_threshold"
    ] == 1
    assert recommendation["recent_activity_summary"][
        "same_component_verified_assignments_last_30_days"
    ] == 1
    assert recommendation["expertise_score"] == pytest.approx(1 / 3)
    assert recommendation["recency_score"] == pytest.approx(np.exp(-8 / 365))


def test_cold_start_explanation_never_claims_historical_experience():
    result = _recommendation_result()
    result["recommendations"][0].update({
        "developer_id": "External-Dev",
        "expertise_score": 0.0,
        "recency_score": 0.0,
        "component_relevance": 0.0,
        "similar_bug_experience_score": 0.0,
        "cold_start": True,
        "evidence": {
            "component": "Core",
            "historical_verified_bug_count": 0,
            "verified_component_assignment_count": 0,
            "component_experience_share": 0.0,
            "similar_bug_count": 0,
            "similar_bug_similarity_sum": 0.0,
            "max_similar_bug_cosine_similarity": 0.0,
            "recent_activity_count_30d": 0,
            "recent_activity_count_90d": 0,
            "recent_component_count_30d": 0,
            "recent_component_count_90d": 0,
            "days_since_last_component": None,
        },
    })
    recommendation = explain_recommendations(result)["recommendations"][0]
    assert recommendation["cold_start"] is True
    assert "cold-start" in recommendation["main_explanation"]
    assert "no verified prior assignment evidence" in recommendation["main_explanation"]
    assert recommendation["component_experience"]["verified_assignment_count"] == 0
    assert recommendation["similar_bug_evidence"][
        "similar_bug_count_at_or_above_threshold"
    ] == 0
    assert recommendation["recency_score"] == 0.0


def test_old_relevant_experience_is_not_described_as_recent():
    result = _recommendation_result()
    result["recommendations"][0].update({
        "recency_score": float(np.exp(-738 / 365)),
        "evidence": {
            **result["recommendations"][0]["evidence"],
            "similar_bug_count": 0,
            "similar_bug_similarity_sum": 0.0,
            "max_similar_bug_cosine_similarity": 0.0,
            "recent_activity_count_30d": 0,
            "recent_activity_count_90d": 0,
            "recent_component_count_30d": 0,
            "recent_component_count_90d": 0,
            "days_since_last_component": 738.0,
        },
        "similar_bug_experience_score": 0.0,
    })
    recommendation = explain_recommendations(result)["recommendations"][0]

    assert recommendation["component_experience"]["verified_assignment_count"] == 1
    assert recommendation["recency_score"] == pytest.approx(
        np.exp(-738 / 365),
        abs=1e-4,
    )
    assert "was 738.0 days ago" in recommendation["main_explanation"]
    assert "Recent Core activity" not in recommendation["main_explanation"]


def test_extensive_verified_experience_is_summarized_from_history():
    result = _recommendation_result()
    result["recommendations"][0].update({
        "expertise_score": 11 / 13,
        "component_relevance": 1.0,
        "similar_bug_experience_score": 0.9658006190156911 / np.sqrt(11),
        "evidence": {
            **result["recommendations"][0]["evidence"],
            "historical_verified_bug_count": 11,
            "verified_component_assignment_count": 11,
            "component_experience_share": 1.0,
        },
    })
    recommendation = explain_recommendations(result)["recommendations"][0]

    assert recommendation["evidence"]["historical_verified_bug_count"] == 11
    assert recommendation["component_experience"]["verified_assignment_count"] == 11
    assert "11 verified prior assignment(s) in Core" in recommendation["main_explanation"]


def test_explanation_identifies_evidence_separately_from_model_interpretation():
    recommendation = explain_recommendations(
        _recommendation_result()
    )["recommendations"][0]
    assert recommendation["supporting_evidence"]
    assert recommendation["model_interpretation"] is None
    assert recommendation["ml_score_type"].startswith("uncalibrated")


def test_score_inconsistency_is_rejected():
    result = _recommendation_result()
    result["recommendations"][0]["expertise_score"] = 0.9
    with pytest.raises(ValueError, match="expertise_score is inconsistent"):
        explain_recommendations(result)


@pytest.mark.parametrize("invalid", [None, [], {"bug_id": "x"}, {"recommendations": [None]}])
def test_invalid_recommendation_input_is_rejected(invalid):
    with pytest.raises(ValueError):
        explain_recommendations(invalid)


def test_linear_svm_group_contributions_reconstruct_decision_margin():
    train_matrix = sparse.csr_matrix([
        [1.0, 0.0, 0.5, 0.0, 1.0, -1.0],
        [0.0, 1.0, 0.0, 0.5, -1.0, 1.0],
        [0.8, 0.1, 0.3, 0.1, 0.9, -0.5],
        [0.1, 0.8, 0.1, 0.3, -0.8, 0.5],
    ])
    model = LinearSVC(random_state=7).fit(train_matrix, [1, 0, 1, 0])
    transformers = {
        "title_vectorizer": _VectorizerSchema(2),
        "description_vectorizer": _VectorizerSchema(2),
        "metadata_encoder": _MetadataSchema(),
        "numeric_input_columns": ["expertise"],
    }

    explanations = linear_svm_feature_contributions(
        train_matrix,
        model,
        transformers,
    )

    assert len(explanations) == train_matrix.shape[0]
    for row, explanation in zip(train_matrix, explanations, strict=True):
        groups = explanation["feature_group_contributions"]
        assert set(groups) == {
            "title_tfidf",
            "description_tfidf",
            "bug_metadata",
            "developer_expertise_recency",
        }
        assert explanation["reconstructed_margin"] == pytest.approx(
            float(model.decision_function(row)[0]),
            abs=1e-6,
        )
        assert abs(explanation["reconstruction_error"]) <= 1e-6
