
"""
Member 3 - Workload Evaluation Results Exporter

Reuses the existing workload evaluation functions.
Does not modify the original evaluation scripts.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------
# PROJECT CONFIGURATION
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "results" / "member3" / "workload"

WINDOW_SCRIPT = (
    PROJECT_ROOT
    / "tests"
    / "evaluation"
    / "evaluate_workload_windows.py"
)

NORMALIZATION_SCRIPT = (
    PROJECT_ROOT
    / "tests"
    / "evaluation"
    / "compare_workload_normalization.py"
)

WINDOWS = [30, 60, 90, 180, 365]


from scoring_engine.workload.workload_calculator import (
    calculate_developer_workload,
)


# ---------------------------------------------------------
# LOAD EXISTING EVALUATION MODULES
# ---------------------------------------------------------

def load_module(name, path):

    if not path.is_file():
        raise FileNotFoundError(f"Script not found: {path}")

    spec = importlib.util.spec_from_file_location(name, path)

    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def main():

    print("\n========== MEMBER 3 WORKLOAD RESULTS EXPORT ==========")

    window_module = load_module(
        "workload_window_evaluation",
        WINDOW_SCRIPT,
    )

    normalization_module = load_module(
        "workload_normalization_evaluation",
        NORMALIZATION_SCRIPT,
    )

    dataset_path = window_module.DATASET_PATH

    if not dataset_path.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {dataset_path}"
        )

    # -----------------------------------------------------
    # LOAD DATASET
    # -----------------------------------------------------

    bug_records, assignment_events, skipped_records = (
        window_module.load_dataset(dataset_path)
    )

    prediction_points = window_module.select_prediction_points(
        bug_records
    )

    if not prediction_points:
        raise ValueError("No historical prediction points found.")

    print("\nDATASET:", dataset_path.name)
    print("Valid bug records:", len(bug_records))
    print("Assignment events:", len(assignment_events))
    print("Skipped records:", skipped_records)
    print("Prediction points:", len(prediction_points))

    window_rows = []
    normalization_rows = []
    point_details = []

    # -----------------------------------------------------
    # EVALUATE WORKLOAD WINDOWS AND NORMALIZATION METHODS
    # -----------------------------------------------------

    for point_name, target in prediction_points.items():

        reference_date = target["_creation_timestamp"]
        target_bug_id = target["bug_id"]

        candidates = window_module.get_historical_candidates(
            assignment_events=assignment_events,
            reference_date=reference_date,
            target_bug_id=target_bug_id,
        )

        point_details.append({
            "prediction_point": point_name,
            "target_bug_id": str(target_bug_id),
            "prediction_timestamp": reference_date.isoformat(),
            "eligible_developers": len(candidates),
        })

        print(f"\nPrediction point: {point_name}")
        print("Target bug:", target_bug_id)
        print("Eligible developers:", len(candidates))

        for window_days in WINDOWS:

            # ---------------------------------------------
            # A. WORKLOAD WINDOW EVALUATION
            # ---------------------------------------------

            summary = window_module.evaluate_window(
                assignment_events=assignment_events,
                reference_date=reference_date,
                target_bug_id=target_bug_id,
                candidate_developers=candidates,
                window_days=window_days,
            )

            window_rows.append({
                "prediction_point": point_name,
                "target_bug_id": str(target_bug_id),
                "prediction_timestamp": reference_date.isoformat(),
                **summary,
            })

            # ---------------------------------------------
            # B. NORMALIZATION COMPARISON
            # ---------------------------------------------

            raw_results = calculate_developer_workload(
                assignment_events=assignment_events,
                reference_date=reference_date,
                candidate_developers=candidates,
                window_days=window_days,
                exclude_bug_id=target_bug_id,
            )

            active_counts = {
                developer: result["assignment_count"]
                for developer, result in raw_results.items()
                if result["assignment_count"] > 0
            }

            total_candidates = len(raw_results)
            active_developers = len(active_counts)
            unknown_developers = (
                total_candidates - active_developers
            )

            median_scores = (
                normalization_module.calculate_median_scores(
                    active_counts
                )
            )

            log_scores = (
                normalization_module.calculate_log_scores(
                    active_counts
                )
            )

            percentile_scores = (
                normalization_module.calculate_percentile_scores(
                    active_counts
                )
            )

            methods = {
                "Median-based": median_scores,
                "Log-based": log_scores,
                "Percentile-based": percentile_scores,
            }

            same_developer_pool = (
                set(median_scores)
                == set(log_scores)
                == set(percentile_scores)
                == set(active_counts)
            )

            for method_name, method_scores in methods.items():

                score_summary = (
                    normalization_module.summarize_scores(
                        method_scores
                    )
                )

                if score_summary is None:
                    score_summary = {
                        "p10": None,
                        "median": None,
                        "p90": None,
                        "minimum": None,
                        "maximum": None,
                        "unique_scores": 0,
                    }

                normalization_rows.append({
                    "prediction_point": point_name,
                    "target_bug_id": str(target_bug_id),
                    "prediction_timestamp": reference_date.isoformat(),
                    "window_days": window_days,
                    "normalization_method": method_name,
                    "total_candidates": total_candidates,
                    "active_developers": active_developers,
                    "unknown_workload_developers": unknown_developers,
                    "same_evaluated_developer_pool": (
                        same_developer_pool
                    ),
                    **score_summary,
                })

    # -----------------------------------------------------
    # SAVE CSV RESULTS
    # -----------------------------------------------------

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    window_path = (
        OUTPUT_DIR / "member3_workload_window_evaluation.csv"
    )

    normalization_path = (
        OUTPUT_DIR / "member3_workload_normalization_comparison.csv"
    )

    validation_path = (
        OUTPUT_DIR / "member3_workload_validation.json"
    )

    window_df = pd.DataFrame(window_rows)
    normalization_df = pd.DataFrame(normalization_rows)

    window_df.to_csv(
        window_path,
        index=False,
        encoding="utf-8",
    )

    normalization_df.to_csv(
        normalization_path,
        index=False,
        encoding="utf-8",
    )

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    expected_window_rows = len(prediction_points) * len(WINDOWS)
    expected_normalization_rows = expected_window_rows * 3

    window_counts_valid = all(
        row["candidate_count"]
        == (
            row["active_developers"]
            + row["zero_assignment_developers"]
        )
        for row in window_rows
    )

    normalization_pools_valid = all(
        row["same_evaluated_developer_pool"]
        for row in normalization_rows
    )

    report = {
        "component": "Member 3 Workload",
        "dataset": dataset_path.name,

        "input_counts": {
            "valid_bug_records": len(bug_records),
            "assignment_events": len(assignment_events),
            "skipped_records": skipped_records,
            "prediction_points": len(prediction_points),
        },

        "workload_windows_days": WINDOWS,

        "expected_workload_rows": expected_window_rows,
        "actual_workload_rows": len(window_rows),

        "expected_normalization_rows": expected_normalization_rows,
        "actual_normalization_rows": len(normalization_rows),

        "window_candidate_count_validation": window_counts_valid,

        "normalization_developer_pool_validation": (
            normalization_pools_valid
        ),

        "target_bug_excluded": True,

        "temporal_policy": (
            "Workload is calculated from historical assignment events "
            "within each selected window, excluding the target bug "
            "and future events."
        ),

        "interpretation_limitation": (
            "Assignment frequency is used as a workload proxy. "
            "The available event data does not establish the number "
            "of currently open bugs or actual developer availability."
        ),

        "prediction_points": point_details,

        "outputs": [
            str(window_path.relative_to(PROJECT_ROOT)),
            str(normalization_path.relative_to(PROJECT_ROOT)),
        ],
    }

    report["validation_passed"] = (
        len(window_rows) == expected_window_rows
        and len(normalization_rows) == expected_normalization_rows
        and window_counts_valid
        and normalization_pools_valid
    )

    with validation_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    # -----------------------------------------------------
    # DISPLAY RESULTS
    # -----------------------------------------------------

    print("\n========== EXPORT VALIDATION ==========")

    print("Workload rows:", len(window_rows))
    print("Expected workload rows:", expected_window_rows)

    print("Normalization rows:", len(normalization_rows))
    print("Expected normalization rows:", expected_normalization_rows)

    print("Window candidate counts valid:", window_counts_valid)
    print("Normalization pools valid:", normalization_pools_valid)

    print("Validation passed:", report["validation_passed"])

    print("\n========== OUTPUT FILES ==========")

    print(window_path)
    print(normalization_path)
    print(validation_path)

    if not report["validation_passed"]:
        raise RuntimeError(
            "Workload export validation failed. "
            "Inspect the validation JSON."
        )

    print("\nWORKLOAD RESULTS EXPORT COMPLETED.")


if __name__ == "__main__":
    main()
