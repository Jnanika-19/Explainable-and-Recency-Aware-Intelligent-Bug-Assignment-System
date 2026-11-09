"""Train leakage-safe text-only JDT baselines and save holdout evaluation results."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC

from ml_model.evaluate_jdt import evaluate_scores


def _bug_documents(frame: pd.DataFrame) -> list[str]:
    return (
        frame["title"].fillna("").astype(str)
        + " "
        + frame["description"].fillna("").astype(str)
    ).str.strip().tolist()


def _read_split(processed_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_path = processed_dir / "jdt_known_entry_train.csv"
    test_path = processed_dir / "jdt_known_entry_test.csv"
    if not train_path.is_file() or not test_path.is_file():
        raise FileNotFoundError(
            "Preprocessed split files are missing. Run "
            "`python -m ml_model.preprocess_jdt` first."
        )
    train = pd.read_csv(train_path, dtype={"bug_id": "int64"}, keep_default_na=False)
    test = pd.read_csv(test_path, dtype={"bug_id": "int64"}, keep_default_na=False)
    for name, frame in (("train", train), ("test", test)):
        if frame.empty:
            raise ValueError(f"The {name} split is empty.")
        if set(frame["label_type"]) != {"known_entry"}:
            raise ValueError(f"The {name} split contains non-verified target labels.")
        if frame["developer_id"].eq("").any():
            raise ValueError(f"The {name} split contains blank developer IDs.")
    train_cutoff = pd.to_datetime(train["created_at"], utc=True).max()
    test_start = pd.to_datetime(test["created_at"], utc=True).min()
    if not train_cutoff < test_start:
        raise ValueError("Train and test creation timestamps overlap.")
    assignment_times = pd.to_datetime(train["assignment_time"], utc=True)
    if not (assignment_times < test_start).all():
        raise ValueError("Training contains target assignments unavailable at test start.")
    if set(train["bug_id"]) & set(test["bug_id"]):
        raise ValueError("Train and test bug IDs overlap.")
    if train["developer_id"].nunique() < 2:
        raise ValueError("At least two training developers are required.")
    return train, test


def train_baselines(
    processed_dir: str | Path = "data/processed",
    models_dir: str | Path = "models",
) -> tuple[pd.DataFrame, dict]:
    """Fit TF-IDF on training text only, then evaluate three classifiers."""
    processed_dir = Path(processed_dir)
    models_dir = Path(models_dir)
    train, test = _read_split(processed_dir)
    y_train = train["developer_id"].astype(str).to_numpy()
    y_test = test["developer_id"].astype(str).to_numpy()

    vectorizer = TfidfVectorizer(
        lowercase=False,
        ngram_range=(1, 2),
        min_df=1,
        max_features=30_000,
        sublinear_tf=True,
    )
    train_documents = _bug_documents(train)
    test_documents = _bug_documents(test)
    start = time.perf_counter()
    x_train = vectorizer.fit_transform(train_documents)
    tfidf_fit_seconds = time.perf_counter() - start
    x_test = vectorizer.transform(test_documents)
    models = {
        "logistic_regression": LogisticRegression(
            class_weight="balanced",
            max_iter=2000,
            random_state=42,
        ),
        "linear_svm": LinearSVC(
            class_weight="balanced",
            dual="auto",
            max_iter=5000,
            random_state=42,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=100,
            max_depth=30,
            min_samples_leaf=2,
            class_weight="balanced_subsample",
            max_features="sqrt",
            n_jobs=1,
            random_state=42,
        ),
    }

    models_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    vectorizer_path = models_dir / "jdt_tfidf_vectorizer.joblib"
    joblib.dump(vectorizer, vectorizer_path)
    metric_rows = []
    prediction_rows = []
    fitted_models = {}
    for name, estimator in models.items():
        fit_start = time.perf_counter()
        estimator.fit(x_train, y_train)
        fit_seconds = time.perf_counter() - fit_start
        predict_start = time.perf_counter()
        if name == "linear_svm":
            scores = estimator.decision_function(x_test)
            if scores.ndim == 1:
                scores = np.column_stack([-scores, scores])
        else:
            scores = estimator.predict_proba(x_test)
        prediction_seconds = time.perf_counter() - predict_start
        metrics, rankings = evaluate_scores(y_test, scores, estimator.classes_)
        metrics.update({
            "model": name,
            "train_rows": len(train),
            "train_developer_classes": int(train["developer_id"].nunique()),
            "test_developer_classes": int(test["developer_id"].nunique()),
            "tfidf_features": int(x_train.shape[1]),
            "tfidf_fit_seconds": tfidf_fit_seconds,
            "training_seconds": fit_seconds,
            "prediction_seconds_per_bug": prediction_seconds / len(test),
        })
        metric_rows.append(metrics)
        fitted_models[name] = estimator
        model_path = models_dir / f"jdt_baseline_{name}.joblib"
        joblib.dump(estimator, model_path)
        for row_index, ranked in enumerate(rankings):
            prediction_rows.append({
                "model": name,
                "bug_id": int(test.iloc[row_index]["bug_id"]),
                "actual_developer_id": y_test[row_index],
                "predicted_top1_developer_id": ranked[0],
                "actual_developer_seen_in_training": y_test[row_index] in estimator.classes_,
                "top5_developer_ids": json.dumps(ranked[:5], ensure_ascii=False),
            })

    results = pd.DataFrame(metric_rows)
    ordered_columns = [
        "model",
        "train_rows",
        "train_developer_classes",
        "test_rows",
        "test_developer_classes",
        "test_rows_with_developer_seen_in_training",
        "test_rows_with_unseen_developer",
        "classification_precision_micro",
        "classification_recall_micro",
        "classification_f1_micro",
        "classification_precision_macro",
        "classification_recall_macro",
        "classification_f1_macro",
        "classification_precision_weighted",
        "classification_recall_weighted",
        "classification_f1_weighted",
        "top1_accuracy",
        "top3_accuracy",
        "top5_accuracy",
        "precision_at_1",
        "recall_at_1",
        "precision_at_3",
        "recall_at_3",
        "precision_at_5",
        "recall_at_5",
        "mean_reciprocal_rank",
        "tfidf_features",
        "tfidf_fit_seconds",
        "training_seconds",
        "prediction_seconds_per_bug",
    ]
    results = results[ordered_columns]
    results_path = processed_dir / "jdt_baseline_model_comparison.csv"
    results.to_csv(results_path, index=False, encoding="utf-8")
    predictions_path = processed_dir / "jdt_baseline_test_predictions.csv"
    pd.DataFrame(prediction_rows).to_csv(predictions_path, index=False, encoding="utf-8")
    metadata = {
        "dataset": "Member 1 JDT known_entry only",
        "train_rows": len(train),
        "test_rows": len(test),
        "train_classes": int(train["developer_id"].nunique()),
        "test_classes": int(test["developer_id"].nunique()),
        "features": ["title", "description"],
        "tfidf_fit_rows": len(train),
        "tfidf_vocabulary_size": len(vectorizer.vocabulary_),
        "tfidf_fit_seconds": tfidf_fit_seconds,
        "model_artifacts": {
            name: str(models_dir / f"jdt_baseline_{name}.joblib")
            for name in fitted_models
        },
        "vectorizer_artifact": str(vectorizer_path),
        "comparison_csv": str(results_path),
        "test_predictions_csv": str(predictions_path),
        "evaluation_population": "All chronological test rows; unseen developers count as misses.",
        "ranking_tie_break": "Developer ID ascending after equal model scores.",
        "provisional_assignments_used_as_targets": False,
        "full_dataset_profile_or_expertise_used_as_features": False,
    }
    metadata_path = processed_dir / "jdt_baseline_model_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return results, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--models-dir", default="models")
    args = parser.parse_args()
    results, metadata = train_baselines(args.processed_dir, args.models_dir)
    print(results.to_string(index=False))
    print(f"Saved model artifacts under {metadata['vectorizer_artifact']}")


if __name__ == "__main__":
    main()
