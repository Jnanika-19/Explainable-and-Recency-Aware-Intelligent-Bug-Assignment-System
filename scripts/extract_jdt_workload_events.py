"""Stream JDT Bugzilla history and derive workload only when replay is complete."""

from __future__ import annotations

import csv
import hashlib
import heapq
import json
import sqlite3
import tempfile
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dataset" / "processed"
RAW_FILE = ROOT / "dataset" / "raw" / "JDT.csv"
AUDIT_FILE = DATA / "jdt_assignment_label_audit.csv"
PRIMARY_FILE = DATA / "jdt_training_primary.csv"
FEATURE_FILE = DATA / "jdt_point_in_time" / "jdt_candidate_features.csv"
IDENTITY_FILE = (
    DATA
    / "cold_start"
    / "jdt_identity_review"
    / "jdt_verified_identity_map.csv"
)
OUTPUT_DIR = DATA / "jdt_workload"
EVENT_OUTPUT = OUTPUT_DIR / "jdt_assignment_lifecycle_events.csv"
COVERAGE_OUTPUT = OUTPUT_DIR / "jdt_bug_history_coverage.csv"
WORKLOAD_OUTPUT = OUTPUT_DIR / "jdt_point_in_time_workload.csv"
REPORT_OUTPUT = ROOT / "research" / "dataset_documentation" / (
    "jdt_workload_event_scan_report.md"
)

RAW_FIELDS = (
    "ID",
    "Product",
    "Component",
    "Creation time",
    "Assigned to",
    "Status",
    "Resolution",
    "Severity",
    "Priority",
    "History/Activity Log",
)

FIELD_ALIASES = {
    "assigned_to": "assignee",
    "product": "product",
    "component": "component",
    "bug_status": "status",
    "status": "status",
    "resolution": "resolution",
    "bug_severity": "severity",
    "severity": "severity",
    "priority": "priority",
}
TEXT_HISTORY_FIELDS = {"description", "short_desc", "summary"}
TERMINAL_STATUSES = {"RESOLVED", "VERIFIED", "CLOSED"}
PRIORITY_BUCKETS = ("P1", "P2", "P3", "P4", "P5", "other")
SEVERITY_BUCKETS = (
    "blocker",
    "critical",
    "major",
    "normal",
    "minor",
    "trivial",
    "other",
)


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def utc_timestamp(value: str) -> tuple[str, bool]:
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return "", False
    if parsed.tzinfo is None:
        return "", False
    normalized = parsed.astimezone(timezone.utc)
    return normalized.isoformat(timespec="microseconds").replace("+00:00", "Z"), True


def canonical(field: str, value: str) -> str:
    normalized = value.strip()
    if field in {"assignee", "product", "component", "status", "resolution", "severity", "priority"}:
        return normalized.casefold()
    return normalized


def opaque_assignee(value: str, developer_by_email: dict[str, str]) -> str:
    email = value.strip().casefold()
    if not email:
        return ""
    verified_id = developer_by_email.get(email)
    if verified_id:
        return verified_id
    digest = hashlib.sha256(f"jdt-assignee:{email}".encode("utf-8")).hexdigest()
    return f"jdt_assignee_{digest[:16]}"


def make_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA temp_store=FILE")
    connection.execute(
        """
        CREATE TABLE bugs (
            record_index INTEGER PRIMARY KEY,
            bug_id TEXT NOT NULL,
            creation_time TEXT NOT NULL,
            current_product TEXT NOT NULL,
            current_component TEXT NOT NULL,
            current_assignee TEXT NOT NULL,
            current_status TEXT NOT NULL,
            current_resolution TEXT NOT NULL,
            current_severity TEXT NOT NULL,
            current_priority TEXT NOT NULL,
            initial_product TEXT NOT NULL,
            initial_component TEXT NOT NULL,
            initial_assignee TEXT NOT NULL,
            initial_status TEXT NOT NULL,
            initial_resolution TEXT NOT NULL,
            initial_severity TEXT NOT NULL,
            initial_priority TEXT NOT NULL,
            history_parse_status TEXT NOT NULL,
            replay_consistency TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE events (
            record_index INTEGER NOT NULL,
            bug_id TEXT NOT NULL,
            event_time TEXT NOT NULL,
            activity_index INTEGER NOT NULL,
            change_index INTEGER NOT NULL,
            logical_field TEXT NOT NULL,
            source_field_name TEXT NOT NULL,
            old_value TEXT NOT NULL,
            new_value TEXT NOT NULL
        )
        """
    )
    return connection


