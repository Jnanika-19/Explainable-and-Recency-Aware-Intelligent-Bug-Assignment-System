"""Evidence summaries and separately fitted confidence calibration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite

from sklearn.isotonic import IsotonicRegression


@dataclass(frozen=True)
class EvidenceSummary:
    level: str
    available_signals: int
    total_signals: int
    mean_quality: float
    conflicting: bool
    calibrated_probability: float | None
    calibration_status: str


def summarize_prediction_evidence(
    qualities: list[float],
    *,
    conflicting: bool = False,
) -> EvidenceSummary:
    if any(not isfinite(value) or not 0 <= value <= 1 for value in qualities):
        raise ValueError("Evidence quality values must be finite and in [0, 1]")
    available = sum(value > 0 for value in qualities)
    mean_quality = sum(qualities) / len(qualities) if qualities else 0.0
    if conflicting or not qualities or not available:
        level = "insufficient_or_conflicting"
    elif available == len(qualities) and mean_quality >= 0.75:
        level = "strong_evidence"
    elif mean_quality >= 0.4:
        level = "moderate_evidence"
    else:
        level = "limited_evidence"
    return EvidenceSummary(
        level=level,
        available_signals=available,
        total_signals=len(qualities),
        mean_quality=mean_quality,
        conflicting=conflicting,
        calibrated_probability=None,
        calibration_status="uncalibrated",
    )


@dataclass(frozen=True)
class CalibrationExample:
    prediction_score: float
    outcome: int
    bug_id: str
    prediction_time: datetime
    outcome_observed_at: datetime
    split: str


class IsotonicConfidenceCalibrator:
    """Fit calibration on an explicitly held-out calibration split only."""

    def __init__(self, *, minimum_examples: int = 20) -> None:
        if minimum_examples < 2:
            raise ValueError("minimum_examples must be at least 2")
        self.minimum_examples = minimum_examples
        self._model: IsotonicRegression | None = None
        self.calibration_count = 0

    def fit(self, examples: list[CalibrationExample]) -> "IsotonicConfidenceCalibrator":
        if len(examples) < self.minimum_examples:
            raise ValueError(
                f"At least {self.minimum_examples} calibration examples are required"
            )
        seen_ids: set[str] = set()
        scores: list[float] = []
        outcomes: list[int] = []
        for example in examples:
            if example.split != "calibration":
                raise ValueError("Calibration may use only the calibration split")
            if not example.bug_id or example.bug_id in seen_ids:
                raise ValueError("Calibration bug IDs must be nonempty and unique")
            seen_ids.add(example.bug_id)
            if not isfinite(example.prediction_score) or not 0 <= example.prediction_score <= 1:
                raise ValueError("Prediction scores must be finite and in [0, 1]")
            if example.outcome not in (0, 1):
                raise ValueError("Calibration outcomes must be binary 0/1")
            if (
                example.prediction_time.tzinfo is None
                or example.outcome_observed_at.tzinfo is None
            ):
                raise ValueError("Calibration timestamps must include a timezone")
            prediction_time = example.prediction_time.astimezone(timezone.utc)
            outcome_time = example.outcome_observed_at.astimezone(timezone.utc)
            if outcome_time < prediction_time:
                raise ValueError(
                    "Calibration outcome cannot predate its prediction timestamp"
                )
            scores.append(example.prediction_score)
            outcomes.append(example.outcome)
        if len(set(outcomes)) < 2 or len(set(scores)) < 2:
            raise ValueError(
                "Calibration requires both outcome classes and varied prediction scores"
            )
        model = IsotonicRegression(out_of_bounds="clip")
        model.fit(scores, outcomes)
        self._model = model
        self.calibration_count = len(examples)
        return self

    def predict_probability(self, score: float) -> float:
        if self._model is None:
            raise RuntimeError("Calibrator must be fit on held-out data first")
        if not isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Prediction score must be finite and in [0, 1]")
        return float(self._model.predict([score])[0])
