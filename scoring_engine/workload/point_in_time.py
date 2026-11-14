"""Workload snapshots from assignment lifecycle events, never Git commit counts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Literal, Mapping


EventType = Literal["assign", "reassign", "close", "resolve", "reopen"]


@dataclass(frozen=True)
class AssignmentEvent:
    event_id: str
    bug_id: str
    occurred_at: datetime
    event_type: EventType
    developer_id: str | None = None
    severity: str | None = None


@dataclass(frozen=True)
class WorkloadSnapshot:
    developer_id: str
    as_of: datetime
    active_bug_count: int
    severity_weighted_count: float | None
    active_bug_ids: tuple[str, ...]
    status: str
    anomalies: tuple[str, ...]


def calculate_workload(
    events: list[AssignmentEvent],
    *,
    developer_id: str,
    cutoff: datetime,
    history_complete: bool,
    severity_weights: Mapping[str, float] | None = None,
) -> WorkloadSnapshot:
    if not developer_id:
        raise ValueError("developer_id is required")
    if cutoff.tzinfo is None:
        raise ValueError("cutoff must include a timezone")
    point = cutoff.astimezone(timezone.utc)
    previous_time: datetime | None = None
    seen_events: set[str] = set()
    state: dict[str, tuple[str | None, str | None, bool]] = {}
    anomalies: list[str] = []

    if severity_weights is not None:
        for severity, weight in severity_weights.items():
            if not isfinite(weight) or weight < 0:
                raise ValueError(
                    f"Severity weight for {severity!r} must be finite and non-negative"
                )

    for event in events:
        if not event.event_id or event.event_id in seen_events:
            raise ValueError("Assignment event IDs must be nonempty and unique")
        seen_events.add(event.event_id)
        if event.occurred_at.tzinfo is None:
            raise ValueError("Assignment event timestamps must include a timezone")
        moment = event.occurred_at.astimezone(timezone.utc)
        if previous_time is not None and moment < previous_time:
            raise ValueError("Assignment events must be chronologically ordered")
        previous_time = moment
        if moment >= point:
            continue

        current = state.get(event.bug_id)
        if event.event_type in ("assign", "reassign"):
            if not event.developer_id:
                anomalies.append(f"{event.event_id}: assignment has no developer")
                continue
            if current is None and event.event_type == "reassign":
                anomalies.append(f"{event.event_id}: reassignment lacks prior state")
            severity = (
                event.severity
                if event.severity is not None
                else (current[1] if current is not None else None)
            )
            state[event.bug_id] = (event.developer_id, severity, True)
        elif event.event_type in ("close", "resolve"):
            if current is None:
                anomalies.append(f"{event.event_id}: closure lacks prior state")
                continue
            state[event.bug_id] = (current[0], current[1], False)
        elif event.event_type == "reopen":
            if current is None:
                anomalies.append(f"{event.event_id}: reopen lacks prior state")
                continue
            state[event.bug_id] = (
                event.developer_id or current[0],
                event.severity or current[1],
                True,
            )
        else:
            raise ValueError(f"Unsupported assignment event type: {event.event_type}")

    active = {
        bug_id: (assignee, severity)
        for bug_id, (assignee, severity, is_active) in state.items()
        if is_active and assignee == developer_id
    }
    weighted: float | None = None
    if severity_weights is not None:
        if all(severity in severity_weights for _, severity in active.values()):
            weighted = sum(
                severity_weights[severity]  # type: ignore[index]
                for _, severity in active.values()
            )
        else:
            anomalies.append("severity missing or unweighted for active bug(s)")

    status = (
        "incomplete_history_manual_review"
        if not history_complete or anomalies
        else "complete_as_of_cutoff"
    )
    if not history_complete:
        anomalies.append("source history marked incomplete")
    return WorkloadSnapshot(
        developer_id=developer_id,
        as_of=point,
        active_bug_count=len(active),
        severity_weighted_count=weighted,
        active_bug_ids=tuple(sorted(active)),
        status=status,
        anomalies=tuple(anomalies),
    )
