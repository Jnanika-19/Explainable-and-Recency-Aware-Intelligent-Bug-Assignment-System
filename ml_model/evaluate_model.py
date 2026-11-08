"""Ranking metrics and model comparison for bug assignment."""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.feature_selection import SelectPercentile, chi2
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

from ml_model.feature_engineering import make_feature_preprocessor


def chronological_split(frame: pd.DataFrame, test_fraction: float = 0.2):
    """Split by creation time; never shuffle historical issues across the cutoff."""
    if "created_at" not in frame or frame["created_at"].isna().any():
        raise ValueError("Evaluation requires a valid created_at timestamp for every row.")
    ordered = frame.sort_values("created_at").reset_index(drop=True)
    cut = int(len(ordered) * (1 - test_fraction))
    if cut < 1 or cut >= len(ordered):
        raise ValueError("Not enough records for the requested chronological split.")
    return ordered.iloc[:cut].copy(), ordered.iloc[cut:].copy()


def ranking_metrics(y_true, score_matrix, classes, k: int = 5) -> dict:
    """Calculate mean Precision@K, Recall@K, reciprocal rank, and AP."""
    y_true = np.asarray(y_true, dtype=str)
    classes = np.asarray(classes, dtype=str)
    precision, recall, reciprocal_rank, average_precision = [], [], [], []
    for actual, scores in zip(y_true, score_matrix):
        order = np.argsort(scores)[::-1]
        ranked = classes[order]
        hits = (ranked[:k] == actual)
        precision.append(float(hits.sum() / min(k, len(ranked))))
        recall.append(float(hits.sum()))
        positions = np.flatnonzero(ranked == actual)
        reciprocal_rank.append(float(1 / (positions[0] + 1)) if len(positions) else 0.0)
        average_precision.append(float(1 / (positions[0] + 1)) if len(positions) else 0.0)
    return {
        f"precision_at_{k}": float(np.mean(precision)),
        f"recall_at_{k}": float(np.mean(recall)),
        "mrr": float(np.mean(reciprocal_rank)),
        "map": float(np.mean(average_precision)),
    }


def compare_models(train: pd.DataFrame, validation: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Compare a fixed-feature and adaptive chi-square selected Random Forest."""
    train = train[train["developer_id"].isin(validation["developer_id"].unique())].copy()
    validation = validation[validation["developer_id"].isin(train["developer_id"].unique())].copy()
    if train["developer_id"].nunique() < 2 or validation.empty:
        raise ValueError("Need at least two known developers represented in both periods.")
    x_train = train
    y_train = train["developer_id"].astype(str)
    x_valid = validation
    y_valid = validation["developer_id"].astype(str).to_numpy()
    results = []
    selected_model = None
    selected_name = None
    for name, adaptive in (("fixed_features", False), ("adaptive_selection", True)):
        steps = [("features", make_feature_preprocessor())]
        if adaptive:
            steps.append(("select", SelectPercentile(chi2, percentile=20)))
        steps.append(("classifier", RandomForestClassifier(
            n_estimators=250, class_weight="balanced_subsample",
            random_state=42, n_jobs=-1,
        )))
        model = Pipeline(steps)
        start = time.perf_counter()
        model.fit(x_train, y_train)
        training_seconds = time.perf_counter() - start
        start = time.perf_counter()
        probabilities = model.predict_proba(x_valid)
        prediction_seconds = time.perf_counter() - start
        metrics = ranking_metrics(y_valid, probabilities, model.classes_)
        results.append({
            "model": name, **metrics,
            "training_seconds": training_seconds,
            "prediction_seconds_per_bug": prediction_seconds / len(validation),
            "train_rows": len(train), "validation_rows": len(validation),
        })
        if selected_model is None or metrics["mrr"] > max(row["mrr"] for row in results[:-1]):
            selected_model, selected_name = model, name
    return pd.DataFrame(results), {"model": selected_model, "name": selected_name,
                                   "training_history": train.reset_index(drop=True)}
