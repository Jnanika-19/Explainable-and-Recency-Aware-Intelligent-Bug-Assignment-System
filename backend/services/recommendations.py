"""Recommendation adapter used until the Member 2/3 interfaces are integrated."""

from __future__ import annotations

from typing import Any


DEMO_NOTICE = (
    "DEMO ONLY: these placeholders are not ML predictions or assignment advice. "
    "Connect the Member 2 recommender and Member 3 scoring engine before operational use."
)


def recommend_demo(bug_report: dict[str, Any], top_k: int = 3) -> dict[str, Any]:
    """Return clearly marked placeholders so the UI can be exercised without model claims."""
    candidates = [
        {
            "developer_id": f"DEMO-{index}",
            "rank": index,
            "mode": "demo",
            "score": None,
            "expertise_score": None,
            "recency_score": None,
            "explanation": "Placeholder only; no developer evidence was evaluated.",
            "evidence": {},
        }
        for index in range(1, min(max(int(top_k), 0), 3) + 1)
    ]
    return {
        "mode": "demo",
        "disclaimer": DEMO_NOTICE,
        "bug": {
            "title": bug_report.get("title"),
            "component": bug_report.get("component"),
        },
        "recommendations": candidates,
    }
