"""Generate leakage-safe Member 2 feature datasets and descriptive analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml_model.jdt_dataset import clean_bug_text
from ml_model.jdt_recommendation import (
    FEATURE_COLUMNS,
    build_temporal_candidate_features,
)


def _read_frame(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Required Phase 2 input is missing: {path}")
    frame = pd.read_csv(path, keep_default_na=False)
    for column in ("created_at", "assignment_time"):
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], utc=True, errors="coerce")
            if frame[column].isna().any():
                raise ValueError(f"{path.name} has an invalid value in {column}.")
    return frame


def _make_labeled_candidate_dataset(
    features: pd.DataFrame,
    predictions: pd.DataFrame,
) -> pd.DataFrame:
    bug_details = predictions[
        ["bug_id", "title", "description", "component", "created_at", "developer_id"]
    ].copy()
    bug_details["bug_text"] = (
        bug_details["title"].map(clean_bug_text).fillna("")
        + " "
        + bug_details["description"].map(clean_bug_text).fillna("")
    ).str.strip()
    bug_details["created_at"] = pd.to_datetime(
        bug_details["created_at"], utc=True, errors="raise"
    ).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    bug_details = bug_details.rename(columns={
        "created_at": "prediction_timestamp_utc",
        "developer_id": "target_developer_id",
    })
    candidate_data = features.rename(columns={
        "prediction_bug_id": "bug_id",
        "prediction_time_utc": "prediction_timestamp_utc",
    }).merge(
        bug_details,
        on=["bug_id", "prediction_timestamp_utc", "component"],
        how="left",
        validate="many_to_one",
    )
    if candidate_data["target_developer_id"].isna().any():
        raise AssertionError("Candidate features could not be joined to a verified target.")
    candidate_data["is_ground_truth_candidate"] = (
        candidate_data["candidate_developer_id"]
        == candidate_data["target_developer_id"]
    )
    ordered_columns = [
        "bug_id",
        "prediction_timestamp_utc",
        "component",
        "title",
        "description",
        "bug_text",
        "candidate_developer_id",
        "target_developer_id",
        "is_ground_truth_candidate",
        *FEATURE_COLUMNS,
    ]
    return candidate_data[ordered_columns].sort_values(
        ["bug_id", "candidate_developer_id"], kind="stable"
    ).reset_index(drop=True)


def build_partition_candidate_features(
    train: pd.DataFrame,
    evaluation: pd.DataFrame,
    candidates: list[str],
    vectorizer: object,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build both partitions from training history, never from test labels."""
    for label, frame in (("training", train), ("evaluation", evaluation)):
        if not set(frame["label_type"]).issubset({"known_entry"}):
            raise ValueError(f"{label.title()} features require verified known-entry rows.")
    training_features = build_temporal_candidate_features(
        train, train, candidates, vectorizer
    )
    evaluation_features = build_temporal_candidate_features(
        train, evaluation, candidates, vectorizer
    )
    return training_features, evaluation_features


