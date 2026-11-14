"""Build cutoff-safe resolution-event evidence from replay-clean JDT histories."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.reconstruct_jdt_partial_workload import (
    ACTIVE_FIELDS,
    Event,
    load_inputs,
)


DATA = ROOT / "dataset" / "processed"
OUTPUT_DIR = DATA / "jdt_workload_partial"
OUTPUT_NAME = "jdt_partial_resolution_activity.csv"
REPORT_NAME = "jdt_partial_resolution_activity_validation_report.md"
OUTPUT_FIELDS = (
    "prediction_bug_id",
    "prediction_cutoff",
    "data_split",
    "developer_id",
    "workload_scope",
    "resolution_event_count_partial",
    "resolution_set_event_count_partial",
    "resolution_clear_event_count_partial",
    "distinct_bugs_with_resolution_change_partial",
    "latest_included_resolution_event_time",
    "resolution_attribution_scope",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def event_timeline(eligibility):
    timeline: list[tuple[datetime, int, int, int, int, str, Event | None]] = []
    for bug_id in eligibility.eligible_ids:
        events = eligibility.events_by_bug[bug_id]
        first = events[0]
        timeline.append(
            (first.creation_time, first.record_index, 0, -1, -1, bug_id, None)
        )
        for event in events:
            timeline.append(
                (
                    event.event_time,
                    event.record_index,
                    1,
                    event.activity_index,
                    event.change_index,
                    event.bug_id,
                    event,
                )
            )
    timeline.sort(key=lambda item: item[:5])
    return timeline


def render_outputs(output_path: Path) -> dict[str, int]:
    eligibility, cutoffs, developer_ids = load_inputs()
    developer_set = set(developer_ids)
    timeline = event_timeline(eligibility)
    event_counts: dict[str, Counter[str]] = {
        developer_id: Counter() for developer_id in developer_ids
    }
    event_bugs: dict[str, set[str]] = {
        developer_id: set() for developer_id in developer_ids
    }
    states: dict[str, dict[str, str]] = {}
    latest_by_developer: dict[str, str] = {developer_id: "" for developer_id in developer_ids}
    timeline_index = 0
    rows_written = 0
    cutoffs_with_resolution_events = 0
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        output = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS)
        output.writeheader()
        for cutoff in cutoffs:
            while (
                timeline_index < len(timeline)
                and timeline[timeline_index][0] < cutoff.cutoff
            ):
                event_time, _record, event_kind, _activity, _change, bug_id, event = (
                    timeline[timeline_index]
                )
                if event_kind == 0:
                    states[bug_id] = dict(eligibility.initial_states[bug_id])
                else:
                    if event is None or bug_id not in states:
                        raise ValueError(f"Lifecycle event precedes creation for {bug_id}")
                    state = states[bug_id]
                    if event.field == "resolution":
                        owner = state["assignee"].strip()
                        if state["product"].strip().casefold() == "jdt" and owner in developer_set:
                            event_counts[owner]["total"] += 1
                            event_counts[owner][
                                "set" if event.new_value.strip() else "clear"
                            ] += 1
                            event_bugs[owner].add(bug_id)
                            latest_by_developer[owner] = event.event_time.isoformat()
                    if event.field in ACTIVE_FIELDS:
                        state[event.field] = event.new_value
                timeline_index += 1

            cutoff_has_resolution_event = any(
                event_counts[developer_id]["total"] > 0
                for developer_id in developer_ids
            )
            cutoffs_with_resolution_events += int(cutoff_has_resolution_event)
            for developer_id in developer_ids:
                output.writerow(
                    {
                        "prediction_bug_id": cutoff.bug_id,
                        "prediction_cutoff": cutoff.cutoff_text,
                        "data_split": cutoff.split,
                        "developer_id": developer_id,
                        "workload_scope": "partial",
                        "resolution_event_count_partial": event_counts[developer_id]["total"],
                        "resolution_set_event_count_partial": event_counts[developer_id]["set"],
                        "resolution_clear_event_count_partial": event_counts[developer_id]["clear"],
                        "distinct_bugs_with_resolution_change_partial": len(
                            event_bugs[developer_id]
                        ),
                        "latest_included_resolution_event_time": latest_by_developer[
                            developer_id
                        ],
                        "resolution_attribution_scope": (
                            "verified_assignee_in_228_replay_clean_seeded_histories_only"
                        ),
                    }
                )
                rows_written += 1

    return {
        "snapshot_rows": rows_written,
        "eligible_source_bugs": eligibility.eligible_count,
        "cutoffs": len(cutoffs),
        "verified_developers": len(developer_ids),
        "cutoffs_with_resolution_events": cutoffs_with_resolution_events,
        "resolution_events": sum(counts["total"] for counts in event_counts.values()),
    }


def validate_existing() -> dict[str, int]:
    output_path = OUTPUT_DIR / OUTPUT_NAME
    report_path = OUTPUT_DIR / REPORT_NAME
    if not output_path.is_file() or not report_path.is_file():
        raise FileNotFoundError("Partial resolution activity output or report is missing")
    sources = (
        DATA / "jdt_workload" / "jdt_assignment_lifecycle_events.csv",
        DATA / "jdt_workload" / "jdt_bug_history_coverage.csv",
        DATA / "jdt_point_in_time" / "jdt_candidate_features.csv",
        DATA / "jdt_point_in_time" / "jdt_bug_splits.csv",
        DATA / "cold_start" / "jdt_identity_review" / "jdt_verified_identity_map.csv",
    )
    hashes = {path: sha256(path) for path in sources}
    with tempfile.TemporaryDirectory(prefix=".jdt_resolution_validate_", dir=DATA) as directory:
        staged = Path(directory) / OUTPUT_NAME
        results = render_outputs(staged)
        if sha256(staged) != sha256(output_path):
            raise ValueError("Partial resolution activity failed deterministic regeneration")
    for path, digest in hashes.items():
        if sha256(path) != digest:
            raise RuntimeError(f"Source changed during validation: {path}")
    return results


def write_outputs() -> dict[str, int]:
    output_path = OUTPUT_DIR / OUTPUT_NAME
    report_path = OUTPUT_DIR / REPORT_NAME
    if output_path.exists() or report_path.exists():
        raise FileExistsError("Refusing to overwrite partial resolution activity outputs")
    if not OUTPUT_DIR.is_dir():
        raise FileNotFoundError(f"Partial workload directory does not exist: {OUTPUT_DIR}")
    sources = (
        DATA / "jdt_workload" / "jdt_assignment_lifecycle_events.csv",
        DATA / "jdt_workload" / "jdt_bug_history_coverage.csv",
        DATA / "jdt_point_in_time" / "jdt_candidate_features.csv",
        DATA / "jdt_point_in_time" / "jdt_bug_splits.csv",
        DATA / "cold_start" / "jdt_identity_review" / "jdt_verified_identity_map.csv",
    )
    hashes = {path: sha256(path) for path in sources}
    with tempfile.TemporaryDirectory(prefix=".jdt_resolution_", dir=DATA) as directory:
        staged = Path(directory) / OUTPUT_NAME
        results = render_outputs(staged)
        for path, digest in hashes.items():
            if sha256(path) != digest:
                raise RuntimeError(f"Source changed during generation: {path}")
        os.replace(staged, output_path)

    lines = [
        "# JDT Partial Resolution Activity Validation",
        "",
        "- Source: existing replay-clean derived lifecycle and point-in-time files; raw JDT export was not read.",
        "- Overall validation: **PASS**.",
        "- Scope is partial and limited to replay-clean, seeded, chain-consistent histories and nine verified identities.",
        "- Resolution events are attributed only to the verified assignee observed in the replayed state; unverified or unassigned accounts are not attributed.",
        "- Resolution changes are activity evidence, not queue size or a prediction label.",
        "- Strict cutoff: only events with `event_time < prediction_cutoff` are included.",
        f"- Snapshot rows: {results['snapshot_rows']:,}.",
        f"- Eligible source histories: {results['eligible_source_bugs']:,}; cutoffs: {results['cutoffs']:,}; verified developers: {results['verified_developers']:,}.",
        f"- Cutoffs with any included verified-assignee resolution activity: {results['cutoffs_with_resolution_events']:,}.",
        f"- Verified-assignee resolution changes represented in the final cutoff: {results['resolution_events']:,}.",
        "- Reproducibility: deterministic staging comparison is available with `--validate-existing`.",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Create the supplemental dataset")
    mode.add_argument("--validate-existing", action="store_true", help="Check outputs and reproducibility")
    args = parser.parse_args()
    results = validate_existing() if args.validate_existing else write_outputs()
    print(f"Partial resolution activity validated: {results}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
