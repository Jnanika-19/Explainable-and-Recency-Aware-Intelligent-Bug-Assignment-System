
import csv
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COMMITS_FILE = ROOT / "dataset/processed/cold_start/jdt_git_commits.csv"
FILES_FILE = ROOT / "dataset/processed/cold_start/jdt_git_commit_files.csv"
OUTPUT_FILE = ROOT / "dataset/processed/cold_start/git_bulk_commit_audit.csv"

# Only evidence-backed cases are classified here.
VERIFIED_DUPLICATE_GROUPS = {
    "3037b7de4ca9": "verified_duplicate_1",
    "cc0f12b3939b": "verified_duplicate_1",
}

UNVERIFIED_DUPLICATE_GROUPS = {
    "fca4d6e83a07": "unverified_duplicate_candidate_1",
    "f6792492f110": "unverified_duplicate_candidate_1",
}

PATCH_IDS = {
    "3037b7de4ca9": "8fcd21310e80c45d2cf0dec28ebdab92b7dbe25a",
    "cc0f12b3939b": "8fcd21310e80c45d2cf0dec28ebdab92b7dbe25a",
    "0278892d5c97": "b3bd89da990f5dfbd024db4f0a03deac666c6d58",
}

def short_id(commit_id):
    return commit_id[:12]

# Count changed-file records in one pass.
file_counts = Counter()

with FILES_FILE.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        file_counts[row["commit_id"]] += 1

rows = []

with COMMITS_FILE.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:
        commit_id = row["commit_id"]
        count = file_counts.get(commit_id, 0)

        if count <= 100:
            continue

        key = short_id(commit_id)

        if key in VERIFIED_DUPLICATE_GROUPS:
            classification = "verified_identical_patch"
            group = VERIFIED_DUPLICATE_GROUPS[key]
            notes = "Patch IDs match; preserve both raw commits, count one unique change."
        elif key in UNVERIFIED_DUPLICATE_GROUPS:
            classification = "unverified_duplicate_candidate"
            group = UNVERIFIED_DUPLICATE_GROUPS[key]
            notes = "Identical file lists; patch identity not verified."
        else:
            classification = "large_commit_candidate_needs_review"
            group = ""
            notes = "Large commit; size alone does not establish duplication."

        rows.append({
            "commit_id": commit_id,
            "git_author_key": row["git_author_key"],
            "author_name": row["author_name"],
            "author_timestamp": row["author_timestamp"],
            "changed_file_count": count,
            "subject": row["subject"],
            "large_commit_flag": True,
            "classification": classification,
            "patch_id": PATCH_IDS.get(key, ""),
            "verified_duplicate_group": group,
            "notes": notes,
        })

fields = [
    "commit_id",
    "git_author_key",
    "author_name",
    "author_timestamp",
    "changed_file_count",
    "subject",
    "large_commit_flag",
    "classification",
    "patch_id",
    "verified_duplicate_group",
    "notes",
]

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT_FILE.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print("Bulk commit audit completed.")
print("Large commits:", len(rows))
print("Output:", OUTPUT_FILE)
print("\nClassification summary:")

for category, count in Counter(
    row["classification"] for row in rows
).items():
    print(f"{category}: {count}")
