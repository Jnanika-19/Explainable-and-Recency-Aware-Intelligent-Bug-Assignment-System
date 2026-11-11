"""Reproduce the final chronological Member 2 evaluation without retraining."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from ml_model.developer_recommender import recommend_developers
from ml_model.evaluate_jdt_phase3 import evaluate_ranked_cohort
from ml_model.generate_jdt_phase3_features import _make_labeled_candidate_dataset
from ml_model.jdt_recommendation import build_temporal_candidate_features
from ml_model.train_jdt_baselines import _bug_documents
from ml_model.train_jdt_phase4 import _make_matrix, _ranking_outputs


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCORED_METRICS = (
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
    "classification_precision_micro",
    "classification_recall_micro",
    "classification_f1_micro",
)


def _read_splits(processed_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = pd.read_csv(
        processed_dir / "jdt_known_entry_train.csv",
        keep_default_na=False,
    )
    test = pd.read_csv(
        processed_dir / "jdt_known_entry_test.csv",
        keep_default_na=False,
    )
    for label, frame in (("train", train), ("test", test)):
        if frame.empty:
            raise ValueError(f"{label} split is empty.")
        if set(frame["label_type"]) != {"known_entry"}:
            raise ValueError(f"{label} split includes non-verified labels.")
        if frame["bug_id"].duplicated().any():
            raise ValueError(f"{label} split contains duplicate bug IDs.")
        for column in ("created_at", "assignment_time"):
            frame[column] = pd.to_datetime(frame[column], utc=True, errors="coerce")
            if frame[column].isna().any():
                raise ValueError(f"{label} split has invalid {column} timestamps.")
    if set(train["bug_id"]) & set(test["bug_id"]):
        raise ValueError("Train and test bug IDs overlap.")
    cutoff = test["created_at"].min()
    if not (train["created_at"] < cutoff).all():
        raise ValueError("Training creation events overlap the chronological test period.")
    if not (train["assignment_time"] < cutoff).all():
        raise ValueError("A training assignment label was not available at test start.")
    if not (test["assignment_time"] >= test["created_at"]).all():
        raise ValueError("A test assignment timestamp predates bug creation.")
    return train, test


def _rank_scores(scores: np.ndarray, developer_ids: list[str]) -> list[list[str]]:
    if scores.shape != (len(scores), len(developer_ids)):
        raise ValueError("Prediction score matrix does not match candidate developers.")
    return [
        [
            developer_ids[index]
            for index in sorted(
                range(len(developer_ids)),
                key=lambda column: (-float(row[column]), developer_ids[column]),
            )
        ]
        for row in scores
    ]


def _phase2_rankings(
    test: pd.DataFrame,
    models_dir: Path,
) -> dict[int, list[str]]:
    vectorizer = joblib.load(models_dir / "jdt_tfidf_vectorizer.joblib")
    classifier = joblib.load(models_dir / "jdt_baseline_linear_svm.joblib")
    matrix = vectorizer.transform(_bug_documents(test))
    scores = np.asarray(classifier.decision_function(matrix))
    if scores.ndim == 1:
        scores = np.column_stack([-scores, scores])
    ranked = _rank_scores(scores, [str(value) for value in classifier.classes_])
    return {
        int(bug_id): ranking
        for bug_id, ranking in zip(test["bug_id"], ranked, strict=True)
    }


def _phase4_rankings(
    train: pd.DataFrame,
    test: pd.DataFrame,
    processed_dir: Path,
    models_dir: Path,
) -> tuple[dict[int, list[str]], pd.DataFrame, dict[str, Any]]:
    model_path = models_dir / "jdt_phase4" / "combined_linear_svm.joblib"
    vectorizer_path = models_dir / "jdt_tfidf_vectorizer.joblib"
    for path in (model_path, vectorizer_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required saved Phase 4 artifact is missing: {path}")
    artifact = joblib.load(model_path)
    vectorizer = joblib.load(vectorizer_path)
    candidate_ids = [str(value) for value in artifact["candidate_developer_ids"]]
    feature_rows = build_temporal_candidate_features(
        train,
        test[["bug_id", "title", "description", "component", "created_at"]],
        candidate_ids,
        vectorizer,
    )
    candidates = _make_labeled_candidate_dataset(feature_rows, test)
    bug_records = test[[
        "bug_id",
        "title",
        "description",
        "product",
        "component",
        "severity",
        "priority",
    ]].copy()
    matrix_candidates = candidates.rename(columns={"bug_id": "bug_id"})
    matrix, _ = _make_matrix(
        bug_records,
        matrix_candidates,
        artifact["transformers"],
        fit=False,
    )
    scores = np.asarray(artifact["classifier"].decision_function(matrix)).reshape(-1)
    rankings, actual = _ranking_outputs(candidates, scores)
    expected_actual = {
        int(row["bug_id"]): str(row["developer_id"])
        for row in test.to_dict(orient="records")
    }
    if actual != expected_actual:
        raise AssertionError("Candidate features do not match test ground-truth labels.")
    predictions_path = processed_dir / "jdt_phase4_test_predictions.csv"
    saved_predictions = pd.read_csv(predictions_path, keep_default_na=False)
    saved_predictions = saved_predictions.loc[
        saved_predictions["model"].eq("combined_linear_svm")
    ]
    for bug_id, group in saved_predictions.groupby("bug_id", sort=False):
        expected_top5 = group.sort_values("rank")["developer_id"].astype(str).tolist()
        if rankings[int(bug_id)][:5] != expected_top5:
            raise AssertionError(
                f"Recomputed Phase 4 ranking differs from saved top five for bug {bug_id}."
            )
    return rankings, candidates, artifact


def _phase5_rankings(
    test: pd.DataFrame,
    candidate_count: int,
    phase4_rankings: dict[int, list[str]],
) -> tuple[dict[int, list[str]], list[float]]:
    rankings: dict[int, list[str]] = {}
    durations: list[float] = []
    for row in test.to_dict(orient="records"):
        bug_report = {
            "bug_id": int(row["bug_id"]),
            "title": row["title"],
            "description": row["description"],
            "component": row["component"],
            "severity": row["severity"],
            "priority": row["priority"],
            "product": row["product"],
            "prediction_timestamp": row["created_at"],
        }
        started = time.perf_counter()
        result = recommend_developers(bug_report, top_k=candidate_count)
        durations.append(time.perf_counter() - started)
        ranking = [
            str(item["developer_id"])
            for item in result["recommendations"]
        ]
        bug_id = int(row["bug_id"])
        if len(ranking) != candidate_count:
            raise AssertionError(f"Phase 5 returned an incomplete roster for bug {bug_id}.")
        if ranking != phase4_rankings[bug_id]:
            raise AssertionError(
                f"Phase 5 API ranking differs from Phase 4 for bug {bug_id}."
            )
        rankings[bug_id] = ranking
    return rankings, durations


def _cohort_metrics(
    name: str,
    rankings: dict[int, list[str]],
    actual: dict[int, str],
    candidates: set[str],
) -> list[dict[str, object]]:
    seen_ids = {
        bug_id for bug_id, developer_id in actual.items()
        if developer_id in candidates
    }
    cohorts = {
        "all_test_records": list(actual),
        "seen_developer_targets": sorted(seen_ids),
        "unseen_developer_targets": sorted(set(actual) - seen_ids),
    }
    rows = []
    for cohort, bug_ids in cohorts.items():
        metrics = evaluate_ranked_cohort(
            [actual[bug_id] for bug_id in bug_ids],
            [rankings[bug_id] for bug_id in bug_ids],
        )
        rows.append({
            "model": name,
            "cohort": cohort,
            "candidate_developers": len(candidates),
            "seen_target_records": len(seen_ids),
            "unseen_target_records": len(actual) - len(seen_ids),
            **metrics,
        })
    return rows


def _error_analysis(
    actual: dict[int, str],
    rankings: dict[int, list[str]],
    candidates: set[str],
) -> pd.DataFrame:
    rows = []
    for bug_id, target in actual.items():
        ranking = rankings[bug_id]
        target_rank = next(
            (index + 1 for index, value in enumerate(ranking) if value == target),
            None,
        )
        if target_rank is None:
            category = "unseen_target_outside_candidate_roster"
        elif target_rank == 1:
            category = "correct_at_rank_1"
        elif target_rank <= 5:
            category = "seen_target_in_top_5_but_not_rank_1"
        else:
            category = "seen_target_below_top_5"
        rows.append({
            "bug_id": bug_id,
            "target_developer_seen_in_training": target in candidates,
            "target_rank": target_rank,
            "top1_developer_id": ranking[0],
            "error_category": category,
        })
    return pd.DataFrame(rows)


def _verify_saved_metrics(metrics: pd.DataFrame, processed_dir: Path) -> None:
    saved = pd.read_csv(processed_dir / "jdt_phase4_model_comparison.csv")
    reference_names = {
        "phase2_linear_svm": "phase2_linear_svm_baseline",
        "phase4_combined_linear_svm": "combined_linear_svm",
        "phase5_developer_recommender": "combined_linear_svm",
    }
    for row in metrics.to_dict(orient="records"):
        reference = saved.loc[
            saved["model"].eq(reference_names[str(row["model"])])
            & saved["cohort"].eq(row["cohort"])
        ]
        if len(reference) != 1:
            raise ValueError(
                f"Saved Phase 4 metrics lack one row for {row['model']} / {row['cohort']}."
            )
        for metric in SCORED_METRICS:
            if not np.isclose(
                float(row[metric]),
                float(reference.iloc[0][metric]),
                atol=1e-12,
            ):
                raise AssertionError(
                    f"Final {metric} differs from the frozen Phase 2/4 evaluation "
                    f"for {row['model']} / {row['cohort']}."
                )


def _format_metric_table(metrics: pd.DataFrame) -> str:
    headers = [
        "Model",
        "Cohort (n)",
        "Top-1",
        "Top-3",
        "Top-5",
        "P@5",
        "R@5",
        "MRR",
        "Top-1 P/R/F1",
    ]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in metrics.to_dict(orient="records"):
        lines.append(
            "| {model} | {cohort} ({n_records}) | {top1_accuracy:.4f} | "
            "{top3_accuracy:.4f} | {top5_accuracy:.4f} | {precision_at_5:.4f} | "
            "{recall_at_5:.4f} | {mean_reciprocal_rank:.4f} | "
            "{classification_precision_micro:.4f} / "
            "{classification_recall_micro:.4f} / "
            "{classification_f1_micro:.4f} |".format(**row)
        )
    return "\n".join(lines)


def run_final_evaluation(
    processed_dir: str | Path = PROJECT_ROOT / "data" / "processed",
    models_dir: str | Path = PROJECT_ROOT / "models",
    report_path: str | Path = PROJECT_ROOT / "docs" / "member2_phase7_final_evaluation.md",
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Re-evaluate saved models and Phase 5 API on the frozen chronological split."""
    processed_dir = Path(processed_dir)
    models_dir = Path(models_dir)
    report_path = Path(report_path)
    train, test = _read_splits(processed_dir)
    phase2_rankings = _phase2_rankings(test, models_dir)
    phase4_rankings, _, artifact = _phase4_rankings(
        train,
        test,
        processed_dir,
        models_dir,
    )
    phase5_rankings, durations = _phase5_rankings(
        test,
        len(artifact["candidate_developer_ids"]),
        phase4_rankings,
    )
    actual = {
        int(row["bug_id"]): str(row["developer_id"])
        for row in test.to_dict(orient="records")
    }
    candidates = set(map(str, artifact["candidate_developer_ids"]))

    metric_rows = []
    for name, rankings in (
        ("phase2_linear_svm", phase2_rankings),
        ("phase4_combined_linear_svm", phase4_rankings),
        ("phase5_developer_recommender", phase5_rankings),
    ):
        metric_rows.extend(_cohort_metrics(name, rankings, actual, candidates))
    metrics = pd.DataFrame(metric_rows)
    _verify_saved_metrics(metrics, processed_dir)

    error_analysis = _error_analysis(actual, phase5_rankings, candidates)
    error_path = processed_dir / "jdt_phase7_error_analysis.csv"
    error_analysis.to_csv(error_path, index=False, encoding="utf-8")
    metrics_path = processed_dir / "jdt_phase7_final_model_comparison.csv"
    metrics.to_csv(metrics_path, index=False, encoding="utf-8")

    wall_seconds = float(sum(durations))
    performance = {
        "api_queries": len(durations),
        "candidate_roster_size": len(candidates),
        "total_api_seconds": wall_seconds,
        "mean_seconds_per_query": float(np.mean(durations)),
        "median_seconds_per_query": float(np.median(durations)),
        "p95_seconds_per_query": float(np.percentile(durations, 95)),
        "maximum_seconds_per_query": float(np.max(durations)),
        "first_query_seconds_includes_cached_resource_load": float(durations[0]),
    }
    performance_path = processed_dir / "jdt_phase7_performance.json"
    performance_path.write_text(
        json.dumps(performance, indent=2) + "\n",
        encoding="utf-8",
    )

    seen_count = sum(developer_id in candidates for developer_id in actual.values())
    unseen_count = len(actual) - seen_count
    missing_description = int(test["description"].fillna("").astype(str).str.strip().eq("").sum())
    missing_component = int(test["component"].fillna("").astype(str).str.strip().eq("").sum())
    error_counts = error_analysis["error_category"].value_counts().to_dict()
    report = f"""# Member 2 Phase 7: Final Chronological Evaluation

## Scope and reproducibility

This evaluation reuses the saved Phase 2 baseline, Phase 4 model, and Phase 5
public API. It does not retrain, tune, overwrite previous phase results, or
modify original CSVs. The chronological test split has {len(test)} verified
`known_entry` bugs; the training partition has {len(train)} verified bugs and
{len(candidates)} candidate developers. Training assignments are strictly
before the first test prediction timestamp. Test labels are used only for
final evaluation, never for features, model selection, or explanation history.

The evaluator independently reconstructs Phase 2 and Phase 4 rankings, checks
Phase 4 Top-5 against its frozen prediction output, then calls
`recommend_developers` on every test bug with the full roster. The Phase 5 API
rank order matched Phase 4 for all {len(test)} bugs. Its reported metrics
therefore describe the exact Phase 5 implementation, not a separately trained
model. All results are checked against the saved Phase 4 comparison before
writing these new Phase 7 outputs.

## Results

Top-K accuracy/recall is the fraction of bug targets found in the first K
positions. Precision@K is hit fraction divided by K. Top-1 micro precision,
recall, and F1 equal Top-1 accuracy for this single-target task. MRR averages
the reciprocal rank over the complete 79-candidate ranking; targets outside
the roster count as zero.

{_format_metric_table(metrics)}

### Baseline versus improved model

Across all test bugs, Phase 4 combined SVM Top-5 is
{float(metrics.loc[(metrics.model == 'phase4_combined_linear_svm') & (metrics.cohort == 'all_test_records'), 'top5_accuracy'].iloc[0]):.4f}
versus Phase 2's
{float(metrics.loc[(metrics.model == 'phase2_linear_svm') & (metrics.cohort == 'all_test_records'), 'top5_accuracy'].iloc[0]):.4f};
MRR is
{float(metrics.loc[(metrics.model == 'phase4_combined_linear_svm') & (metrics.cohort == 'all_test_records'), 'mean_reciprocal_rank'].iloc[0]):.4f}
versus
{float(metrics.loc[(metrics.model == 'phase2_linear_svm') & (metrics.cohort == 'all_test_records'), 'mean_reciprocal_rank'].iloc[0]):.4f}.
Phase 5 is the same Phase 4 ranker wrapped with validated explanations; it is
not an independent model improvement.

## Seen and unseen developer performance

There are {seen_count} seen-developer test targets and {unseen_count} targets
outside the {len(candidates)}-developer training roster. Seen-target metrics
are reported separately and must not be presented as overall performance.
Every unseen target is an unavoidable closed-roster miss for all three
systems; the overall denominator retains those rows.

## Error analysis

Phase 5 target-rank categories across the test set:

| Category | Bugs |
|---|---:|
{chr(10).join(f'| {key} | {int(value)} |' for key, value in sorted(error_counts.items()))}

Detailed bug-level ranks and categories are saved in
`data/processed/jdt_phase7_error_analysis.csv`. The test partition has
{missing_description} blank descriptions and {missing_component} blank
components. Missing descriptions are accepted by the API as empty text;
missing component and invalid prediction timestamp are rejected and covered
by tests. The original processed test data are not altered.

## Leakage, missing values, and ranking checks

- Both partitions contain `known_entry` labels only; train/test bug IDs are
  disjoint and ordered chronologically.
- Every training assignment timestamp precedes the first test creation time.
- Phase 3 history is generated from verified training events only and admits
  events strictly earlier than each prediction timestamp.
- The Phase 4 artifact metadata records developer/target IDs as excluded from
  predictive inputs and the test split as excluded from tuning.
- Text and metadata transforms are loaded from fitted artifacts and never
  refit during final evaluation.
- The Phase 5 API's full ranked list matched the Phase 4 ranking for every
  holdout bug, including deterministic score-tie ordering.
- The explainability layer validates expertise, recency, similarity, and
  additive model-margin consistency. No missing history is imputed as an
  invented assignment.

## Runtime

The measured workload made {performance['api_queries']} sequential API calls
(the first includes artifact loading; later calls reuse cached resources),
each returning explanations for the complete {performance['candidate_roster_size']}-developer
roster, over the chronological test set:

| Measurement | Seconds |
|---|---:|
| Total | {performance['total_api_seconds']:.4f} |
| Mean/query | {performance['mean_seconds_per_query']:.6f} |
| Median/query | {performance['median_seconds_per_query']:.6f} |
| P95/query | {performance['p95_seconds_per_query']:.6f} |
| Maximum/query | {performance['maximum_seconds_per_query']:.6f} |
| First query (includes cached artifact load) | {performance['first_query_seconds_includes_cached_resource_load']:.6f} |

This is a local sequential measurement, not a production latency guarantee.
Top-5 API responses construct fewer explanation payloads than this
full-roster measurement; all candidates must still be scored.

## Scenario validation and tests

The suite covers complete bug input, missing title/description, missing
component, invalid timestamps, empty and singleton candidate sets, new
cold-start developers, extensive verified history, old versus recent
component activity, stable ties, model contribution arithmetic, score
consistency, and rejection of provisional history. Phase 7 also executes the
public API on every real holdout row. The complete test suite result is
recorded in the final completion summary after the last changes.

## Limitations

There is one chronological holdout with 331 bugs, and 188 (56.8%) targets
are outside the candidate roster. Thus seen-developer performance is not
overall deployment performance. The task has a highly imbalanced one-positive
candidate-pair label. Historical bug-text snapshots are unavailable, so
point-in-time text visibility cannot be proven. The dataset has no reliable
resolution timestamp; resolution-time features remain unavailable. More
temporal cutoffs, a vetted cold-start roster, calibration, and real integration
load testing are needed before operational claims.

## Generated files

- `data/processed/jdt_phase7_final_model_comparison.csv`
- `data/processed/jdt_phase7_error_analysis.csv`
- `data/processed/jdt_phase7_performance.json`
- `docs/member2_phase7_final_evaluation.md`
"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return metrics, error_analysis, performance


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", default=str(PROJECT_ROOT / "data" / "processed"))
    parser.add_argument("--models-dir", default=str(PROJECT_ROOT / "models"))
    parser.add_argument(
        "--report",
        default=str(PROJECT_ROOT / "docs" / "member2_phase7_final_evaluation.md"),
    )
    arguments = parser.parse_args()
    metrics, _, performance = run_final_evaluation(
        arguments.processed_dir,
        arguments.models_dir,
        arguments.report,
    )
    print(metrics.to_string(index=False))
    print(json.dumps(performance, indent=2))


if __name__ == "__main__":
    main()
