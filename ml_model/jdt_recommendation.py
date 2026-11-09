"""Chronological expertise features, evidence reranking, and explanations."""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from ml_model.jdt_dataset import _format_utc, clean_bug_text

RECENT_WINDOW_DAYS = 365
SIMILARITY_THRESHOLD = 0.2
FEATURE_COLUMNS = (
    "historical_bug_count",
    "historical_active_days",
    "component_experience_count",
    "component_experience_share",
    "recent_activity_count_30d",
    "recent_activity_count_90d",
    "recent_activity_count_365d",
    "recent_component_count_30d",
    "recent_component_count_90d",
    "recent_component_count_365d",
    "days_since_last_activity",
    "days_since_last_component",
    "component_recency_score",
    "similar_bug_count",
    "similar_bug_similarity_sum",
    "max_similar_bug_similarity",
    "expertise_score",
    "similarity_score",
)

RERANK_WEIGHTS = {
    "component_history": {
        "component_experience_count": 0.45,
        "component_experience_share": 0.15,
        "recent_component_count_365d": 0.2,
        "component_recency_score": 0.2,
    },
    "similarity_history": {
        "similar_bug_count": 0.35,
        "similar_bug_similarity_sum": 0.4,
        "max_similar_bug_similarity": 0.25,
    },
    "temporal_expertise": {
        "historical_bug_count": 0.05,
        "component_experience_count": 0.2,
        "component_experience_share": 0.05,
        "recent_activity_count_365d": 0.05,
        "recent_component_count_365d": 0.15,
        "component_recency_score": 0.15,
        "similar_bug_count": 0.2,
        "similar_bug_similarity_sum": 0.15,
    },
    "svm_temporal_combined": {
        "svm_rank_score": 0.55,
        "historical_bug_count": 0.0225,
        "component_experience_count": 0.09,
        "component_experience_share": 0.0225,
        "recent_activity_count_365d": 0.0225,
        "recent_component_count_365d": 0.0675,
        "component_recency_score": 0.0675,
        "similar_bug_count": 0.09,
        "similar_bug_similarity_sum": 0.0675,
    },
}

RANK_FEATURE_COLUMNS = {
    "svm_rank_score": "svm_rank_score",
    "historical_bug_count": "history_count_rank",
    "component_experience_count": "component_count_rank",
    "component_experience_share": "component_share_rank",
    "recent_activity_count_365d": "recent_activity_rank",
    "recent_component_count_365d": "recent_component_rank",
    "component_recency_score": "component_recency_rank",
    "similar_bug_count": "similar_count_rank",
    "similar_bug_similarity_sum": "similar_sum_rank",
    "max_similar_bug_similarity": "similar_max_rank",
}


def _utc_timestamp(value: object, field: str) -> pd.Timestamp:
    timestamp = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(timestamp):
        raise ValueError(f"{field} must be a valid timezone-aware timestamp.")
    return pd.Timestamp(timestamp)


