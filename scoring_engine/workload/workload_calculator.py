
from collections import Counter
from datetime import timedelta
import math
from statistics import median

from scoring_engine.recency.recency_calculator import parse_timestamp


def calculate_developer_workload(
    assignment_events,
    reference_date,
    candidate_developers=None,
    window_days=30,
    exclude_bug_id=None
):
    """
    Calculate recent assignment workload for developers.

    Only assignment_added events within the observation
    window are counted.

    Future events and the target bug's own assignment
    are excluded.

    All eligible developers are included, even if they
    have no recorded assignments in the window.
    """

    # Validate observation window.
    try:
        window_days = float(window_days)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Window days must be a positive number"
        ) from error

    if not math.isfinite(window_days) or window_days <= 0:
        raise ValueError(
            "Window days must be a positive number"
        )

    # Convert prediction timestamp.
    reference_timestamp = parse_timestamp(reference_date)

    # Calculate observation window start.
    window_start = reference_timestamp - timedelta(
        days=window_days
    )

    workload_counts = Counter()

    # Process assignment events.
    for event in assignment_events:

        # Exclude target bug.
        if (
            exclude_bug_id is not None
            and str(event["bug_id"]) == str(exclude_bug_id)
        ):
            continue

        # Count only assignment additions.
        if event["label_event_type"] != "assignment_added":
            continue

        developer = event["developer_label"]

        if not isinstance(developer, str):
            continue

        developer = developer.strip()

        if not developer:
            continue

        # Parse assignment timestamp.
        event_timestamp = parse_timestamp(
            event["label_event_time"]
        )

        # Count only historical assignments within the window.
        if window_start <= event_timestamp < reference_timestamp:
            workload_counts[developer] += 1

    # Identify eligible developers.
    if candidate_developers is None:

        developers = set(workload_counts.keys())

    else:

        developers = {
            developer.strip()
            for developer in candidate_developers
            if isinstance(developer, str) and developer.strip()
        }

    # Build raw workload results.
    results = {}

    for developer in sorted(developers):

        assignment_count = workload_counts.get(
            developer, 0
        )

        results[developer] = {
            "assignment_count": assignment_count,
            "has_recent_assignments": assignment_count > 0
        }

    return results


def normalize_developer_workload(workload_results):
    """
    Normalize workload counts into scores between 0 and 1.

    The median of developers with positive assignment
    counts is used as the reference.

    Developers with no recent assignment evidence receive
    None rather than an artificially high suitability score.

    Higher suitability means lower recorded assignment
    activity relative to the active-developer median.

    This is an assignment-activity proxy, not a measurement
    of actual unresolved workload or availability.
    """

    if not workload_results:
        return {}

    active_counts = []

    # Validate assignment counts.
    for developer, result in workload_results.items():

        if not isinstance(result, dict):
            raise ValueError(
                f"Invalid workload data for {developer}"
            )

        count = result.get("assignment_count")

        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError(
                f"Invalid assignment count for {developer}"
            )

        if count < 0:
            raise ValueError(
                f"Assignment count cannot be negative for {developer}"
            )

        if count > 0:
            active_counts.append(count)

    # Calculate median among developers with positive activity.
    reference_median = (
        median(active_counts)
        if active_counts
        else None
    )

    normalized_results = {}

    for developer, result in workload_results.items():

        count = result["assignment_count"]

        # No positive assignment evidence for this developer.
        if count == 0:

            workload_pressure = None
            workload_suitability = None
            evidence_available = False

            evidence_status = "no_recent_assignment_evidence"

        else:

            # Calculate workload pressure.
            workload_pressure = count / (
                count + reference_median
            )

            # Calculate workload suitability.
            workload_suitability = 1 - workload_pressure

            evidence_available = True

            evidence_status = "recent_assignment_evidence_available"

        normalized_results[developer] = {
            "assignment_count": count,
            "has_recent_assignments": count > 0,
            "workload_pressure": workload_pressure,
            "workload_suitability_score": workload_suitability,
            "reference_median": reference_median,
            "workload_evidence_available": evidence_available,
            "workload_evidence_status": evidence_status
        }

    return normalized_results
