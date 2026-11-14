"""Build an explicitly partial JDT workload dataset from existing derived files."""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "dataset" / "processed"
EVENTS_PATH = PROCESSED / "jdt_workload" / "jdt_assignment_lifecycle_events.csv"
COVERAGE_PATH = PROCESSED / "jdt_workload" / "jdt_bug_history_coverage.csv"
FEATURES_PATH = PROCESSED / "jdt_point_in_time" / "jdt_candidate_features.csv"
SPLITS_PATH = PROCESSED / "jdt_point_in_time" / "jdt_bug_splits.csv"
IDENTITY_PATH = (
    PROCESSED / "cold_start" / "jdt_identity_review" / "jdt_verified_identity_map.csv"
)
OUTPUT_DIR = PROCESSED / "jdt_workload_partial"
SNAPSHOTS_NAME = "jdt_partial_workload_snapshots.csv"
COVERAGE_NAME = "jdt_partial_workload_coverage.csv"
RECONSTRUCTION_REPORT_NAME = "jdt_partial_workload_reconstruction_report.md"
VALIDATION_REPORT_NAME = "jdt_partial_workload_validation_report.md"

REQUIRED_STATE_FIELDS = {"assignee", "product", "status"}
ACTIVE_FIELDS = REQUIRED_STATE_FIELDS
TERMINAL_STATUSES = {"RESOLVED", "VERIFIED", "CLOSED"}
EXPECTED_SOURCE_COHORT = 4542
EXPECTED_STRICT_COHORT = 228
EXPECTED_TARGET_BUGS = 33246
EXPECTED_DEVELOPERS = 9
PARTIAL_SCOPE_NOTE = (
    "Partial replay-clean observed-history subset only; bugs outside the "
    "228 eligible histories are not assumed absent from developer queues. "
    "Histories with 13,427 replay mismatches and 1,880 incomplete records "
    "remain unavailable."
)

SNAPSHOT_FIELDS = (
    "prediction_bug_id",
    "prediction_cutoff",
    "data_split",
    "developer_id",
    "workload_scope",
    "suitable_for_experimental_use",
    "severity_breakdown_supported",
    "eligible_bug_cohort_size",
    "eligible_bugs_created_before_cutoff",
    "eligible_active_jdt_bug_count",
    "eligible_active_verified_assignee_bug_count",
    "eligible_active_unverified_or_unassigned_bug_count",
    "verified_developer_pool_size",
    "developers_with_active_observed_bugs_at_cutoff",
    "active_assigned_bug_count_partial",
    "assigned_event_count_partial",
    "distinct_bugs_assigned_partial",
    "reassignment_in_event_count_partial",
    "distinct_bugs_reassigned_in_partial",
    "reassignment_out_event_count_partial",
    "distinct_bugs_reassigned_out_partial",
    "terminalization_event_count_partial",
    "distinct_bugs_terminalized_partial",
    "reopened_event_count_partial",
    "distinct_bugs_reopened_partial",
    "state_events_applied_before_cutoff",
    "latest_included_event_time",
    "evidence_coverage_ratio_within_eligible_cohort",
    "known_limitations",
)

COVERAGE_FIELDS = (
    "prediction_bug_id",
    "prediction_cutoff",
    "data_split",
    "workload_scope",
    "suitable_for_experimental_use",
    "severity_breakdown_supported",
    "source_replay_clean_verified_assignment_bug_count",
    "eligible_bug_cohort_size",
    "eligible_bugs_created_before_cutoff",
    "eligible_active_jdt_bug_count",
    "eligible_active_verified_assignee_bug_count",
    "eligible_active_unverified_or_unassigned_bug_count",
    "verified_developer_pool_size",
    "developers_with_active_observed_bugs_at_cutoff",
    "state_events_applied_before_cutoff",
    "latest_included_event_time",
    "evidence_coverage_ratio_within_eligible_cohort",
    "mismatch_histories_excluded",
    "incomplete_histories_excluded",
    "strict_seed_or_chain_exclusions_from_source_cohort",
    "known_limitations",
)


@dataclass(frozen=True)
class Event:
    bug_id: str
    creation_time: datetime
    event_time: datetime
    activity_index: int
    change_index: int
    field: str
    old_value: str
    new_value: str
    record_index: int


@dataclass(frozen=True)
class TargetCutoff:
    bug_id: str
    cutoff: datetime
    cutoff_text: str
    split: str


@dataclass
class Eligibility:
    events_by_bug: dict[str, list[Event]]
    initial_states: dict[str, dict[str, str]]
    source_cohort_count: int
    eligible_count: int
    exclusions: Counter[str]
    source_eligible_ids: set[str]
    eligible_ids: set[str]
    coverage_by_bug: dict[str, dict[str, str]]


