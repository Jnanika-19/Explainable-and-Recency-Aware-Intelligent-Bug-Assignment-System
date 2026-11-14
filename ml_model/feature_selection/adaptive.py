"""Availability-aware feature scoring; this is a scorer, not a trained model."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal, Mapping


FORBIDDEN_FEATURE_COLUMNS = frozenset({
    "developer_label",
    "actual_developer",
    "final_assignee",
    "assigned_to",
    "duplicate_label",
    "duplicate_resolution",
    "resolution",
    "target",
    "label",
})


@dataclass(frozen=True)
class FeatureSignal:
    value: float | None
    evidence_quality: float = 1.0


@dataclass(frozen=True)
class FeatureScore:
    score: float | None
    contributions: Mapping[str, float]
    normalized_weights: Mapping[str, float]
    used_features: tuple[str, ...]
    omitted_features: tuple[str, ...]
    evidence_coverage: float
    mode: Literal["fixed", "adaptive"]


def validate_feature_columns(columns: list[str] | tuple[str, ...]) -> None:
    """Reject target/outcome columns before they enter the scoring feature set."""
    normalized = {
        column: column.strip().casefold().replace(" ", "_").replace("-", "_")
        for column in columns
    }
    forbidden = sorted(
        column for column, normalized_name in normalized.items()
        if normalized_name in FORBIDDEN_FEATURE_COLUMNS
    )
    if forbidden:
        raise ValueError(
            f"Target/outcome columns are not valid model inputs: {forbidden}"
        )


def score_features(
    *,
    weights: Mapping[str, float],
    signals: Mapping[str, FeatureSignal],
    mode: Literal["fixed", "adaptive"] = "adaptive",
) -> FeatureScore:
    """Score only available signals and renormalize; absent evidence gets no weight."""
    if mode not in ("fixed", "adaptive"):
        raise ValueError(f"Unsupported feature-selection mode: {mode}")
    validate_feature_columns(tuple(weights))
    if not weights:
        raise ValueError("At least one feature weight is required")
    unknown = set(signals) - set(weights)
    if unknown:
        raise ValueError(f"Signals have no configured weights: {sorted(unknown)}")

    for name, weight in weights.items():
        if not isfinite(weight) or weight < 0:
            raise ValueError(f"Weight for {name!r} must be finite and non-negative")
    total_base_weight = sum(weights.values())
    if total_base_weight <= 0:
        raise ValueError("At least one feature weight must be positive")

    effective_weights: dict[str, float] = {}
    omitted: list[str] = []
    for name, base_weight in weights.items():
        signal = signals.get(name)
        if signal is None:
            omitted.append(name)
            continue
        if not isfinite(signal.evidence_quality) or not 0 <= signal.evidence_quality <= 1:
            raise ValueError(
                f"Evidence quality for {name!r} must be within [0, 1]"
            )
        if signal.value is None:
            omitted.append(name)
            continue
        if not isfinite(signal.value) or not 0 <= signal.value <= 1:
            raise ValueError(f"Signal value for {name!r} must be within [0, 1]")
        effective = base_weight
        if mode == "adaptive":
            effective *= signal.evidence_quality
        if effective <= 0:
            omitted.append(name)
            continue
        effective_weights[name] = effective

    active_total = sum(effective_weights.values())
    if active_total <= 0:
        return FeatureScore(
            None, {}, {}, (), tuple(omitted), 0.0, mode
        )

    normalized = {
        name: weight / active_total
        for name, weight in effective_weights.items()
    }
    active_values: dict[str, float] = {}
    for name in normalized:
        value = signals[name].value
        if value is None:
            raise RuntimeError(f"Selected feature {name!r} has no signal value")
        active_values[name] = value
    contributions = {
        name: normalized[name] * active_values[name]
        for name in normalized
    }
    coverage = sum(effective_weights.values()) / total_base_weight
    return FeatureScore(
        sum(contributions.values()),
        contributions,
        normalized,
        tuple(name for name in weights if name in normalized),
        tuple(omitted),
        min(coverage, 1.0),
        mode,
    )
