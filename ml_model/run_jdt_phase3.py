"""Evaluate temporal expertise reranking against the saved Phase 2 Linear SVM."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from ml_model.evaluate_jdt_phase3 import evaluate_ranked_cohort
from ml_model.jdt_recommendation import (
    FEATURE_COLUMNS,
    RERANK_WEIGHTS,
    build_temporal_candidate_features,
    rank_candidate_features,
)


METHODS = (
    "linear_svm_baseline",
    "component_expertise",
    "similar_bug_history",
    "temporal_expertise",
    "svm_temporal_combined",
)


def _read_frame(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Required Phase 2 dataset is missing: {path}")
    frame = pd.read_csv(path, keep_default_na=False)
    for column in ("created_at", "assignment_time"):
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], utc=True, errors="coerce")
            if frame[column].isna().any():
                raise ValueError(f"{path.name} has an invalid value in {column}.")
    return frame


def _score_for_bug(
    bug: pd.Series,
    vectorizer: Any,
    classifier: Any,
) -> dict[str, float]:
    document = f"{bug['title']} {bug['description']}".strip()
    matrix = vectorizer.transform([document])
    scores = classifier.decision_function(matrix)
    if np.ndim(scores) == 1:
        scores = np.column_stack([-scores, scores])
    row = np.asarray(scores)[0]
    return {
        str(developer_id): float(row[index])
        for index, developer_id in enumerate(classifier.classes_)
    }


def run_phase3(
    processed_dir: str | Path = "data/processed",
    model_dir: str | Path = "models",
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    processed_dir = Path(processed_dir)
    model_dir = Path(model_dir)
    train = _read_frame(processed_dir / "jdt_known_entry_train.csv")
    test = _read_frame(processed_dir / "jdt_known_entry_test.csv")
    vectorizer_path = model_dir / "jdt_tfidf_vectorizer.joblib"
    svm_path = model_dir / "jdt_baseline_linear_svm.joblib"
    for path in (vectorizer_path, svm_path):
        if not path.is_file():
            raise FileNotFoundError(
                f"Required Phase 2 artifact is missing: {path}. "
                "Run the Phase 2 training command first."
            )
    vectorizer = joblib.load(vectorizer_path)
    svm_model = joblib.load(svm_path)
    candidates = [str(value) for value in svm_model.classes_]
    train_developers = set(train["developer_id"].astype(str))
    if train_developers != set(candidates):
        raise ValueError("Linear SVM classes do not match the saved training split.")
    if not set(test["label_type"]).issubset({"known_entry"}):
        raise ValueError("Phase 3 evaluation only accepts verified known-entry test rows.")

    candidate_features = build_temporal_candidate_features(
        train,
        test,
        candidates,
        vectorizer,
    )
    expected_pairs = len(test) * len(candidates)
    if len(candidate_features) != expected_pairs:
        raise AssertionError(
            f"Expected {expected_pairs} test-candidate rows, got {len(candidate_features)}."
        )
    candidate_features_path = processed_dir / "jdt_phase3_candidate_features.csv"
    candidate_features.to_csv(candidate_features_path, index=False, encoding="utf-8")

    test_by_bug = {
        int(row["bug_id"]): row for row in test.to_dict(orient="records")
    }
    per_bug_rankings: dict[str, dict[int, list[str]]] = {name: {} for name in METHODS}
    recommendation_rows: list[dict[str, object]] = []
    for bug_id, group in candidate_features.groupby("prediction_bug_id", sort=False):
        test_row = test_by_bug[int(bug_id)]
        svm_scores = _score_for_bug(pd.Series(test_row), vectorizer, svm_model)
        ranked_methods = rank_candidate_features(group, svm_scores)
        for method in METHODS:
            ranked = ranked_methods[method]
            per_bug_rankings[method][int(bug_id)] = ranked[
                "candidate_developer_id"
            ].astype(str).tolist()
        combined = ranked_methods["svm_temporal_combined"].head(5)
        for _, row in combined.iterrows():
            recommendation_rows.append({
                "bug_id": int(bug_id),
                "created_at": test_row["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "actual_developer_id_for_evaluation": str(test_row["developer_id"]),
                "actual_developer_seen_in_training": (
                    str(test_row["developer_id"]) in train_developers
                ),
                "rank": int(row["rank"]),
                "developer_id": str(row["candidate_developer_id"]),
                "recommendation_score": float(row["recommendation_score"]),
                "linear_svm_score": float(row["svm_score"]),
                **{column: row[column] for column in FEATURE_COLUMNS},
                "reasons": json.dumps(row["reasons"], ensure_ascii=False),
            })

    evaluation_rows: list[dict[str, object]] = []
    actual_by_bug = {
        int(row["bug_id"]): str(row["developer_id"])
        for row in test.to_dict(orient="records")
    }
    seen_bugs = {
        bug_id for bug_id, developer_id in actual_by_bug.items()
        if developer_id in train_developers
    }
    unseen_bugs = set(actual_by_bug) - seen_bugs
    cohorts = {
        "all_test_records": list(actual_by_bug),
        "seen_developer_targets": sorted(seen_bugs),
        "unseen_developer_targets": sorted(unseen_bugs),
    }
    for method in METHODS:
        for cohort_name, bug_ids in cohorts.items():
            rows = sorted(bug_ids)
            metrics = evaluate_ranked_cohort(
                [actual_by_bug[bug_id] for bug_id in rows],
                [per_bug_rankings[method][bug_id] for bug_id in rows],
            )
            metrics.update({
                "method": method,
                "cohort": cohort_name,
                "candidate_developer_count": len(candidates),
                "unseen_target_rows": sum(
                    actual_by_bug[bug_id] not in train_developers for bug_id in rows
                ),
            })
            evaluation_rows.append(metrics)

    metrics_frame = pd.DataFrame(evaluation_rows)
    metrics_path = processed_dir / "jdt_phase3_evaluation.csv"
    metrics_frame.to_csv(metrics_path, index=False, encoding="utf-8")
    recommendations = pd.DataFrame(recommendation_rows)
    recommendations_path = processed_dir / "jdt_phase3_test_recommendations.csv"
    recommendations.to_csv(recommendations_path, index=False, encoding="utf-8")

    phase2_results_path = processed_dir / "jdt_baseline_model_comparison.csv"
    phase2_results = pd.read_csv(phase2_results_path)
    phase2_svm = phase2_results.loc[phase2_results["model"].eq("linear_svm")]
    phase2_svm_all = metrics_frame.loc[
        metrics_frame["method"].eq("linear_svm_baseline")
        & metrics_frame["cohort"].eq("all_test_records")
    ].iloc[0]
    if phase2_svm.empty or len(phase2_svm) != 1:
        raise ValueError("Cannot find exactly one Phase 2 Linear SVM result for comparison.")
    phase2_row = phase2_svm.iloc[0]
    if not np.isclose(float(phase2_row["top5_accuracy"]), float(phase2_svm_all["top5_accuracy"])):
        raise AssertionError("Recomputed Phase 2 SVM Top-5 differs from saved Phase 2 results.")
    if not np.isclose(float(phase2_row["mean_reciprocal_rank"]), float(phase2_svm_all["mean_reciprocal_rank"])):
        raise AssertionError("Recomputed Phase 2 SVM MRR differs from saved Phase 2 results.")

    phase3_bundle = {
        "baseline_name": "linear_svm_baseline",
        "vectorizer": vectorizer,
        "classifier": svm_model,
        "candidate_developer_ids": candidates,
        "recent_window_days": 365,
        "similarity_threshold": 0.2,
        "score_weights": RERANK_WEIGHTS,
        "training_scope": "Linear SVM and TF-IDF fit only on Phase 2 training data.",
        "phase3_evaluation_rows": len(test),
    }
    bundle_path = model_dir / "jdt_phase3"
    bundle_path.mkdir(parents=True, exist_ok=True)
    artifact_path = bundle_path / "jdt_phase3_ranker.joblib"
    joblib.dump(phase3_bundle, artifact_path)
    metadata = {
        "test_rows": len(test),
        "training_rows": len(train),
        "candidate_developers": len(candidates),
        "seen_developer_target_rows": len(seen_bugs),
        "unseen_developer_target_rows": len(unseen_bugs),
        "candidate_feature_rows": len(candidate_features),
        "methods": list(METHODS),
        "evaluation_csv": str(metrics_path),
        "candidate_features_csv": str(candidate_features_path),
        "recommendations_csv": str(recommendations_path),
        "ranker_artifact": str(artifact_path),
        "phase2_linear_svm_baseline_unchanged": True,
        "provisional_targets_used": False,
        "future_events_used": False,
        "evaluation_labels_used_as_history": False,
        "full_dataset_aggregates_used": False,
    }
    metadata_path = processed_dir / "jdt_phase3_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metrics_frame, recommendations, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--models-dir", default="models")
    args = parser.parse_args()
    metrics, _, metadata = run_phase3(args.processed_dir, args.models_dir)
    print(metrics.to_string(index=False))
    print(f"Saved Phase 3 ranker to {metadata['ranker_artifact']}")


if __name__ == "__main__":
    main()