def parse_timestamp(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError(f"Invalid {label} timestamp: {value!r}") from error
    if parsed.tzinfo is None:
        raise ValueError(f"Naive {label} timestamp is not allowed: {value!r}")
    return parsed.astimezone(timezone.utc)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader.fieldnames), list(reader)


def iter_csv_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        yield from reader


def csv_headers(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader.fieldnames)


def canonical(value: str) -> str:
    return value.strip().casefold()


def event_is_before_cutoff(event_time: datetime, cutoff: datetime) -> bool:
    return event_time < cutoff


def load_inputs() -> tuple[Eligibility, list[TargetCutoff], list[str]]:
    identity_fields, identity_rows = read_csv(IDENTITY_PATH)
    if not {"developer_id", "bugzilla_user_id", "bugzilla_email"}.issubset(identity_fields):
        raise ValueError("Verified identity map is missing required columns")
    developer_ids = {row["developer_id"].strip() for row in identity_rows}
    if len(developer_ids) != len(identity_rows) or "" in developer_ids:
        raise ValueError("Verified developer IDs are blank or duplicated")

    coverage_fields, coverage_rows = read_csv(COVERAGE_PATH)
    required_coverage = {
        "bug_id",
        "creation_time",
        "product_at_export",
        "component_at_export",
        "current_status",
        "history_parse_status",
        "replay_consistency",
    }
    if not required_coverage.issubset(coverage_fields):
        raise ValueError("Workload coverage source is missing required columns")
    coverage_by_bug: dict[str, dict[str, str]] = {}
    for row in coverage_rows:
        bug_id = row["bug_id"].strip()
        if not bug_id or bug_id in coverage_by_bug:
            raise ValueError("Coverage source contains a blank or duplicate bug ID")
        parse_timestamp(row["creation_time"], f"bug {bug_id} creation")
        coverage_by_bug[bug_id] = row

    source_eligible_ids: set[str] = set()
    events_by_bug: dict[str, list[Event]] = defaultdict(list)
    # First pass selects exactly the documented 4,542-bug cohort.
    event_fields = csv_headers(EVENTS_PATH)
    required_events = {
        "bug_id",
        "creation_time",
        "event_time",
        "activity_index",
        "change_index",
        "field",
        "old_value",
        "new_value",
        "record_index",
    }
    if not required_events.issubset(event_fields):
        raise ValueError("Lifecycle event source is missing required columns")
    for row in iter_csv_rows(EVENTS_PATH):
        bug_id = row["bug_id"].strip()
        coverage = coverage_by_bug.get(bug_id)
        if coverage is None:
            raise ValueError(f"Event references bug without coverage: {bug_id}")
        if (
            coverage["history_parse_status"] == "parsed"
            and coverage["replay_consistency"] == "pass"
            and row["field"] == "assignee"
            and (
                row["old_value"].strip() in developer_ids
                or row["new_value"].strip() in developer_ids
            )
        ):
            source_eligible_ids.add(bug_id)

    if len(source_eligible_ids) != EXPECTED_SOURCE_COHORT:
        raise ValueError(
            "Dry-run source cohort changed: expected "
            f"{EXPECTED_SOURCE_COHORT}, found {len(source_eligible_ids)}"
        )

    # Second pass retains only that cohort's already-derived events.
    event_keys: set[tuple[str, int, int]] = set()
    for row in iter_csv_rows(EVENTS_PATH):
        bug_id = row["bug_id"].strip()
        if bug_id not in source_eligible_ids:
            continue
        coverage = coverage_by_bug[bug_id]
        creation_time = parse_timestamp(row["creation_time"], f"bug {bug_id} creation")
        event_time = parse_timestamp(row["event_time"], f"bug {bug_id} event")
        if event_time < creation_time:
            raise ValueError(f"Pre-creation event in source cohort: bug {bug_id}")
        try:
            activity_index = int(row["activity_index"])
            change_index = int(row["change_index"])
            record_index = int(row["record_index"])
        except ValueError as error:
            raise ValueError(f"Invalid event index for bug {bug_id}") from error
        if parse_timestamp(coverage["creation_time"], f"coverage bug {bug_id}") != creation_time:
            raise ValueError(f"Event/coverage creation time mismatch for bug {bug_id}")
        event_key = (bug_id, activity_index, change_index)
        if event_key in event_keys:
            raise ValueError(f"Duplicate event key in source cohort: {event_key}")
        event_keys.add(event_key)
        events_by_bug[bug_id].append(
            Event(
                bug_id=bug_id,
                creation_time=creation_time,
                event_time=event_time,
                activity_index=activity_index,
                change_index=change_index,
                field=row["field"].strip(),
                old_value=row["old_value"],
                new_value=row["new_value"],
                record_index=record_index,
            )
        )

    exclusions: Counter[str] = Counter()
    eligible_ids: set[str] = set()
    initial_states: dict[str, dict[str, str]] = {}
    for bug_id in sorted(source_eligible_ids):
        bug_events = sorted(
            events_by_bug[bug_id],
            key=lambda event: (
                event.event_time,
                event.activity_index,
                event.change_index,
            ),
        )
        field_events: dict[str, list[Event]] = defaultdict(list)
        for event in bug_events:
            field_events[event.field].append(event)

        missing_seed = sorted(
            field for field in REQUIRED_STATE_FIELDS if not field_events[field]
        )
        if missing_seed:
            exclusions["missing_seed:" + ",".join(missing_seed)] += 1
            continue
        initial = {
            field: field_events[field][0].old_value
            for field in REQUIRED_STATE_FIELDS
        }
        if not initial["product"].strip() or not initial["status"].strip():
            exclusions["blank_product_or_status_seed"] += 1
            continue
        if any(
            not event.old_value.strip() or not event.new_value.strip()
            for field in ("product", "status")
            for event in field_events[field]
        ):
            exclusions["blank_product_or_status_transition"] += 1
            continue

        broken_fields = []
        for field, changes in field_events.items():
            if any(
                canonical(previous.new_value) != canonical(current.old_value)
                for previous, current in zip(changes, changes[1:])
            ):
                broken_fields.append(field)
        if broken_fields:
            exclusions["broken_chain:" + ",".join(sorted(broken_fields))] += 1
            continue

        final = dict(initial)
        for event in bug_events:
            if event.field in final:
                final[event.field] = event.new_value
        coverage = coverage_by_bug[bug_id]
        if canonical(final["product"]) != canonical(coverage["product_at_export"]):
            exclusions["final_product_replay_mismatch"] += 1
            continue
        if canonical(final["status"]) != canonical(coverage["current_status"]):
            exclusions["final_status_replay_mismatch"] += 1
            continue

        eligible_ids.add(bug_id)
        initial_states[bug_id] = initial
        events_by_bug[bug_id] = bug_events

    if len(eligible_ids) != EXPECTED_STRICT_COHORT:
        raise ValueError(
            "Dry-run strict eligibility changed: expected "
            f"{EXPECTED_STRICT_COHORT}, found {len(eligible_ids)}"
        )

    feature_fields = csv_headers(FEATURES_PATH)
    split_fields, split_rows = read_csv(SPLITS_PATH)
    if not {"bug_id", "prediction_cutoff", "developer_id"}.issubset(feature_fields):
        raise ValueError("Candidate features are missing cutoff/developer fields")
    if not {"bug_id", "prediction_cutoff", "data_split"}.issubset(split_fields):
        raise ValueError("Bug split file is missing required fields")

    split_by_bug: dict[str, tuple[str, str]] = {}
    for row in split_rows:
        bug_id = row["bug_id"].strip()
        if bug_id in split_by_bug:
            raise ValueError(f"Duplicate bug in chronological split: {bug_id}")
        split_by_bug[bug_id] = (row["prediction_cutoff"], row["data_split"])

    feature_developers: dict[str, set[str]] = defaultdict(set)
    feature_rows_per_bug: Counter[str] = Counter()
    feature_cutoffs: dict[str, str] = {}
    seen_feature_keys: set[tuple[str, str]] = set()
    for row in iter_csv_rows(FEATURES_PATH):
        bug_id = row["bug_id"].strip()
        developer_id = row["developer_id"].strip()
        feature_key = (bug_id, developer_id)
        if feature_key in seen_feature_keys:
            raise ValueError(f"Duplicate candidate feature key: {feature_key}")
        seen_feature_keys.add(feature_key)
        feature_rows_per_bug[bug_id] += 1
        cutoff_text = row["prediction_cutoff"].strip()
        parse_timestamp(cutoff_text, f"prediction bug {bug_id}")
        if developer_id not in developer_ids:
            raise ValueError(f"Feature file contains unverified developer: {developer_id}")
        if bug_id in feature_cutoffs and feature_cutoffs[bug_id] != cutoff_text:
            raise ValueError(f"Candidate rows disagree on cutoff for bug {bug_id}")
        feature_cutoffs[bug_id] = cutoff_text
        feature_developers[bug_id].add(developer_id)
        if bug_id not in split_by_bug or split_by_bug[bug_id][0] != cutoff_text:
            raise ValueError(f"Feature/split cutoff mismatch for bug {bug_id}")

    if len(split_by_bug) != EXPECTED_TARGET_BUGS:
        raise ValueError(f"Unexpected target cutoff count: {len(split_by_bug)}")
    expected_developers = developer_ids
    for bug_id, candidates in feature_developers.items():
        if candidates != expected_developers or feature_rows_per_bug[bug_id] != EXPECTED_DEVELOPERS:
            raise ValueError(f"Candidate developer coverage is incomplete for {bug_id}")
    if len(seen_feature_keys) != EXPECTED_TARGET_BUGS * EXPECTED_DEVELOPERS:
        raise ValueError("Candidate feature row count differs from target/developer coverage")
    if set(feature_cutoffs) != set(split_by_bug):
        raise ValueError("Candidate feature and chronological split bug sets differ")

    cutoffs = [
        TargetCutoff(
            bug_id=bug_id,
            cutoff=parse_timestamp(cutoff_text, f"prediction bug {bug_id}"),
            cutoff_text=cutoff_text,
            split=split_by_bug[bug_id][1],
        )
        for bug_id, (cutoff_text, _split) in split_by_bug.items()
    ]
    cutoffs.sort(key=lambda item: (item.cutoff, item.bug_id))
    verify_split_chronology(cutoffs)

    eligibility = Eligibility(
        events_by_bug={
            bug_id: events_by_bug[bug_id]
            for bug_id in sorted(eligible_ids)
        },
        initial_states=initial_states,
        source_cohort_count=len(source_eligible_ids),
        eligible_count=len(eligible_ids),
        exclusions=exclusions,
        source_eligible_ids=source_eligible_ids,
        eligible_ids=eligible_ids,
        coverage_by_bug=coverage_by_bug,
    )
    return eligibility, cutoffs, sorted(developer_ids)


