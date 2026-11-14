import csv
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "dataset" / "processed" / "jdt_workload"
EVENTS_PATH = OUTPUT_DIR / "jdt_assignment_lifecycle_events.csv"
COVERAGE_PATH = OUTPUT_DIR / "jdt_bug_history_coverage.csv"


def parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def require_columns(path: Path, reader: csv.DictReader, required: set[str]) -> None:
    actual = set(reader.fieldnames or [])
    missing = required - actual
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")


def validate() -> int:
    errors: list[str] = []
    replay_counts: Counter[str] = Counter()
    coverage_blank_values: Counter[str] = Counter()
    coverage: dict[str, tuple[str, datetime | None]] = {}
    tracked_event_total = 0
    coverage_rows = 0
    invalid_coverage_timestamps = 0

    with COVERAGE_PATH.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        require_columns(
            COVERAGE_PATH,
            reader,
            {
                "record_index",
                "bug_id",
                "creation_time",
                "history_parse_status",
                "tracked_lifecycle_change_count",
                "replay_consistency",
            },
        )
        for row in reader:
            coverage_rows += 1
            for column, value in row.items():
                if not value:
                    coverage_blank_values[column] += 1
            bug_id = row["bug_id"]
            if not bug_id:
                errors.append(f"coverage row {coverage_rows} has no bug_id")
            elif bug_id in coverage:
                errors.append(f"duplicate coverage bug_id: {bug_id}")
            else:
                coverage[bug_id] = (row["record_index"], parse_timestamp(row["creation_time"]))

            if parse_timestamp(row["creation_time"]) is None:
                invalid_coverage_timestamps += 1
            try:
                tracked_event_total += int(row["tracked_lifecycle_change_count"])
            except ValueError:
                errors.append(f"invalid tracked event count for bug_id {bug_id}")
            replay_counts[row["replay_consistency"]] += 1

    event_rows = 0
    event_keys: set[tuple[str, str, str]] = set()
    invalid_event_timestamps = 0
    events_before_creation = 0
    orphan_events = 0
    record_index_mismatches = 0
    creation_time_mismatches = 0
    missing_required_event_values = 0
    event_blank_values: Counter[str] = Counter()

    with EVENTS_PATH.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        require_columns(
            EVENTS_PATH,
            reader,
            {
                "record_index",
                "bug_id",
                "creation_time",
                "event_time",
                "activity_index",
                "change_index",
                "field",
            },
        )
        for row in reader:
            event_rows += 1
            for column, value in row.items():
                if not value:
                    event_blank_values[column] += 1
            key = (row["record_index"], row["activity_index"], row["change_index"])
            if key in event_keys:
                errors.append(f"duplicate event key: {key}")
            event_keys.add(key)

            bug_id = row["bug_id"]
            reference = coverage.get(bug_id)
            if reference is None:
                orphan_events += 1
            else:
                if reference[0] != row["record_index"]:
                    record_index_mismatches += 1
                if reference[1] != parse_timestamp(row["creation_time"]):
                    creation_time_mismatches += 1

            if not bug_id or not row["event_time"] or not row["field"]:
                missing_required_event_values += 1
            event_time = parse_timestamp(row["event_time"])
            creation_time = parse_timestamp(row["creation_time"])
            if event_time is None or creation_time is None:
                invalid_event_timestamps += 1
            elif event_time < creation_time:
                events_before_creation += 1

    if invalid_coverage_timestamps:
        errors.append(f"{invalid_coverage_timestamps} invalid coverage creation timestamps")
    if invalid_event_timestamps:
        errors.append(f"{invalid_event_timestamps} invalid event/creation timestamps")
    if events_before_creation:
        errors.append(f"{events_before_creation} tracked events precede bug creation")
    if orphan_events:
        errors.append(f"{orphan_events} events reference bugs absent from coverage")
    if record_index_mismatches:
        errors.append(f"{record_index_mismatches} event/coverage record index mismatches")
    if creation_time_mismatches:
        errors.append(f"{creation_time_mismatches} event/coverage creation time mismatches")
    if missing_required_event_values:
        errors.append(f"{missing_required_event_values} events lack required values")
    if event_rows != len(event_keys):
        errors.append(f"event key count mismatch: {event_rows} rows, {len(event_keys)} keys")
    if event_rows != tracked_event_total:
        errors.append(
            f"tracked event count mismatch: {event_rows} rows, "
            f"{tracked_event_total} coverage total"
        )

    print(f"Coverage rows / unique bug IDs: {coverage_rows:,} / {len(coverage):,}")
    print(f"Lifecycle event rows / unique keys: {event_rows:,} / {len(event_keys):,}")
    print(f"History replay statuses: {dict(sorted(replay_counts.items()))}")
    print(f"Coverage blank values by column: {dict(sorted(coverage_blank_values.items()))}")
    print(f"Event blank values by column: {dict(sorted(event_blank_values.items()))}")
    print(f"Invalid timestamps: {invalid_coverage_timestamps + invalid_event_timestamps:,}")
    print(f"Events before creation: {events_before_creation:,}")
    print(f"Orphan events: {orphan_events:,}")
    print(f"Tracked events vs coverage totals: {event_rows:,} / {tracked_event_total:,}")
    if errors:
        print("Validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Validation PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(validate())
