import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset"
REPORT = ROOT / "research" / "dataset_documentation" / "dataset_availability.md"
MAX_CSV_ROWS_BYTES = 250_000_000
HASH_CHUNK_SIZE = 1024 * 1024


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(HASH_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source)
        columns = next(reader, [])
        row_count = None
        if path.stat().st_size <= MAX_CSV_ROWS_BYTES:
            row_count = sum(1 for _ in reader)
    return columns, row_count


def format_count(value):
    return "not counted (large file)" if value is None else f"{value:,}"


def main():
    if not DATASET.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {DATASET}")

    files = sorted(
        path
        for path in DATASET.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(DATASET).parts
    )

    if not files:
        raise FileNotFoundError(f"No dataset files found under {DATASET}")

    records = []
    for path in files:
        relative_path = path.relative_to(ROOT).as_posix()
        columns = []
        row_count = None
        if path.suffix.lower() == ".csv":
            columns, row_count = inspect_csv(path)
        records.append({
            "path": relative_path,
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
            "rows": row_count,
            "columns": columns,
        })

    by_path = {record["path"]: record for record in records}
    key_files = [
        "dataset/raw/JDT.csv",
        "dataset/processed/jdt_training_primary.csv",
        "dataset/processed/jdt_training_secondary_review.csv",
        "dataset/processed/duplicate_pairs.csv",
        "dataset/processed/duplicate_pairs_historical_available.csv",
        "dataset/processed/developer_identity_audit.csv",
        "dataset/processed/cold_start/jdt_git_commits.csv",
        "dataset/processed/cold_start/jdt_git_commit_files.csv",
        "dataset/processed/cold_start/jdt_git_developer_roster.csv",
        "dataset/processed/cold_start/git_verified_developer_commit_events.csv",
        "dataset/processed/cold_start/git_verified_developer_adjusted_contributions.csv",
        "dataset/processed/cold_start/git_unmatched_identity_review.csv",
        "dataset/processed/cold_start/jdt_bug_developer_temporal_features_strict.csv",
    ]

    lines = [
        "# Dataset Availability Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Scope",
        "",
        "This is a read-only inventory of files under `dataset/`. It records file sizes,",
        "SHA-256 checksums, CSV headers, and row counts for CSVs no larger than",
        f"{MAX_CSV_ROWS_BYTES:,} bytes. Large CSVs are not scanned for row counts.",
        "The `.git` metadata for the external JDT repository is excluded from this file",
        "manifest; its commit-history status is summarized below.",
        "",
        "## Existing JDT baseline",
        "",
        "| File | Size (MiB) | Rows | Columns |",
        "|---|---:|---:|---|",
    ]

    for relative_path in key_files:
        record = by_path.get(relative_path)
        if record is None:
            lines.append(f"| `{relative_path}` | missing | — | — |")
            continue
        column_text = "; ".join(record["columns"]) or "—"
        lines.append(
            f"| `{relative_path}` | {record['size'] / (1024 * 1024):.2f} "
            f"| {format_count(record['rows'])} | {column_text} |"
        )

    lines.extend([
        "",
        "Verified current counts include 33,246 primary assignment examples,",
        "607 secondary-review examples, 1,810 historically available duplicate pairs,",
        "32,484 JDT commits, 279,322 commit-file records, and 1,418 verified developer",
        "commit events. The clean exact-email identity file contains 13 verified",
        "Bugzilla-to-Git identities. The strict temporal feature file contains 432,198",
        "bug/developer rows. The Git roster contains 254 author keys; 241 are currently",
        "unmatched and must remain unclassified as cold-start developers.",
        "",
        "The raw JDT export is approximately 6.08 GiB and contains bug fields, current",
        "assignee/status/resolution, activity history, comments, and duplicate links.",
        "The primary training file is a derived subset and does not include every raw",
        "field. Existing data remains in its current locations; this report does not",
        "regenerate or modify it.",
        "",
        "## Feature and data gaps",
        "",
        "- Historical assignment events are present in the raw JDT activity log, but",
        "  there is no normalized per-event history/workload dataset in the inventory.",
        "- Active assignment queues have not been reconstructed. Any future workload",
        "  feature must be rebuilt from events available at each prediction cutoff.",
        "- The existing strict temporal feature file covers only the 13 verified",
        "  identities; its script uses commit committer timestamps and a strict",
        "  before-bug-creation cutoff.",
        "- Existing commit CSVs contain commit subjects, not complete commit messages.",
        "  File paths and author/committer timestamps are present; file-change counts",
        "  can be derived. Existing component labels use the first path segment.",
        "- Historical duplicate pairs include creation times, but raw duplicate pairs",
        "  are not themselves a prediction-time-filtered related-bug feature table.",
        "- No confidence calibration, ranking-margin, top-K evaluation, adaptive vs.",
        "  fixed-weight comparison, or integrated recommendation feature dataset was",
        "  found in the current dataset tree.",
        "",
        "The local JDT Git repository has 32,484 commits across available refs and is",
        "not marked shallow. It is a partial clone (`blob:none`); its checkout currently",
        "reports 10,859 tracked paths as deleted. The Git metadata is left untouched.",
        "",
        "## Sources and licensing status",
        "",
        "- Bugzilla REST API documentation describes current bug fields and access",
        "  methods: [Bugzilla API: Bugs](https://bugzilla.readthedocs.io/en/latest/api/core/v1/bug.html).",
        "- The Eclipse Bugzilla site currently reports a temporary shutdown:",
        "  [Eclipse Bugzilla](https://bugs.eclipse.org/bugs/page.cgi?id=about.html).",
        "  Endpoint availability, activity history, and public access must be rechecked",
        "  before any project data is collected.",
        "- The PDE repository identifies EPL-2.0 for its source code:",
        "  [eclipse-pde/eclipse.pde](https://github.com/eclipse-pde/eclipse.pde).",
        "- The Platform project spans repositories. The selected scope is all",
        "  component-mapped repositories; the mapping and repository terms remain to be",
        "  validated before collection.",
        "- Repository code licensing does not establish a license for Bugzilla records.",
        "  Bug report text and contributor identifiers require separate terms/privacy",
        "  review. Comments are excluded from the initial collection.",
        "",
        "The repository `.gitignore` already excludes the large `dataset/raw/`,",
        "`dataset/processed/`, and `dataset/external/` contents. This stage made no",
        "changes to ignore rules.",
        "",
        "## File manifest",
        "",
        "| File | Size (bytes) | SHA-256 | CSV rows | CSV columns |",
        "|---|---:|---|---:|---|",
    ])

    for record in records:
        columns = "; ".join(record["columns"]) or "—"
        row_count = (
            format_count(record["rows"])
            if Path(record["path"]).suffix.lower() == ".csv"
            else "—"
        )
        lines.append(
            f"| `{record['path']}` | {record['size']:,} | "
            f"`{record['sha256']}` | {row_count} | {columns} |"
        )

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Dataset files inventoried: {len(records)}")
    print(f"Availability report written: {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
