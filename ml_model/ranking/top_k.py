"""Deterministic developer ranking and standard offline ranking metrics."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping


@dataclass(frozen=True)
class RankedDeveloper:
    developer_id: str
    score: float
    score_breakdown: Mapping[str, float]
    eligible_for_assignment: bool
    explanation: object | None = None


def rank_developers(
    candidates: Iterable[RankedDeveloper],
    *,
    k: int | None = None,
) -> list[RankedDeveloper]:
    records = list(candidates)
    ids: set[str] = set()
    for candidate in records:
        if not candidate.developer_id or candidate.developer_id in ids:
            raise ValueError("Candidate developer IDs must be nonempty and unique")
        ids.add(candidate.developer_id)
        if not candidate.eligible_for_assignment:
            raise ValueError(
                f"Developer {candidate.developer_id!r} is not eligible for assignment ranking"
            )
        if not isfinite(candidate.score):
            raise ValueError("Candidate scores must be finite")
        if any(not isfinite(value) for value in candidate.score_breakdown.values()):
            raise ValueError("Score breakdown values must be finite")
    if k is not None and k < 0:
        raise ValueError("k must be non-negative or None")
    records.sort(key=lambda item: (-item.score, item.developer_id))
    return records if k is None else records[:k]


def ranking_metrics(
    ranked_developer_ids: Iterable[str],
    relevant_developer_ids: Iterable[str],
    *,
    ks: tuple[int, ...] = (1, 3, 5),
) -> dict[str, float | None]:
    ranked = list(ranked_developer_ids)
    relevant = set(relevant_developer_ids)
    if len(ranked) != len(set(ranked)):
        raise ValueError("Ranked developer IDs must be unique")
    if any(k <= 0 for k in ks):
        raise ValueError("All K values must be positive")
    metrics: dict[str, float | None] = {}
    for k in ks:
        hits = sum(developer in relevant for developer in ranked[:k])
        metrics[f"precision_at_{k}"] = hits / k
        metrics[f"recall_at_{k}"] = hits / len(relevant) if relevant else None
    first_relevant_rank = next(
        (rank for rank, developer in enumerate(ranked, start=1)
         if developer in relevant),
        None,
    )
    metrics["mrr"] = (
        1 / first_relevant_rank
        if relevant and first_relevant_rank is not None
        else (0.0 if relevant else None)
    )
    return metrics
