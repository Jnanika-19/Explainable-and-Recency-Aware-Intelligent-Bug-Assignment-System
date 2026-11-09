"""Tune and evaluate combined text, metadata, expertise, and recency rankers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import LinearSVC

from ml_model.evaluate_jdt_phase3 import evaluate_ranked_cohort
from ml_model.generate_jdt_phase3_features import (
    _make_labeled_candidate_dataset,
)
from ml_model.jdt_dataset import (
    chronological_split,
)
from ml_model.jdt_recommendation import (
    FEATURE_COLUMNS,
    build_temporal_candidate_features,
)
from ml_model.train_jdt_baselines import _bug_documents


MODEL_CANDIDATES = ("combined_linear_svm", "combined_logistic_regression")
TUNING_C_VALUES = (0.1, 1.0, 10.0)
BUG_METADATA_COLUMNS = ("product", "component", "severity", "priority")
TEXT_VECTOR_LIMIT = 15_000
TUNING_TEST_FRACTION = 0.2
RANDOM_STATE = 42


def _read_split(processed_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_path = processed_dir / "jdt_known_entry_train.csv"
    test_path = processed_dir / "jdt_known_entry_test.csv"
    for path in (train_path, test_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required chronological split is missing: {path}")
    train = pd.read_csv(train_path, keep_default_na=False)
    test = pd.read_csv(test_path, keep_default_na=False)
    for label, frame in (("training", train), ("evaluation", test)):
        if frame.empty or not set(frame["label_type"]).issubset({"known_entry"}):
            raise ValueError(f"{label.title()} split must contain verified known_entry rows.")
        if frame["bug_id"].duplicated().any():
            raise ValueError(f"{label.title()} split contains duplicate bug IDs.")
        for column in ("created_at", "assignment_time"):
            frame[column] = pd.to_datetime(frame[column], utc=True, errors="coerce")
            if frame[column].isna().any():
                raise ValueError(f"{label.title()} split has invalid {column} timestamps.")
    if set(train["bug_id"]) & set(test["bug_id"]):
        raise ValueError("Training and evaluation bug IDs overlap.")
    cutoff = test["created_at"].min()
    if not (train["created_at"] < cutoff).all():
        raise ValueError("Training bug creation overlaps the chronological evaluation split.")
    if not (train["assignment_time"] < cutoff).all():
        raise ValueError("Training contains assignment labels unavailable at test start.")
    if not (test["assignment_time"] >= test["created_at"]).all():
        raise ValueError("An evaluation assignment event predates its prediction.")
    return train, test


def _read_candidate_features(path: Path) -> pd.DataFrame:
    columns = [
        "bug_id",
        "candidate_developer_id",
        "target_developer_id",
        "is_ground_truth_candidate",
        *FEATURE_COLUMNS,
    ]
    if not path.is_file():
        raise FileNotFoundError(
            f"Phase 3 candidate features are missing: {path}. "
            "Run ml_model.generate_jdt_phase3_features first."
        )
    frame = pd.read_csv(
        path,
        usecols=columns,
        keep_default_na=False,
        dtype={
            "candidate_developer_id": "string",
            "target_developer_id": "string",
            "is_ground_truth_candidate": "string",
        },
    )
    frame["bug_id"] = pd.to_numeric(frame["bug_id"], errors="raise").astype("int64")
    frame["is_ground_truth_candidate"] = frame[
        "is_ground_truth_candidate"
    ].str.casefold().eq("true")
    for column in FEATURE_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame[["candidate_developer_id", "target_developer_id"]].isna().any().any():
        raise ValueError(f"Candidate feature identifiers are missing in {path.name}.")
    if frame.duplicated(["bug_id", "candidate_developer_id"]).any():
        raise ValueError(f"Duplicate bug/candidate pairs in {path.name}.")
    target_agreement = (
        frame["candidate_developer_id"].astype(str)
        == frame["target_developer_id"].astype(str)
    )
    if not np.array_equal(
        target_agreement.to_numpy(dtype=bool),
        frame["is_ground_truth_candidate"].to_numpy(dtype=bool),
    ):
        raise ValueError(f"Candidate labels do not match target IDs in {path.name}.")
    return frame


def _bug_inputs(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"bug_id", "title", "description", *BUG_METADATA_COLUMNS}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Bug records are missing model inputs: {sorted(missing)}")
    bugs = frame[["bug_id", "title", "description", *BUG_METADATA_COLUMNS]].copy()
    if bugs["bug_id"].duplicated().any():
        raise ValueError("Bug metadata contains duplicate bug IDs.")
    for column in ("title", "description", *BUG_METADATA_COLUMNS):
        bugs[column] = bugs[column].fillna("").astype(str)
    return bugs.reset_index(drop=True)


def _numeric_input(candidate_rows: pd.DataFrame) -> pd.DataFrame:
    numeric = candidate_rows[list(FEATURE_COLUMNS)].apply(pd.to_numeric, errors="coerce")
    elapsed_columns = ("days_since_last_activity", "days_since_last_component")
    missing_indicators = pd.DataFrame(
        {
            f"{column}_missing": numeric[column].isna().astype("float32")
            for column in elapsed_columns
        },
        index=numeric.index,
    )
    numeric = numeric.fillna(0.0).astype("float32")
    return pd.concat([numeric, missing_indicators], axis=1)


def _fit_transformers(
    bug_records: pd.DataFrame,
    candidate_rows: pd.DataFrame,
) -> dict[str, Any]:
    title_vectorizer = TfidfVectorizer(
        lowercase=False,
        ngram_range=(1, 2),
        max_features=TEXT_VECTOR_LIMIT,
        sublinear_tf=True,
        dtype=np.float32,
    )
    description_vectorizer = TfidfVectorizer(
        lowercase=False,
        ngram_range=(1, 2),
        max_features=TEXT_VECTOR_LIMIT,
        sublinear_tf=True,
        dtype=np.float32,
    )
    title_vectorizer.fit(bug_records["title"].tolist())
    description_documents = bug_records["description"].replace("", " ").tolist()
    description_vectorizer.fit(description_documents)

    metadata_encoder = OneHotEncoder(
        handle_unknown="ignore",
        sparse_output=True,
        dtype=np.float32,
    )
    metadata_encoder.fit(bug_records[list(BUG_METADATA_COLUMNS)])
    numeric_scaler = StandardScaler()
    numeric_scaler.fit(_numeric_input(candidate_rows))
    return {
        "title_vectorizer": title_vectorizer,
        "description_vectorizer": description_vectorizer,
        "metadata_encoder": metadata_encoder,
        "numeric_scaler": numeric_scaler,
        "numeric_input_columns": list(_numeric_input(candidate_rows).columns),
    }


def _make_matrix(
    bug_records: pd.DataFrame,
    candidate_rows: pd.DataFrame,
    transformers: dict[str, Any],
    *,
    fit: bool,
) -> tuple[sparse.csr_matrix, dict[str, Any]]:
    bug_records = _bug_inputs(bug_records)
    bug_positions = {
        int(bug_id): index for index, bug_id in enumerate(bug_records["bug_id"])
    }
    try:
        row_positions = np.asarray(
            [bug_positions[int(value)] for value in candidate_rows["bug_id"]],
            dtype=np.int64,
        )
    except KeyError as error:
        raise ValueError(f"Candidate rows refer to unknown bug ID {error.args[0]}.") from error

    if fit:
        transformers = _fit_transformers(bug_records, candidate_rows)
    title_matrix = transformers["title_vectorizer"].transform(
        bug_records["title"].tolist()
    )
    description_matrix = transformers["description_vectorizer"].transform(
        bug_records["description"].replace("", " ").tolist()
    )
    metadata_matrix = transformers["metadata_encoder"].transform(
        bug_records[list(BUG_METADATA_COLUMNS)]
    )
    numeric = _numeric_input(candidate_rows)
    expected_columns = transformers["numeric_input_columns"]
    if list(numeric.columns) != expected_columns:
        raise ValueError("Numeric model feature columns differ from the fitted training schema.")
    numeric_matrix = transformers["numeric_scaler"].transform(numeric).astype(np.float32)
    matrix = sparse.hstack(
        [
            title_matrix[row_positions],
            description_matrix[row_positions],
            metadata_matrix[row_positions],
            sparse.csr_matrix(numeric_matrix),
        ],
        format="csr",
        dtype=np.float32,
    )
    if matrix.shape[0] != len(candidate_rows):
        raise AssertionError("Candidate feature matrix row count is inconsistent.")
    return matrix, transformers


def _binary_target(candidate_rows: pd.DataFrame) -> np.ndarray:
    target = candidate_rows["is_ground_truth_candidate"].to_numpy(dtype=bool)
    if not target.any():
        raise ValueError("Candidate training matrix has no positive candidate labels.")
    return target.astype(np.int8)


def _candidate_model(name: str, c_value: float) -> Any:
    if name == "combined_linear_svm":
        return LinearSVC(
            C=c_value,
            class_weight="balanced",
            dual="auto",
            max_iter=5000,
            random_state=RANDOM_STATE,
        )
    if name == "combined_logistic_regression":
        return LogisticRegression(
            C=c_value,
            class_weight="balanced",
            solver="liblinear",
            max_iter=1500,
            random_state=RANDOM_STATE,
        )
    raise ValueError(f"Unsupported candidate model: {name}")


def _ranking_outputs(
    candidate_rows: pd.DataFrame,
    scores: np.ndarray,
) -> tuple[dict[int, list[str]], dict[int, str]]:
    if len(candidate_rows) != len(scores):
        raise ValueError("There must be one model score per bug-candidate pair.")
    scored = candidate_rows[[
        "bug_id",
        "candidate_developer_id",
        "target_developer_id",
    ]].copy()
    scored["score"] = scores
    rankings: dict[int, list[str]] = {}
    actual: dict[int, str] = {}
    for bug_id, group in scored.groupby("bug_id", sort=False):
        targets = group["target_developer_id"].astype(str).unique()
        if len(targets) != 1:
            raise ValueError(f"Bug {bug_id} has inconsistent ground-truth labels.")
        group = group.sort_values(
            ["score", "candidate_developer_id"],
            ascending=[False, True],
            kind="stable",
        )
        rankings[int(bug_id)] = group["candidate_developer_id"].astype(str).tolist()
        actual[int(bug_id)] = str(targets[0])
    return rankings, actual


def _score_cohorts(
    rankings: dict[int, list[str]],
    actual: dict[int, str],
    candidate_developers: set[str],
    name: str,
) -> list[dict[str, Any]]:
    seen_bugs = {
        bug_id for bug_id, developer_id in actual.items()
        if developer_id in candidate_developers
    }
    cohorts = {
        "all_test_records": list(actual),
        "seen_developer_targets": sorted(seen_bugs),
        "unseen_developer_targets": sorted(set(actual) - seen_bugs),
    }
    rows = []
    for cohort_name, bug_ids in cohorts.items():
        if not bug_ids:
            continue
        metrics = evaluate_ranked_cohort(
            [actual[bug_id] for bug_id in bug_ids],
            [rankings[bug_id] for bug_id in bug_ids],
        )
        metrics.update({
            "model": name,
            "cohort": cohort_name,
            "candidate_developers": len(candidate_developers),
            "seen_target_records": len(seen_bugs),
            "unseen_target_records": len(actual) - len(seen_bugs),
        })
        rows.append(metrics)
    return rows


def _tune_on_training(
    train: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, float], dict[str, Any]]:
    inner_train, inner_validation, cutoff, excluded = chronological_split(
        train, test_fraction=TUNING_TEST_FRACTION
    )
    candidates = sorted(inner_train["developer_id"].astype(str).unique())
    if len(candidates) < 2:
        raise ValueError("Inner chronological training split has fewer than two developers.")

    similarity_vectorizer = TfidfVectorizer(
        lowercase=False,
        ngram_range=(1, 2),
        max_features=30_000,
        sublinear_tf=True,
    )
    similarity_vectorizer.fit(_bug_documents(inner_train))
    train_features = build_temporal_candidate_features(
        inner_train,
        inner_train,
        candidates,
        similarity_vectorizer,
    )
    validation_features = build_temporal_candidate_features(
        inner_train,
        inner_validation,
        candidates,
        similarity_vectorizer,
    )
    train_rows = _make_labeled_candidate_dataset(train_features, inner_train)
    validation_rows = _make_labeled_candidate_dataset(
        validation_features, inner_validation
    )
    train_matrix, transformers = _make_matrix(
        inner_train, train_rows, {}, fit=True
    )
    validation_matrix, _ = _make_matrix(
        inner_validation, validation_rows, transformers, fit=False
    )
    y_train = _binary_target(train_rows)
    validation_actual = {
        int(row["bug_id"]): str(row["developer_id"])
        for row in inner_validation.to_dict(orient="records")
    }
    candidate_set = set(candidates)
    validation_seen = {
        bug_id for bug_id, developer_id in validation_actual.items()
        if developer_id in candidate_set
    }

    trial_rows: list[dict[str, Any]] = []
    selected: dict[str, float] = {}
    for name in MODEL_CANDIDATES:
        best_key: tuple[float, float, float] | None = None
        for c_value in TUNING_C_VALUES:
            estimator = _candidate_model(name, c_value)
            estimator.fit(train_matrix, y_train)
            scores = estimator.decision_function(validation_matrix)
            rankings, actual = _ranking_outputs(validation_rows, np.asarray(scores).ravel())
            metrics = evaluate_ranked_cohort(
                [actual[bug_id] for bug_id in actual],
                [rankings[bug_id] for bug_id in actual],
            )
            key = (
                float(metrics["mean_reciprocal_rank"]),
                float(metrics["top5_accuracy"]),
                -c_value,
            )
            trial_rows.append({
                "model": name,
                "C": c_value,
                "selection_metric": "validation_mrr",
                "validation_mrr": metrics["mean_reciprocal_rank"],
                "validation_top1": metrics["top1_accuracy"],
                "validation_top3": metrics["top3_accuracy"],
                "validation_top5": metrics["top5_accuracy"],
                "validation_rows": len(inner_validation),
                "validation_seen_target_rows": len(validation_seen),
                "validation_unseen_target_rows": len(inner_validation) - len(validation_seen),
                "candidate_developers": len(candidates),
                "training_candidate_rows": len(train_rows),
            })
            if best_key is None or key > best_key:
                best_key = key
                selected[name] = c_value

    metadata = {
        "inner_training_bugs": len(inner_train),
        "inner_validation_bugs": len(inner_validation),
        "inner_excluded_future_label_bugs": len(excluded),
        "inner_cutoff_utc": cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inner_training_candidate_developers": len(candidates),
        "vectorizer_fit_partition": "inner chronological training bugs only",
        "feature_history_partition": "inner chronological training assignments only",
        "validation_labels_used_for_tuning_only": True,
        "outer_test_used_for_tuning": False,
        "selection_metric": "validation mean reciprocal rank; top-5 and smaller C break ties",
    }
    return pd.DataFrame(trial_rows), selected, metadata


def train_phase4(
    processed_dir: str | Path = "data/processed",
    models_dir: str | Path = "models",
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Tune on a chronological training-only validation split; test once."""
    processed_dir = Path(processed_dir)
    models_dir = Path(models_dir)
    phase4_model_dir = models_dir / "jdt_phase4"
    phase4_model_dir.mkdir(parents=True, exist_ok=True)
    train, test = _read_split(processed_dir)
    train_candidates = _read_candidate_features(
        processed_dir / "jdt_phase3_feature_train.csv"
    )
    test_candidates = _read_candidate_features(
        processed_dir / "jdt_phase3_feature_evaluation.csv"
    )
    expected_train_developers = set(train["developer_id"].astype(str))
    if set(train_candidates["bug_id"]) != set(train["bug_id"]):
        raise ValueError("Phase 3 training candidates do not match the Phase 2 training split.")
    if set(test_candidates["bug_id"]) != set(test["bug_id"]):
        raise ValueError("Phase 3 evaluation candidates do not match the Phase 2 test split.")
    if set(train_candidates["candidate_developer_id"]) != expected_train_developers:
        raise ValueError("Training candidate universe does not match training developer classes.")
    if set(test_candidates["candidate_developer_id"]) != expected_train_developers:
        raise ValueError("Evaluation candidate universe differs from training developers.")

    tuning_results, selected_c, tuning_metadata = _tune_on_training(train)
    tuning_path = processed_dir / "jdt_phase4_hyperparameter_tuning.csv"
    tuning_results.to_csv(tuning_path, index=False, encoding="utf-8")

    baseline_vectorizer_path = models_dir / "jdt_tfidf_vectorizer.joblib"
    baseline_model_path = models_dir / "jdt_baseline_linear_svm.joblib"
    for path in (baseline_vectorizer_path, baseline_model_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required Phase 2 baseline artifact is missing: {path}")
    baseline_vectorizer = joblib.load(baseline_vectorizer_path)
    baseline_model = joblib.load(baseline_model_path)
    if set(map(str, baseline_model.classes_)) != expected_train_developers:
        raise ValueError("Phase 2 baseline classes do not match the training partition.")

    train_matrix, transformers = _make_matrix(
        train, train_candidates, {}, fit=True
    )
    test_matrix, _ = _make_matrix(
        test, test_candidates, transformers, fit=False
    )
    y_train = _binary_target(train_candidates)
    actual = {
        int(row["bug_id"]): str(row["developer_id"])
        for row in test.to_dict(orient="records")
    }
    candidate_developers = sorted(expected_train_developers)
    metric_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []

    baseline_scores = baseline_model.decision_function(
        baseline_vectorizer.transform(_bug_documents(test))
    )
    if np.ndim(baseline_scores) == 1:
        baseline_scores = np.column_stack([-baseline_scores, baseline_scores])
    baseline_rankings = {}
    baseline_classes = [str(value) for value in baseline_model.classes_]
    for row_index, row in enumerate(test.to_dict(orient="records")):
        scores_by_developer = {
            developer_id: float(baseline_scores[row_index, class_index])
            for class_index, developer_id in enumerate(baseline_classes)
        }
        baseline_rankings[int(row["bug_id"])] = sorted(
            baseline_classes,
            key=lambda developer_id: (-scores_by_developer[developer_id], developer_id),
        )
    metric_rows.extend(_score_cohorts(
        baseline_rankings, actual, expected_train_developers, "phase2_linear_svm_baseline"
    ))

    fitted_models: dict[str, Any] = {}
    total_features = int(train_matrix.shape[1])
    for name in MODEL_CANDIDATES:
        estimator = _candidate_model(name, selected_c[name])
        estimator.fit(train_matrix, y_train)
        scores = np.asarray(estimator.decision_function(test_matrix)).ravel()
        rankings, ranked_actual = _ranking_outputs(test_candidates, scores)
        if ranked_actual != actual:
            raise AssertionError("Candidate table evaluation targets differ from the test split.")
        model_metric_rows = _score_cohorts(
            rankings, actual, expected_train_developers, name
        )
        metric_rows.extend(model_metric_rows)
        fitted_models[name] = estimator
        artifact = {
            "model_name": name,
            "classifier": estimator,
            "transformers": transformers,
            "numeric_feature_columns": list(FEATURE_COLUMNS),
            "bug_metadata_columns": list(BUG_METADATA_COLUMNS),
            "candidate_developer_ids": candidate_developers,
            "selected_C": selected_c[name],
            "class_weight": "balanced",
            "target_or_developer_ids_used_as_predictive_inputs": False,
            "feature_matrix_columns": total_features,
        }
        joblib.dump(artifact, phase4_model_dir / f"{name}.joblib")
        for bug_id, ranked_developers in rankings.items():
            test_prediction = test.loc[test["bug_id"].eq(bug_id)].iloc[0]
            row_scores = test_candidates.loc[test_candidates["bug_id"].eq(bug_id)].copy()
            score_by_candidate = {
                str(candidate): float(score)
                for candidate, score in zip(row_scores["candidate_developer_id"], scores[
                    test_candidates["bug_id"].eq(bug_id).to_numpy()
                ], strict=True)
            }
            for rank, developer_id in enumerate(ranked_developers[:5], start=1):
                feature_row = row_scores.loc[
                    row_scores["candidate_developer_id"].eq(developer_id)
                ].iloc[0]
                prediction_rows.append({
                    "model": name,
                    "bug_id": bug_id,
                    "prediction_timestamp_utc": test_prediction["created_at"].strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    "rank": rank,
                    "developer_id": developer_id,
                    "score": score_by_candidate[developer_id],
                    "actual_developer_id_for_evaluation": actual[bug_id],
                    "actual_developer_seen_in_training": (
                        actual[bug_id] in expected_train_developers
                    ),
                    **{column: feature_row[column] for column in FEATURE_COLUMNS},
                })

    metrics_frame = pd.DataFrame(metric_rows)
    metrics_path = processed_dir / "jdt_phase4_model_comparison.csv"
    metrics_frame.to_csv(metrics_path, index=False, encoding="utf-8")
    predictions_path = processed_dir / "jdt_phase4_test_predictions.csv"
    pd.DataFrame(prediction_rows).to_csv(
        predictions_path, index=False, encoding="utf-8"
    )
    bundle = {
        "models": fitted_models,
        "transformers": transformers,
        "candidate_developer_ids": candidate_developers,
        "numeric_feature_columns": list(FEATURE_COLUMNS),
        "bug_metadata_columns": list(BUG_METADATA_COLUMNS),
        "selected_C": selected_c,
    }
    bundle_path = phase4_model_dir / "jdt_phase4_combined_models.joblib"
    joblib.dump(bundle, bundle_path)

    metadata = {
        "dataset": "verified JDT known_entry only",
        "training_bugs": len(train),
        "test_bugs": len(test),
        "training_candidate_rows": len(train_candidates),
        "test_candidate_rows": len(test_candidates),
        "candidate_developers": len(candidate_developers),
        "seen_test_targets": sum(value in expected_train_developers for value in actual.values()),
        "unseen_test_targets": sum(value not in expected_train_developers for value in actual.values()),
        "training_positive_candidate_rows": int(y_train.sum()),
        "bug_text_features": {
            "title": "training-only unigram/bigram TF-IDF; max 15000 features",
            "description": "training-only unigram/bigram TF-IDF; max 15000 features",
        },
        "bug_metadata_features": list(BUG_METADATA_COLUMNS),
        "developer_features": list(FEATURE_COLUMNS),
        "candidate_developer_id_used_as_predictive_feature": False,
        "target_developer_id_used_as_predictive_feature": False,
        "class_imbalance": "class_weight=balanced; no oversampling",
        "test_data_used_for_tuning": False,
        "selected_hyperparameters": selected_c,
        "tuning": tuning_metadata,
        "tuning_C_values": list(TUNING_C_VALUES),
        "selection_metric": "inner chronological validation MRR",
        "phase2_baseline_model_unchanged": True,
        "outputs": {
            "tuning": str(tuning_path),
            "evaluation": str(metrics_path),
            "predictions": str(predictions_path),
            "model_bundle": str(bundle_path),
        },
    }
    metadata_path = processed_dir / "jdt_phase4_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return tuning_results, metrics_frame, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--models-dir", default="models")
    args = parser.parse_args()
    _, metrics, metadata = train_phase4(args.processed_dir, args.models_dir)
    print(metrics.to_string(index=False))
    print(json.dumps(metadata, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