def current_state(row: dict[str, str]) -> dict[str, str]:
    return {
        "product": clean(row.get("Product", "")),
        "component": clean(row.get("Component", "")),
        "assignee": clean(row.get("Assigned to", "")),
        "status": clean(row.get("Status", "")),
        "resolution": clean(row.get("Resolution", "")),
        "severity": clean(row.get("Severity", "")),
        "priority": clean(row.get("Priority", "")),
    }


def parse_bug_history(
    raw_history: str,
    creation_time: str,
    current: dict[str, str],
    record_index: int,
    bug_id: str,
    counters: Counter[str],
    field_counts: Counter[str],
) -> tuple[
    str,
    list[tuple[str, int, int, str, str, str, str]],
    dict[str, str],
    str,
    int,
    int,
]:
    if not raw_history.strip():
        return "missing", [], current.copy(), "not_testable_no_history", 0, 0
    try:
        activities = json.loads(raw_history)
    except (json.JSONDecodeError, TypeError):
        counters["invalid_json_rows"] += 1
        return "invalid_json", [], current.copy(), "not_testable_invalid_history", 0, 0
    if not isinstance(activities, list):
        counters["invalid_history_shape_rows"] += 1
        return "invalid_shape", [], current.copy(), "not_testable_invalid_history", 0, 0
    if not activities:
        counters["empty_history_rows"] += 1
        return "empty", [], current.copy(), "not_testable_empty_history", 0, 0

    creation_normalized, creation_valid = utc_timestamp(creation_time)

    parsed_activities: list[tuple[str, int, list[dict[str, object]]]] = []
    malformed_event = False
    timestamp_invalid = 0
    text_changes = 0
    for activity_index, activity in enumerate(activities):
        if not isinstance(activity, dict):
            malformed_event = True
            counters["invalid_activity_objects"] += 1
            continue
        event_time, time_valid = utc_timestamp(clean(activity.get("when", "")))
        changes = activity.get("changes")
        if not time_valid:
            timestamp_invalid += 1
            counters["invalid_event_timestamps"] += 1
        if not isinstance(changes, list):
            malformed_event = True
            counters["invalid_activity_changes"] += 1
            continue
        event_changes: list[dict[str, object]] = []
        for change_index, change in enumerate(changes):
            if not isinstance(change, dict):
                malformed_event = True
                counters["invalid_change_objects"] += 1
                continue
            field_name = clean(change.get("field_name", ""))
            field_key = field_name.casefold()
            field_counts[field_key] += 1
            if field_key in TEXT_HISTORY_FIELDS:
                text_changes += 1
                if "removed" in change:
                    counters["text_changes_with_old_value_field"] += 1
                else:
                    counters["text_changes_without_old_value_field"] += 1
                if "added" in change:
                    counters["text_changes_with_new_value_field"] += 1
                else:
                    counters["text_changes_without_new_value_field"] += 1
                if "removed" in change and "added" in change:
                    counters["text_changes_with_both_value_fields"] += 1
            logical_field = FIELD_ALIASES.get(field_key)
            if logical_field is None:
                continue
            if not time_valid:
                continue
            old_present = "removed" in change
            new_present = "added" in change
            old_value = clean(change.get("removed")) if old_present else ""
            new_value = clean(change.get("added")) if new_present else ""
            event_changes.append(
                {
                    "change_index": change_index,
                    "field_name": field_name,
                    "logical_field": logical_field,
                    "old_present": old_present,
                    "new_present": new_present,
                    "old_value": old_value,
                    "new_value": new_value,
                }
            )
        if time_valid:
            parsed_activities.append((event_time, activity_index, event_changes))

    if timestamp_invalid:
        counters["rows_with_invalid_history_timestamps"] += 1
    parsed_activities.sort(key=lambda activity: (activity[0], activity[1]))
    if creation_valid and any(event_time < creation_normalized for event_time, _, _ in parsed_activities):
        counters["events_before_bug_creation"] += sum(
            event_time < creation_normalized
            for event_time, _, _ in parsed_activities
        )

    tracked: list[tuple[str, int, int, str, str, str, str]] = []
    first_old: dict[str, str] = {}
    missing_state_value = False
    assignment_changes = 0
    status_changes = 0
    resolution_changes = 0
    product_changes = 0
    component_changes = 0
    severity_changes = 0
    priority_changes = 0
    for event_time, activity_index, changes in parsed_activities:
        for change in changes:
            field = str(change["logical_field"])
            old_value = str(change["old_value"])
            new_value = str(change["new_value"])
            if field not in first_old:
                first_old[field] = old_value
            if not bool(change["old_present"]) or not bool(change["new_present"]):
                missing_state_value = True
                counters["tracked_changes_missing_old_or_new"] += 1
            tracked.append(
                (
                    event_time,
                    activity_index,
                    int(change["change_index"]),
                    field,
                    str(change["field_name"]),
                    old_value,
                    new_value,
                )
            )
            counters[f"{field}_changes"] += 1
            if field == "assignee":
                assignment_changes += 1
            elif field == "status":
                status_changes += 1
            elif field == "resolution":
                resolution_changes += 1
            elif field == "product":
                product_changes += 1
            elif field == "component":
                component_changes += 1
            elif field == "severity":
                severity_changes += 1
            elif field == "priority":
                priority_changes += 1
    tracked.sort(key=lambda event: (event[0], event[1], event[2]))

    initial = current.copy()
    for field, old_value in first_old.items():
        initial[field] = old_value
    replay = initial.copy()
    for _event_time, _activity_index, _change_index, field, _name, _old, new in tracked:
        replay[field] = new
    mismatches = [
        field
        for field in first_old
        if canonical(field, replay[field]) != canonical(field, current[field])
    ]
    replay_status = "pass" if not mismatches else "mismatch:" + ";".join(mismatches)
    if mismatches:
        counters["state_replay_mismatch_rows"] += 1
    if missing_state_value:
        counters["rows_with_missing_tracked_old_or_new"] += 1
    if malformed_event:
        status = "invalid_event"
        counters["invalid_history_event_rows"] += 1
    elif timestamp_invalid:
        status = "invalid_timestamp"
    else:
        status = "parsed"
        counters["parsed_nonempty_history_rows"] += 1
    if not creation_valid:
        replay_status = "not_testable_invalid_creation_time"
    elif any(
        not initial[field].strip()
        for field in ("product", "component", "status", "severity", "priority")
    ):
        replay_status = "incomplete_initial_state"
    elif missing_state_value:
        replay_status = "incomplete_change_values"
    elif counters["events_before_bug_creation"] and any(
        event[0] < creation_normalized for event in tracked
    ):
        replay_status = "events_before_creation"

    counters["tracked_lifecycle_changes"] += len(tracked)
    counters["history_text_change_events"] += text_changes
    return (
        status,
        tracked,
        initial,
        replay_status,
        len(activities),
        text_changes,
    )