def verify_split_chronology(cutoffs: list[TargetCutoff]) -> None:
    ranges: dict[str, list[datetime]] = defaultdict(list)
    for cutoff in cutoffs:
        ranges[cutoff.split].append(cutoff.cutoff)
    expected = ("train", "validation", "test")
    if set(ranges) != set(expected):
        raise ValueError(f"Unexpected data split values: {sorted(ranges)}")
    if not (
        max(ranges["train"]) <= min(ranges["validation"])
        and max(ranges["validation"]) <= min(ranges["test"])
    ):
        raise ValueError("Bug-level split cutoffs are not chronologically ordered")


def is_active_jdt(state: dict[str, str]) -> bool:
    return (
        canonical(state["product"]) == "jdt"
        and state["status"].strip().upper() not in TERMINAL_STATUSES
    )


def active_owner(state: dict[str, str], developer_ids: set[str]) -> str | None:
    if is_active_jdt(state) and state["assignee"] in developer_ids:
        return state["assignee"]
    return None


def assigned_verified_owner(
    state: dict[str, str], developer_ids: set[str]
) -> str | None:
    if canonical(state["product"]) == "jdt" and state["assignee"] in developer_ids:
        return state["assignee"]
    return None


def add_state(
    state: dict[str, str],
    sign: int,
    developer_ids: set[str],
    active_by_developer: Counter[str],
    eligible_active: Counter[str],
    verified_active: Counter[str],
) -> None:
    if not is_active_jdt(state):
        return
    eligible_active["total"] += sign
    owner = active_owner(state, developer_ids)
    if owner is None:
        eligible_active["unknown_or_unassigned"] += sign
    else:
        active_by_developer[owner] += sign
        verified_active["total"] += sign
    if (
        eligible_active["total"] < 0
        or eligible_active["unknown_or_unassigned"] < 0
        or verified_active["total"] < 0
        or any(value < 0 for value in active_by_developer.values())
    ):
        raise ValueError("Partial workload replay produced a negative active count")


