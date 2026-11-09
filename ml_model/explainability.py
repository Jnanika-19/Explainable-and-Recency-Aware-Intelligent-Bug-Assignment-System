"""Evidence-grounded recommendation explanations and LinearSVC attribution."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import exp, isclose, isfinite, sqrt
from typing import Any

import numpy as np
from scipy import sparse
from sklearn.svm import LinearSVC


_SCORE_FIELDS = (
    "ml_score",
    "expertise_score",
    "recency_score",
    "component_relevance",
    "similar_bug_experience_score",
)


def linear_svm_feature_contributions(
    matrix: sparse.spmatrix,
    classifier: LinearSVC,
    transformers: Mapping[str, Any],
) -> list[dict[str, object]]:
    """Decompose each binary LinearSVC margin into additive feature groups."""
    if not isinstance(classifier, LinearSVC):
        raise ValueError("Grouped model contributions require a fitted LinearSVC.")
    if list(classifier.classes_) != [0, 1] or classifier.coef_.shape[0] != 1:
        raise ValueError("Grouped contributions require binary labels ordered [0, 1].")
    if matrix.shape[1] != classifier.coef_.shape[1]:
        raise ValueError("Feature matrix width does not match the fitted LinearSVC.")

    try:
        widths = (
            len(transformers["title_vectorizer"].vocabulary_),
            len(transformers["description_vectorizer"].vocabulary_),
            sum(len(group) for group in transformers["metadata_encoder"].categories_),
            len(transformers["numeric_input_columns"]),
        )
    except (KeyError, AttributeError, TypeError) as error:
        raise ValueError("Fitted transformer artifact has an invalid feature schema.") from error
    if sum(widths) != matrix.shape[1]:
        raise ValueError("Fitted transformer widths do not match the model feature matrix.")

    group_names = (
        "title_tfidf",
        "description_tfidf",
        "bug_metadata",
        "developer_expertise_recency",
    )
    coefficients = classifier.coef_.getrow(0) if sparse.issparse(classifier.coef_) else classifier.coef_[0]
    decision_margins = np.asarray(classifier.decision_function(matrix)).reshape(-1)
    contributions: list[dict[str, object]] = []
    for row_index in range(matrix.shape[0]):
        row_contributions: dict[str, float] = {}
        start = 0
        row = matrix.getrow(row_index)
        for group_name, width in zip(group_names, widths, strict=True):
            end = start + width
            row_contributions[group_name] = float(
                row[:, start:end].multiply(coefficients[start:end]).sum()
            )
            start = end
        intercept = float(classifier.intercept_[0])
        reconstructed = intercept + sum(row_contributions.values())
        margin = float(decision_margins[row_index])
        if not isclose(reconstructed, margin, rel_tol=1e-5, abs_tol=1e-6):
            raise ValueError("Grouped LinearSVC contributions do not reconstruct its margin.")
        contributions.append({
            "method": "LinearSVC additive grouped feature contributions (x_i * coefficient_i)",
            "positive_candidate_class": 1,
            "intercept": intercept,
            "feature_group_contributions": row_contributions,
            "reconstructed_margin": reconstructed,
            "decision_margin": margin,
            "reconstruction_error": margin - reconstructed,
        })
    return contributions


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite number.")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be a finite number.") from error
    if not isfinite(result):
        raise ValueError(f"{field} must be a finite number.")
    return result


def _count(evidence: Mapping[str, object], field: str) -> int:
    value = evidence.get(field)
    if isinstance(value, bool):
        raise ValueError(f"Evidence field {field} must be a nonnegative integer.")
    try:
        converted = int(value)
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Evidence field {field} must be a nonnegative integer.") from error
    if converted < 0 or numeric != converted:
        raise ValueError(f"Evidence field {field} must be a nonnegative integer.")
    return converted


def _validate_recommendation(row: Mapping[str, object]) -> tuple[dict[str, object], str]:
    required = {
        "developer_id",
        "rank",
        "ml_score",
        "expertise_score",
        "recency_score",
        "component_relevance",
        "similar_bug_experience_score",
        "cold_start",
        "evidence",
    }
    missing = required - set(row)
    if missing:
        raise ValueError(f"Recommendation is missing required fields: {sorted(missing)}")
    developer_id = row["developer_id"]
    rank = row["rank"]
    if not isinstance(developer_id, str) or not developer_id.strip():
        raise ValueError("Recommendation developer_id must be nonempty text.")
    if isinstance(rank, bool) or not isinstance(rank, int) or rank <= 0:
        raise ValueError("Recommendation rank must be a positive integer.")
    if not isinstance(row["cold_start"], bool):
        raise ValueError("Recommendation cold_start must be a boolean.")
    scores = {
        field: _finite_number(row[field], field)
        for field in _SCORE_FIELDS
    }
    for field in _SCORE_FIELDS[1:]:
        if not 0 <= scores[field] <= 1:
            raise ValueError(f"{field} must be between zero and one.")
    evidence = row["evidence"]
    if not isinstance(evidence, Mapping):
        raise ValueError("Recommendation evidence must be a mapping.")

    history_count = _count(evidence, "historical_verified_bug_count")
    component_count = _count(evidence, "verified_component_assignment_count")
    similar_count = _count(evidence, "similar_bug_count")
    if component_count > history_count:
        raise ValueError("Component experience cannot exceed total verified history.")
    if row["cold_start"] != (history_count == 0):
        raise ValueError("cold_start must match the verified historical bug count.")

    expected_expertise = component_count / (component_count + 2.0)
    expected_component_relevance = (
        component_count / history_count if history_count else 0.0
    )
    if not isclose(scores["expertise_score"], expected_expertise, abs_tol=1e-8):
        raise ValueError("expertise_score is inconsistent with verified component history.")
    if not isclose(
        scores["component_relevance"],
        expected_component_relevance,
        abs_tol=1e-8,
    ):
        raise ValueError("component_relevance is inconsistent with verified history.")

    days_since_component = evidence.get("days_since_last_component")
    if days_since_component is None:
        expected_recency = 0.0
    else:
        days = _finite_number(days_since_component, "days_since_last_component")
        if days < 0:
            raise ValueError("days_since_last_component cannot be negative.")
        expected_recency = exp(-days / 365.0)
    if not isclose(scores["recency_score"], expected_recency, abs_tol=1e-8):
        raise ValueError("recency_score is inconsistent with the last component assignment.")

    similarity_sum = _finite_number(
        evidence.get("similar_bug_similarity_sum", 0.0),
        "similar_bug_similarity_sum",
    )
    if similarity_sum < 0:
        raise ValueError("similar_bug_similarity_sum cannot be negative.")
    expected_similarity = min(
        1.0,
        similarity_sum / max(1.0, sqrt(history_count)),
    )
    if not isclose(
        scores["similar_bug_experience_score"],
        expected_similarity,
        abs_tol=1e-8,
    ):
        raise ValueError(
            "similar_bug_experience_score is inconsistent with historical similarity."
        )
    if similar_count and history_count == 0:
        raise ValueError("Similar bug evidence requires verified historical assignments.")

    component = evidence.get("component")
    if component is not None and (not isinstance(component, str) or not component.strip()):
        raise ValueError("Evidence component must be nonempty text when supplied.")
    contribution = row.get("model_contribution")
    if contribution is not None:
        if not isinstance(contribution, Mapping):
            raise ValueError("model_contribution must be a mapping or None.")
        margin = _finite_number(contribution.get("decision_margin"), "decision_margin")
        if not isclose(margin, scores["ml_score"], rel_tol=1e-5, abs_tol=1e-6):
            raise ValueError("Model contribution margin does not match ml_score.")
        groups = contribution.get("feature_group_contributions")
        if not isinstance(groups, Mapping) or not groups:
            raise ValueError("Model contribution requires feature group contributions.")
        group_sum = sum(
            _finite_number(value, f"feature contribution {key}")
            for key, value in groups.items()
        )
        intercept = _finite_number(contribution.get("intercept"), "model intercept")
        if not isclose(
            group_sum + intercept,
            margin,
            rel_tol=1e-5,
            abs_tol=1e-6,
        ):
            raise ValueError("Model contribution groups do not reconstruct ml_score.")
    return dict(evidence), str(component) if component is not None else "the requested component"


def _explanation_for(
    row: Mapping[str, object],
    evidence: Mapping[str, object],
    component: str,
) -> dict[str, object]:
    developer_id = str(row["developer_id"])
    history_count = _count(evidence, "historical_verified_bug_count")
    component_count = _count(evidence, "verified_component_assignment_count")
    similar_count = _count(evidence, "similar_bug_count")
    recent_overall_30 = _count(evidence, "recent_activity_count_30d")
    recent_overall_90 = _count(evidence, "recent_activity_count_90d")
    recent_component_30 = _count(evidence, "recent_component_count_30d")
    recent_component_90 = _count(evidence, "recent_component_count_90d")
    maximum_similarity = _finite_number(
        evidence.get("max_similar_bug_cosine_similarity", 0.0),
        "max_similar_bug_cosine_similarity",
    )
    if not 0 <= maximum_similarity <= 1:
        raise ValueError("max_similar_bug_cosine_similarity must be between zero and one.")
    ml_score = _finite_number(row["ml_score"], "ml_score")

    component_experience = {
        "component": component,
        "verified_assignment_count": component_count,
        "share_of_verified_history": float(row["component_relevance"]),
    }
    similar_bug_evidence = {
        "similar_bug_count_at_or_above_threshold": similar_count,
        "similarity_threshold": 0.2,
        "maximum_cosine_similarity": maximum_similarity,
        "similarity_sum": _finite_number(
            evidence.get("similar_bug_similarity_sum", 0.0),
            "similar_bug_similarity_sum",
        ),
    }
    recent_activity_summary = {
        "all_components_verified_assignments_last_30_days": recent_overall_30,
        "all_components_verified_assignments_last_90_days": recent_overall_90,
        "same_component_verified_assignments_last_30_days": recent_component_30,
        "same_component_verified_assignments_last_90_days": recent_component_90,
        "days_since_last_verified_assignment_in_component": evidence.get(
            "days_since_last_component"
        ),
    }

    facts: list[str] = []
    if history_count == 0:
        facts.append("No verified assignment history was available before prediction time.")
    else:
        facts.append(f"{history_count} verified prior assignment(s) across the available history.")
        if component_count:
            facts.append(f"{component_count} verified prior assignment(s) in {component}.")
        else:
            facts.append(f"No verified prior assignment in {component}.")
        if similar_count:
            facts.append(
                f"{similar_count} historical bug description(s) met the 0.20 similarity threshold "
                f"(maximum cosine similarity {maximum_similarity:.3f})."
            )
        else:
            facts.append(
                f"No historical description met the 0.20 similarity threshold "
                f"(maximum cosine similarity {maximum_similarity:.3f})."
            )
        if recent_component_30 or recent_component_90:
            facts.append(
                f"Recent {component} activity: {recent_component_30} assignment(s) in 30 days "
                f"and {recent_component_90} in 90 days."
            )
        elif recent_overall_30 or recent_overall_90:
            facts.append(
                f"Recent verified activity in other or mixed components: "
                f"{recent_overall_30} assignment(s) in 30 days and {recent_overall_90} in 90 days; "
                f"none in {component}."
            )
        else:
            facts.append("No verified assignment activity in the previous 90 days.")
        days_since = evidence.get("days_since_last_component")
        if days_since is None:
            facts.append(f"No prior verified assignment date is available for {component}.")
        else:
            days = _finite_number(days_since, "days_since_last_component")
            facts.append(f"The last verified assignment in {component} was {days:.1f} days ago.")

    rank = int(row["rank"])
    if row["cold_start"]:
        main_explanation = (
            f"Developer {developer_id} is ranked {rank} by the model "
            f"(uncalibrated decision margin {ml_score:.3f}) but is cold-start: "
            "no verified prior assignment evidence is available. Historical expertise "
            "and recency cannot support this recommendation."
        )
    else:
        main_explanation = (
            f"Developer {developer_id} is ranked {rank} by the model "
            f"(uncalibrated decision margin {ml_score:.3f}). " + " ".join(facts[1:])
        )

    contribution = row.get("model_contribution")
    model_interpretation = None
    if isinstance(contribution, Mapping):
        groups = contribution["feature_group_contributions"]
        model_interpretation = (
            "LinearSVC additive feature-group contributions to this margin: "
            + ", ".join(
                f"{name}={float(value):+.4f}"
                for name, value in groups.items()
            )
            + ". These are model contributions, not probabilities or causal claims."
        )

    return {
        "main_explanation": main_explanation,
        "supporting_evidence": facts,
        "component_experience": component_experience,
        "similar_bug_evidence": similar_bug_evidence,
        "recent_activity_summary": recent_activity_summary,
        "model_interpretation": model_interpretation,
    }


def explain_recommendations(
    recommendation_result: Mapping[str, object],
) -> dict[str, object]:
    """Attach structured explanations using only recommendation evidence."""
    if not isinstance(recommendation_result, Mapping):
        raise ValueError("recommendation_result must be a mapping.")
    if "recommendations" not in recommendation_result:
        raise ValueError("recommendation_result is missing recommendations.")
    recommendations = recommendation_result["recommendations"]
    if not isinstance(recommendations, Sequence) or isinstance(
        recommendations, (str, bytes)
    ):
        raise ValueError("recommendations must be a sequence.")

    explained_rows: list[dict[str, object]] = []
    for row in recommendations:
        if not isinstance(row, Mapping):
            raise ValueError("Each recommendation must be a mapping.")
        evidence, component = _validate_recommendation(row)
        explained_rows.append({
            **dict(row),
            **_explanation_for(row, evidence, component),
        })
    return {
        **dict(recommendation_result),
        "recommendations": explained_rows,
    }
