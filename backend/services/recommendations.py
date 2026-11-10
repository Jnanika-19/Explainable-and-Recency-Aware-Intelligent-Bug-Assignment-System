"""Backend adapter for Member 2's trained developer recommender."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any


def _load_recommender() -> Callable[..., Mapping[str, Any]]:
    try:
        from ml_model.developer_recommender import recommend_developers
    except ModuleNotFoundError as error:
        if error.name != "ml_model.developer_recommender":
            raise
        raise FileNotFoundError(
            "Member 2's recommender source is not installed on this branch."
        ) from error
    return recommend_developers


def recommendation_readiness() -> dict[str, Any]:
    try:
        recommender = _load_recommender()
        module = __import__(recommender.__module__, fromlist=["_load_default_resources"])
        load_resources = getattr(module, "_load_default_resources", None)
        if load_resources is None:
            return {
                "available": False,
                "detail": "Member 2's recommender does not expose its resource loader.",
            }
        load_resources()
    except FileNotFoundError as error:
        return {"available": False, "detail": str(error)}
    return {"available": True, "detail": None}


def recommend_for_bug(
    bug_report: Mapping[str, Any],
    top_k: int = 3,
    candidates: Sequence[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(bug_report, Mapping):
        raise ValueError("bug_report must be an object.")
    if not candidates:
        raise ValueError("No developer candidates are registered.")

    recommender = _load_recommender()
    result = recommender(bug_report, top_k=top_k, candidates=candidates)
    if not isinstance(result, Mapping):
        raise RuntimeError("Member 2's recommender returned an invalid response.")
    recommendations = result.get("recommendations")
    if not isinstance(recommendations, list):
        raise RuntimeError("Member 2's response is missing its recommendations list.")

    mapped = []
    for item in recommendations:
        if not isinstance(item, Mapping):
            raise RuntimeError("Member 2's response contains an invalid recommendation.")
        evidence = item.get("evidence")
        if not isinstance(evidence, Mapping):
            raise RuntimeError("Member 2's recommendation is missing evidence.")
        mapped.append(
            {
                "developer_id": item["developer_id"],
                "rank": item["rank"],
                "ml_score": item["ml_score"],
                "ml_score_type": item["ml_score_type"],
                "expertise_score": item["expertise_score"],
                "recency_score": item["recency_score"],
                "component_relevance": item["component_relevance"],
                "similar_bug_experience_score": item[
                    "similar_bug_experience_score"
                ],
                "cold_start": item["cold_start"],
                "explanation": item["main_explanation"],
                "supporting_evidence": item["supporting_evidence"],
                "model_interpretation": item.get("model_interpretation"),
                "model_contribution": item.get("model_contribution"),
                "evidence": dict(evidence),
                "assignment_score": None,
                "assignment_status": "awaiting_member3",
            }
        )

    return {
        "mode": "ml",
        "disclaimer": (
            "ML relevance only. Final assignment scoring is unavailable until "
            "Member 3's scoring engine is integrated."
        ),
        "bug": {
            "bug_id": result.get("bug_id"),
            "title": bug_report.get("title"),
            "component": bug_report.get("component") or bug_report.get("module"),
        },
        "recommendations": mapped,
        "assignment_status": "awaiting_member3",
    }