def validate_synthetic_replay() -> None:
    verified = {"dev-a", "dev-b"}
    state = {"product": "JDT", "status": "NEW", "assignee": "dev-a"}
    active = Counter()
    eligible_active = Counter()
    verified_active = Counter()
    add_state(state, 1, verified, active, eligible_active, verified_active)
    assert active["dev-a"] == 1
    add_state(state, -1, verified, active, eligible_active, verified_active)
    state["status"] = "RESOLVED"
    add_state(state, 1, verified, active, eligible_active, verified_active)
    assert active["dev-a"] == 0
    add_state(state, -1, verified, active, eligible_active, verified_active)
    state["status"] = "REOPENED"
    add_state(state, 1, verified, active, eligible_active, verified_active)
    assert active["dev-a"] == 1
    add_state(state, -1, verified, active, eligible_active, verified_active)
    state["assignee"] = "dev-b"
    add_state(state, 1, verified, active, eligible_active, verified_active)
    assert active["dev-a"] == 0 and active["dev-b"] == 1


def build_outputs(
    eligibility: Eligibility,
    cutoffs: list[TargetCutoff],
    developer_ids: list[str],
    output_dir: Path,
) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=False)
    developer_set = set(developer_ids)
    timeline: list[tuple[datetime, int, int, int, str, Event | None]] = []
    for bug_id in eligibility.eligible_ids:
        events = eligibility.events_by_bug[bug_id]
        creation_time = events[0].creation_time
        record_index = events[0].record_index
        timeline.append((creation_time, record_index, 0, -1, bug_id, None))
        for event in events:
            if event.field in ACTIVE_FIELDS:
                timeline.append(
                    (
                        event.event_time,
                        event.record_index,
                        1,
                        event.activity_index,
                        event.bug_id,
                        event,
                    )
                )
    timeline.sort(
        key=lambda item: (
            item[0],
            item[1],
            item[2],
            item[3],
            item[5].change_index if item[5] is not None else -1,
        )
    )

    event_counts: dict[str, Counter[str]] = {
        developer_id: Counter() for developer_id in developer_ids
    }
    event_bugs: dict[str, dict[str, set[str]]] = {
        developer_id: {
            "assigned": set(),
            "reassigned_in": set(),
            "reassigned_out": set(),
            "terminalized": set(),
            "reopened": set(),
        }
        for developer_id in developer_ids
    }
    states: dict[str, dict[str, str]] = {}
    active_by_developer: Counter[str] = Counter()
    eligible_active: Counter[str] = Counter()
    verified_active: Counter[str] = Counter()
    created_count = 0
    processed_event_count = 0
    latest_event_time = ""
    timeline_index = 0
    snapshot_count = 0
    coverage_count = 0
    split_snapshot_counts: Counter[str] = Counter()
    developer_nonzero_snapshot_counts: Counter[str] = Counter()
    developer_max_active: Counter[str] = Counter()
    period_coverage: dict[str, list[float]] = defaultdict(list)
    period_covered_snapshots: Counter[str] = Counter()
    period_snapshot_counts: Counter[str] = Counter()

    snapshots_path = output_dir / SNAPSHOTS_NAME
    coverage_path = output_dir / COVERAGE_NAME
    with (
        snapshots_path.open("w", encoding="utf-8", newline="") as snapshots_stream,
        coverage_path.open("w", encoding="utf-8", newline="") as coverage_stream,
    ):
        snapshots_writer = csv.DictWriter(snapshots_stream, fieldnames=SNAPSHOT_FIELDS)
        coverage_writer = csv.DictWriter(coverage_stream, fieldnames=COVERAGE_FIELDS)
        snapshots_writer.writeheader()
        coverage_writer.writeheader()
        for cutoff in cutoffs:
            while timeline_index < len(timeline) and event_is_before_cutoff(
                timeline[timeline_index][0], cutoff.cutoff
            ):
                time_value, _record, event_kind, _activity, bug_id, event = timeline[timeline_index]
                if event_kind == 0:
                    state = dict(eligibility.initial_states[bug_id])
                    states[bug_id] = state
                    created_count += 1
                    add_state(
                        state,
                        1,
                        developer_set,
                        active_by_developer,
                        eligible_active,
                        verified_active,
                    )
                else:
                    if event is None or bug_id not in states:
                        raise ValueError(f"Lifecycle event precedes creation for {bug_id}")
                    state = states[bug_id]
                    old_owner = active_owner(state, developer_set)
                    if event.field == "assignee":
                        old_value = event.old_value
                        new_value = event.new_value
                        if new_value in developer_set and old_value != new_value:
                            event_counts[new_value]["assigned"] += 1
                            event_bugs[new_value]["assigned"].add(bug_id)
                        if old_value and new_value and old_value != new_value:
                            if new_value in developer_set:
                                event_counts[new_value]["reassigned_in"] += 1
                                event_bugs[new_value]["reassigned_in"].add(bug_id)
                            if old_value in developer_set:
                                event_counts[old_value]["reassigned_out"] += 1
                                event_bugs[old_value]["reassigned_out"].add(bug_id)
                    elif event.field == "status":
                        old_status = event.old_value.strip().upper()
                        new_status = event.new_value.strip().upper()
                        assigned_owner = assigned_verified_owner(state, developer_set)
                        if (
                            old_status not in TERMINAL_STATUSES
                            and new_status in TERMINAL_STATUSES
                            and assigned_owner is not None
                        ):
                            event_counts[assigned_owner]["terminalized"] += 1
                            event_bugs[assigned_owner]["terminalized"].add(bug_id)
                        if (
                            old_status in TERMINAL_STATUSES
                            and new_status == "REOPENED"
                            and assigned_owner is not None
                        ):
                            event_counts[assigned_owner]["reopened"] += 1
                            event_bugs[assigned_owner]["reopened"].add(bug_id)
                    add_state(
                        state,
                        -1,
                        developer_set,
                        active_by_developer,
                        eligible_active,
                        verified_active,
                    )
                    state[event.field] = event.new_value
                    add_state(
                        state,
                        1,
                        developer_set,
                        active_by_developer,
                        eligible_active,
                        verified_active,
                    )
                    processed_event_count += 1
                    latest_event_time = event.event_time.isoformat().replace("+00:00", "Z")
                timeline_index += 1

            active_count = int(eligible_active["total"])
            verified_active_count = int(verified_active["total"])
            unknown_active_count = int(eligible_active["unknown_or_unassigned"])
            if active_count != verified_active_count + unknown_active_count:
                raise ValueError("Active subset coverage counts do not reconcile")
            coverage_ratio = (
                f"{verified_active_count / active_count:.6f}" if active_count else ""
            )
            active_developer_count = sum(
                active_by_developer[developer_id] > 0
                for developer_id in developer_ids
            )
            period = f"{(cutoff.cutoff.year // 5) * 5}-{(cutoff.cutoff.year // 5) * 5 + 4}"
            if active_count:
                period_coverage[period].append(verified_active_count / active_count)
                period_covered_snapshots[period] += 1
            period_snapshot_counts[period] += 1

            shared = {
                "prediction_bug_id": cutoff.bug_id,
                "prediction_cutoff": cutoff.cutoff_text,
                "data_split": cutoff.split,
                "workload_scope": "partial",
                "suitable_for_experimental_use": "true",
                "severity_breakdown_supported": "false",
                "eligible_bug_cohort_size": eligibility.eligible_count,
                "eligible_bugs_created_before_cutoff": created_count,
                "eligible_active_jdt_bug_count": active_count,
                "eligible_active_verified_assignee_bug_count": verified_active_count,
                "eligible_active_unverified_or_unassigned_bug_count": unknown_active_count,
                "verified_developer_pool_size": len(developer_ids),
                "developers_with_active_observed_bugs_at_cutoff": active_developer_count,
                "state_events_applied_before_cutoff": processed_event_count,
                "latest_included_event_time": latest_event_time,
                "evidence_coverage_ratio_within_eligible_cohort": coverage_ratio,
                "known_limitations": PARTIAL_SCOPE_NOTE,
            }
            coverage_row = dict(shared)
            coverage_row.update(
                {
                    "source_replay_clean_verified_assignment_bug_count":
                        eligibility.source_cohort_count,
                    "mismatch_histories_excluded": 13427,
                    "incomplete_histories_excluded": 1880,
                    "strict_seed_or_chain_exclusions_from_source_cohort":
                        eligibility.source_cohort_count - eligibility.eligible_count,
                }
            )
            coverage_writer.writerow(coverage_row)
            coverage_count += 1
            split_snapshot_counts[cutoff.split] += 1
            for developer_id in developer_ids:
                active_for_developer = int(active_by_developer[developer_id])
                developer_max_active[developer_id] = max(
                    developer_max_active[developer_id], active_for_developer
                )
                if active_for_developer:
                    developer_nonzero_snapshot_counts[developer_id] += 1
                counts = event_counts[developer_id]
                bug_sets = event_bugs[developer_id]
                snapshots_writer.writerow(
                    {
                        **shared,
                        "developer_id": developer_id,
                        "active_assigned_bug_count_partial": active_for_developer,
                        "assigned_event_count_partial": counts["assigned"],
                        "distinct_bugs_assigned_partial": len(bug_sets["assigned"]),
                        "reassignment_in_event_count_partial": counts["reassigned_in"],
                        "distinct_bugs_reassigned_in_partial": len(bug_sets["reassigned_in"]),
                        "reassignment_out_event_count_partial": counts["reassigned_out"],
                        "distinct_bugs_reassigned_out_partial": len(bug_sets["reassigned_out"]),
                        "terminalization_event_count_partial": counts["terminalized"],
                        "distinct_bugs_terminalized_partial": len(bug_sets["terminalized"]),
                        "reopened_event_count_partial": counts["reopened"],
                        "distinct_bugs_reopened_partial": len(bug_sets["reopened"]),
                    }
                )
                snapshot_count += 1

    if created_count > eligibility.eligible_count:
        raise ValueError("Created eligible bug count exceeds the cohort size")
    write_reconstruction_report(
        output_dir / RECONSTRUCTION_REPORT_NAME,
        eligibility,
        cutoffs,
        developer_ids,
        snapshot_count,
        coverage_count,
        split_snapshot_counts,
        developer_max_active,
        developer_nonzero_snapshot_counts,
        period_snapshot_counts,
        period_coverage,
        period_covered_snapshots,
    )
    return {
        "snapshot_rows": snapshot_count,
        "coverage_rows": coverage_count,
        "eligible_bug_count": eligibility.eligible_count,
        "source_cohort_count": eligibility.source_cohort_count,
        "target_bug_count": len(cutoffs),
        "developer_count": len(developer_ids),
    }


