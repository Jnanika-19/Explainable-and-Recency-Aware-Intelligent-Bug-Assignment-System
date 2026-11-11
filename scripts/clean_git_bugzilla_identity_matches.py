import pandas as pd
from pathlib import Path

folder = Path("dataset/processed/cold_start")

exact_path = folder / "git_bugzilla_exact_email_matches.csv"
candidate_path = folder / "git_bugzilla_candidate_matches.csv"

exact = pd.read_csv(exact_path, dtype=str).fillna("")
candidates = pd.read_csv(candidate_path, dtype=str).fillna("")

# Remove duplicate exact mapping rows.
exact_clean = exact.drop_duplicates(
    subset=["bugzilla_email", "git_author_key"]
).copy()

# Build exact identity lookup.
exact_lookup = {}

for _, row in exact_clean.iterrows():
    exact_lookup.setdefault(row["bugzilla_email"], set()).add(
        row["git_author_key"]
    )

# Classify candidate matches conservatively.
def classify(row):
    email = row["bugzilla_email"]
    git_key = row["git_author_key"]

    if email not in exact_lookup:
        return "manual_review_required"

    if git_key in exact_lookup[email]:
        return "already_confirmed_by_exact_email"

    return "conflicting_git_identity_manual_review"

candidates["review_classification"] = candidates.apply(
    classify, axis=1
)

exact_clean.to_csv(
    folder / "git_bugzilla_exact_email_matches_clean.csv",
    index=False
)

candidates.to_csv(
    folder / "git_bugzilla_candidate_review.csv",
    index=False
)

print("Identity review preparation completed.")
print("Clean exact mappings:", len(exact_clean))
print("Unique exact Bugzilla emails:",
      exact_clean["bugzilla_email"].nunique())
print("\nCandidate classifications:")
print(candidates["review_classification"].value_counts().to_string())

print("\nOutput files:")
print("git_bugzilla_exact_email_matches_clean.csv")
print("git_bugzilla_candidate_review.csv")
