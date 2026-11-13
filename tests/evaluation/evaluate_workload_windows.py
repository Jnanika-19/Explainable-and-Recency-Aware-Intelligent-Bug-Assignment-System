
import csv
import sys
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
    / "jdt_known_entry_preprocessed.csv"
)

from scoring_engine.recency.recency_calculator import parse_timestamp

from scoring_engine.workload.workload_calculator import (
    calculate_developer_workload,
    normalize_developer_workload
)


# ==================================================
# 2. LOAD DATASET
# ==================================================

def load_dataset(file_path):
    """
    Load verified known_entry records only.
    Assignment activity uses the verified assignment_time.
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
            "developer_id",
            "created_at",
            "assignment_time",
            "label_type"
        }

        missing_columns = (
            required_columns - set(reader.fieldnames or [])
        )

        if missing_columns:
            raise ValueError(
                f"Missing dataset columns: {sorted(missing_columns)}"
            )

        for row in reader:

            if row["label_type"].strip() != "known_entry":
                skipped_records += 1
                continue

            developer = (row["developer_id"] or "").strip()
            bug_id = (row["bug_id"] or "").strip()

            if not bug_id or not developer:
                skipped_records += 1
                continue

            try:
                creation_timestamp = parse_timestamp(
                    row["created_at"]
                )

                event_timestamp = parse_timestamp(
                    row["assignment_time"]
                )

            except (ValueError, TypeError):
                skipped_records += 1
                continue

            normalized_row = dict(row)
            normalized_row["creation_time"] = row["created_at"]
            normalized_row["developer_label"] = developer
            normalized_row["label_event_time"] = event_timestamp
            normalized_row["label_event_type"] = "assignment_added"
            normalized_row["_creation_timestamp"] = creation_timestamp

            bug_records.append(normalized_row)

            assignment_events.append({
                "bug_id": bug_id,
                "developer_label": developer,
                "label_event_time": event_timestamp,
                "label_event_type": "assignment_added"
            })

    bug_records.sort(
        key=lambda record: record["_creation_timestamp"]
    )

    return bug_records, assignment_events, skipped_records


def calculate_percentile(values, percentile):

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
# 5. IDENTIFY HISTORICALLY ELIGIBLE DEVELOPERS
# ==================================================

def get_historical_candidates(
    assignment_events,
    reference_date,
    target_bug_id
):

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

        if event["label_event_time"] < reference_date:
            candidates.add(developer)

    return sorted(candidates)


# ==================================================
# 6. EVALUATE ONE WORKLOAD WINDOW
# ==================================================

def evaluate_window(
    assignment_events,
    reference_date,
    target_bug_id,
    candidate_developers,
    window_days
):

    raw_results = calculate_developer_workload(
        assignment_events=assignment_events,
        reference_date=reference_date,
        candidate_developers=candidate_developers,
        window_days=window_days,
        exclude_bug_id=target_bug_id
    )

    normalized_results = normalize_developer_workload(
        raw_results
    )

    # Assignment counts for all eligible developers.
    assignment_counts = [
        result["assignment_count"]
        for result in raw_results.values()
    ]

    # Assignment counts only for active developers.
    active_counts = [
        count
        for count in assignment_counts
        if count > 0
    ]

    total_candidates = len(candidate_developers)
    active_developers = len(active_counts)

    zero_assignment_developers = (
        total_candidates - active_developers
    )

    # Extract available suitability scores.
    suitability_scores = [
        result["workload_suitability_score"]
        for result in normalized_results.values()
        if result["workload_suitability_score"] is not None
    ]

    summary = {

        "window_days": window_days,

        "candidate_count": total_candidates,

        "active_developers": active_developers,

        "active_percentage": (
            active_developers / total_candidates * 100
            if total_candidates > 0
            else 0
        ),

        "zero_assignment_developers": (
            zero_assignment_developers
        ),

        "median_active_assignments": (
            median(active_counts)
            if active_counts else None
        ),

        # P90 including developers with zero assignments.
        "p90_all_candidates": calculate_percentile(
            assignment_counts,
            0.90
        ),

        # P90 considering only developers with activity.
        "p90_active_developers": calculate_percentile(
            active_counts,
            0.90
        ),

        "maximum_assignments": (
            max(assignment_counts)
            if assignment_counts else None
        ),

        "suitability_p10": calculate_percentile(
            suitability_scores,
            0.10
        ),

        "suitability_median": (
            median(suitability_scores)
            if suitability_scores else None
        ),

        "suitability_p90": calculate_percentile(
            suitability_scores,
            0.90
        ),

        "scored_developers": len(suitability_scores)
    }

    return summary


# ==================================================
# 7. DISPLAY RESULTS
# ==================================================

def format_value(value):

    if value is None:
        return "N/A"

    if isinstance(value, float):
        return f"{value:.4f}"

    return str(value)


def display_summary(summary):

    print(
        f"WINDOW={summary['window_days']:>3} days | "
        f"Candidates={summary['candidate_count']:>3} | "
        f"Active={summary['active_developers']:>3} | "
        f"Active %={summary['active_percentage']:.2f}% | "
        f"Zero assignments="
        f"{summary['zero_assignment_developers']:>3}"
    )

    print(
        f"  Median active count="
        f"{format_value(summary['median_active_assignments'])} | "
        f"P90 all candidates="
        f"{format_value(summary['p90_all_candidates'])} | "
        f"P90 active developers="
        f"{format_value(summary['p90_active_developers'])} | "
        f"Maximum="
        f"{format_value(summary['maximum_assignments'])}"
    )

    print(
        f"  Suitability P10="
        f"{format_value(summary['suitability_p10'])} | "
        f"Median="
        f"{format_value(summary['suitability_median'])} | "
        f"P90="
        f"{format_value(summary['suitability_p90'])} | "
        f"Scored={summary['scored_developers']}"
    )


# ==================================================
# 8. MAIN EVALUATION
# ==================================================

def main():

    print(
        "\n========== WORKLOAD WINDOW EVALUATION =========="
    )

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    bug_records, assignment_events, skipped_records = (
        load_dataset(DATASET_PATH)
    )

    print(f"\nDATASET: {DATASET_PATH.name}")

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

        print("\n" + "=" * 110)

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

        print("-" * 110)

        for window_days in workload_windows:

            summary = evaluate_window(
                assignment_events=assignment_events,
                reference_date=reference_date,
                target_bug_id=target_bug_id,
                candidate_developers=candidates,
                window_days=window_days
            )

            display_summary(summary)

    print(
        "\n========== EVALUATION COMPLETED =========="
    )


# ==================================================
# 9. PROGRAM ENTRY POINT
# ==================================================

if __name__ == "__main__":
    main()