def write_reconstruction_report(
    path: Path,
    eligibility: Eligibility,
    cutoffs: list[TargetCutoff],
    developer_ids: list[str],
    snapshot_count: int,
    coverage_count: int,
    split_counts: Counter[str],
    developer_max_active: Counter[str],
    developer_nonzero_snapshots: Counter[str],
    period_counts: Counter[str],
    period_coverage: dict[str, list[float]],
    period_covered_snapshots: Counter[str],
) -> None:
    exclusions = ", ".join(
        f"`{reason}`: {count:,}"
        for reason, count in sorted(eligibility.exclusions.items())
    ) or "none"
    dev_lines = [
        "| Verified developer ID | Max active bugs observed in partial cohort | Cutoffs with active bugs |",
        "|---|---:|---:|",
    ]
    for developer_id in developer_ids:
        dev_lines.append(
            f"| `{developer_id}` | {developer_max_active[developer_id]:,} | "
            f"{developer_nonzero_snapshots[developer_id]:,} |"
        )
    period_lines = [
        "| Prediction cutoff period | Cutoff snapshots | Cutoffs with active cohort bugs | Mean evidence coverage on those cutoffs |",
        "|---|---:|---:|---:|",
    ]
    for period in sorted(period_counts):
        ratios = period_coverage[period]
        mean = sum(ratios) / len(ratios) if ratios else None
        mean_text = f"{mean:.4f}" if mean is not None else "n/a"
        period_lines.append(
            f"| {period} | {period_counts[period]:,} | "
            f"{period_covered_snapshots[period]:,} | {mean_text} |"
        )

    lines = [
        "# JDT Partial Workload Reconstruction Report",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}",
        "",
        "## Scope",
        "",
        "This is an experimental partial dataset, not a reconstruction of total developer workload. "
        "The original 6-GB JDT export was not read. Inputs were the existing lifecycle event and "
        "coverage CSVs, verified JDT identity map, candidate feature table, and chronological bug split.",
        "",
        "Only the documented 4,542 replay-clean bugs with a verified developer value in an assignment "
        "event were considered. Strict state seeding and event-chain validation retained "
        f"**{eligibility.eligible_count} bugs**. The other "
        f"{eligibility.source_cohort_count - eligibility.eligible_count:,} source-cohort records were "
        f"excluded: {exclusions}. A missing product seed prevents point-in-time JDT membership from "
        "being established; a missing status seed prevents active/terminal state from being established. "
        "Broken event chains were not repaired.",
        "",
        "## Outputs and coverage",
        "",
        f"- Prediction target cutoffs: {len(cutoffs):,}, taken from existing bug-level chronological splits.",
        f"- Verified JDT candidate developers: {len(developer_ids):,}.",
        f"- Workload snapshot rows: {snapshot_count:,} ({len(cutoffs):,} cutoff bugs × "
        f"{len(developer_ids):,} verified developers).",
        f"- Aggregate cutoff coverage rows: {coverage_count:,}.",
        f"- Data splits: {', '.join(f'{name}={count:,}' for name, count in sorted(split_counts.items()))}.",
        "- Snapshot key: `(prediction_bug_id, prediction_cutoff, developer_id)`; each bug's candidate rows stay together.",
        "- Targets/labels are not included. Cutoffs are from the existing feature/split metadata only.",
        "- Every snapshot has `workload_scope=partial`; complete queue size is never asserted.",
        "",
        "### Per-developer observed coverage",
        "",
        *dev_lines,
        "",
        "Max counts and active-cutoff counts describe only the 228 eligible source histories. They do not measure each developer's total queue.",
        "",
        "### Cutoff period coverage",
        "",
        *period_lines,
        "",
        "The evidence-coverage ratio is the share of active JDT bugs inside this eligible partial cohort whose assignee is one of the nine verified IDs. It is not coverage of all JDT bugs or a developer's real workload.",
        "",
        "## Reconstruction rules",
        "",
        "- A source bug is eligible only when its history was parsed, full replay status was `pass`, and an assignment event contains a verified JDT developer ID.",
        "- Further require explicit first-old seeds for `assignee`, `product`, and `status`; validate every tracked field's old/new chain; reject pre-creation events; and require product/status final parity with retained coverage values.",
        "- Product, status, and assignee state are initialized from their first event's old value. Events are ordered by `(event_time, record_index, activity_index, change_index)`.",
        "- At cutoff `t`, only bug creations and events with timestamps strictly `< t` are applied. An event at exactly the cutoff is excluded.",
        "- A partial active bug is in product JDT and has a non-terminal status. `RESOLVED`, `VERIFIED`, and `CLOSED` are treated as terminal; `REOPENED` restores active status.",
        "- Only the nine verified developer IDs contribute to per-developer counts. Opaque/unmatched accounts and blank assignees are not assigned to a verified person.",
        "- Assignment and reassignment metrics count observed events in this subset before cutoff; distinct-bug columns count unique bug IDs. Terminalization counts transitions into a terminal status while assigned to a verified developer. Reopening counts transitions from a terminal status to `REOPENED` while assigned to a verified developer.",
        "- Severity breakdown is not generated. The derived coverage file lacks current/initial severity for histories without severity changes, so a complete cutoff-safe severity baseline cannot be established.",
        "- Final resolution values are not used as prediction features. Status events alone drive the active/terminal state.",
        "",
        "## Limitations",
        "",
        "- 4,542 replay-clean assignment-history candidates reduced to 228 seedable, chain-consistent bugs. Eight of these do not have a candidate feature/split cutoff, but may still contribute as source bugs at later cutoffs.",
        "- The 13,427 full-source replay mismatches and 1,880 incomplete histories remain excluded; additional bugs outside the 4,542 source cohort are also absent.",
        "- Replay-pass status is not proof that all historical changes were captured. The coverage ratio is conditional on the eligible subset.",
        "- The count of active bugs with an unverified or blank assignee is reported separately; those bugs are not assigned to a developer.",
        "- These values are suitable only for exploratory within-cohort experiments and must not be interpreted as total workload or used as a complete workload feature without an explicit partial-scope policy.",
        "",
    ]
    path.write_text("\\n".join(lines), encoding="utf-8")


