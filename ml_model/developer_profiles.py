"""Build auditable developer expertise summaries from historical assignments."""

from __future__ import annotations

from collections import Counter

import pandas as pd


def build_developer_profiles(history: pd.DataFrame) -> dict[str, dict]:
    """Summarize each developer using only the history supplied by the caller."""
    profiles: dict[str, dict] = {}
    for developer_id, group in history.groupby("developer_id", sort=True):
        products = Counter(value for value in group.get("product", []) if value)
        components = Counter(value for value in group.get("component", []) if value)
        profiles[str(developer_id)] = {
            "bugs_handled": int(group["bug_id"].nunique()),
            "product_experience": dict(products),
            "component_experience": dict(components),
            "expertise_terms": _expertise_terms(group),
            "last_assignment_at": _last_activity(group),
        }
    return profiles


def _expertise_terms(group: pd.DataFrame, limit: int = 20) -> list[str]:
    text = " ".join(
        (str(row.get("title", "")) + " " + str(row.get("description", ""))).lower()
        for _, row in group.iterrows()
    )
    words = Counter(
        word for word in text.split()
        if len(word) > 2 and word.isalpha()
    )
    return [term for term, _ in words.most_common(limit)]


def _last_activity(group: pd.DataFrame) -> str | None:
    if "resolved_at" in group and group["resolved_at"].notna().any():
        return group["resolved_at"].max().isoformat()
    if "created_at" in group and group["created_at"].notna().any():
        return group["created_at"].max().isoformat()
    return None
