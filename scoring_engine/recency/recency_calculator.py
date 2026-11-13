

from datetime import datetime, date, time, timezone
import math


# Standardise all timestamps to UTC.
UTC = timezone.utc


# Provisional half-life selected from dataset distribution analysis.
# This value will be validated during final recommendation evaluation.
DEFAULT_HALF_LIFE_DAYS = 1095


def parse_timestamp(value):
    """
    Convert a date or timestamp into a timezone-aware UTC datetime.

    Supports:
    - datetime objects
    - date objects
    - ISO timestamps ending in Z
    - ISO timestamps containing timezone offsets

    Naive timestamps are assumed to be UTC.
    """

    if isinstance(value, datetime):
        timestamp = value

    elif isinstance(value, date):
        timestamp = datetime.combine(value, time.min)

    elif isinstance(value, str):
        value = value.strip()

        if not value:
            raise ValueError("Timestamp cannot be empty")

        value = value.replace("Z", "+00:00")

        try:
            timestamp = datetime.fromisoformat(value)
        except ValueError as error:
            raise ValueError(
                f"Invalid timestamp format: {value}"
            ) from error

    else:
        raise TypeError("Invalid activity timestamp format")

    # Assume timestamps without timezone information are UTC.
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)

    # Convert all timestamps into UTC.
    return timestamp.astimezone(UTC)


def calculate_recency_score(
    last_activity,
    reference_date,
    half_life_days=DEFAULT_HALF_LIFE_DAYS
):
    """
    Calculate developer recency using exponential decay.

    More recent activity produces a higher score.

    Formula:
        R = 2 ^ (-d / H)

    Where:
        R = Recency score
        d = Days since last activity
        H = Half-life in days

    Full numerical precision is preserved.
    """

    # Validate half-life.
    if isinstance(half_life_days, bool):
        raise ValueError("Half-life must be a positive number")

    try:
        half_life_days = float(half_life_days)

    except (TypeError, ValueError) as error:
        raise ValueError(
            "Half-life must be a positive number"
        ) from error

    if not math.isfinite(half_life_days) or half_life_days <= 0:
        raise ValueError(
            "Half-life must be a positive number"
        )

    # Convert timestamps into UTC.
    last_timestamp = parse_timestamp(last_activity)
    reference_timestamp = parse_timestamp(reference_date)

    # Calculate exact time difference in seconds.
    time_difference = (
        reference_timestamp - last_timestamp
    ).total_seconds()

    # Prevent future activity from being considered.
    if time_difference < 0:
        raise ValueError(
            "Activity timestamp cannot be after reference timestamp"
        )

    # Convert seconds into days.
    days_since_activity = time_difference / 86400

    # Calculate exponential decay score.
    score = math.pow(
        2,
        -days_since_activity / half_life_days
    )

    # Preserve full numerical precision.
    return score


def get_developer_recency(
    activity_dates,
    reference_date,
    half_life_days=DEFAULT_HALF_LIFE_DAYS
):
    """
    Find the latest eligible historical activity
    and calculate its recency score.

    Future activities are excluded.

    Returns None when no historical activity exists.

    The caller must exclude the target bug's own
    assignment event before passing activity dates.
    """

    if activity_dates is None:
        return None

    reference_timestamp = parse_timestamp(reference_date)

    valid_timestamps = []

    for activity in activity_dates:

        activity_timestamp = parse_timestamp(activity)

        # Include only activities at or before prediction time.
        if activity_timestamp < reference_timestamp:
            valid_timestamps.append(activity_timestamp)

    # Handle developers without historical activity.
    if not valid_timestamps:
        return None

    # Find the latest historical activity.
    latest_activity = max(valid_timestamps)

    # Calculate exact difference in days.
    time_difference = (
        reference_timestamp - latest_activity
    ).total_seconds()

    days_since_activity = time_difference / 86400

    # Calculate recency score.
    score = calculate_recency_score(
        latest_activity,
        reference_timestamp,
        half_life_days
    )

    return {
        "last_activity": latest_activity.isoformat(),
        "days_since_activity": days_since_activity,
        "recency_score": score
    }


def get_all_developer_recency(
    assignment_events,
    reference_date,
    candidate_developers=None,
    exclude_bug_id=None,
    half_life_days=DEFAULT_HALF_LIFE_DAYS
):
    """
    Calculate recency for all eligible developers
    at a particular historical prediction timestamp.

    Only assignment_added events are considered.

    Future events and the target bug's own assignment
    event are excluded.

    Developers without historical activity receive None.

    When candidate_developers is supplied, only those
    developers are included in the result.
    """

    # Convert prediction timestamp into UTC.
    reference_timestamp = parse_timestamp(reference_date)

    # Store latest historical activity for each developer.
    latest_activity_by_developer = {}

    for event in assignment_events:

        # Consider only assignment-added events.
        if event.get("label_event_type") != "assignment_added":
            continue

        # Exclude the target bug.
        if (
            exclude_bug_id is not None
            and str(event["bug_id"]) == str(exclude_bug_id)
        ):
            continue

        developer = event.get("developer_label")

        if not isinstance(developer, str) or not developer.strip():
            continue

        developer = developer.strip()

        # Parse assignment event timestamp.
        activity_timestamp = parse_timestamp(
            event["label_event_time"]
        )

        # Exclude future assignment events.
        if activity_timestamp >= reference_timestamp:
            continue

        # Store the latest eligible historical assignment.
        previous_activity = latest_activity_by_developer.get(
            developer
        )

        if (
            previous_activity is None
            or activity_timestamp > previous_activity
        ):
            latest_activity_by_developer[developer] = (
                activity_timestamp
            )

    # Identify the developer candidate pool.
    if candidate_developers is None:

        developers = set(latest_activity_by_developer)

    else:

        developers = {
            developer.strip()
            for developer in candidate_developers
            if isinstance(developer, str) and developer.strip()
        }

    results = {}

    for developer in sorted(developers):

        latest_activity = latest_activity_by_developer.get(
            developer
        )

        # Handle developers without historical activity.
        if latest_activity is None:

            results[developer] = None
            continue

        # Calculate exact time difference.
        time_difference = (
            reference_timestamp - latest_activity
        ).total_seconds()

        days_since_activity = time_difference / 86400

        # Calculate recency score.
        score = calculate_recency_score(
            latest_activity,
            reference_timestamp,
            half_life_days
        )

        results[developer] = {
            "last_activity": latest_activity.isoformat(),
            "days_since_activity": days_since_activity,
            "recency_score": score
        }

    return results
