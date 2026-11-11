import csv
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime, timezone

REPO = Path("dataset/external/eclipse.jdt.core")
OUT = Path("dataset/processed/cold_start")
OUT.mkdir(parents=True, exist_ok=True)

SEP = "\x1f"

commit_path = OUT / "jdt_git_commits.csv"
file_path = OUT / "jdt_git_commit_files.csv"
roster_path = OUT / "jdt_git_developer_roster.csv"

def make_key(email, name):
    identity = email.strip().lower() or name.strip().lower()
    return hashlib.sha256(identity.encode()).hexdigest()[:16]

def utc_date(value):
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).astimezone(timezone.utc)

command = [
    "git", "-C", str(REPO), "log",
    "--all", "--root", "--no-renames",
    "--format=%H%x1f%an%x1f%ae%x1f%aI%x1f%cI%x1f%s",
    "--name-only"
]

process = subprocess.Popen(
    command, stdout=subprocess.PIPE,
    text=True, encoding="utf-8", errors="replace"
)

authors = {}
commit_count = 0
file_count = 0

with open(commit_path, "w", newline="", encoding="utf-8-sig") as cf, \
     open(file_path, "w", newline="", encoding="utf-8-sig") as ff:

    cw = csv.writer(cf)
    fw = csv.writer(ff)

    cw.writerow([
        "commit_id", "git_author_key", "author_name",
        "author_email", "author_timestamp",
        "committer_timestamp", "subject"
    ])

    fw.writerow([
        "commit_id", "git_author_key", "author_name",
        "author_email", "author_timestamp",
        "file_path", "component"
    ])

    current = None

    for raw in process.stdout:
        line = raw.rstrip("\r\n")

        if SEP in line:
            parts = line.split(SEP, 5)
            if len(parts) != 6:
                current = None
                continue

            commit_id, name, email, author_date, committer_date, subject = parts
            key = make_key(email, name)
            current = (commit_id, key, name, email, author_date)

            cw.writerow([
                commit_id, key, name, email,
                author_date, committer_date, subject
            ])
            commit_count += 1

            dt = utc_date(author_date)
            if key not in authors:
                authors[key] = {
                    "names": set(), "emails": set(),
                    "first": dt, "latest": dt,
                    "commits": 0, "files": 0,
                    "components": set()
                }

            a = authors[key]
            a["names"].add(name)
            if email:
                a["emails"].add(email)
            a["first"] = min(a["first"], dt)
            a["latest"] = max(a["latest"], dt)
            a["commits"] += 1

        elif line and current:
            commit_id, key, name, email, author_date = current
            component = line.split("/", 1)[0]

            fw.writerow([
                commit_id, key, name, email,
                author_date, line, component
            ])

            authors[key]["files"] += 1
            authors[key]["components"].add(component)
            file_count += 1

return_code = process.wait()
if return_code != 0:
    raise RuntimeError("Git extraction failed.")

with open(roster_path, "w", newline="", encoding="utf-8-sig") as rf:
    rw = csv.writer(rf)
    rw.writerow([
        "git_author_key", "author_name", "author_email",
        "first_commit_at", "latest_commit_at",
        "commit_count", "changed_file_count", "components"
    ])

    for key, a in authors.items():
        rw.writerow([
            key, "; ".join(sorted(a["names"])),
            "; ".join(sorted(a["emails"])),
            a["first"].isoformat(), a["latest"].isoformat(),
            a["commits"], a["files"],
            "; ".join(sorted(a["components"]))
        ])

print("EXTRACTION COMPLETED")
print("Commits:", commit_count)
print("File changes:", file_count)
print("Unique Git authors:", len(authors))
print("Output folder:", OUT)
