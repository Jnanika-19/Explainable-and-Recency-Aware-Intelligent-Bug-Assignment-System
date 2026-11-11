import pandas as pd
import re
import unicodedata
from pathlib import Path

BASE = Path("dataset/processed")
COLD = BASE / "cold_start"
COLD.mkdir(parents=True, exist_ok=True)

bugzilla = pd.read_csv(BASE / "developer_identity_audit.csv", dtype=str).fillna("")
git = pd.read_csv(COLD / "jdt_git_developer_roster.csv", dtype=str).fillna("")

def split_values(value):
    return [x.strip() for x in str(value).split(";") if x.strip()]

def clean_email(value):
    return value.strip().lower()

def name_key(value):
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", value.lower())

# Build Bugzilla identity records
bug_records = []
for _, row in bugzilla.iterrows():
    email = clean_email(row["email"])
    bug_records.append({
        "bugzilla_email": email,
        "bugzilla_name": row.get("real_names", ""),
        "bugzilla_name_key": name_key(email.split("@")[0]),
    })

# Build Git identity records
git_records = []
for _, row in git.iterrows():
    emails = split_values(row["author_email"])
    names = split_values(row["author_name"])

    git_records.append({
        "git_author_key": row["git_author_key"],
        "git_names": "; ".join(names),
        "git_emails": "; ".join(emails),
        "git_name_keys": sorted(set(name_key(n) for n in names if name_key(n))),
        "git_email_keys": sorted(set(name_key(e.split("@")[0]) for e in emails if "@" in e)),
        "commit_count": row["commit_count"],
        "changed_file_count": row["changed_file_count"],
        "components": row["components"],
    })

exact_matches = []
candidate_matches = []
matched_git_keys = set()

# Exact email matches
for b in bug_records:
    for g in git_records:
        git_emails = [clean_email(x) for x in split_values(g["git_emails"])]
        if b["bugzilla_email"] in git_emails:
            exact_matches.append({
                "bugzilla_email": b["bugzilla_email"],
                "git_author_key": g["git_author_key"],
                "git_names": g["git_names"],
                "matched_email": b["bugzilla_email"],
                "match_type": "exact_email",
                "review_status": "exact_email_match_review",
            })
            matched_git_keys.add(g["git_author_key"])

# Name-key candidates; not confirmed identity matches
for b in bug_records:
    bug_key = b["bugzilla_name_key"]
    if not bug_key:
        continue

    for g in git_records:
        if bug_key in g["git_name_keys"] or bug_key in g["git_email_keys"]:
            candidate_matches.append({
                "bugzilla_email": b["bugzilla_email"],
                "bugzilla_name_key": bug_key,
                "git_author_key": g["git_author_key"],
                "git_names": g["git_names"],
                "git_emails": g["git_emails"],
                "match_reason": "same_normalized_name_key",
                "review_status": "manual_review_required",
            })

# Git authors without an exact email match remain unknown
unmatched = []
for g in git_records:
    if g["git_author_key"] not in matched_git_keys:
        unmatched.append({
            "git_author_key": g["git_author_key"],
            "git_names": g["git_names"],
            "git_emails": g["git_emails"],
            "commit_count": g["commit_count"],
            "changed_file_count": g["changed_file_count"],
            "components": g["components"],
            "identity_status": "unmatched_unknown_not_confirmed_cold_start",
        })

pd.DataFrame(exact_matches).to_csv(
    COLD / "git_bugzilla_exact_email_matches.csv", index=False
)
pd.DataFrame(candidate_matches).drop_duplicates().to_csv(
    COLD / "git_bugzilla_candidate_matches.csv", index=False
)
pd.DataFrame(unmatched).to_csv(
    COLD / "git_unmatched_identity_review.csv", index=False
)

print("Identity matching completed.")
print("Exact email matches:", len(exact_matches))
print("Name-based candidates:", len(candidate_matches))
print("Unmatched Git identities:", len(unmatched))
print("Output folder:", COLD)
