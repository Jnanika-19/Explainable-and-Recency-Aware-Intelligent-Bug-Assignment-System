"""Strict-cutoff recency decay for timestamped evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite


def recency_decay_score(
    evidence_available_at: datetime | None,
    *,
    prediction_cutoff: datetime,
    half_life_days: float = 90.0,
) -> float | None:
    """Return exponential decay by evidence age; missing evidence stays unknown.

    The availability timestamp must be timezone-aware and strictly earlier
    than the prediction cutoff. The score is 1.0 at zero age and halves every
    ``half_life_days``; no evidence timestamp returns ``None``.
    """
    if prediction_cutoff.tzinfo is None:
        raise ValueError("prediction_cutoff must include a timezone")
    if not isfinite(half_life_days) or half_life_days <= 0:
        raise ValueError("half_life_days must be finite and positive")
    if evidence_available_at is None:
        return None
    if evidence_available_at.tzinfo is None:
        raise ValueError("evidence_available_at must include a timezone")

    cutoff = prediction_cutoff.astimezone(timezone.utc)
    available_at = evidence_available_at.astimezone(timezone.utc)
    if available_at >= cutoff:
        raise ValueError(
            "evidence must be available strictly before prediction cutoff"
        )
    age_days = (cutoff - available_at).total_seconds() / 86_400
    return 2.0 ** (-age_days / half_life_days)