def summarize_eligibility(
    eligibility: Eligibility,
    cutoffs: list[TargetCutoff],
    developer_ids: list[str],
) -> None:
    feature_target_ids = {cutoff.bug_id for cutoff in cutoffs}
    split_counts = Counter(cutoff.split for cutoff in cutoffs)
    print(f"Replay-clean verified-assignment source cohort: {eligibility.source_cohort_count:,}")
    print(f"Strict seed/chain-eligible source bugs: {eligibility.eligible_count:,}")
    print(f"Strict eligibility exclusions: {dict(sorted(eligibility.exclusions.items()))}")
    print(
        "Strict source bugs with a target cutoff: "
        f"{len(eligibility.eligible_ids & feature_target_ids):,}; without cutoff: "
        f"{len(eligibility.eligible_ids - feature_target_ids):,}"
    )
    print(f"Prediction target cutoffs: {len(cutoffs):,} ({dict(sorted(split_counts.items()))})")
    print(f"Verified developers: {len(developer_ids):,}")
    print(
        "Dry-run PASS: every source bug to be used has required state seeds, "
        "chronological and chain-consistent events, and current product/status parity."
    )


def run_dry_run() -> tuple[Eligibility, list[TargetCutoff], list[str]]:
    validate_synthetic_replay()
    eligibility, cutoffs, developer_ids = load_inputs()
    summarize_eligibility(eligibility, cutoffs, developer_ids)
    return eligibility, cutoffs, developer_ids


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Check eligibility without writing outputs")
    mode.add_argument("--write", action="store_true", help="Write outputs after eligibility checks pass")
    args = parser.parse_args()

    eligibility, cutoffs, developer_ids = run_dry_run()
    if args.dry_run:
        if OUTPUT_DIR.exists():
            raise FileExistsError(f"Refusing to overwrite existing output directory: {OUTPUT_DIR}")
        return 0

    if OUTPUT_DIR.exists():
        raise FileExistsError(f"Refusing to overwrite existing output directory: {OUTPUT_DIR}")
    PROCESSED.mkdir(parents=True, exist_ok=True)
    staging_parent = Path(
        tempfile.mkdtemp(prefix=".jdt_workload_partial_", dir=PROCESSED)
    )
    staging_dir = staging_parent / OUTPUT_DIR.name
    try:
        result = build_outputs(eligibility, cutoffs, developer_ids, staging_dir)
        if OUTPUT_DIR.exists():
            raise FileExistsError(f"Output directory appeared during build: {OUTPUT_DIR}")
        os.rename(staging_dir, OUTPUT_DIR)
    finally:
        shutil.rmtree(staging_parent, ignore_errors=True)
    print(f"Created {OUTPUT_DIR.relative_to(ROOT)}: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
