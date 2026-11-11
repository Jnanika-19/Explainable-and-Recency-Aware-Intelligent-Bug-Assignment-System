
import csv
import sys
import math
from pathlib import Path
from statistics import median

# ==================================================
# 1. PROJECT PATHS AND IMPORTS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "jdt_training_primary.csv"
)

from scoring_engine.recency.recency_calculator import parse_timestamp

from scoring_engine.workload.workload_calculator import (
    calculate_developer_workload
)


# ==================================================
# 2. LOAD DATASET
# ==================================================

def load_dataset(file_path):
    """
    Load bug records and assignment events
    from the primary JDT dataset.
    """

    bug_records = []
    assignment_events = []
    skipped_records = 0

    with open(
        file_path,
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        required_columns = {
            "bug_id",
            "developer_label",
            "creation_time",
            "label_event_time",
            "label_event_type"
        }

        missing_columns = (
            required_columns - set(reader.fieldnames or [])
        )

        if missing_columns:
            raise ValueError(
                f"Missing dataset columns: {sorted(missing_columns)}"
            )

        for row in reader:

            try:
                creation_timestamp = parse_timestamp(
                    row["creation_time"]
                )

                event_timestamp = parse_timestamp(
                    row["label_event_time"]
                )

            except (ValueError, TypeError):
                skipped_records += 1
                continue

            row["_creation_timestamp"] = creation_timestamp

            bug_records.append(row)

            assignment_events.append({
                "bug_id": row["bug_id"],
                "developer_label": row["developer_label"],
                "label_event_time": event_timestamp,
                "label_event_type": row["label_event_type"]
            })

    bug_records.sort(
        key=lambda record: record["_creation_timestamp"]
    )

    return bug_records, assignment_events, skipped_records


# ==================================================
# 3. PERCENTILE CALCULATION
# ==================================================

def calculate_percentile(values, percentile):
    """
    Calculate percentile using linear interpolation.
    """

    if not values:
        return None

    ordered_values = sorted(values)

    position = (len(ordered_values) - 1) * percentile

    lower_index = int(position)

    upper_index = min(
        lower_index + 1,
        len(ordered_values) - 1
    )

    fraction = position - lower_index

    return (
        ordered_values[lower_index] * (1 - fraction)
        + ordered_values[upper_index] * fraction
    )


# ==================================================
# 4. SELECT HISTORICAL PREDICTION POINTS
# ==================================================

def select_prediction_points(bug_records):
    """
    Select four representative points from
    the dataset timeline.
    """

    total_records = len(bug_records)

    if total_records == 0:
        raise ValueError(
            "No valid bug records were found."
        )

    positions = {
        "25_PERCENT": 0.25,
        "MIDDLE": 0.50,
        "75_PERCENT": 0.75,
        "LATEST": 1.00
    }

    selected_points = {}

    for label, percentile in positions.items():

        index = round(
            (total_records - 1) * percentile
        )

        selected_points[label] = bug_records[index]

    return selected_points


# ==================================================
# 5. FIND HISTORICALLY ELIGIBLE DEVELOPERS
# ==================================================

def get_historical_candidates(
    assignment_events,
    reference_date,
    target_bug_id
):
    """
    Find developers with assignment history
    available by the prediction date.
    """

    candidates = set()

    for event in assignment_events:

        if event["label_event_type"] != "assignment_added":
            continue

        if str(event["bug_id"]) == str(target_bug_id):
            continue

        developer = event["developer_label"]

        if not isinstance(developer, str):
            continue

        developer = developer.strip()

        if not developer:
            continue

        if event["label_event_time"] <= reference_date:
            candidates.add(developer)

    return sorted(candidates)


# ==================================================
# 6. MEDIAN-BASED NORMALIZATION
# ==================================================

def calculate_median_scores(active_counts):
    """
    Existing method:
    Workload pressure = count / (count + median)

    Suitability = 1 - workload pressure
    """

    if not active_counts:
        return {}

    reference_median = median(
        active_counts.values()
    )

    scores = {}

    for developer, count in active_counts.items():

        pressure = count / (
            count + reference_median
        )

        scores[developer] = 1 - pressure

    return scores


# ==================================================
# 7. LOG-BASED NORMALIZATION
# ==================================================

def calculate_log_scores(active_counts):
    """
    Log-based method:
    Applies logarithmic scaling to reduce
    the influence of very high assignment counts.

    The maximum log-transformed count is used
    as the reference.
    """

    if not active_counts:
        return {}

    maximum_count = max(
        active_counts.values()
    )

    reference_value = math.log1p(maximum_count)

    scores = {}

    for developer, count in active_counts.items():

        pressure = math.log1p(count) / reference_value

        scores[developer] = 1 - pressure

    return scores


# ==================================================
# 8. PERCENTILE-BASED NORMALIZATION
# ==================================================

def calculate_percentile_scores(active_counts):
    """
    Calculate workload pressure using the
    developer's midrank percentile among active
    developers.

    Higher assignment count means higher
    workload pressure and lower suitability.
    """

    if not active_counts:
        return {}

    all_counts = list(active_counts.values())

    total_developers = len(all_counts)

    scores = {}

    for developer, count in active_counts.items():

        lower_count = sum(
            1 for value in all_counts
            if value < count
        )

        equal_count = sum(
            1 for value in all_counts
            if value == count
        )

        percentile_pressure = (
            lower_count + 0.5 * equal_count
        ) / total_developers

        scores[developer] = (
            1 - percentile_pressure
        )

    return scores


# ==================================================
# 9. SUMMARIZE NORMALIZATION SCORES
# ==================================================

def summarize_scores(scores):
    """
    Calculate score distribution statistics.
    """

    values = list(scores.values())

    if not values:
        return None

    return {
        "p10": calculate_percentile(values, 0.10),
        "median": median(values),
        "p90": calculate_percentile(values, 0.90),
        "minimum": min(values),
        "maximum": max(values),
        "unique_scores": len(set(values))
    }


# ==================================================
# 10. DISPLAY NORMALIZATION RESULTS
# ==================================================

def format_value(value):

    if value is None:
        return "N/A"

    return f"{value:.4f}"


def display_method_results(method_name, scores):

    summary = summarize_scores(scores)

    if summary is None:

        print(
            f"{method_name:<24} | No workload evidence"
        )

        return

    print(
        f"{method_name:<24} | "
        f"P10={format_value(summary['p10'])} | "
        f"Median={format_value(summary['median'])} | "
        f"P90={format_value(summary['p90'])} | "
        f"Min={format_value(summary['minimum'])} | "
        f"Max={format_value(summary['maximum'])} | "
        f"Unique scores={summary['unique_scores']}"
    )


# ==================================================
# 11. COMPARE NORMALIZATION METHODS
# ==================================================

def compare_normalization_methods(
    assignment_events,
    reference_date,
    target_bug_id,
    candidates,
    window_days
):
    """
    Compare all three normalization methods
    using the same assignment counts.
    """

    raw_results = calculate_developer_workload(
        assignment_events=assignment_events,
        reference_date=reference_date,
        candidate_developers=candidates,
        window_days=window_days,
        exclude_bug_id=target_bug_id
    )

    # Include only developers with positive
    # recorded assignment activity.
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

    # Calculate suitability scores using
    # the three alternative methods.
    median_scores = calculate_median_scores(
        active_counts
    )

    log_scores = calculate_log_scores(
        active_counts
    )

    percentile_scores = calculate_percentile_scores(
        active_counts
    )

    print(
        f"\nWINDOW: {window_days} days"
    )

    print(
        f"Eligible developers: {total_candidates}"
    )

    print(
        f"Developers with evidence: {active_developers}"
    )

    print(
        f"Developers with unknown workload: {unknown_developers}"
    )

    print("-" * 115)

    print(
        f"{'Normalization method':<24} | "
        "P10       | Median    | P90       | "
        "Minimum   | Maximum   | Unique scores"
    )

    print("-" * 115)

    display_method_results(
        "Median-based",
        median_scores
    )

    display_method_results(
        "Log-based",
        log_scores
    )

    display_method_results(
        "Percentile-based",
        percentile_scores
    )

    # Confirm whether every method scores
    # exactly the same active developers.
    same_candidates = (
        set(median_scores)
        == set(log_scores)
        == set(percentile_scores)
        == set(active_counts)
    )

    print("-" * 115)

    print(
        f"Same evaluated developer pool: {same_candidates}"
    )


# ==================================================
# 12. MAIN EVALUATION
# ==================================================

def main():

    print(
        "\n========== WORKLOAD NORMALIZATION COMPARISON =========="
    )

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    bug_records, assignment_events, skipped_records = (
        load_dataset(DATASET_PATH)
    )

    print(
        f"\nDATASET: {DATASET_PATH.name}"
    )

    print(
        f"VALID BUG RECORDS: {len(bug_records)}"
    )

    print(
        f"VALID ASSIGNMENT EVENTS: {len(assignment_events)}"
    )

    print(
        f"SKIPPED RECORDS: {skipped_records}"
    )

    prediction_points = select_prediction_points(
        bug_records
    )

    workload_windows = [
        30,
        60,
        90,
        180,
        365
    ]

    for point_name, target in prediction_points.items():

        reference_date = target["_creation_timestamp"]

        target_bug_id = target["bug_id"]

        print("\n" + "=" * 115)

        print(
            f"PREDICTION POINT: {point_name}"
        )

        print(
            f"TARGET BUG: {target_bug_id}"
        )

        print(
            f"PREDICTION DATE: {reference_date.isoformat()}"
        )

        candidates = get_historical_candidates(
            assignment_events=assignment_events,
            reference_date=reference_date,
            target_bug_id=target_bug_id
        )

        print(
            f"ELIGIBLE DEVELOPERS: {len(candidates)}"
        )

        for window_days in workload_windows:

            compare_normalization_methods(
                assignment_events=assignment_events,
                reference_date=reference_date,
                target_bug_id=target_bug_id,
                candidates=candidates,
                window_days=window_days
            )

    print(
        "\n========== COMPARISON COMPLETED =========="
    )


# ==================================================
# 13. PROGRAM ENTRY POINT
# ==================================================

if __name__ == "__main__":
    main()
