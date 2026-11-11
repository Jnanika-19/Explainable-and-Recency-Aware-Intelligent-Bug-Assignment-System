
import csv
import math
from collections import defaultdict, Counter
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dataset/processed/cold_start"

EVENTS_FILE = DATA / "git_verified_developer_commit_events.csv"
FILES_FILE = DATA / "jdt_git_commit_files.csv"
AUDIT_FILE = DATA / "git_bulk_commit_audit.csv"
OUTPUT_FILE = DATA / "git_verified_developer_adjusted_contributions.csv"

# --------------------------------------------------
# 1. Count changed-file records for every commit
# --------------------------------------------------

file_counts = Counter()

with FILES_FILE.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        file_counts[row["commit_id"]] += 1

print("Commit file counts loaded:", len(file_counts))

# --------------------------------------------------
# 2. Identify only verified duplicate patch groups
# --------------------------------------------------

verified_groups = {}

with AUDIT_FILE.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        if row["classification"] == "verified_identical_patch":
            verified_groups[row["commit_id"]] = row["verified_duplicate_group"]

# --------------------------------------------------
# 3. Aggregate developer contributions
# --------------------------------------------------

developers = defaultdict(lambda: {
    "git_author_key": "",
    "raw_commit_count": 0,
    "raw_changed_file_records": 0,
    "unique_changes": {},
    "timestamps": [],
})

with EVENTS_FILE.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        email = row["bugzilla_email"]
        commit_id = row["commit_id"]
        author = developers[email]

        author["git_author_key"] = row["git_author_key"]
        author["raw_commit_count"] += 1

        changed_files = file_counts.get(commit_id, 0)
        author["raw_changed_file_records"] += changed_files

        # Collapse only commits with verified identical patch IDs.
        # Keep all other commits as separate contributions.
        unique_key = verified_groups.get(commit_id, commit_id)

        if unique_key not in author["unique_changes"]:
            author["unique_changes"][unique_key] = {
                "changed_files": changed_files
            }
        else:
            # Same verified patch: count its file changes once.
            author["unique_changes"][unique_key]["changed_files"] = max(
                author["unique_changes"][unique_key]["changed_files"],
                changed_files
            )

        if row["author_timestamp"]:
            author["timestamps"].append(
                datetime.fromisoformat(row["author_timestamp"])
            )

# --------------------------------------------------
# 4. Create adjusted developer summaries
# --------------------------------------------------

output_rows = []

for email, data in developers.items():
    unique_changes = data["unique_changes"]

    adjusted_file_records = sum(
        item["changed_files"] for item in unique_changes.values()
    )

    log_adjusted_contribution = sum(
        math.log1p(item["changed_files"])
        for item in unique_changes.values()
    )

    timestamps = data["timestamps"]

    output_rows.append({
        "bugzilla_email": email,
        "git_author_key": data["git_author_key"],
        "raw_commit_count": data["raw_commit_count"],
        "unique_change_units": len(unique_changes),
        "raw_changed_file_records": data["raw_changed_file_records"],
        "adjusted_changed_file_records": adjusted_file_records,
        "log_adjusted_file_contribution": round(
            log_adjusted_contribution, 4
        ),
        "first_git_contribution": min(timestamps).isoformat() if timestamps else "",
        "latest_git_contribution": max(timestamps).isoformat() if timestamps else "",
    })

# --------------------------------------------------
# 5. Save output
# --------------------------------------------------

fields = [
    "bugzilla_email",
    "git_author_key",
    "raw_commit_count",
    "unique_change_units",
    "raw_changed_file_records",
    "adjusted_changed_file_records",
    "log_adjusted_file_contribution",
    "first_git_contribution",
    "latest_git_contribution",
]

with OUTPUT_FILE.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(sorted(
        output_rows,
        key=lambda row: row["bugzilla_email"].lower()
    ))

print("\nAdjusted contribution analysis completed.")
print("Verified developers:", len(output_rows))
print("Output:", OUTPUT_FILE)
print("\nSample results:")

for row in output_rows[:5]:
    print(
        row["bugzilla_email"],
        "| raw commits:", row["raw_commit_count"],
        "| unique changes:", row["unique_change_units"],
        "| raw files:", row["raw_changed_file_records"],
        "| adjusted files:", row["adjusted_changed_file_records"],
    )
