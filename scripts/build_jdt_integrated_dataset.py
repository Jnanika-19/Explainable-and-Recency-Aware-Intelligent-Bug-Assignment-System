"""Integrate validated JDT candidate, partial-workload, label, and audit data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dataset" / "processed"
FEATURES_PATH = DATA / "jdt_point_in_time" / "jdt_candidate_features.csv"
TARGETS_PATH = DATA / "jdt_point_in_time" / "jdt_assignment_targets.csv"
SPLITS_PATH = DATA / "jdt_point_in_time" / "jdt_bug_splits.csv"
COLD_START_PATH = DATA / "jdt_point_in_time" / "jdt_cold_start_scenarios.csv"
DUPLICATE_PATH = (
    DATA / "jdt_duplicate_retrieval" / "jdt_duplicate_positive_pairs_audit.csv"
)
IDENTITY_PATH = (
    DATA / "cold_start" / "jdt_identity_review" / "jdt_verified_identity_map.csv"
)
WORKLOAD_PATH = (
    DATA / "jdt_workload_partial" / "jdt_partial_workload_snapshots.csv"
)
OUTPUT_DIR = DATA / "jdt_integrated"

OUTPUTS = {
    "jdt_integrated_candidate_features.csv",
    "jdt_integrated_bug_context_metadata.csv",
    "jdt_integrated_bug_context_by_bug.csv",
    "jdt_integrated_targets.csv",
    "jdt_integrated_cold_start_evaluation.csv",
    "jdt_integrated_duplicate_evaluation_pairs.csv",
    "jdt_integrated_developer_identity_metadata.csv",
}

BASE_FEATURE_FIELDS = (
    "bug_id",
    "prediction_cutoff",
    "developer_id",
    "point_in_time_candidate_eligible",
    "prior_direct_assignment_count",
    "prior_same_component_direct_assignment_count",
    "days_since_last_direct_assignment",
    "historical_commit_count",
    "historical_changed_file_count",
    "commits_last_30_days",
    "commits_last_90_days",
    "commits_last_365_days",
    "files_last_30_days",
    "files_last_90_days",
    "files_last_365_days",
    "days_since_last_contribution",
)

WORKLOAD_FIELDS = (
    "workload_scope",
    "suitable_for_experimental_use",
    "severity_breakdown_supported",
    "eligible_bug_cohort_size",
    "eligible_bugs_created_before_cutoff",
    "eligible_active_jdt_bug_count",
    "eligible_active_verified_assignee_bug_count",
    "eligible_active_unverified_or_unassigned_bug_count",
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
)

FEATURE_STATUS_FIELDS = (
    "expertise_evidence_status",
    "same_component_expertise_status",
    "recency_evidence_status",
    "workload_evidence_status",
    "workload_coverage_status",
    "explainability_status",
    "cold_start_status",
    "genuine_newness_status",
    "adaptive_selection_status",
    "prediction_confidence_status",
    "duplicate_related_status",
    "top_k_status",
)

FEATURE_FIELDS = (
    *BASE_FEATURE_FIELDS[:2],
    "data_split",
    *BASE_FEATURE_FIELDS[2:],
    *WORKLOAD_FIELDS,
    "verified_candidate_pool_size",
    *FEATURE_STATUS_FIELDS,
)

CONTEXT_FIELDS = (
    "bug_id",
    "prediction_cutoff",
    "product_as_exported",
    "component_as_exported",
    "severity_as_exported",
    "priority_as_exported",
    "temporal_status",
    "model_input_eligible",
)

TARGET_FIELDS = (
    "bug_id",
    "prediction_cutoff",
    "data_split",
    "target_developer_id",
    "target_status",
    "target_label_tier",
    "label_event_time",
    "label_event_type",
)

COLD_START_FIELDS = (
    "bug_id",
    "prediction_cutoff",
    "developer_id",
    "data_split",
    "prior_direct_assignment_count",
    "evaluation_only_first_assignment_after_cutoff",
    "prior_git_commit_count",
    "cold_start_status",
    "genuinely_new_developer",
    "git_activity_is_assignment_evidence",
    "fallback_status",
    "evaluation_only",
)

DUPLICATE_FIELDS = (
    "duplicate_bug_id",
    "original_bug_id",
    "family_id",
    "duplicate_creation_time",
    "original_creation_time",
    "product",
    "component",
    "duplicate_target_label",
    "label_use",
    "original_existed_before_cutoff",
    "text_snapshot_time",
    "retrieval_model_ready",
    "evaluation_only",
)

IDENTITY_FIELDS = (
    "developer_id",
    "bugzilla_user_id",
    "bugzilla_email",
    "git_author_key",
    "identity_evidence",
    "metadata_use",
)

INPUTS = (
    FEATURES_PATH,
    TARGETS_PATH,
    SPLITS_PATH,
    COLD_START_PATH,
    DUPLICATE_PATH,
    IDENTITY_PATH,
    WORKLOAD_PATH,
)


def parse_timestamp(value: str, label: str) -> datetime:
    try:
        timestamp = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError(f"Invalid {label} timestamp: {value!r}") from error
    if timestamp.tzinfo is None:
        raise ValueError(f"Naive {label} timestamp: {value!r}")
    return timestamp.astimezone(timezone.utc)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        yield from reader


def require_columns(path: Path, required: tuple[str, ...]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(required).difference(reader.fieldnames or ())
    if missing:
        raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")


def writer(path: Path, fields: tuple[str, ...]) -> tuple[object, csv.DictWriter]:
    stream = path.open("w", encoding="utf-8", newline="")
    return stream, csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")


def context_row(bug_id: str, cutoff: str, row: dict[str, str]) -> dict[str, str]:
    return {
        "bug_id": bug_id,
        "prediction_cutoff": cutoff,
        "product_as_exported": row.get("product", ""),
        "component_as_exported": row.get("component", ""),
        "severity_as_exported": row.get("severity", ""),
        "priority_as_exported": row.get("priority", ""),
        "temporal_status": "export_time_value_not_verified_at_cutoff",
        "model_input_eligible": "false",
    }


def build_outputs(output_dir: Path) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=False)
    require_columns(FEATURES_PATH, BASE_FEATURE_FIELDS)
    require_columns(SPLITS_PATH, ("bug_id", "prediction_cutoff", "data_split"))
    require_columns(TARGETS_PATH, TARGET_FIELDS[0:1] + TARGET_FIELDS[3:8])
    require_columns(WORKLOAD_PATH, ("prediction_bug_id", "prediction_cutoff", "developer_id", *WORKLOAD_FIELDS))
    require_columns(COLD_START_PATH, COLD_START_FIELDS[:-1])
    require_columns(DUPLICATE_PATH, DUPLICATE_FIELDS[:-1])
    require_columns(IDENTITY_PATH, IDENTITY_FIELDS[:-1])

    verified_developer_ids = {
        row["developer_id"].strip() for row in rows(IDENTITY_PATH)
    }
    if len(verified_developer_ids) != 9 or "" in verified_developer_ids:
        raise ValueError("Verified identity map must contain nine unique developer IDs")

    split_by_bug: dict[str, tuple[str, str]] = {}
    for row in rows(SPLITS_PATH):
        bug_id = row["bug_id"].strip()
        if not bug_id or bug_id in split_by_bug:
            raise ValueError(f"Blank or duplicate bug split key: {bug_id!r}")
        parse_timestamp(row["prediction_cutoff"], f"split bug {bug_id}")
        split_by_bug[bug_id] = (row["prediction_cutoff"], row["data_split"])

    workload_by_key: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows(WORKLOAD_PATH):
        key = (
            row["prediction_bug_id"].strip(),
            row["prediction_cutoff"].strip(),
            row["developer_id"].strip(),
        )
        if not all(key) or key in workload_by_key:
            raise ValueError(f"Blank or duplicate partial workload key: {key!r}")
        workload_by_key[key] = {field: row[field] for field in WORKLOAD_FIELDS}

    candidate_path = output_dir / "jdt_integrated_candidate_features.csv"
    context_path = output_dir / "jdt_integrated_bug_context_metadata.csv"
    context_by_bug_path = output_dir / "jdt_integrated_bug_context_by_bug.csv"
    candidate_stream, candidate_writer = writer(candidate_path, FEATURE_FIELDS)
    context_stream, context_writer = writer(context_path, CONTEXT_FIELDS)
    context_by_bug_stream, context_by_bug_writer = writer(
        context_by_bug_path, CONTEXT_FIELDS
    )
    candidate_writer.writeheader()
    context_writer.writeheader()
    context_by_bug_writer.writeheader()
    seen_candidate_keys: set[tuple[str, str, str]] = set()
    context_bug_ids: set[str] = set()
    context_by_bug_rows: dict[str, dict[str, str]] = {}
    candidate_count = 0
    candidates_per_bug: dict[str, int] = {}
    try:
        for row in rows(FEATURES_PATH):
            bug_id = row["bug_id"].strip()
            developer_id = row["developer_id"].strip()
            cutoff = row["prediction_cutoff"].strip()
            key = (bug_id, cutoff, developer_id)
            if not all(key) or key in seen_candidate_keys:
                raise ValueError(f"Blank or duplicate candidate key: {key!r}")
            seen_candidate_keys.add(key)
            split = split_by_bug.get(bug_id)
            if split is None:
                raise ValueError(f"Candidate bug has no split row: {bug_id}")
            if split[0] != cutoff:
                raise ValueError(f"Candidate cutoff mismatch for bug {bug_id}")
            if developer_id not in verified_developer_ids:
                raise ValueError(f"Candidate developer is not verified: {developer_id}")
            workload = workload_by_key.pop(key, None)
            if workload is None:
                raise ValueError(f"Candidate lacks partial workload row: {key}")
            if workload["workload_scope"] != "partial":
                raise ValueError(f"Non-partial workload row for {key}")
            if workload["suitable_for_experimental_use"] != "true":
                raise ValueError(f"Workload experimental-use flag missing for {key}")
            if workload["severity_breakdown_supported"] != "false":
                raise ValueError(f"Unexpected severity support for {key}")

            cutoff_time = parse_timestamp(cutoff, f"candidate {bug_id}")
            latest = workload["latest_included_event_time"]
            if latest and parse_timestamp(latest, f"workload {bug_id}") >= cutoff_time:
                raise ValueError(f"Workload includes an event at/after cutoff for {key}")

            prior_assignments = int(row["prior_direct_assignment_count"])
            git_commits = int(row["historical_commit_count"])
            if prior_assignments < 0 or git_commits < 0:
                raise ValueError(f"Negative history count for {key}")
            if row["point_in_time_candidate_eligible"] != (
                "true" if prior_assignments > 0 else "false"
            ):
                raise ValueError(f"Assignment eligibility disagrees with history for {key}")
            for field in (
                "days_since_last_direct_assignment",
                "days_since_last_contribution",
            ):
                if row[field] and float(row[field]) < 0:
                    raise ValueError(f"Negative recency feature {field} for {key}")
            for field in (
                "prior_direct_assignment_count",
                "prior_same_component_direct_assignment_count",
                "historical_commit_count",
                "historical_changed_file_count",
                "commits_last_30_days",
                "commits_last_90_days",
                "commits_last_365_days",
                "files_last_30_days",
                "files_last_90_days",
                "files_last_365_days",
            ):
                if int(row[field]) < 0:
                    raise ValueError(f"Negative feature {field} for {key}")
            coverage_value = workload["evidence_coverage_ratio_within_eligible_cohort"]
            if coverage_value:
                coverage = float(coverage_value)
                if not 0 <= coverage <= 1:
                    raise ValueError(f"Invalid partial evidence coverage for {key}")
                workload["workload_coverage_status"] = (
                    "observed_within_partial_eligible_cohort"
                )
            elif int(workload["eligible_active_jdt_bug_count"]) == 0:
                workload["workload_coverage_status"] = (
                    "not_applicable_no_active_eligible_bugs"
                )
            else:
                raise ValueError(f"Missing evidence coverage with active cohort bugs for {key}")

            result = {field: row[field] for field in BASE_FEATURE_FIELDS}
            result["data_split"] = split[1]
            result.update(workload)
            result["verified_candidate_pool_size"] = "9"
            result.update(
                {
                    "expertise_evidence_status": (
                        "prior_direct_assignment_observed"
                        if prior_assignments
                        else "no_prior_assignment_evidence"
                    ),
                    "same_component_expertise_status": (
                        "component_timestamp_unverified_not_model_safe"
                    ),
                    "recency_evidence_status": (
                        "prior_git_contribution_observed"
                        if git_commits
                        else "no_prior_git_contribution"
                    ),
                    "workload_evidence_status": "partial_experimental_only",
                    "explainability_status": "raw_evidence_available_not_scored",
                    "cold_start_status": (
                        "prior_assignment_history_observed"
                        if prior_assignments
                        else "zero_prior_assignment_history"
                    ),
                    "genuine_newness_status": "unknown",
                    "adaptive_selection_status": "availability_indicators_only",
                    "prediction_confidence_status": "uncalibrated_no_probability",
                    "duplicate_related_status": (
                        "blocked_missing_historical_text_snapshots"
                    ),
                    "top_k_status": "candidate_pool_available_not_ranked",
                }
            )
            candidate_writer.writerow(result)
            candidates_per_bug[bug_id] = candidates_per_bug.get(bug_id, 0) + 1
            candidate_count += 1

            context = context_row(bug_id, cutoff, row)
            context_writer.writerow(context)
            if bug_id not in context_bug_ids:
                context_bug_ids.add(bug_id)
                context_by_bug_rows[bug_id] = context
                context_by_bug_writer.writerow(context)
            elif context_by_bug_rows[bug_id] != context:
                raise ValueError(f"Context metadata differs between candidates for {bug_id}")
    finally:
        candidate_stream.close()
        context_stream.close()
        context_by_bug_stream.close()
    if workload_by_key:
        raise ValueError(f"Orphan partial workload keys: {len(workload_by_key)}")
    if set(candidates_per_bug) != set(split_by_bug):
        raise ValueError("Candidate bugs and split bugs do not match")
    if set(candidates_per_bug.values()) != {9}:
        raise ValueError("Every bug must have exactly nine verified candidates")
    if context_bug_ids != set(split_by_bug):
        raise ValueError("Deduplicated bug context does not match split bugs")

    target_path = output_dir / "jdt_integrated_targets.csv"
    target_stream, target_writer = writer(target_path, TARGET_FIELDS)
    target_writer.writeheader()
    target_count = 0
    seen_targets: set[str] = set()
    try:
        for row in rows(TARGETS_PATH):
            bug_id = row["bug_id"].strip()
            split = split_by_bug.get(bug_id)
            if not bug_id or bug_id in seen_targets or split is None:
                raise ValueError(f"Blank, duplicate, or unlinked target bug: {bug_id!r}")
            seen_targets.add(bug_id)
            event_time = parse_timestamp(row["label_event_time"], f"target {bug_id}")
            cutoff_time = parse_timestamp(split[0], f"target cutoff {bug_id}")
            if event_time < cutoff_time:
                raise ValueError(f"Target event predates cutoff for bug {bug_id}")
            target_writer.writerow(
                {
                    "bug_id": bug_id,
                    "prediction_cutoff": split[0],
                    "data_split": split[1],
                    **{field: row[field] for field in TARGET_FIELDS[3:]},
                }
            )
            target_count += 1
    finally:
        target_stream.close()
    if seen_targets != set(split_by_bug):
        raise ValueError("Target bugs and split bugs do not match")

    cold_path = output_dir / "jdt_integrated_cold_start_evaluation.csv"
    cold_stream, cold_writer = writer(cold_path, COLD_START_FIELDS)
    cold_writer.writeheader()
    cold_count = 0
    seen_cold_keys: set[tuple[str, str, str]] = set()
    try:
        for row in rows(COLD_START_PATH):
            bug_id = row["bug_id"].strip()
            developer_id = row["developer_id"].strip()
            cutoff = row["prediction_cutoff"].strip()
            key = (bug_id, cutoff, developer_id)
            if key in seen_cold_keys or key not in seen_candidate_keys:
                raise ValueError(f"Duplicate or unlinked cold-start evaluation row: {key}")
            seen_cold_keys.add(key)
            cutoff_time = parse_timestamp(
                cutoff, f"cold-start bug {bug_id}"
            )
            after = row["evaluation_only_first_assignment_after_cutoff"]
            if after:
                if parse_timestamp(after, f"first assignment {row['bug_id']}") <= cutoff_time:
                    raise ValueError(
                        f"Cold-start evaluation assignment is not after cutoff: {bug_id}"
                    )
            if (
                row["genuinely_new_developer"] != "unknown"
                or int(row["prior_direct_assignment_count"]) != 0
                or row["git_activity_is_assignment_evidence"] != "false"
            ):
                raise ValueError(
                    f"Invalid cold-start evidence for {bug_id}/{developer_id}"
                )
            cold_writer.writerow({**{field: row[field] for field in COLD_START_FIELDS[:-1]}, "evaluation_only": "true"})
            cold_count += 1
    finally:
        cold_stream.close()
    if cold_count != 206_990:
        raise ValueError(f"Expected 206,990 cold-start evaluation rows, got {cold_count}")

    duplicate_path = output_dir / "jdt_integrated_duplicate_evaluation_pairs.csv"
    duplicate_stream, duplicate_writer = writer(duplicate_path, DUPLICATE_FIELDS)
    duplicate_writer.writeheader()
    duplicate_count = 0
    seen_pairs: set[tuple[str, str]] = set()
    try:
        for row in rows(DUPLICATE_PATH):
            key = (row["duplicate_bug_id"].strip(), row["original_bug_id"].strip())
            if not all(key) or key in seen_pairs:
                raise ValueError(f"Blank or duplicate duplicate-pair key: {key!r}")
            seen_pairs.add(key)
            duplicate_time = parse_timestamp(
                row["duplicate_creation_time"], f"duplicate {key[0]}"
            )
            original_time = parse_timestamp(
                row["original_creation_time"], f"original {key[1]}"
            )
            if original_time >= duplicate_time:
                raise ValueError(f"Duplicate candidate is not historical: {key}")
            if row["duplicate_target_label"] != "1" or row["label_use"] != "evaluation_target_only":
                raise ValueError(f"Duplicate target is not evaluation-only: {key}")
            if row["original_existed_before_cutoff"] != "true":
                raise ValueError(f"Duplicate original did not predate its query: {key}")
            if row["retrieval_model_ready"] != "false" or row["text_snapshot_time"]:
                raise ValueError(f"Unexpected historical text availability for {key}")
            duplicate_writer.writerow(
                {
                    **{field: row[field] for field in DUPLICATE_FIELDS[:-1]},
                    "evaluation_only": "true",
                }
            )
            duplicate_count += 1
    finally:
        duplicate_stream.close()

    identity_path = output_dir / "jdt_integrated_developer_identity_metadata.csv"
    identity_stream, identity_writer = writer(identity_path, IDENTITY_FIELDS)
    identity_writer.writeheader()
    identity_ids: set[str] = set()
    try:
        for row in rows(IDENTITY_PATH):
            developer_id = row["developer_id"].strip()
            if not developer_id or developer_id in identity_ids:
                raise ValueError(f"Blank or duplicate verified identity: {developer_id!r}")
            identity_ids.add(developer_id)
            identity_writer.writerow(
                {
                    **{field: row[field] for field in IDENTITY_FIELDS[:-1]},
                    "metadata_use": "identity_metadata_not_a_predictor_feature",
                }
            )
    finally:
        identity_stream.close()
    if len(identity_ids) != 9:
        raise ValueError(f"Expected nine verified JDT identities, got {len(identity_ids)}")

    return {
        "candidate_features": candidate_count,
        "bug_context_metadata": candidate_count,
        "bug_context_by_bug": len(context_bug_ids),
        "targets": target_count,
        "cold_start_evaluation": cold_count,
        "duplicate_evaluation_pairs": duplicate_count,
        "developer_identity_metadata": len(identity_ids),
    }


def validate_existing() -> dict[str, int]:
    missing = [OUTPUT_DIR / name for name in sorted(OUTPUTS) if not (OUTPUT_DIR / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Integrated dataset output(s) missing: {missing}")
    source_hashes = {path: sha256(path) for path in INPUTS}
    with tempfile.TemporaryDirectory(prefix=".jdt_integrated_validate_", dir=DATA) as temporary:
        staged = Path(temporary) / "jdt_integrated"
        counts = build_outputs(staged)
        for name in sorted(OUTPUTS):
            if sha256(staged / name) != sha256(OUTPUT_DIR / name):
                raise ValueError(f"Integrated dataset is not reproducible: {name}")
    for path, digest in source_hashes.items():
        if sha256(path) != digest:
            raise RuntimeError(f"Source changed during validation: {path}")
    return counts


def add_context_by_bug() -> int:
    if not OUTPUT_DIR.is_dir():
        raise FileNotFoundError(f"Integrated dataset directory is missing: {OUTPUT_DIR}")
    output_path = OUTPUT_DIR / "jdt_integrated_bug_context_by_bug.csv"
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite {output_path}")
    source_path = OUTPUT_DIR / "jdt_integrated_bug_context_metadata.csv"
    require_columns(source_path, CONTEXT_FIELDS)
    with tempfile.TemporaryDirectory(prefix=".jdt_context_", dir=DATA) as directory:
        staged = Path(directory) / output_path.name
        seen: dict[str, dict[str, str]] = {}
        with staged.open("w", encoding="utf-8", newline="") as stream:
            output = csv.DictWriter(stream, fieldnames=CONTEXT_FIELDS)
            output.writeheader()
            for row in rows(source_path):
                bug_id = row["bug_id"].strip()
                if not bug_id:
                    raise ValueError("Blank bug ID in per-candidate context metadata")
                context = {field: row[field] for field in CONTEXT_FIELDS}
                if bug_id in seen:
                    if seen[bug_id] != context:
                        raise ValueError(f"Context metadata differs across candidates: {bug_id}")
                    continue
                seen[bug_id] = context
                output.writerow(context)
        if len(seen) != 33_246:
            raise ValueError(f"Expected 33,246 unique bug contexts, got {len(seen)}")
        os.rename(staged, output_path)
    return len(seen)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Create outputs once")
    mode.add_argument(
        "--add-context-by-bug",
        action="store_true",
        help="Add normalized bug context while preserving existing outputs",
    )
    mode.add_argument(
        "--validate-existing",
        action="store_true",
        help="Validate existing outputs and deterministic regeneration",
    )
    args = parser.parse_args()
    if args.add_context_by_bug:
        print(f"Added unique bug context rows: {add_context_by_bug():,}")
        return 0
    if args.validate_existing:
        counts = validate_existing()
        print(f"Integrated outputs validated; deterministic regeneration passed: {counts}")
        return 0
    if OUTPUT_DIR.exists():
        raise FileExistsError(f"Refusing to overwrite integrated output directory: {OUTPUT_DIR}")
    for path in INPUTS:
        if not path.is_file():
            raise FileNotFoundError(path)
    source_hashes = {path: sha256(path) for path in INPUTS}
    staging_parent = Path(tempfile.mkdtemp(prefix=".jdt_integrated_", dir=DATA))
    staged = staging_parent / OUTPUT_DIR.name
    try:
        counts = build_outputs(staged)
        for path, digest in source_hashes.items():
            if sha256(path) != digest:
                raise RuntimeError(f"Source changed during integration: {path}")
        if OUTPUT_DIR.exists():
            raise FileExistsError(f"Output directory appeared during build: {OUTPUT_DIR}")
        os.rename(staged, OUTPUT_DIR)
    finally:
        shutil.rmtree(staging_parent, ignore_errors=True)
    print(f"Created {OUTPUT_DIR.relative_to(ROOT)}: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
