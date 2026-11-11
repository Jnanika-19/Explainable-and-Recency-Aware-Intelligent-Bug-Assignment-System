
import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
from bisect import bisect_left, bisect_right

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dataset/processed"
COLD = DATA / "cold_start"

BUG_FILE = DATA / "jdt_training_primary.csv"
COMMIT_FILE = COLD / "jdt_git_commits.csv"
FILE_CHANGE_FILE = COLD / "jdt_git_commit_files.csv"
IDENTITY_FILE = COLD / "git_bugzilla_exact_email_matches_clean.csv"
AUDIT_FILE = COLD / "git_bulk_commit_audit.csv"

OUTPUT_FILE = COLD / "jdt_bug_developer_temporal_features_strict.csv"


def parse_time(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# --------------------------------------------------
# 1. Load verified Git-to-Bugzilla identities
# --------------------------------------------------

git_to_bugzilla = {}
bugzilla_developers = set()

with IDENTITY_FILE.open(encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        key = row["git_author_key"]
        email = row["bugzilla_email"].strip().lower()

        git_to_bugzilla[key] = email
        bugzilla_developers.add(email)

print("Verified developers:", len(bugzilla_developers))


# --------------------------------------------------
# 2. Count changed-file records per commit
# --------------------------------------------------

file_counts = defaultdict(int)

with FILE_CHANGE_FILE.open(encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        file_counts[row["commit_id"]] += 1

print("Commit file counts loaded:", len(file_counts))


# --------------------------------------------------
# 3. Read verified duplicate groups
# --------------------------------------------------

duplicate_groups = {}

with AUDIT_FILE.open(encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        if row["classification"] == "verified_identical_patch":
            duplicate_groups[row["commit_id"]] = (
                row["verified_duplicate_group"]
            )


# --------------------------------------------------
# 4. Build unique, timestamped developer contributions
# --------------------------------------------------

unique_events = defaultdict(dict)

with COMMIT_FILE.open(encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        author_key = row["git_author_key"]

        if author_key not in git_to_bugzilla:
            continue

        timestamp = parse_time(row["committer_timestamp"])

        if timestamp is None:
            continue

        email = git_to_bugzilla[author_key]
        commit_id = row["commit_id"]

        # Only verified identical patches are collapsed.
        unique_key = duplicate_groups.get(commit_id, commit_id)

        changed_files = file_counts.get(commit_id, 0)

        existing = unique_events[email].get(unique_key)

        if existing is None:
            unique_events[email][unique_key] = {
                "timestamp": timestamp,
                "changed_files": changed_files
            }
        else:
            # Keep the earliest availability time and maximum
            # file count for the verified identical patch.
            existing["timestamp"] = min(
                existing["timestamp"], timestamp
            )
            existing["changed_files"] = max(
                existing["changed_files"], changed_files
            )

print("Developer contribution histories prepared.")


# --------------------------------------------------
# 5. Prepare sorted timelines and prefix sums
# --------------------------------------------------

timelines = {}

for email in bugzilla_developers:
    events = list(unique_events[email].values())
    events.sort(key=lambda x: x["timestamp"])

    timestamps = [event["timestamp"] for event in events]

    prefix_files = [0]
    for event in events:
        prefix_files.append(
            prefix_files[-1] + event["changed_files"]
        )

    timelines[email] = (timestamps, prefix_files)

# --------------------------------------------------
# 6. Generate bug-developer temporal features
# --------------------------------------------------

fields = [
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
]

total_rows = 0
invalid_bugs = 0

with BUG_FILE.open(encoding="utf-8-sig", newline="") as source, \
     OUTPUT_FILE.open("w", encoding="utf-8-sig", newline="") as target:

    reader = csv.DictReader(source)
    writer = csv.DictWriter(target, fieldnames=fields)
    writer.writeheader()

    for bug in reader:
        bug_time = parse_time(bug["creation_time"])

        if bug_time is None:
            invalid_bugs += 1
            continue

        actual_label = bug["developer_label"].strip().lower()

        for email in sorted(bugzilla_developers):
            timestamps, prefix_files = timelines[email]

            # Contributions available on or before bug creation.
            end = bisect_left(timestamps, bug_time)

            # Historical window boundaries.
            start_30 = bisect_left(
                timestamps, bug_time - timedelta(days=30), 0, end
            )
            start_90 = bisect_left(
                timestamps, bug_time - timedelta(days=90), 0, end
            )
            start_365 = bisect_left(
                timestamps, bug_time - timedelta(days=365), 0, end
            )

            historical_count = end
            historical_files = prefix_files[end]

            files_30 = prefix_files[end] - prefix_files[start_30]
            files_90 = prefix_files[end] - prefix_files[start_90]
            files_365 = prefix_files[end] - prefix_files[start_365]

            days_since = ""
            if end > 0:
                days_since = round(
                    (bug_time - timestamps[end - 1]).total_seconds()
                    / 86400,
                    3
                )

            writer.writerow({
                "bug_id": bug["bug_id"],
                "bug_creation_time": bug["creation_time"],
                "component": bug["component"],
                "developer_email": email,
                "is_assigned_developer": int(actual_label == email),
                "historical_commit_count": historical_count,
                "historical_changed_file_count": historical_files,
                "commits_last_30_days": end - start_30,
                "commits_last_90_days": end - start_90,
                "commits_last_365_days": end - start_365,
                "files_last_30_days": files_30,
                "files_last_90_days": files_90,
                "files_last_365_days": files_365,
                "days_since_last_contribution": days_since,
                "label_type": bug["label_type"],
                "candidate_evidence_type": bug["candidate_evidence_type"],
            })

            total_rows += 1

        if total_rows and total_rows % 50000 == 0:
            print("Rows generated:", total_rows)

print("\nTemporal feature extraction completed.")
print("Bugs with invalid timestamps:", invalid_bugs)
print("Verified developers:", len(bugzilla_developers))
print("Bug-developer rows:", total_rows)
print("Expected output:", OUTPUT_FILE)