def _descending_rank_percentiles(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if len(values) <= 1:
        return np.ones(len(values), dtype=float)
    ranks = rankdata(-values, method="average")
    return 1.0 - (ranks - 1.0) / (len(values) - 1)


def _safe_count(values: Counter, developer_id: str, component: str | None = None) -> int:
    if component is None:
        return int(values[developer_id])
    return int(values[(developer_id, component)])


def build_temporal_candidate_features(
    history: pd.DataFrame,
    predictions: pd.DataFrame,
    candidates: list[str],
    vectorizer: Any,
    *,
    recent_window_days: int = RECENT_WINDOW_DAYS,
    similarity_threshold: float = SIMILARITY_THRESHOLD,
) -> pd.DataFrame:
    """Create one candidate row per bug using only prior known assignments.

    The vectorizer must already be fitted on the training partition. History
    events are admitted only when their assignment timestamp is strictly
    earlier than the prediction timestamp.
    """
    required_history = {
        "bug_id", "title", "description", "component", "developer_id",
        "created_at", "assignment_time", "label_type",
    }
    required_predictions = {"bug_id", "title", "description", "component", "created_at"}
    if not required_history.issubset(history.columns):
        raise ValueError(f"History is missing columns: {sorted(required_history - set(history.columns))}")
    if not required_predictions.issubset(predictions.columns):
        raise ValueError(
            f"Predictions are missing columns: {sorted(required_predictions - set(predictions.columns))}"
        )
    if recent_window_days <= 0:
        raise ValueError("recent_window_days must be positive.")
    if not 0 <= similarity_threshold <= 1:
        raise ValueError("similarity_threshold must be between 0 and 1.")
    if not candidates or len(candidates) != len(set(candidates)):
        raise ValueError("Candidate developer IDs must be nonempty and unique.")

    known = history.loc[history["label_type"].eq("known_entry")].copy()
    if known["developer_id"].eq("").any():
        raise ValueError("History contains a blank developer ID.")
    known["assignment_time"] = pd.to_datetime(known["assignment_time"], utc=True, errors="coerce")
    known["created_at"] = pd.to_datetime(known["created_at"], utc=True, errors="coerce")
    if known[["assignment_time", "created_at"]].isna().any().any():
        raise ValueError("Verified history contains an invalid timestamp.")
    if (known["assignment_time"] < known["created_at"]).any():
        raise ValueError("A verified assignment event predates bug creation.")
    known = known.sort_values(["assignment_time", "bug_id"], kind="stable").reset_index(drop=True)
    known["clean_document"] = (
        known["title"].map(clean_bug_text).fillna("")
        + " "
        + known["description"].map(clean_bug_text).fillna("")
    ).str.strip()
    history_matrix = vectorizer.transform(known["clean_document"].tolist()).tocsr()

    ordered_predictions = predictions.copy()
    ordered_predictions["created_at"] = pd.to_datetime(
        ordered_predictions["created_at"], utc=True, errors="coerce"
    )
    if ordered_predictions["created_at"].isna().any():
        raise ValueError("Predictions contain an invalid creation timestamp.")
    if ordered_predictions["component"].isna().any():
        raise ValueError("Predictions contain a missing component.")
    ordered_predictions = ordered_predictions.sort_values(
        ["created_at", "bug_id"], kind="stable"
    )

    dev_total: Counter[str] = Counter()
    component_total: Counter[tuple[str, str]] = Counter()
    assignment_times: dict[str, list[pd.Timestamp]] = defaultdict(list)
    component_times: dict[tuple[str, str], list[pd.Timestamp]] = defaultdict(list)
    active_days: dict[str, set[str]] = defaultdict(set)
    recent_dev_times_30d: dict[str, deque[pd.Timestamp]] = defaultdict(deque)
    recent_dev_times_90d: dict[str, deque[pd.Timestamp]] = defaultdict(deque)
    recent_dev_times: dict[str, deque[pd.Timestamp]] = defaultdict(deque)
    recent_component_times_30d: dict[tuple[str, str], deque[pd.Timestamp]] = defaultdict(deque)
    recent_component_times_90d: dict[tuple[str, str], deque[pd.Timestamp]] = defaultdict(deque)
    recent_component_times: dict[tuple[str, str], deque[pd.Timestamp]] = defaultdict(deque)
    eligible_developers: list[str] = []
    cursor = 0
    feature_rows: list[dict[str, object]] = []

    for prediction in ordered_predictions.to_dict(orient="records"):
        prediction_time = pd.Timestamp(prediction["created_at"])
        while cursor < len(known) and pd.Timestamp(known.iloc[cursor]["assignment_time"]) < prediction_time:
            event = known.iloc[cursor]
            developer_id = str(event["developer_id"])
            component = str(event["component"])
            event_time = pd.Timestamp(event["assignment_time"])
            key = (developer_id, component)
            dev_total[developer_id] += 1
            component_total[key] += 1
            assignment_times[developer_id].append(event_time)
            component_times[key].append(event_time)
            active_days[developer_id].add(event_time.date().isoformat())
            recent_dev_times_30d[developer_id].append(event_time)
            recent_dev_times_90d[developer_id].append(event_time)
            recent_dev_times[developer_id].append(event_time)
            recent_component_times_30d[key].append(event_time)
            recent_component_times_90d[key].append(event_time)
            recent_component_times[key].append(event_time)
            eligible_developers.append(developer_id)
            cursor += 1

        query_document = (
            clean_bug_text(prediction["title"])
            + " "
            + clean_bug_text(prediction["description"])
        ).strip()
        query_vector = vectorizer.transform([query_document])
        if cursor:
            similarities = (query_vector @ history_matrix[:cursor].T).toarray().ravel()
            similar_counts: Counter[str] = Counter()
            similar_sums: Counter[str] = Counter()
            similar_max: dict[str, float] = defaultdict(float)
            for index, similarity in enumerate(similarities):
                if similarity > 0:
                    developer_id = eligible_developers[index]
                    similarity_value = float(similarity)
                    similar_sums[developer_id] += similarity_value
                    if similarity_value >= similarity_threshold:
                        similar_counts[developer_id] += 1
                    similar_max[developer_id] = max(
                        similar_max[developer_id], similarity_value
                    )
        else:
            similar_counts = Counter()
            similar_sums = Counter()
            similar_max = {}

        window_start = prediction_time - timedelta(days=recent_window_days)
        window_start_30d = prediction_time - timedelta(days=30)
        window_start_90d = prediction_time - timedelta(days=90)
        current_component = str(prediction["component"])
        for developer_id in candidates:
            dev_recent_30d = recent_dev_times_30d[developer_id]
            while dev_recent_30d and dev_recent_30d[0] < window_start_30d:
                dev_recent_30d.popleft()
            dev_recent_90d = recent_dev_times_90d[developer_id]
            while dev_recent_90d and dev_recent_90d[0] < window_start_90d:
                dev_recent_90d.popleft()
            dev_recent = recent_dev_times[developer_id]
            while dev_recent and dev_recent[0] < window_start:
                dev_recent.popleft()
            component_key = (developer_id, current_component)
            comp_recent_30d = recent_component_times_30d[component_key]
            while comp_recent_30d and comp_recent_30d[0] < window_start_30d:
                comp_recent_30d.popleft()
            comp_recent_90d = recent_component_times_90d[component_key]
            while comp_recent_90d and comp_recent_90d[0] < window_start_90d:
                comp_recent_90d.popleft()
            comp_recent = recent_component_times[component_key]
            while comp_recent and comp_recent[0] < window_start:
                comp_recent.popleft()

            last_activity = (
                assignment_times[developer_id][-1]
                if assignment_times[developer_id] else None
            )
            component_history = component_times[component_key]
            last_component = component_history[-1] if component_history else None
            days_since_activity = (
                (prediction_time - last_activity).total_seconds() / 86400
                if last_activity is not None else None
            )
            days_since_component = (
                (prediction_time - last_component).total_seconds() / 86400
                if last_component is not None else None
            )
            history_count = _safe_count(dev_total, developer_id)
            component_count = _safe_count(component_total, developer_id, current_component)
            similarity_count = _safe_count(similar_counts, developer_id)
            similarity_sum = float(similar_sums[developer_id])
            max_similarity = float(similar_max.get(developer_id, 0.0))
            expertise_score = (
                component_count / (component_count + 2.0) if component_count else 0.0
            )
            similarity_score = min(
                1.0,
                similarity_sum / max(1.0, np.sqrt(history_count)),
            )
            feature_rows.append({
                "prediction_bug_id": int(prediction["bug_id"]),
                "prediction_time_utc": _format_utc(prediction_time),
                "component": current_component,
                "candidate_developer_id": developer_id,
                "historical_bug_count": history_count,
                "historical_active_days": len(active_days[developer_id]),
                "component_experience_count": component_count,
                "component_experience_share": (
                    component_count / history_count if history_count else 0.0
                ),
                "recent_activity_count_30d": len(dev_recent_30d),
                "recent_activity_count_90d": len(dev_recent_90d),
                "recent_activity_count_365d": len(dev_recent),
                "recent_component_count_30d": len(comp_recent_30d),
                "recent_component_count_90d": len(comp_recent_90d),
                "recent_component_count_365d": len(comp_recent),
                "days_since_last_activity": (
                    days_since_activity if days_since_activity is not None else ""
                ),
                "days_since_last_component": (
                    days_since_component if days_since_component is not None else ""
                ),
                "component_recency_score": (
                    float(np.exp(-days_since_component / recent_window_days))
                    if days_since_component is not None else 0.0
                ),
                "similar_bug_count": similarity_count,
                "similar_bug_similarity_sum": similarity_sum,
                "max_similar_bug_similarity": max_similarity,
                "expertise_score": expertise_score,
                "similarity_score": similarity_score,
            })
        if cursor and (known.iloc[cursor - 1]["assignment_time"] >= prediction_time):
            raise AssertionError("Future assignment was included in candidate features.")

    result = pd.DataFrame(feature_rows)
    if not result.empty:
        last_times = result.loc[
            result["days_since_last_component"].astype(str).ne(""),
            ["prediction_time_utc", "days_since_last_component"],
        ]
        if not last_times.empty and (pd.to_numeric(last_times["days_since_last_component"]) < 0).any():
            raise AssertionError("Negative component-recency interval found.")
    return result


def _component_reason(row: pd.Series) -> str | None:
    count = int(row["component_experience_count"])
    if count <= 0:
        return None
    return f"{count} verified prior assignment(s) in {row['component']}."


def _similarity_reason(row: pd.Series) -> str | None:
    count = int(row["similar_bug_count"])
    maximum = float(row["max_similar_bug_similarity"])
    if count <= 0:
        return None
    return (
        f"{count} prior bug(s) exceeded the configured text-similarity threshold; "
        f"highest cosine similarity {maximum:.3f}."
    )


def _recency_reason(row: pd.Series) -> str | None:
    days = row["days_since_last_component"]
    if days == "" or pd.isna(days):
        return None
    return f"Last verified assignment in {row['component']} was {float(days):.1f} days ago."


def explain_candidate(row: pd.Series) -> list[str]:
    """Generate only reasons supported by values in the candidate feature row."""
    reasons = [
        reason for reason in (
            _component_reason(row),
            _similarity_reason(row),
            _recency_reason(row),
        )
        if reason is not None
    ]
    if int(row["historical_bug_count"]) == 0:
        reasons.append("No prior verified assignment history was available at prediction time.")
    if not reasons:
        reasons.append("No relevant prior expertise or similar-bug evidence was available.")
    return reasons


def rank_candidate_features(
    candidate_features: pd.DataFrame,
    svm_scores: dict[str, float] | None = None,
) -> dict[str, pd.DataFrame]:
    """Return fixed, transparent baseline and evidence-based ranking variants."""
    if candidate_features.empty:
        return {name: candidate_features.copy() for name in (
            "linear_svm_baseline", "component_expertise", "similar_bug_history",
            "temporal_expertise", "svm_temporal_combined",
        )}
    required = {"candidate_developer_id", *FEATURE_COLUMNS}
    missing = required - set(candidate_features.columns)
    if missing:
        raise ValueError(f"Candidate evidence is missing columns: {sorted(missing)}")
    frame = candidate_features.copy().reset_index(drop=True)
    frame["svm_score"] = frame["candidate_developer_id"].map(svm_scores or {}).fillna(0.0)
    frame["svm_rank_score"] = _descending_rank_percentiles(frame["svm_score"].to_numpy())
    frame["component_count_rank"] = _descending_rank_percentiles(
        frame["component_experience_count"].to_numpy(dtype=float)
    )
    frame["component_share_rank"] = _descending_rank_percentiles(
        frame["component_experience_share"].to_numpy(dtype=float)
    )
    frame["recent_component_rank"] = _descending_rank_percentiles(
        frame["recent_component_count_365d"].to_numpy(dtype=float)
    )
    frame["component_recency_rank"] = _descending_rank_percentiles(
        frame["component_recency_score"].to_numpy(dtype=float)
    )
    frame["similar_count_rank"] = _descending_rank_percentiles(
        frame["similar_bug_count"].to_numpy(dtype=float)
    )
    frame["similar_sum_rank"] = _descending_rank_percentiles(
        frame["similar_bug_similarity_sum"].to_numpy(dtype=float)
    )
    frame["similar_max_rank"] = _descending_rank_percentiles(
        frame["max_similar_bug_similarity"].to_numpy(dtype=float)
    )
    frame["history_count_rank"] = _descending_rank_percentiles(
        frame["historical_bug_count"].to_numpy(dtype=float)
    )
    frame["recent_activity_rank"] = _descending_rank_percentiles(
        frame["recent_activity_count_365d"].to_numpy(dtype=float)
    )
    frame["expertise_score_rank"] = _descending_rank_percentiles(
        frame["expertise_score"].to_numpy(dtype=float)
    )
    frame["similarity_score_rank"] = _descending_rank_percentiles(
        frame["similarity_score"].to_numpy(dtype=float)
    )

    component_score = sum(
        weight * frame[RANK_FEATURE_COLUMNS[feature]]
        for feature, weight in RERANK_WEIGHTS["component_history"].items()
    )
    similarity_score = sum(
        weight * frame[RANK_FEATURE_COLUMNS[feature]]
        for feature, weight in RERANK_WEIGHTS["similarity_history"].items()
    )
    temporal_score = sum(
        weight * frame[RANK_FEATURE_COLUMNS[feature]]
        for feature, weight in RERANK_WEIGHTS["temporal_expertise"].items()
    )
    combined_score = sum(
        weight * frame[RANK_FEATURE_COLUMNS[feature]]
        for feature, weight in RERANK_WEIGHTS["svm_temporal_combined"].items()
    )
    scores = {
        "linear_svm_baseline": frame["svm_score"].to_numpy(dtype=float),
        "component_expertise": component_score.to_numpy(dtype=float),
        "similar_bug_history": similarity_score.to_numpy(dtype=float),
        "temporal_expertise": temporal_score.to_numpy(dtype=float),
        "svm_temporal_combined": combined_score.to_numpy(dtype=float),
    }
    result = {}
    for name, score_values in scores.items():
        ranked = frame.copy()
        ranked["recommendation_score"] = score_values
        ranked = ranked.sort_values(
            ["recommendation_score", "candidate_developer_id"],
            ascending=[False, True],
            kind="stable",
        ).reset_index(drop=True)
        ranked["rank"] = np.arange(1, len(ranked) + 1)
        ranked["reasons"] = ranked.apply(explain_candidate, axis=1)
        result[name] = ranked
    return result


def recommend_bug(
    bug: dict[str, object],
    history: pd.DataFrame,
    candidates: list[str],
    vectorizer: Any,
    svm_model: Any,
    top_k: int = 5,
) -> list[dict[str, object]]:
    """Recommend candidates for a bug using provided point-in-time history."""
    if top_k <= 0:
        raise ValueError("top_k must be positive.")
    prediction_time = _utc_timestamp(bug.get("created_at"), "created_at")
    title = clean_bug_text(bug.get("title", ""))
    description = clean_bug_text(bug.get("description", ""))
    component = str(bug.get("component", "") or "").strip()
    if not component:
        raise ValueError("component is required for relevant expertise features.")
    bug_id = int(bug.get("bug_id", 0))
    prediction = pd.DataFrame([{
        "bug_id": bug_id,
        "created_at": prediction_time,
        "title": title,
        "description": description,
        "component": component,
    }])
    features = build_temporal_candidate_features(
        history, prediction, candidates, vectorizer
    )
    document = f"{title} {description}".strip()
    text_vector = vectorizer.transform([document])
    svm_scores_raw = svm_model.decision_function(text_vector)
    if np.ndim(svm_scores_raw) == 1:
        svm_scores_raw = np.column_stack([-svm_scores_raw, svm_scores_raw])
    model_classes = [str(value) for value in svm_model.classes_]
    score_row = np.asarray(svm_scores_raw)[0]
    svm_scores = {
        developer_id: float(score_row[index])
        for index, developer_id in enumerate(model_classes)
    }
    ranked = rank_candidate_features(features, svm_scores)["svm_temporal_combined"]
    return [
        {
            "developer_id": str(row["candidate_developer_id"]),
            "rank": int(row["rank"]),
            "recommendation_score": float(row["recommendation_score"]),
            "evidence": {
                "historical_bug_count": int(row["historical_bug_count"]),
                "historical_active_days": int(row["historical_active_days"]),
                "component_experience_count": int(row["component_experience_count"]),
                "component_experience_share": float(row["component_experience_share"]),
                "recent_activity_count_30d": int(row["recent_activity_count_30d"]),
                "recent_activity_count_90d": int(row["recent_activity_count_90d"]),
                "recent_activity_count_365d": int(row["recent_activity_count_365d"]),
                "recent_component_count_30d": int(row["recent_component_count_30d"]),
                "recent_component_count_90d": int(row["recent_component_count_90d"]),
                "recent_component_count_365d": int(row["recent_component_count_365d"]),
                "days_since_last_activity": (
                    None if row["days_since_last_activity"] == ""
                    else float(row["days_since_last_activity"])
                ),
                "days_since_last_component": (
                    None if row["days_since_last_component"] == ""
                    else float(row["days_since_last_component"])
                ),
                "component_recency_score": float(row["component_recency_score"]),
                "similar_bug_count": int(row["similar_bug_count"]),
                "similar_bug_similarity_sum": float(row["similar_bug_similarity_sum"]),
                "max_similar_bug_similarity": float(row["max_similar_bug_similarity"]),
                "expertise_score": float(row["expertise_score"]),
                "similarity_score": float(row["similarity_score"]),
                "linear_svm_score": float(row["svm_score"]),
            },
            "reasons": list(row["reasons"]),
        }
        for _, row in ranked.head(top_k).iterrows()
    ]
