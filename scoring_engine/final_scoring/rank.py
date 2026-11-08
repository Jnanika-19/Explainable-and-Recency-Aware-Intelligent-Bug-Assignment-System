"""Combine ML relevance with explicit expertise, recency, and workload signals."""

from __future__ import annotations

from datetime import datetime, timezone
import math


def apply_intelligent_scoring(result: dict, bug: dict, workload: dict | None = None,
                              top_k: int = 5) -> dict:
    """Add transparent scoring factors; missing workload data receives a neutral score."""
    workload = workload or {}
    recommendations = result.get("recommendations", [])
    for item in recommendations:
        evidence = item.get("evidence", {})
        ml = float(item.get("relevance_score", 0.0))
        component_count = int(evidence.get("component_experience", 0))
        product_count = int(evidence.get("product_experience", 0))
        expertise = 1 - math.exp(-0.18 * (component_count + product_count))
        recency = _recency_score(evidence.get("last_assignment_at"))
        developer_load = workload.get(item["developer_id"])
        load_score = 0.5 if developer_load is None else 1 / (1 + max(0, float(developer_load)))
        final = 0.65 * ml + 0.15 * expertise + 0.10 * recency + 0.10 * load_score
        item["model_relevance_score"] = ml
        item["relevance_score"] = float(final)
        evidence["recency_score"] = float(recency)
        evidence["workload"] = developer_load
        evidence["workload_score"] = float(load_score)
        evidence["expertise_score"] = float(expertise)
        evidence["scoring_weights"] = {
            "model": 0.65, "expertise": 0.15, "recency": 0.10, "workload": 0.10
        }
    recommendations.sort(key=lambda item: item["relevance_score"], reverse=True)
    result["recommendations"] = recommendations[:top_k]
    result["scoring_method"] = "weighted_ml_expertise_recency_workload_v1"
    return result


def _recency_score(last_assignment_at: str | None) -> float:
    if not last_assignment_at:
        return 0.5
    try:
        last = datetime.fromisoformat(last_assignment_at.replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        days = max(0.0, (datetime.now(timezone.utc) - last).total_seconds() / 86400)
        return math.exp(-days / 365.0)
    except (ValueError, TypeError):
        return 0.5
