import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

BASE = Path("dataset/processed/cold_start")

IDENTITY_FILE = BASE / "git_bugzilla_exact_email_matches_clean.csv"
COMMITS_FILE = BASE / "jdt_git_commits.csv"
FILES_FILE = BASE / "jdt_git_commit_files.csv"

# Map verified Git identities to Bugzilla developer emails.
identity_map = {}

with IDENTITY_FILE.open(encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        identity_map[row["git_author_key"]] = row["bugzilla_email"]

# Developer-level statistics.
developers = defaultdict(lambda: {
    "commit_ids": set(),
    "first_timestamp": None,
    "latest_timestamp": None,
    "components": set()
})

# Component-level statistics.
component_stats = defaultdict(lambda: {
    "commit_ids": set(),
    "file_changes": 0,
    "first_timestamp": None,
    "latest_timestamp": None
})

def update_dates(record, timestamp):
    if not timestamp:
        return

    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
    except ValueError:
        return

    if record["first_timestamp"] is None or dt < record["first_timestamp"]:
        record["first_timestamp"] = dt

    if record["latest_timestamp"] is None or dt > record["latest_timestamp"]:
        record["latest_timestamp"] = dt

def format_date(value):
    return value.isoformat() if value else ""

# 1. Extract commit events for verified developers.
events_path = BASE / "git_verified_developer_commit_events.csv"

with COMMITS_FILE.open(encoding="utf-8-sig", newline="") as source, \
     events_path.open("w", encoding="utf-8", newline="") as output:

    reader = csv.DictReader(source)
    fields = [
        "bugzilla_email",
        "git_author_key",
        "commit_id",
        "author_timestamp",
        "subject"
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()

    for row in reader:
        key = row["git_author_key"]

        if key not in identity_map:
            continue

        email = identity_map[key]
        writer.writerow({
            "bugzilla_email": email,
            "git_author_key": key,
            "commit_id": row["commit_id"],
            "author_timestamp": row["author_timestamp"],
            "subject": row["subject"]
        })

        stats = developers[email]
        stats["commit_ids"].add(row["commit_id"])
        update_dates(stats, row["author_timestamp"])

# 2. Aggregate component expertise from changed files.
with FILES_FILE.open(encoding="utf-8-sig", newline="") as source:
    for row in csv.DictReader(source):
        key = row["git_author_key"]

        if key not in identity_map:
            continue

        email = identity_map[key]
        component = row["component"] or "unknown"

        stats = component_stats[(email, component)]
        stats["commit_ids"].add(row["commit_id"])
        stats["file_changes"] += 1
        update_dates(stats, row["author_timestamp"])

        developers[email]["components"].add(component)

# 3. Save developer summary.
summary_path = BASE / "git_verified_developer_summary.csv"

with summary_path.open("w", encoding="utf-8", newline="") as f:
    fields = [
        "bugzilla_email",
        "git_author_key",
        "git_commit_count",
        "changed_file_count",
        "components_worked_on",
        "first_git_contribution",
        "latest_git_contribution"
    ]
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()

    for key, email in sorted(identity_map.items(), key=lambda x: x[1]):
        stats = developers[email]
        matching_components = [
            value for (dev, _), value in component_stats.items()
            if dev == email
        ]

        writer.writerow({
            "bugzilla_email": email,
            "git_author_key": key,
            "git_commit_count": len(stats["commit_ids"]),
            "changed_file_count": sum(
                item["file_changes"] for item in matching_components
            ),
            "components_worked_on": "; ".join(sorted(stats["components"])),
            "first_git_contribution": format_date(stats["first_timestamp"]),
            "latest_git_contribution": format_date(stats["latest_timestamp"])
        })

# 4. Save developer-component expertise.
expertise_path = BASE / "git_verified_developer_component_expertise.csv"

with expertise_path.open("w", encoding="utf-8", newline="") as f:
    fields = [
        "bugzilla_email",
        "component",
        "commit_count",
        "changed_file_count",
        "first_component_contribution",
        "latest_component_contribution"
    ]
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()

    for (email, component), stats in sorted(component_stats.items()):
        writer.writerow({
            "bugzilla_email": email,
            "component": component,
            "commit_count": len(stats["commit_ids"]),
            "changed_file_count": stats["file_changes"],
            "first_component_contribution": format_date(stats["first_timestamp"]),
            "latest_component_contribution": format_date(stats["latest_timestamp"])
        })

print("Git contribution feature extraction completed.")
print("Verified developers:", len(identity_map))
print("Developer summaries:", len(developers))
print("Developer-component records:", len(component_stats))
print("\nGenerated files:")
print(events_path)
print(summary_path)
print(expertise_path)