def load_verified_developers() -> tuple[dict[str, str], set[str]]:
    developer_by_email: dict[str, str] = {}
    developer_ids: set[str] = set()
    with IDENTITY_FILE.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            email = row["bugzilla_email"].strip().casefold()
            developer_id = row["developer_id"].strip()
            if not email or not developer_id:
                raise ValueError("Verified identity map contains a blank key")
            if email in developer_by_email or developer_id in developer_ids:
                raise ValueError("Verified identity map is not one-to-one")
            developer_by_email[email] = developer_id
            developer_ids.add(developer_id)
    return developer_by_email, developer_ids


def scan_raw_to_staging(
    connection: sqlite3.Connection,
    coverage_path: Path,
    developer_by_email: dict[str, str],
) -> tuple[Counter[str], Counter[str], int, int]:
    counters: Counter[str] = Counter()
    field_counts: Counter[str] = Counter()
    coverage_fields = (
        "record_index",
        "bug_id",
        "creation_time",
        "product_at_export",
        "component_at_export",
        "current_assignee_is_verified_candidate",
        "current_status",
        "current_resolution",
        "history_parse_status",
        "source_history_event_count",
        "tracked_lifecycle_change_count",
        "assignment_change_count",
        "status_change_count",
        "resolution_change_count",
        "product_change_count",
        "component_change_count",
        "severity_change_count",
        "priority_change_count",
        "text_revision_change_count",
        "replay_consistency",
    )
    row_count = 0
    batch: list[tuple[object, ...]] = []
    seen_bug_ids: set[str] = set()
    with coverage_path.open("w", encoding="utf-8", newline="") as coverage_file:
        writer = csv.DictWriter(coverage_file, fieldnames=coverage_fields)
        writer.writeheader()
        with RAW_FILE.open(encoding="utf-8-sig", newline="") as raw_file:
            reader = csv.DictReader(raw_file)
            missing_columns = set(RAW_FIELDS).difference(reader.fieldnames or [])
            if missing_columns:
                raise ValueError(f"Raw export is missing columns: {sorted(missing_columns)}")
            csv.field_size_limit(2_000_000_000)
            for record_index, row in enumerate(reader):
                row_count += 1
                if None in row:
                    counters["malformed_csv_rows"] += 1
                bug_id = clean(row.get("ID", ""))
                if not bug_id:
                    counters["missing_bug_id_rows"] += 1
                if bug_id in seen_bug_ids:
                    counters["duplicate_bug_id_rows"] += 1
                seen_bug_ids.add(bug_id)
                current = current_state(row)
                raw_history = clean(row.get("History/Activity Log", ""))
                (
                    history_status,
                    tracked,
                    initial,
                    replay_status,
                    activity_count,
                    text_change_count,
                ) = parse_bug_history(
                    raw_history,
                    clean(row.get("Creation time", "")),
                    current,
                    record_index,
                    bug_id,
                    counters,
                    field_counts,
                )
                creation_time, creation_valid = utc_timestamp(
                    clean(row.get("Creation time", ""))
                )
                if not creation_valid:
                    counters["invalid_creation_timestamp_rows"] += 1
                current_assignee_email = current["assignee"].casefold()
                current["assignee"] = current_assignee_email
                initial["assignee"] = initial["assignee"].casefold()
                if not bug_id or not creation_valid or not current["status"] or not current["product"]:
                    counters["rows_with_missing_required_current_state"] += 1
                state_counts = Counter(
                    event[3] for event in tracked
                )
                if history_status in {"missing", "empty", "invalid_json", "invalid_shape", "invalid_event", "invalid_timestamp"}:
                    counters[f"history_status_{history_status}"] += 1
                if replay_status == "pass":
                    counters["replay_pass_rows"] += 1
                elif replay_status.startswith("mismatch"):
                    counters["replay_mismatch_rows"] += 1
                elif replay_status.startswith("incomplete"):
                    counters["replay_incomplete_rows"] += 1
                elif replay_status.startswith("events_before"):
                    counters["replay_before_creation_rows"] += 1
                else:
                    counters["replay_not_testable_rows"] += 1

                batch.append(
                    (
                        record_index,
                        bug_id,
                        creation_time,
                        current["product"],
                        current["component"],
                        current_assignee_email,
                        current["status"],
                        current["resolution"],
                        current["severity"],
                        current["priority"],
                        initial["product"],
                        initial["component"],
                        initial["assignee"],
                        initial["status"],
                        initial["resolution"],
                        initial["severity"],
                        initial["priority"],
                        history_status,
                        replay_status,
                    )
                )
                for event in tracked:
                    event_time, activity_index, change_index, field, name, old, new = event
                    batch.append(
                        (
                            "EVENT",
                            record_index,
                            bug_id,
                            event_time,
                            activity_index,
                            change_index,
                            field,
                            name,
                            old,
                            new,
                        )
                    )
                connection.execute(
                    """
                    INSERT INTO bugs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    batch.pop(0),
                )
                event_rows = [item for item in batch if item and item[0] == "EVENT"]
                batch.clear()
                if event_rows:
                    connection.executemany(
                        """
                        INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)
                        """,
                        [
                            (
                                item[1],
                                item[2],
                                item[3],
                                item[4],
                                item[5],
                                item[6],
                                item[7],
                                item[8],
                                item[9],
                            )
                            for item in event_rows
                        ],
                    )
                assignment_count = state_counts["assignee"]
                status_count = state_counts["status"]
                resolution_count = state_counts["resolution"]
                product_count = state_counts["product"]
                component_count = state_counts["component"]
                severity_count = state_counts["severity"]
                priority_count = state_counts["priority"]
                writer.writerow(
                    {
                        "record_index": record_index,
                        "bug_id": bug_id,
                        "creation_time": clean(row.get("Creation time", "")),
                        "product_at_export": clean(row.get("Product", "")),
                        "component_at_export": clean(row.get("Component", "")),
                        "current_assignee_is_verified_candidate": str(
                            current_assignee_email in developer_by_email
                        ).lower(),
                        "current_status": clean(row.get("Status", "")),
                        "current_resolution": clean(row.get("Resolution", "")),
                        "history_parse_status": history_status,
                        "source_history_event_count": activity_count,
                        "tracked_lifecycle_change_count": len(tracked),
                        "assignment_change_count": assignment_count,
                        "status_change_count": status_count,
                        "resolution_change_count": resolution_count,
                        "product_change_count": product_count,
                        "component_change_count": component_count,
                        "severity_change_count": severity_count,
                        "priority_change_count": priority_count,
                        "text_revision_change_count": text_change_count,
                        "replay_consistency": replay_status,
                    }
                )
                if row_count % 1000 == 0:
                    print(
                        f"Scanned {row_count:,} raw bug records; "
                        f"{counters['tracked_lifecycle_changes']:,} lifecycle changes"
                    )
    connection.commit()
    counters["raw_bug_rows"] = row_count
    counters["unique_bug_ids"] = len(seen_bug_ids)
    counters["tracked_event_rows"] = connection.execute(
        "SELECT COUNT(*) FROM events"
    ).fetchone()[0]
    return counters, field_counts, row_count, len(seen_bug_ids)


def write_event_output(
    connection: sqlite3.Connection,
    path: Path,
    developer_by_email: dict[str, str],
) -> int:
    fields = (
        "record_index",
        "bug_id",
        "creation_time",
        "event_time",
        "activity_index",
        "change_index",
        "field",
        "source_field_name",
        "old_value",
        "new_value",
    )
    row_count = 0
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        cursor = connection.execute(
            """
            SELECT e.record_index, e.bug_id, b.creation_time, e.event_time,
                   e.activity_index, e.change_index, e.logical_field,
                   e.source_field_name, e.old_value, e.new_value
            FROM events e
            JOIN bugs b ON b.record_index = e.record_index
            ORDER BY e.record_index, e.event_time, e.activity_index, e.change_index
            """
        )
        for row in cursor:
            field = row[6]
            old_value = row[8]
            new_value = row[9]
            if field == "assignee":
                old_value = opaque_assignee(old_value, developer_by_email)
                new_value = opaque_assignee(new_value, developer_by_email)
            writer.writerow(
                {
                    "record_index": row[0],
                    "bug_id": row[1],
                    "creation_time": row[2],
                    "event_time": row[3],
                    "activity_index": row[4],
                    "change_index": row[5],
                    "field": field,
                    "source_field_name": row[7],
                    "old_value": old_value,
                    "new_value": new_value,
                }
            )
            row_count += 1
    return row_count


def active_contribution(state: dict[str, str], developer_by_email: dict[str, str]):
    if state["product"].strip().casefold() != "jdt":
        return None
    if state["status"].strip().upper() in TERMINAL_STATUSES:
        return None
    developer_id = developer_by_email.get(state["assignee"].strip().casefold())
    if not developer_id:
        return None
    return developer_id


def priority_bucket(value: str) -> str:
    priority = value.strip().upper()
    return priority if priority in PRIORITY_BUCKETS[:-1] else "other"


def severity_bucket(value: str) -> str:
    severity = value.strip().casefold()
    return severity if severity in SEVERITY_BUCKETS[:-1] else "other"


def add_workload(
    state: dict[str, str],
    delta: int,
    developer_by_email: dict[str, str],
    totals: Counter[str],
    by_component: dict[str, Counter[str]],
    by_priority: dict[str, Counter[str]],
    by_severity: dict[str, Counter[str]],
) -> None:
    developer_id = active_contribution(state, developer_by_email)
    if not developer_id:
        return
    totals[developer_id] += delta
    component = state["component"].strip()
    by_component[developer_id][component] += delta
    by_priority[developer_id][priority_bucket(state["priority"])] += delta
    by_severity[developer_id][severity_bucket(state["severity"])] += delta
    if (
        totals[developer_id] < 0
        or by_component[developer_id][component] < 0
        or by_priority[developer_id][priority_bucket(state["priority"])] < 0
        or by_severity[developer_id][severity_bucket(state["severity"])] < 0
    ):
        raise ValueError("Workload replay produced a negative active count")


def create_timeline_stream(connection: sqlite3.Connection):
    create_cursor = connection.execute(
        """
        SELECT creation_time, record_index, bug_id, initial_product,
               initial_component, initial_assignee, initial_status,
               initial_resolution, initial_severity, initial_priority
        FROM bugs
        ORDER BY creation_time, record_index
        """
    )
    change_cursor = connection.execute(
        """
        SELECT e.event_time, e.record_index, e.activity_index, e.change_index,
               e.bug_id, e.logical_field, e.new_value
        FROM events e
        ORDER BY e.event_time, e.record_index, e.activity_index, e.change_index
        """
    )

    def creates():
        for row in create_cursor:
            yield (
                row[0],
                row[1],
                0,
                -1,
                -1,
                "CREATE",
                row[2],
                {
                    "product": row[3],
                    "component": row[4],
                    "assignee": row[5],
                    "status": row[6],
                    "resolution": row[7],
                    "severity": row[8],
                    "priority": row[9],
                },
            )

    def changes():
        for row in change_cursor:
            yield (
                row[0],
                row[1],
                1,
                row[2],
                row[3],
                row[5],
                row[4],
                row[6],
            )

    return heapq.merge(
        creates(),
        changes(),
        key=lambda item: (item[0], item[1], item[2], item[3], item[4]),
    )


def derive_workload(
    connection: sqlite3.Connection,
    staged_path: Path,
    developer_by_email: dict[str, str],
    developer_ids: set[str],
) -> int:
    queries = []
    with FEATURE_FILE.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            queries.append(
                (
                    utc_timestamp(row["prediction_cutoff"])[0],
                    row["bug_id"],
                    row["component"],
                    row["developer_id"],
                    row["prediction_cutoff"],
                )
            )
    if not queries or any(not item[0] for item in queries):
        raise ValueError("Candidate feature cutoffs are missing or invalid")
    queries.sort(key=lambda item: (item[0], item[1], item[3]))
    if {item[3] for item in queries} != developer_ids:
        raise ValueError("Workload candidate IDs do not match the verified map")

    fields = (
        "bug_id",
        "prediction_cutoff",
        "component",
        "developer_id",
        "active_assigned_bug_count",
        "active_same_component_bug_count",
        *(f"active_priority_{value.casefold()}_count" for value in PRIORITY_BUCKETS),
        *(f"active_severity_{value}_count" for value in SEVERITY_BUCKETS),
    )
    totals: Counter[str] = Counter()
    by_component: dict[str, Counter[str]] = defaultdict(Counter)
    by_priority: dict[str, Counter[str]] = defaultdict(Counter)
    by_severity: dict[str, Counter[str]] = defaultdict(Counter)
    states: dict[str, dict[str, str]] = {}
    timeline = iter(create_timeline_stream(connection))
    next_event = next(timeline, None)
    row_count = 0
    with staged_path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        for cutoff, bug_id, component, developer_id, cutoff_source in queries:
            while next_event and next_event[0] < cutoff:
                event = next_event
                event_bug_id = event[6]
                if event[5] == "CREATE":
                    state = event[7]
                    states[event_bug_id] = state
                    add_workload(
                        state,
                        1,
                        developer_by_email,
                        totals,
                        by_component,
                        by_priority,
                        by_severity,
                    )
                else:
                    state = states.get(event_bug_id)
                    if state is None:
                        raise ValueError(
                            f"Lifecycle change precedes bug creation: {event_bug_id}"
                        )
                    add_workload(
                        state,
                        -1,
                        developer_by_email,
                        totals,
                        by_component,
                        by_priority,
                        by_severity,
                    )
                    state[event[5]] = clean(event[7])
                    add_workload(
                        state,
                        1,
                        developer_by_email,
                        totals,
                        by_component,
                        by_priority,
                        by_severity,
                    )
                next_event = next(timeline, None)

            if developer_id not in developer_ids:
                raise ValueError(f"Unknown candidate developer ID: {developer_id}")
            writer.writerow(
                {
                    "bug_id": bug_id,
                    "prediction_cutoff": cutoff_source,
                    "component": component,
                    "developer_id": developer_id,
                    "active_assigned_bug_count": totals[developer_id],
                    "active_same_component_bug_count": by_component[developer_id][component],
                    **{
                        f"active_priority_{value.casefold()}_count":
                            by_priority[developer_id][value]
                        for value in PRIORITY_BUCKETS
                    },
                    **{
                        f"active_severity_{value}_count":
                            by_severity[developer_id][value]
                        for value in SEVERITY_BUCKETS
                    },
                }
            )
            row_count += 1

    if row_count != len(queries):
        raise ValueError("Workload output row count differs from candidate features")
    return row_count


def write_report(
    path: Path,
    counters: Counter[str],
    field_counts: Counter[str],
    row_count: int,
    unique_bug_count: int,
    event_rows: int,
    workload_rows: int,
    workload_supported: bool,
    output_paths: list[Path],
    elapsed_seconds: float,
    raw_bytes: int,
    raw_mtime: str,
    output_sizes: dict[Path, int],
) -> None:
    lines = [
        "# JDT Workload Event Scan Report",
        "",
        f"Scan date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}",
        "",
        "## Scope and source",
        "",
        "- Source: `dataset/raw/JDT.csv` (read-only, one streaming pass).",
        f"- Source size before/after scan: {raw_bytes:,} bytes.",
        f"- Source last-write time before/after scan: `{raw_mtime}`.",
        "- Read fields: bug ID, product, component, creation time, assignee, status, resolution, severity, priority, and `History/Activity Log`. Summary, description, comments, and reporter identity values were not exported.",
        "- Assignee values in derived event output are represented by stable opaque JDT account keys; exact verified identities use the existing JDT-only developer IDs. No name-based identity merging was performed.",
        "",
        "## Scan results",
        "",
        f"- Raw records: {row_count:,}; unique bug IDs: {unique_bug_count:,}.",
        f"- History rows with non-empty, valid activity lists: {counters['parsed_nonempty_history_rows']:,}.",
        f"- Missing/empty/invalid histories: {counters['history_status_missing'] + counters['history_status_empty'] + counters['history_status_invalid_json'] + counters['history_status_invalid_shape'] + counters['history_status_invalid_event'] + counters['history_status_invalid_timestamp']:,}.",
        f"- Tracked lifecycle changes extracted: {counters['tracked_event_rows']:,}.",
        f"- Rows whose final replay matched current raw state: {counters['replay_pass_rows']:,}.",
        f"- State-replay mismatch rows: {counters['replay_mismatch_rows']:,}; incomplete/not-testable rows: {counters['replay_incomplete_rows'] + counters['replay_not_testable_rows'] + counters['replay_before_creation_rows']:,}.",
        f"- Invalid event timestamps: {counters['invalid_event_timestamps']:,}; events before bug creation: {counters['events_before_bug_creation']:,}; duplicate bug IDs: {counters['duplicate_bug_id_rows']:,}; malformed CSV rows: {counters['malformed_csv_rows']:,}.",
        f"- Text-change metadata events (`summary`/`description` fields) observed: {counters['history_text_change_events']:,}; text values were not exported.",
        f"- Text-change entries with both old/new fields: {counters['text_changes_with_both_value_fields']:,}; inspect timestamps and field semantics before attempting historical text reconstruction.",
        "",
        "### History field counts",
        "",
        "| History field | Changes |",
        "|---|---:|",
    ]
    for field, count in sorted(field_counts.items()):
        lines.append(f"| `{field}` | {count:,} |")
    lines.extend(["", "## Workload decision", ""])
    if workload_supported:
        lines.extend(
            [
                f"**Point-in-time workload generated:** {workload_rows:,} bug/developer rows.",
                "The workload uses only events strictly earlier than each bug-creation cutoff. A bug is counted when its historical product is JDT, its status is not `RESOLVED`, `VERIFIED`, or `CLOSED`, and its assigned account maps to one of the 9 conservative JDT developers.",
                "The output includes active total, same-component, priority-bucket, and severity-bucket counts. It does not apply an arbitrary severity/priority weight.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "**Point-in-time workload not generated.** The scanned history did not meet the completeness/replay criteria. The event and coverage outputs retain the observed evidence, but missing or invalid history prevents reliable active-queue reconstruction; no workload values were guessed.",
                "",
            ]
        )
    lines.extend(
        [
            "## Validation and limitations",
            "",
            "- Every raw bug row has a coverage record; all parseable lifecycle change events are retained in the event file.",
            "- Derived assignee keys are pseudonymous account keys, not person merges. Unmatched email accounts remain separate.",
            "- Current-state replay consistency checks compare the first recorded old value and chronological changes with current product/component/assignee/status/resolution/severity/priority values.",
            "- Historical text-change counts only establish that summary/description field changes were recorded; text bodies and snapshots were not exported or indexed.",
            "- A current export may not prove complete historical coverage merely because replay reaches the current values. Missing history, unresolved aliases, or unrecorded transitions remain limitations.",
            f"- Scan elapsed time: {elapsed_seconds:.1f} seconds. Derived-output sizes: {sum(output_sizes.values()):,} bytes.",
            "",
            "## Outputs",
            "",
        ]
    )
    for output in output_paths:
        lines.append(
            f"- `{output.relative_to(ROOT).as_posix()}` "
            f"({output_sizes.get(output, 0):,} bytes)"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run() -> None:
    if EVENT_OUTPUT.exists() or COVERAGE_OUTPUT.exists() or WORKLOAD_OUTPUT.exists() or REPORT_OUTPUT.exists():
        raise FileExistsError("Refusing to overwrite any JDT workload output")
    if not RAW_FILE.is_file() or not FEATURE_FILE.is_file() or not IDENTITY_FILE.is_file():
        raise FileNotFoundError("Required raw, feature, or identity input is missing")

    raw_stat = RAW_FILE.stat()
    raw_bytes = raw_stat.st_size
    raw_mtime = datetime.fromtimestamp(
        raw_stat.st_mtime, timezone.utc
    ).isoformat(timespec="seconds")
    developer_by_email, developer_ids = load_verified_developers()
    start = time.perf_counter()

    with tempfile.TemporaryDirectory(
        prefix=".jdt_workload_scan_", dir=DATA
    ) as temporary_directory:
        temp_root = Path(temporary_directory)
        database_path = temp_root / "workload_scan.sqlite"
        staged_coverage = temp_root / "jdt_bug_history_coverage.csv"
        staged_events = temp_root / "jdt_assignment_lifecycle_events.csv"
        staged_workload = temp_root / "jdt_point_in_time_workload.csv"
        connection = make_database(database_path)
        try:
            counters, field_counts, row_count, unique_bug_count = scan_raw_to_staging(
                connection, staged_coverage, developer_by_email
            )
            connection.execute(
                "CREATE INDEX events_by_time ON events(event_time, record_index, activity_index, change_index)"
            )
            connection.commit()
            event_rows = write_event_output(
                connection, staged_events, developer_by_email
            )

            history_complete = (
                counters["raw_bug_rows"] == counters["unique_bug_ids"]
                and counters["malformed_csv_rows"] == 0
                and counters["missing_bug_id_rows"] == 0
                and counters["invalid_creation_timestamp_rows"] == 0
                and counters["invalid_event_timestamps"] == 0
                and counters["events_before_bug_creation"] == 0
                and counters["tracked_changes_missing_old_or_new"] == 0
                and counters["state_replay_mismatch_rows"] == 0
                and counters["replay_incomplete_rows"] == 0
                and counters["replay_not_testable_rows"] == 0
                and counters["replay_before_creation_rows"] == 0
                and counters["parsed_nonempty_history_rows"] == row_count
                and counters["status_changes"] > 0
                and counters["resolution_changes"] > 0
                and counters["rows_with_missing_required_current_state"] == 0
            )
            workload_rows = 0
            if history_complete:
                workload_rows = derive_workload(
                    connection,
                    staged_workload,
                    developer_by_email,
                    developer_ids,
                )
            else:
                counters["workload_completeness_gate_failed"] = 1
        finally:
            connection.close()

        current_stat = RAW_FILE.stat()
        if current_stat.st_size != raw_bytes or current_stat.st_mtime != raw_stat.st_mtime:
            raise RuntimeError("Raw JDT source changed during the read-only scan")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        staged_outputs = [
            (staged_events, EVENT_OUTPUT),
            (staged_coverage, COVERAGE_OUTPUT),
        ]
        if history_complete:
            staged_outputs.append((staged_workload, WORKLOAD_OUTPUT))
        for _source, destination in staged_outputs:
            if destination.exists():
                raise FileExistsError(f"Refusing to overwrite {destination}")
        for source, destination in staged_outputs:
            source.rename(destination)

    elapsed_seconds = time.perf_counter() - start
    output_paths = [EVENT_OUTPUT, COVERAGE_OUTPUT]
    if history_complete:
        output_paths.append(WORKLOAD_OUTPUT)
    output_sizes = {path: path.stat().st_size for path in output_paths}
    write_report(
        REPORT_OUTPUT,
        counters,
        field_counts,
        row_count,
        unique_bug_count,
        event_rows,
        workload_rows,
        history_complete,
        output_paths,
        elapsed_seconds,
        raw_bytes,
        raw_mtime,
        output_sizes,
    )
    print(f"Raw rows: {row_count:,}; unique bug IDs: {unique_bug_count:,}")
    print(f"History state replay passes: {counters['replay_pass_rows']:,}")
    print(f"History state replay mismatches: {counters['replay_mismatch_rows']:,}")
    print(f"Tracked lifecycle events written: {event_rows:,}")
    print(f"Workload complete: {history_complete}; workload rows: {workload_rows:,}")
    print(f"Event and coverage outputs: {EVENT_OUTPUT.relative_to(ROOT)}; {COVERAGE_OUTPUT.relative_to(ROOT)}")
    if history_complete:
        print(f"Workload output: {WORKLOAD_OUTPUT.relative_to(ROOT)}")
    print(f"Report: {REPORT_OUTPUT.relative_to(ROOT)}")
    print(f"Scan elapsed seconds: {elapsed_seconds:.1f}")


if __name__ == "__main__":
    run()
