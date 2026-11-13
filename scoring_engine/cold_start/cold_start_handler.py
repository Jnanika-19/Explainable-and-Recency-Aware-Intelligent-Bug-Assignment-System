
from collections import Counter, defaultdict

from scoring_engine.recency.recency_calculator import parse_timestamp


# Initial configurable threshold.
MIN_HISTORY_ASSIGNMENTS = 5


def classify_developer_history(
    assignment_events,
    reference_date,
    candidate_developers,
    minimum_history=MIN_HISTORY_ASSIGNMENTS,
    exclude_bug_id=None
):
    """
    Classify eligible developers according to their
    historical assignment evidence.

    Categories:
    1. sufficient_history: At least minimum_history assignments.
    2. limited_history: Between 1 and minimum_history - 1 assignments.
    3. no_assignment_history: No previous assignment evidence.

    Only assignment events available at the prediction
    timestamp are considered.
    """

    # Validate minimum history threshold.
    if (
        isinstance(minimum_history, bool)
        or not isinstance(minimum_history, int)
        or minimum_history <= 0
    ):
        raise ValueError(
            "Minimum history must be a positive integer"
        )

    # Convert prediction timestamp to UTC.
    prediction_time = parse_timestamp(reference_date)

    # Store historical assignment counts.
    assignment_counts = Counter()

    # Store historically observed components.
    developer_components = defaultdict(set)

    # Process available assignment events.
    for event in assignment_events:

        # Consider only assignment-added events.
        if event.get("label_event_type") != "assignment_added":
            continue

        # Exclude the target bug's own assignment.
        if (
            exclude_bug_id is not None
            and str(event["bug_id"]) == str(exclude_bug_id)
        ):
            continue

        developer = event["developer_label"]

        if not developer or not developer.strip():
            continue

        developer = developer.strip()

        # Parse assignment timestamp.
        event_time = parse_timestamp(
            event["label_event_time"]
        )

        # Exclude future assignment events.
        if event_time >= prediction_time:
            continue

        # Count valid historical assignments.
        assignment_counts[developer] += 1

        # Collect component expertise from historical records only.
        component = event.get("component")

        if component and component.strip():
            developer_components[developer].add(
                component.strip()
            )

    # Construct results for eligible candidates.
    results = {}

    for developer in sorted(set(candidate_developers)):

        if not developer or not developer.strip():
            continue

        developer = developer.strip()

        history_count = assignment_counts.get(
            developer, 0
        )

        components = sorted(
            developer_components.get(developer, set())
        )

        # Classify historical evidence.
        if history_count >= minimum_history:

            status = "sufficient_history"

        elif history_count > 0:

            status = "limited_history"

        else:

            status = "no_assignment_history"

        results[developer] = {
            "history_count": history_count,
            "distinct_components": len(components),
            "historical_components": components,
            "history_status": status,
            "has_sufficient_history": (
                status == "sufficient_history"
            ),
            "requires_cold_start_support": (
                status != "sufficient_history"
            ),
            "minimum_history_threshold": minimum_history
        }

    return results

def evaluate_limited_history_component_evidence(
    assignment_events,
    reference_date,
    developer_history,
    target_component,
    exclude_bug_id=None
):
    """
    Evaluate historical component evidence for developers
    classified as having limited assignment history.

    Only assignment events available at the prediction
    timestamp are considered.

    Returns component-match evidence without treating it
    as a prediction-confidence score.
    """

    if not target_component or not target_component.strip():
        raise ValueError("Target component cannot be empty")

    prediction_time = parse_timestamp(reference_date)

    target_component = target_component.strip().casefold()

    # Select developers with limited historical evidence.
    limited_developers = {
        developer
        for developer, result in developer_history.items()
        if result["history_status"] == "limited_history"
    }

    # Track historical component evidence.
    component_counts = Counter()
    matching_component_counts = Counter()

    for event in assignment_events:

        if event.get("label_event_type") != "assignment_added":
            continue

        # Exclude the target bug itself.
        if (
            exclude_bug_id is not None
            and str(event["bug_id"]) == str(exclude_bug_id)
        ):
            continue

        developer = event.get("developer_label", "")

        if not developer or developer.strip() not in limited_developers:
            continue

        developer = developer.strip()

        event_time = parse_timestamp(
            event["label_event_time"]
        )

        # Prevent future information from being used.
        if event_time >= prediction_time:
            continue

        component = event.get("component", "")

        if not component or not component.strip():
            continue

        component_counts[developer] += 1

        if component.strip().casefold() == target_component:
            matching_component_counts[developer] += 1

    results = {}

    for developer in sorted(limited_developers):

        observed = component_counts[developer]
        matches = matching_component_counts[developer]

        if observed == 0:
            status = "component_data_unavailable"
            share = None

        elif matches > 0:
            status = "component_match_found"
            share = matches / observed

        else:
            status = "no_component_match"
            share = 0.0

        results[developer] = {
            "target_component": target_component,
            "component_observation_count": observed,
            "component_match_count": matches,
            "component_experience_share": (
                round(share, 4) if share is not None else None
            ),
            "component_evidence_status": status,
            "requires_additional_evidence": matches == 0
        }

    return results

def build_cold_start_assessment(
    history_results,
    component_results=None
):
    """
    Combine historical classification and component evidence
    into one cold-start assessment for each developer.

    This function identifies the available evidence.
    It does not calculate prediction confidence or final ranking.
    """

    component_results = component_results or {}

    assessments = {}

    for developer, history in history_results.items():

        history_status = history["history_status"]

        component_evidence = component_results.get(
            developer
        )

        if history_status == "sufficient_history":

            recommendation_path = "standard_history_based"

            component_status = "not_required_for_classification"

            additional_evidence_required = False

        elif history_status == "limited_history":

            if component_evidence is None:

                recommendation_path = "additional_evidence_required"
                component_status = "not_evaluated"
                additional_evidence_required = True

            elif component_evidence["component_match_count"] > 0:

                recommendation_path = "limited_history_component_supported"
                component_status = "component_match_found"
                additional_evidence_required = False

            else:

                recommendation_path = "additional_evidence_required"
                component_status = "no_component_match"
                additional_evidence_required = True

        else:

            recommendation_path = "external_evidence_required"
            component_status = "no_assignment_history"
            additional_evidence_required = True

        assessments[developer] = {
            "history_count": history["history_count"],
            "history_status": history_status,
            "historical_components": history[
                "historical_components"
            ],
            "component_evidence_status": component_status,
            "recommendation_path": recommendation_path,
            "additional_evidence_required": (
                additional_evidence_required
            )
        }

    return assessments