def _analysis_outputs(
    train_features: pd.DataFrame,
    evaluation_features: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    numeric_features = list(FEATURE_COLUMNS)
    summaries: list[dict[str, object]] = []
    missingness: list[dict[str, object]] = []
    for partition, frame in (
        ("training", train_features),
        ("evaluation", evaluation_features),
    ):
        for column in frame.columns:
            values = frame[column]
            missing = values.isna() | values.astype("string").str.strip().eq("").fillna(False)
            missingness.append({
                "partition": partition,
                "column": column,
                "row_count": len(frame),
                "missing_count": int(missing.sum()),
                "missing_fraction": float(missing.mean()) if len(frame) else 0.0,
            })
        for column in numeric_features:
            values = pd.to_numeric(frame[column], errors="coerce")
            summaries.append({
                "partition": partition,
                "feature": column,
                "row_count": len(frame),
                "non_missing_count": int(values.notna().sum()),
                "missing_count": int(values.isna().sum()),
                "mean": float(values.mean()) if values.notna().any() else np.nan,
                "std": float(values.std()) if values.notna().any() else np.nan,
                "min": float(values.min()) if values.notna().any() else np.nan,
                "median": float(values.median()) if values.notna().any() else np.nan,
                "max": float(values.max()) if values.notna().any() else np.nan,
            })

    numeric_evaluation = evaluation_features[numeric_features].apply(
        pd.to_numeric, errors="coerce"
    )
    correlation = numeric_evaluation.corr(method="spearman").rename_axis("feature").reset_index()

    latest_training_time = train_features["prediction_timestamp_utc"].max()
    latest_snapshot = train_features.loc[
        train_features["prediction_timestamp_utc"].eq(latest_training_time)
    ].copy()
    developer_distribution = latest_snapshot[[
        "candidate_developer_id",
        "historical_bug_count",
        "historical_active_days",
        "component",
        "component_experience_count",
        "component_experience_share",
        "recent_activity_count_30d",
        "recent_activity_count_90d",
        "recent_component_count_30d",
        "recent_component_count_90d",
        "days_since_last_activity",
        "days_since_last_component",
        "similar_bug_count",
    ]].drop_duplicates("candidate_developer_id").copy()
    median_history = float(developer_distribution["historical_bug_count"].median())
    developer_distribution["activity_group"] = np.where(
        developer_distribution["historical_bug_count"] >= median_history,
        "high_activity",
        "low_activity",
    )
    group_comparison = (
        developer_distribution.groupby("activity_group", as_index=False)
        .agg(
            developer_count=("candidate_developer_id", "nunique"),
            mean_historical_bug_count=("historical_bug_count", "mean"),
            median_historical_bug_count=("historical_bug_count", "median"),
            mean_historical_active_days=("historical_active_days", "mean"),
            mean_component_experience_count=("component_experience_count", "mean"),
            mean_component_experience_share=("component_experience_share", "mean"),
            mean_recent_activity_count_30d=("recent_activity_count_30d", "mean"),
            mean_recent_activity_count_90d=("recent_activity_count_90d", "mean"),
            mean_similar_bug_count=("similar_bug_count", "mean"),
        )
        .sort_values("activity_group")
        .reset_index(drop=True)
    )
    return {
        "feature_summary": pd.DataFrame(summaries),
        "feature_missingness": pd.DataFrame(missingness),
        "feature_correlations": correlation,
        "developer_expertise_distribution": developer_distribution.sort_values(
            ["historical_bug_count", "candidate_developer_id"],
            ascending=[False, True],
            kind="stable",
        ).reset_index(drop=True),
        "activity_group_comparison": group_comparison,
    }


def generate_phase3_features(
    processed_dir: str | Path = "data/processed",
    model_dir: str | Path = "models",
) -> dict[str, object]:
    """Write separate train/evaluation feature sets and descriptive summaries."""
    processed_dir = Path(processed_dir)
    model_dir = Path(model_dir)
    train_path = processed_dir / "jdt_known_entry_train.csv"
    test_path = processed_dir / "jdt_known_entry_test.csv"
    vectorizer_path = model_dir / "jdt_tfidf_vectorizer.joblib"
    for path in (train_path, test_path, vectorizer_path):
        if not path.is_file():
            raise FileNotFoundError(
                f"Required Phase 2 artifact is missing: {path}. "
                "Run the existing preprocessing and baseline training first."
            )

    train = _read_frame(train_path)
    test = _read_frame(test_path)
    if not set(train["label_type"]).issubset({"known_entry"}) or not set(
        test["label_type"]
    ).issubset({"known_entry"}):
        raise ValueError("Phase 3 features require verified known-entry train/test rows.")

    vectorizer = joblib.load(vectorizer_path)
    candidates = sorted(train["developer_id"].astype(str).unique())
    train_raw_features, evaluation_raw_features = build_partition_candidate_features(
        train, test, candidates, vectorizer
    )
    train_features = _make_labeled_candidate_dataset(train_raw_features, train)
    evaluation_features = _make_labeled_candidate_dataset(
        evaluation_raw_features, test
    )
    if train_features["is_ground_truth_candidate"].sum() != len(train):
        raise AssertionError("Training feature labels do not map one-to-one to verified bugs.")
    if evaluation_features["is_ground_truth_candidate"].sum() != int(
        test["developer_id"].isin(candidates).sum()
    ):
        raise AssertionError("Evaluation feature labels disagree with seen training targets.")
    for frame in (train_features, evaluation_features):
        for column in ("days_since_last_activity", "days_since_last_component"):
            intervals = pd.to_numeric(frame[column], errors="coerce")
            if (intervals.dropna() < 0).any():
                raise AssertionError(f"Generated feature contains a negative {column}.")

    outputs = {
        "jdt_phase3_feature_train.csv": train_features,
        "jdt_phase3_feature_evaluation.csv": evaluation_features,
    }
    outputs.update({
        f"jdt_phase3_{name}.csv": frame
        for name, frame in _analysis_outputs(train_features, evaluation_features).items()
    })
    for filename, frame in outputs.items():
        frame.to_csv(processed_dir / filename, index=False, encoding="utf-8")

    metadata = {
        "training_bugs": int(len(train)),
        "evaluation_bugs": int(len(test)),
        "training_candidate_rows": int(len(train_features)),
        "evaluation_candidate_rows": int(len(evaluation_features)),
        "training_candidate_developers": int(len(candidates)),
        "training_positive_candidate_rows": int(
            train_features["is_ground_truth_candidate"].sum()
        ),
        "evaluation_positive_candidate_rows": int(
            evaluation_features["is_ground_truth_candidate"].sum()
        ),
        "unseen_evaluation_target_bugs": int(
            (~test["developer_id"].isin(candidates)).sum()
        ),
        "history_policy": (
            "known_entry assignments from training partition only; assignment_time "
            "strictly earlier than prediction_timestamp_utc; no evaluation labels "
            "are used as history"
        ),
        "vectorizer_path": str(vectorizer_path),
        "phase2_outputs_modified": False,
        "provisional_records_used": False,
        "evaluation_labels_used_as_history": False,
        "target_or_candidate_ids_in_numeric_features": False,
        "outputs": sorted(outputs),
    }
    metadata_path = processed_dir / "jdt_phase3_feature_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--models-dir", default="models")
    args = parser.parse_args()
    metadata = generate_phase3_features(args.processed_dir, args.models_dir)
    print(json.dumps(metadata, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
