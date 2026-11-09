"""Inference interface for the validated Phase 4 developer ranker."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

import joblib
import numpy as np
import pandas as pd

from ml_model.jdt_recommendation import (
    build_temporal_candidate_features,
    explain_candidate,
)
from ml_model.jdt_dataset import clean_bug_text
from ml_model.explainability import (
    explain_recommendations,
    linear_svm_feature_contributions,
)
from ml_model.train_jdt_phase4 import _make_matrix
from sklearn.svm import LinearSVC

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DEFAULT_MODELS_DIR = PROJECT_ROOT / "models"
DEFAULT_MODEL_NAME = "combined_linear_svm"


@lru_cache(maxsize=1)
def _load_default_resources() -> tuple[dict[str, Any], pd.DataFrame, Any]:
    """Load the selected Phase 4 model and training-only history once."""
    model_path = (
        DEFAULT_MODELS_DIR / "jdt_phase4" / f"{DEFAULT_MODEL_NAME}.joblib"
    )
    history_path = DEFAULT_PROCESSED_DIR / "jdt_known_entry_train.csv"
    similarity_vectorizer_path = DEFAULT_MODELS_DIR / "jdt_tfidf_vectorizer.joblib"
    for path in (model_path, history_path, similarity_vectorizer_path):
        if not path.is_file():
            raise FileNotFoundError(
                f"Recommendation dependency is missing: {path}. "
                "Complete Phase 2, Phase 3, and Phase 4 first."
            )
    model_artifact = joblib.load(model_path)
    history = pd.read_csv(history_path, keep_default_na=False)
    similarity_vectorizer = joblib.load(similarity_vectorizer_path)
    return model_artifact, history, similarity_vectorizer


def _prediction_timestamp(bug_report: Mapping[str, object]) -> pd.Timestamp:
    value = bug_report.get("prediction_timestamp", bug_report.get("created_at"))
    timestamp = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(timestamp):
        raise ValueError(
            "bug_report requires a valid prediction_timestamp (or created_at)."
        )
    return pd.Timestamp(timestamp)


def _text_value(value: object, field: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text when supplied.")
    return value


def _candidate_ids(
    model_artifact: Mapping[str, Any],
    candidates: Sequence[str] | None,
) -> list[str]:
    values = (
        model_artifact.get("candidate_developer_ids", [])
        if candidates is None
        else candidates
    )
    if isinstance(values, str):
        raise ValueError("Candidate developers must be a sequence of IDs, not text.")
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Candidate developer IDs must be nonempty strings.")
        developer_id = value.strip()
        if developer_id not in seen:
            result.append(developer_id)
            seen.add(developer_id)
    if not result:
        raise ValueError("No candidate developers are available for recommendation.")
    return result


def _normalised_bug_id(value: object) -> tuple[object, int]:
    if value is None:
        return None, 0
    if isinstance(value, bool):
        raise ValueError("bug_id must be text or an integer, not a boolean.")
    if isinstance(value, (int, np.integer)):
        return value, int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return value, 0
        try:
            return value, int(stripped)
        except ValueError:
            return value, 0
    raise ValueError("bug_id must be text or an integer when supplied.")


def _recommend_with_resources(
    bug_report: Mapping[str, object],
    top_k: int,
    model_artifact: Mapping[str, Any],
    history: pd.DataFrame,
    similarity_vectorizer: Any,
    candidates: Sequence[str] | None,
) -> dict[str, object]:
    if not isinstance(bug_report, Mapping):
        raise ValueError("bug_report must be a mapping.")
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k must be a positive integer.")
    if not isinstance(model_artifact, Mapping):
        raise ValueError("Phase 4 model artifact must be a mapping.")
    for field in ("classifier", "transformers", "candidate_developer_ids"):
        if field not in model_artifact:
            raise ValueError(f"Phase 4 model artifact is missing {field}.")
    if "created_at" not in history or "assignment_time" not in history:
        raise ValueError("Training history must include creation and assignment timestamps.")
    if "label_type" not in history or not set(history["label_type"]).issubset({"known_entry"}):
        raise ValueError("Recommendation history may contain only verified known_entry rows.")

    timestamp = _prediction_timestamp(bug_report)
    component_value = bug_report.get("component") or bug_report.get("module")
    if not isinstance(component_value, str) or not component_value.strip():
        raise ValueError("bug_report requires a nonempty component or module.")
    component = component_value.strip()
    title = clean_bug_text(_text_value(bug_report.get("title"), "title"))
    description = clean_bug_text(_text_value(bug_report.get("description"), "description"))
    bug_id, internal_bug_id = _normalised_bug_id(bug_report.get("bug_id"))
    candidates_list = _candidate_ids(model_artifact, candidates)

    required_history_columns = {
        "bug_id",
        "title",
        "description",
        "component",
        "developer_id",
        "created_at",
        "assignment_time",
        "label_type",
        "product",
        "severity",
        "priority",
    }
    missing_history = required_history_columns - set(history.columns)
    if missing_history:
        raise ValueError(
            f"Training history is missing required columns: {sorted(missing_history)}"
        )
    prediction = pd.DataFrame([{
        "bug_id": internal_bug_id,
        "created_at": timestamp,
        "component": component,
        "title": title,
        "description": description,
    }])
    candidate_features = build_temporal_candidate_features(
        history,
        prediction,
        candidates_list,
        similarity_vectorizer,
    )
    product = bug_report.get("product")
    if product is None or not str(product).strip():
        product = history["product"].mode().iloc[0]
    bug_record = pd.DataFrame([{
        "bug_id": internal_bug_id,
        "title": title,
        "description": description,
        "product": str(product),
        "component": component,
        "severity": _text_value(bug_report.get("severity"), "severity"),
        "priority": _text_value(bug_report.get("priority"), "priority"),
    }])
    matrix_candidate_features = candidate_features.rename(
        columns={"prediction_bug_id": "bug_id"}
    )
    matrix, _ = _make_matrix(
        bug_record,
        matrix_candidate_features,
        model_artifact["transformers"],
        fit=False,
    )
    scores = np.asarray(
        model_artifact["classifier"].decision_function(matrix)
    ).reshape(-1)
    if len(scores) != len(candidate_features) or not np.isfinite(scores).all():
        raise ValueError("Phase 4 model returned missing or invalid candidate scores.")
    if isinstance(model_artifact["classifier"], LinearSVC):
        model_contributions = linear_svm_feature_contributions(
            matrix,
            model_artifact["classifier"],
            model_artifact["transformers"],
        )
    else:
        model_contributions = [None] * len(candidate_features)
    ranked = candidate_features.copy()
    ranked["ml_score"] = scores
    ranked["model_contribution"] = pd.Series(
        model_contributions,
        index=ranked.index,
        dtype=object,
    )
    ranked = ranked.sort_values(
        ["ml_score", "candidate_developer_id"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)

    recommendations: list[dict[str, object]] = []
    for rank, (_, row) in enumerate(ranked.head(top_k).iterrows(), start=1):
        feature_evidence = {
            column: (
                None
                if row[column] == "" or pd.isna(row[column])
                else float(row[column])
            )
            for column in (
                "days_since_last_activity",
                "days_since_last_component",
            )
        }
        evidence = {
            "component": component,
            "historical_verified_bug_count": int(row["historical_bug_count"]),
            "historical_active_days": int(row["historical_active_days"]),
            "verified_component_assignment_count": int(
                row["component_experience_count"]
            ),
            "component_experience_share": float(
                row["component_experience_share"]
            ),
            "recent_activity_count_30d": int(row["recent_activity_count_30d"]),
            "recent_activity_count_90d": int(row["recent_activity_count_90d"]),
            "recent_component_count_30d": int(
                row["recent_component_count_30d"]
            ),
            "recent_component_count_90d": int(
                row["recent_component_count_90d"]
            ),
            "days_since_last_activity": feature_evidence[
                "days_since_last_activity"
            ],
            "days_since_last_component": feature_evidence[
                "days_since_last_component"
            ],
            "similar_bug_count": int(row["similar_bug_count"]),
            "similar_bug_similarity_sum": float(
                row["similar_bug_similarity_sum"]
            ),
            "max_similar_bug_cosine_similarity": float(
                row["max_similar_bug_similarity"]
            ),
            "expertise_score_method": "component_count / (component_count + 2)",
            "recency_score_method": "exp(-days_since_last_component / 365)",
            "similar_bug_score_method": (
                "min(1, similarity_sum / max(1, sqrt(historical_bug_count)))"
            ),
        }
        recommendations.append({
            "developer_id": str(row["candidate_developer_id"]),
            "rank": rank,
            "ml_score": float(row["ml_score"]),
            "ml_score_type": "uncalibrated Phase 4 LinearSVC decision margin",
            "expertise_score": float(row["expertise_score"]),
            "recency_score": float(row["component_recency_score"]),
            "component_relevance": float(row["component_experience_share"]),
            "similar_bug_experience_score": float(row["similarity_score"]),
            "cold_start": int(row["historical_bug_count"]) == 0,
            "evidence": evidence,
            "model_contribution": row["model_contribution"],
            "explanations": explain_candidate(row),
        })
    return explain_recommendations({
        "bug_id": bug_id,
        "recommendations": recommendations,
    })


def recommend_developers(
    bug_report: Mapping[str, object],
    top_k: int = 3,
    *,
    candidates: Sequence[str] | None = None,
    model_artifact: Mapping[str, Any] | None = None,
    history: pd.DataFrame | None = None,
    similarity_vectorizer: Any | None = None,
) -> dict[str, object]:
    """Return ranked developers using verified pre-prediction evidence.

    Optional keyword-only dependencies support a trusted external candidate
    roster and deterministic integration tests. Normal callers need only pass
    the bug report and desired recommendation count.
    """
    if (
        model_artifact is None
        or history is None
        or similarity_vectorizer is None
    ):
        defaults = _load_default_resources()
        model_artifact = (
            model_artifact if model_artifact is not None else defaults[0]
        )
        history = history if history is not None else defaults[1]
        similarity_vectorizer = (
            similarity_vectorizer
            if similarity_vectorizer is not None
            else defaults[2]
        )
    return _recommend_with_resources(
        bug_report,
        top_k,
        model_artifact,
        history,
        similarity_vectorizer,
        candidates,
    )
