"""Verify temporal variant hashes and strict cutoff features without rewriting data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from bisect import bisect_left
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dataset/processed"
COLD = DATA / "cold_start"
BUG_FILE = DATA / "jdt_training_primary.csv"
COMMIT_FILE = COLD / "jdt_git_commits.csv"
FILE_CHANGE_FILE = COLD / "jdt_git_commit_files.csv"
IDENTITY_FILE = COLD / "git_bugzilla_exact_email_matches_clean.csv"
AUDIT_FILE = COLD / "git_bulk_commit_audit.csv"
VARIANTS = (
    COLD / "jdt_bug_developer_temporal_features.csv",
    COLD / "jdt_bug_developer_temporal_features_strict.csv",
    COLD / "jdt_bug_developer_temporal_features_inclusive.csv",
)
FIELDS = (
    "bug_id",
    "bug_creation_time",
    "component",
    "developer_email",
    "is_assigned_developer",
    "historical_commit_count",
    "historical_changed_file_count",
    "commits_last_30_days",
    "commits_last_90_days",
    "commits_last_365_days",
    "files_last_30_days",
    "files_last_90_days",
    "files_last_365_days",
    "days_since_last_contribution",
    "label_type",
    "candidate_evidence_type",
)


def parse_time(value: str, *, source: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Timezone missing in {source}: {value!r}")
    return parsed.astimezone(timezone.utc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_identity_map() -> tuple[dict[str, str], set[str]]:
    mapping: dict[str, str] = {}
    developers: set[str] = set()
    with IDENTITY_FILE.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            key = row["git_author_key"]
            email = row["bugzilla_email"].strip().lower()
            if not key or not email:
                raise ValueError("Verified identity mapping has an empty key/email")
            if key in mapping and mapping[key] != email:
                raise ValueError(f"Git key maps to multiple emails: {key}")
            mapping[key] = email
            developers.add(email)
    return mapping, developers


def build_timelines(
    git_to_bugzilla: dict[str, str],
) -> dict[str, tuple[list[datetime], list[int]]]:
    file_counts: dict[str, int] = defaultdict(int)
    with FILE_CHANGE_FILE.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            file_counts[row["commit_id"]] += 1

    duplicate_groups: dict[str, str] = {}
    with AUDIT_FILE.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            if row["classification"] == "verified_identical_patch":
                duplicate_groups[row["commit_id"]] = row["verified_duplicate_group"]

    unique_events: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    with COMMIT_FILE.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            git_key = row["git_author_key"]
            if git_key not in git_to_bugzilla:
                continue
            timestamp = parse_time(
                row["committer_timestamp"],
                source=f"committer timestamp for {row['commit_id']}",
            )
            email = git_to_bugzilla[git_key]
            commit_id = row["commit_id"]
            unit_key = duplicate_groups.get(commit_id, commit_id)
            changed_files = file_counts.get(commit_id, 0)
            existing = unique_events[email].get(unit_key)
            if existing is None:
                unique_events[email][unit_key] = {
                    "timestamp": timestamp,
                    "changed_files": changed_files,
                }
            else:
                existing["timestamp"] = min(existing["timestamp"], timestamp)
                existing["changed_files"] = max(
                    existing["changed_files"], changed_files
                )

    timelines: dict[str, tuple[list[datetime], list[int]]] = {}
    for email in sorted(set(git_to_bugzilla.values())):
        events = sorted(
            unique_events[email].values(),
            key=lambda item: item["timestamp"],
        )
        timestamps = [item["timestamp"] for item in events]
        prefix_files = [0]
        for event in events:
            prefix_files.append(prefix_files[-1] + event["changed_files"])
        timelines[email] = (timestamps, prefix_files)
    return timelines


def expected_rows(
    timelines: dict[str, tuple[list[datetime], list[int]]],
    developers: set[str],
):
    with BUG_FILE.open(encoding="utf-8-sig", newline="") as source:
        for bug in csv.DictReader(source):
            try:
                bug_time = parse_time(
                    bug["creation_time"], source=f"bug {bug['bug_id']} creation time"
                )
            except (TypeError, ValueError):
                continue
            actual_label = bug["developer_label"].strip().lower()
            for email in sorted(developers):
                timestamps, prefix_files = timelines[email]
                end = bisect_left(timestamps, bug_time)
                start_30 = bisect_left(
                    timestamps, bug_time - timedelta(days=30), 0, end
                )
                start_90 = bisect_left(
                    timestamps, bug_time - timedelta(days=90), 0, end
                )
                start_365 = bisect_left(
                    timestamps, bug_time - timedelta(days=365), 0, end
                )
                days_since = ""
                if end:
                    days_since = str(round(
                        (bug_time - timestamps[end - 1]).total_seconds() / 86400,
                        3,
                    ))
                yield {
                    "bug_id": bug["bug_id"],
                    "bug_creation_time": bug["creation_time"],
                    "component": bug["component"],
                    "developer_email": email,
                    "is_assigned_developer": str(int(actual_label == email)),
                    "historical_commit_count": str(end),
                    "historical_changed_file_count": str(prefix_files[end]),
                    "commits_last_30_days": str(end - start_30),
                    "commits_last_90_days": str(end - start_90),
                    "commits_last_365_days": str(end - start_365),
                    "files_last_30_days": str(prefix_files[end] - prefix_files[start_30]),
                    "files_last_90_days": str(prefix_files[end] - prefix_files[start_90]),
                    "files_last_365_days": str(prefix_files[end] - prefix_files[start_365]),
                    "days_since_last_contribution": days_since,
                    "label_type": bug["label_type"],
                    "candidate_evidence_type": bug["candidate_evidence_type"],
                }


def validate_variants(
    timelines: dict[str, tuple[list[datetime], list[int]]],
    developers: set[str],
) -> tuple[dict[str, object], list[str]]:
    errors: list[str] = []
    variant_info: list[dict[str, object]] = []
    hashes: list[str] = []
    for path in VARIANTS:
        if not path.is_file():
            raise FileNotFoundError(path)
        digest = sha256_file(path)
        hashes.append(digest)
        rows = 0
        with path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames != list(FIELDS):
                errors.append(f"{path.name}: unexpected header {reader.fieldnames}")
            for row in reader:
                rows += 1
                if not row["bug_id"] or not row["developer_email"]:
                    errors.append(f"{path.name}: empty bug/developer key at row {rows}")
                creation = parse_time(
                    row["bug_creation_time"],
                    source=f"{path.name} row {rows} bug creation",
                )
                if int(row["is_assigned_developer"]) not in (0, 1):
                    errors.append(f"{path.name}: invalid target at row {rows}")
                numeric_fields = (
                    "historical_commit_count", "historical_changed_file_count",
                    "commits_last_30_days", "commits_last_90_days",
                    "commits_last_365_days", "files_last_30_days",
                    "files_last_90_days", "files_last_365_days",
                )
                values = {name: int(row[name]) for name in numeric_fields}
                if any(value < 0 for value in values.values()):
                    errors.append(f"{path.name}: negative feature at row {rows}")
                if not (
                    values["commits_last_30_days"]
                    <= values["commits_last_90_days"]
                    <= values["commits_last_365_days"]
                    <= values["historical_commit_count"]
                ):
                    errors.append(f"{path.name}: commit windows inconsistent at row {rows}")
                if not (
                    values["files_last_30_days"]
                    <= values["files_last_90_days"]
                    <= values["files_last_365_days"]
                    <= values["historical_changed_file_count"]
                ):
                    errors.append(f"{path.name}: file windows inconsistent at row {rows}")
                days = row["days_since_last_contribution"]
                if days and float(days) < 0:
                    errors.append(f"{path.name}: negative recency at row {rows}")
                if days and creation == parse_time(
                    row["bug_creation_time"], source="creation"
                ) and float(days) < 0:
                    errors.append(f"{path.name}: future contribution at row {rows}")
        variant_info.append({
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": digest,
            "rows": rows,
        })

    same_bytes = len(set(hashes)) == 1
    expected_count = 0
    strict_matches = 0
    strict_path = VARIANTS[1]
    with strict_path.open(encoding="utf-8-sig", newline="") as source:
        actual = csv.DictReader(source)
        actual_row = next(actual, None)
        for expected in expected_rows(timelines, developers):
            expected_count += 1
            if actual_row is None:
                errors.append(f"Strict output ended early at expected row {expected_count}")
                break
            actual_values = {field: actual_row[field] for field in FIELDS}
            if actual_values != expected:
                errors.append(
                    f"Strict feature mismatch at row {expected_count}: "
                    f"bug={expected['bug_id']} developer={expected['developer_email']}"
                )
            else:
                strict_matches += 1
            actual_row = next(actual, None)
        if actual_row is not None:
            errors.append("Strict output has extra rows beyond reconstructed features")

    report: dict[str, object] = {
        "variants": variant_info,
        "identical_sha256": same_bytes,
        "verified_developer_count": len(developers),
        "expected_rows": expected_count,
        "strict_rows_matching_reconstruction": strict_matches,
        "errors": errors,
    }
    if not same_bytes:
        errors.append("Temporal variants differ by SHA-256; compare row semantics")
    if strict_matches != expected_count:
        errors.append(
            f"Strict output matches {strict_matches}/{expected_count} reconstructed rows"
        )
    return report, errors


def write_report(path: Path, report: dict[str, object], errors: list[str]) -> None:
    lines = [
        "# Temporal Feature Variant Checksum and Semantics Audit",
        "",
        "This is a read-only audit. No temporal dataset was regenerated or overwritten.",
        "",
        "## Variant files",
        "",
        "| File | Bytes | SHA-256 | Rows |",
        "|---|---:|---|---:|",
    ]
    for variant in report["variants"]:
        lines.append(
            f"| `{variant['path']}` | {variant['bytes']} | "
            f"`{variant['sha256']}` | {variant['rows']} |"
        )
    lines.extend([
        "",
        f"- Byte-identical by SHA-256: **{report['identical_sha256']}**.",
        f"- Verified JDT Git-to-Bugzilla identities: {report['verified_developer_count']}.",
        f"- Expected bug/developer rows reconstructed from existing processed inputs: {report['expected_rows']}.",
        f"- Strict variant rows matching reconstructed values: {report['strict_rows_matching_reconstruction']}.",
        "",
        "## Interpretation",
        "",
        "The generator found in the repository writes only the `strict` filename.",
        "Its `bisect_left(timestamps, bug_time)` excludes commits whose committer",
        "timestamp equals bug creation time, so the implemented cutoff is strictly",
        "before bug creation. The file's feature counts are Git code-contribution",
        "proxies for the 13 clean exact-email mappings, not Bugzilla assignment",
        "history or active workload. The base and inclusive filenames have no",
        "distinct generator in the inspected scripts. If hashes and reconstructed",
        "values match, preserve all names but treat them as byte-identical copies,",
        "not separately verified strict/inclusive variants.",
        "",
        "## Validation",
        "",
        "- Reconstructed strict feature rows from the existing primary training",
        "  table, clean identity mapping, JDT Git commit/file CSVs, and bulk-commit",
        "  audit, using the existing script's duplicate-patch and cutoff rules.",
        "- Checked all variants' headers, IDs, target domain, nonnegative features,",
        "  nested 30/90/365-day window counts, and nonnegative recency values.",
        "- No raw JDT export was opened; source inputs were existing derived files.",
        "",
        "## Result",
        "",
        "**PASS**" if not errors else "**FAIL**",
        "",
    ])
    if errors:
        lines.extend(["Errors:", *[f"- {error}" for error in errors], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "research/dataset_documentation/temporal_feature_variant_audit.md",
    )
    args = parser.parse_args()
    if args.report.exists():
        raise FileExistsError(f"Refusing to overwrite report: {args.report}")
    identity_map, developers = read_identity_map()
    timelines = build_timelines(identity_map)
    report, errors = validate_variants(timelines, developers)
    write_report(args.report, report, errors)
    print(f"Temporal audit report: {args.report}")
    print(f"Strict reconstructed rows: {report['strict_rows_matching_reconstruction']}")
    print(f"Validation errors: {len(errors)}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
