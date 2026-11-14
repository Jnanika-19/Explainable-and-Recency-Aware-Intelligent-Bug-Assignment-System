"""Validate partial JDT workload outputs and deterministic regeneration."""

from __future__ import annotations

import csv
import hashlib
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.reconstruct_jdt_partial_workload import (
    COVERAGE_FIELDS,
    COVERAGE_NAME,
    EXPECTED_DEVELOPERS,
    EXPECTED_SOURCE_COHORT,
    EXPECTED_STRICT_COHORT,
    EXPECTED_TARGET_BUGS,
    IDENTITY_PATH,
    OUTPUT_DIR,
    SNAPSHOT_FIELDS,
    SNAPSHOTS_NAME,
    TERMINAL_STATUSES,
    active_owner,
    build_outputs,
    canonical,
    event_is_before_cutoff,
    load_inputs,
    parse_timestamp,
    read_csv,
)


VALIDATION_REPORT_NAME = "jdt_partial_workload_validation_report.md"
NONNEGATIVE_COLUMNS = (
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
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_source_sequences(
    eligibility, developer_ids: set[str]
) -> tuple[int, int]:
    checked_bugs = 0
    status_transition_count = 0
    for bug_id, events in eligibility.events_by_bug.items():
        state = dict(eligibility.initial_states[bug_id])
        previous_time = None
        last_by_field: dict[str, str] = {}
        for event in events:
            if previous_time is not None and event.event_time < previous_time:
                raise ValueError(f"Unordered lifecycle events for bug {bug_id}")
            previous_time = event.event_time
            if event.field in last_by_field and canonical(last_by_field[event.field]) != canonical(event.old_value):
                raise ValueError(f"Broken {event.field} chain for bug {bug_id}")
            if event.field in {"assignee", "product", "status"}:
                if canonical(state[event.field]) != canonical(event.old_value):
                    raise ValueError(
                        f"Unexpected old value in {event.field} transition for bug {bug_id}"
                    )
                state[event.field] = event.new_value
            if event.field == "assignee":
                value = event.new_value
                if value and not (
                    value.startswith("jdt_assignee_")
                    or value in developer_ids
                ):
                    raise ValueError(f"Unrecognized assignee key in bug {bug_id}")
            if event.field == "status":
                if not event.old_value.strip() or not event.new_value.strip():
                    raise ValueError(f"Blank status transition in bug {bug_id}")
                old_status = event.old_value.strip().upper()
                new_status = event.new_value.strip().upper()
                owner = active_owner(
                    {
                        "product": state["product"],
                        "status": old_status,
                        "assignee": state["assignee"],
                    },
                    developer_ids,
                )
                if (
                    old_status not in TERMINAL_STATUSES
                    and new_status in TERMINAL_STATUSES
                    and owner is not None
                ):
                    status_transition_count += 1
            last_by_field[event.field] = event.new_value
        checked_bugs += 1
    return checked_bugs, status_transition_count


def validate_outputs() -> dict[str, object]:
    if not OUTPUT_DIR.is_dir():
        raise FileNotFoundError(f"Partial workload output directory is missing: {OUTPUT_DIR}")
    snapshots_path = OUTPUT_DIR / SNAPSHOTS_NAME
    coverage_path = OUTPUT_DIR / COVERAGE_NAME
    reconstruction_report = OUTPUT_DIR / "jdt_partial_workload_reconstruction_report.md"
    for path in (snapshots_path, coverage_path, reconstruction_report):
        if not path.is_file():
            raise FileNotFoundError(f"Required partial workload output is missing: {path}")

    eligibility, cutoffs, developer_ids = load_inputs()
    if len(developer_ids) != EXPECTED_DEVELOPERS:
        raise ValueError(f"Expected {EXPECTED_DEVELOPERS} verified developers")
    checked_source_bugs, verified_terminal_transitions = validate_source_sequences(
        eligibility, set(developer_ids)
    )

    coverage_rows = 0
    coverage_by_bug: dict[str, dict[str, str]] = {}
    with coverage_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != COVERAGE_FIELDS:
            raise ValueError("Partial workload coverage columns do not match the schema")
        for row in reader:
            coverage_rows += 1
            bug_id = row["prediction_bug_id"]
            if not bug_id or bug_id in coverage_by_bug:
                raise ValueError(f"Blank or duplicate coverage prediction bug: {bug_id!r}")
            cutoff = parse_timestamp(row["prediction_cutoff"], f"coverage bug {bug_id}")
            if row["workload_scope"] != "partial":
                raise ValueError(f"Non-partial scope label for prediction bug {bug_id}")
            if row["suitable_for_experimental_use"] != "true":
                raise ValueError(f"Experimental suitability is not explicitly true for {bug_id}")
            if row["severity_breakdown_supported"] != "false":
                raise ValueError(f"Severity support flag is incorrect for {bug_id}")
            if int(row["eligible_bug_cohort_size"]) != EXPECTED_STRICT_COHORT:
                raise ValueError(f"Unexpected eligible cohort size for {bug_id}")
            if int(row["source_replay_clean_verified_assignment_bug_count"]) != EXPECTED_SOURCE_COHORT:
                raise ValueError(f"Unexpected replay-clean source cohort for {bug_id}")
            if int(row["verified_developer_pool_size"]) != EXPECTED_DEVELOPERS:
                raise ValueError(f"Unexpected developer pool size for {bug_id}")
            for column in (
                "eligible_bugs_created_before_cutoff",
                "eligible_active_jdt_bug_count",
                "eligible_active_verified_assignee_bug_count",
                "eligible_active_unverified_or_unassigned_bug_count",
                "developers_with_active_observed_bugs_at_cutoff",
                "state_events_applied_before_cutoff",
                "mismatch_histories_excluded",
                "incomplete_histories_excluded",
                "strict_seed_or_chain_exclusions_from_source_cohort",
            ):
                if int(row[column]) < 0:
                    raise ValueError(f"Negative coverage value in {column} for {bug_id}")
            if int(row["eligible_bugs_created_before_cutoff"]) > EXPECTED_STRICT_COHORT:
                raise ValueError(f"Created eligible bugs exceed cohort for {bug_id}")
            active_count = int(row["eligible_active_jdt_bug_count"])
            verified_count = int(row["eligible_active_verified_assignee_bug_count"])
            unknown_count = int(row["eligible_active_unverified_or_unassigned_bug_count"])
            if active_count != verified_count + unknown_count:
                raise ValueError(f"Active workload coverage does not reconcile for {bug_id}")
            ratio = row["evidence_coverage_ratio_within_eligible_cohort"]
            if active_count == 0:
                if ratio:
                    raise ValueError(f"Coverage ratio should be blank with no active bugs: {bug_id}")
            elif abs(float(ratio) - verified_count / active_count) > 0.000001:
                raise ValueError(f"Coverage ratio mismatch for prediction bug {bug_id}")
            if row["data_split"] not in {"train", "validation", "test"}:
                raise ValueError(f"Invalid data split in coverage row for {bug_id}")
            coverage_by_bug[bug_id] = row

    if coverage_rows != EXPECTED_TARGET_BUGS:
        raise ValueError(f"Expected {EXPECTED_TARGET_BUGS} coverage rows, got {coverage_rows}")

    _, split_rows = read_csv(
        OUTPUT_DIR.parents[0] / "jdt_point_in_time" / "jdt_bug_splits.csv"
    )
    split_by_bug = {row["bug_id"]: row for row in split_rows}
    if set(coverage_by_bug) != set(split_by_bug):
        raise ValueError("Coverage predictions do not match chronological split bugs")
    for bug_id, row in coverage_by_bug.items():
        split = split_by_bug[bug_id]
        if row["prediction_cutoff"] != split["prediction_cutoff"] or row["data_split"] != split["data_split"]:
            raise ValueError(f"Coverage cutoff/split mismatch for bug {bug_id}")

    snapshot_rows = 0
    current_bug = None
    group_developers: set[str] = set()
    group_active_sum = 0
    group_active_developers = 0
    group_shared: dict[str, str] = {}
    previous_order: tuple[datetime, str, str] | None = None
    previous_state_event_count = -1
    nonzero_active_by_developer: Counter[str] = Counter()
    maximum_active_by_developer: Counter[str] = Counter()
    split_row_counts: Counter[str] = Counter()

    def finish_group(bug_id: str | None) -> None:
        if bug_id is None:
            return
        expected = set(developer_ids)
        if group_developers != expected:
            raise ValueError(f"Candidate developer coverage is incomplete for {bug_id}")
        coverage_row = coverage_by_bug.get(bug_id)
        if coverage_row is None:
            raise ValueError(f"Snapshot has no matching coverage row: {bug_id}")
        if group_active_sum != int(coverage_row["eligible_active_verified_assignee_bug_count"]):
            raise ValueError(f"Per-developer active count sum mismatch for {bug_id}")
        if group_active_developers != int(coverage_row["developers_with_active_observed_bugs_at_cutoff"]):
            raise ValueError(f"Active developer count mismatch for {bug_id}")
        for field in (
            "prediction_cutoff",
            "data_split",
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
            "state_events_applied_before_cutoff",
            "latest_included_event_time",
            "evidence_coverage_ratio_within_eligible_cohort",
            "known_limitations",
        ):
            if group_shared.get(field) != coverage_row.get(field):
                raise ValueError(f"Snapshot/coverage value mismatch for {bug_id}: {field}")

    with snapshots_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != SNAPSHOT_FIELDS:
            raise ValueError("Partial workload snapshot columns do not match the schema")
        if any("label" in column.casefold() for column in reader.fieldnames or ()):
            raise ValueError("A target label column leaked into workload snapshots")
        for row in reader:
            snapshot_rows += 1
            bug_id = row["prediction_bug_id"]
            cutoff = parse_timestamp(row["prediction_cutoff"], f"snapshot bug {bug_id}")
            developer_id = row["developer_id"]
            if developer_id not in developer_ids:
                raise ValueError(f"Snapshot references unverified developer {developer_id}")
            order = (cutoff, bug_id, developer_id)
            if previous_order is not None and order <= previous_order:
                raise ValueError("Snapshot keys are duplicated or not sorted")
            previous_order = order
            if current_bug != bug_id:
                finish_group(current_bug)
                current_bug = bug_id
                group_developers = set()
                group_active_sum = 0
                group_active_developers = 0
                group_shared = {}
            if developer_id in group_developers:
                raise ValueError(f"Duplicate developer/cutoff key for {bug_id}, {developer_id}")
            group_developers.add(developer_id)
            if row["workload_scope"] != "partial":
                raise ValueError(f"Snapshot is not labeled partial: {bug_id}")
            if row["suitable_for_experimental_use"] != "true":
                raise ValueError(f"Snapshot experimental-use flag missing: {bug_id}")
            if row["severity_breakdown_supported"] != "false":
                raise ValueError(f"Unsupported severity flag in snapshot: {bug_id}")
            for column in NONNEGATIVE_COLUMNS:
                value = int(row[column])
                if value < 0:
                    raise ValueError(f"Negative workload count {column} for {bug_id}")
            latest = row["latest_included_event_time"]
            if latest and not event_is_before_cutoff(
                parse_timestamp(latest, f"latest event in {bug_id}"), cutoff
            ):
                raise ValueError(f"Future event included at cutoff for bug {bug_id}")
            event_count = int(row["state_events_applied_before_cutoff"])
            if event_count < previous_state_event_count:
                raise ValueError("Applied event count decreases across chronological cutoffs")
            previous_state_event_count = event_count
            active = int(row["active_assigned_bug_count_partial"])
            group_active_sum += active
            group_active_developers += active > 0
            if active > 0:
                nonzero_active_by_developer[developer_id] += 1
            maximum_active_by_developer[developer_id] = max(
                maximum_active_by_developer[developer_id], active
            )
            split_row_counts[row["data_split"]] += 1
            for field in (
                "prediction_cutoff",
                "data_split",
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
                "state_events_applied_before_cutoff",
                "latest_included_event_time",
                "evidence_coverage_ratio_within_eligible_cohort",
                "known_limitations",
            ):
                if field in group_shared and group_shared[field] != row[field]:
                    raise ValueError(f"Shared cutoff metadata differs across developers: {field}")
                group_shared[field] = row[field]
        finish_group(current_bug)

    expected_snapshots = EXPECTED_TARGET_BUGS * EXPECTED_DEVELOPERS
    if snapshot_rows != expected_snapshots:
        raise ValueError(f"Expected {expected_snapshots} snapshot rows, got {snapshot_rows}")
    if split_row_counts != Counter(
        {
            "train": 23272 * EXPECTED_DEVELOPERS,
            "validation": 4987 * EXPECTED_DEVELOPERS,
            "test": 4987 * EXPECTED_DEVELOPERS,
        }
    ):
        raise ValueError(f"Unexpected snapshot coverage by split: {dict(split_row_counts)}")

    with tempfile.TemporaryDirectory(prefix="jdt_partial_workload_validation_") as temp:
        regenerated_dir = Path(temp) / "jdt_workload_partial"
        result = build_outputs(eligibility, cutoffs, developer_ids, regenerated_dir)
        for filename in (SNAPSHOTS_NAME, COVERAGE_NAME):
            existing = OUTPUT_DIR / filename
            regenerated = regenerated_dir / filename
            if sha256(existing) != sha256(regenerated):
                raise ValueError(f"Reproducibility check failed for {filename}")

    return {
        "snapshot_rows": snapshot_rows,
        "coverage_rows": coverage_rows,
        "source_cohort": eligibility.source_cohort_count,
        "strict_eligible_bugs": eligibility.eligible_count,
        "checked_source_bugs": checked_source_bugs,
        "verified_terminal_transitions": verified_terminal_transitions,
        "developer_max_active": dict(sorted(maximum_active_by_developer.items())),
        "developer_nonzero_snapshots": dict(sorted(nonzero_active_by_developer.items())),
        "split_snapshot_rows": dict(sorted(split_row_counts.items())),
        "reproduced_outputs": result,
    }


def write_validation_report(results: dict[str, object]) -> Path:
    path = OUTPUT_DIR / VALIDATION_REPORT_NAME
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite validation report: {path}")
    lines = [
        "# JDT Partial Workload Validation Report",
        "",
        f"Validation date: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "",
        "## Results",
        "",
        "- Overall validation: **PASS**.",
        "- Raw JDT source: not read.",
        f"- Replay-clean verified-assignment source cohort: {results['source_cohort']:,}.",
        f"- Strict seed/chain-eligible source bugs: {results['strict_eligible_bugs']:,}.",
        f"- Source state sequences checked: {results['checked_source_bugs']:,}.",
        f"- Valid verified-owner terminalization transitions: {results['verified_terminal_transitions']:,}.",
        f"- Snapshot rows: {results['snapshot_rows']:,}; coverage rows: {results['coverage_rows']:,}.",
        "- Unique `(prediction_bug_id, prediction_cutoff, developer_id)` keys: PASS.",
        "- Valid timestamps and strict no-future cutoff checks: PASS.",
        "- Nonnegative active workload and event counts: PASS.",
        "- Developer IDs restricted to the verified JDT map: PASS.",
        "- Partial scope and experimental-use indicators on every row: PASS.",
        "- Severity breakdown marked unsupported; no severity counts emitted: PASS.",
        "- Split grouping and chronological coverage: PASS.",
        "- Target labels absent from the workload tables: PASS.",
        "- Assignment/status/product chains and final product/status parity: PASS.",
        "- Reproducibility: snapshot and coverage CSVs were regenerated from the existing derived inputs in a temporary directory and matched byte-for-byte.",
        "",
        "### Snapshot rows by split",
        "",
        "| Split | Rows |",
        "|---|---:|",
        *[
            f"| {split} | {count:,} |"
            for split, count in sorted(results["split_snapshot_rows"].items())
        ],
        "",
        "### Per-developer partial cohort coverage",
        "",
        "| Verified developer ID | Maximum active eligible bugs observed | Cutoffs with nonzero observed workload |",
        "|---|---:|---:|",
        *[
            f"| `{developer_id}` | {results['developer_max_active'].get(developer_id, 0):,} | "
            f"{results['developer_nonzero_snapshots'].get(developer_id, 0):,} |"
            for developer_id in sorted(results["developer_max_active"])
        ],
        "",
        "These counts are limited to the 228 eligible source histories and must not be interpreted as total developer workload.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    results = validate_outputs()
    report_path = OUTPUT_DIR / VALIDATION_REPORT_NAME
    if report_path.exists():
        print("Existing validation report preserved.")
    else:
        write_validation_report(results)
    print(f"Validation PASSED. Report: {report_path.relative_to(OUTPUT_DIR.parents[1])}")
    print(
        f"Snapshots: {results['snapshot_rows']:,}; coverage rows: "
        f"{results['coverage_rows']:,}; eligible source bugs: "
        f"{results['strict_eligible_bugs']:,}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
