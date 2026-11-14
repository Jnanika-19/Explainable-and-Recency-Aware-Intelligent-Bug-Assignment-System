"""Evidence-grounded score decomposition and recommendation explanations."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite
from typing import Mapping

from ml_model.feature_selection.adaptive import FeatureScore


@dataclass(frozen=True)
class FeatureExplanation:
    feature: str
    value: float | None
    normalized_weight: float
    score_contribution: float
    evidence: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class RecommendationExplanation:
    developer_id: str
    score: float | None
    features: tuple[FeatureExplanation, ...]
    overall_status: str


def explain_recommendation(
    *,
    developer_id: str,
    score: FeatureScore,
    values: Mapping[str, float | None],
    evidence: Mapping[str, tuple[str, ...]],
) -> RecommendationExplanation:
    if not developer_id:
        raise ValueError("developer_id is required")
    if score.score is None:
        if score.contributions:
            raise ValueError("Feature contributions require a supplied feature score")
    else:
        if not isfinite(score.score) or any(
            not isfinite(contribution)
            for contribution in score.contributions.values()
        ):
            raise ValueError("Feature score and contributions must be finite")
        if not isclose(
            sum(score.contributions.values()),
            score.score,
            rel_tol=1e-9,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "Feature contributions do not reconcile with supplied feature score"
            )
    feature_names = set(values) | set(score.used_features) | set(score.omitted_features)
    details: list[FeatureExplanation] = []
    for name in sorted(feature_names):
        value = values.get(name)
        used = name in score.normalized_weights
        if used:
            if value is None or not isfinite(value):
                raise ValueError(f"Used feature {name!r} requires a finite value")
            expected_contribution = score.normalized_weights[name] * value
            if not isclose(
                expected_contribution,
                score.contributions[name],
                rel_tol=1e-9,
                abs_tol=1e-12,
            ):
                raise ValueError(
                    f"Explanation value for {name!r} does not match score decomposition"
                )
        statements = tuple(evidence.get(name, ()))
        if any(not statement.strip() for statement in statements):
            raise ValueError(f"Evidence statements for {name!r} must be nonempty")
        details.append(FeatureExplanation(
            feature=name,
            value=value,
            normalized_weight=score.normalized_weights.get(name, 0.0),
            score_contribution=score.contributions.get(name, 0.0),
            evidence=statements,
            status="used" if used else (
                "missing_or_unavailable" if value is None else "not_selected"
            ),
        ))
    status = (
        "scored_with_available_evidence"
        if score.score is not None else "insufficient_feature_evidence"
    )
    return RecommendationExplanation(
        developer_id=developer_id,
        score=score.score,
        features=tuple(details),
        overall_status=status,
    )
