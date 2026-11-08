
import pandas as pd
from pathlib import Path

INPUT_FILE = Path("dataset/processed/jdt_assignment_label_audit.csv")
OUTPUT_DIR = Path("dataset/processed")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("Loading assignment audit...")
df = pd.read_csv(INPUT_FILE, low_memory=False)

# Use only the strongest assignment evidence.
df = df[
    df["candidate_evidence_type"] == "direct_assignment"
].copy()

# Remove rows without a developer name.
df = df[
    df["first_observed_developer"].notna()
    & (df["first_observed_developer"].str.strip() != "")
].copy()

# Convert assignment timestamps into datetime values.
df["first_assignment_time"] = pd.to_datetime(
    df["first_assignment_time"],
    errors="coerce",
    utc=True
)

print("Direct assignment records:", len(df))

# ---------------------------------------
# 1. Overall developer profiles
# ---------------------------------------

profiles = df.groupby("first_observed_developer").agg(
    total_assigned_bugs=("bug_id", "count"),
    components_worked_on=("component", "nunique"),
    known_entry_bugs=(
        "label_type",
        lambda x: (x == "known_entry").sum()
    ),
    provisional_bugs=(
        "label_type",
        lambda x: (x == "provisional").sum()
    ),
    first_recorded_assignment=("first_assignment_time", "min"),
    latest_recorded_assignment=("first_assignment_time", "max")
).reset_index()

profiles = profiles.sort_values(
    "total_assigned_bugs",
    ascending=False
)

profiles.to_csv(
    OUTPUT_DIR / "developer_profile_summary.csv",
    index=False
)

# ---------------------------------------
# 2. Developer expertise by component
# ---------------------------------------

expertise = df.groupby(
    ["first_observed_developer", "component"]
).size().reset_index(name="bug_count")

expertise["share_within_developer"] = (
    expertise["bug_count"]
    / expertise.groupby("first_observed_developer")["bug_count"].transform("sum")
)

expertise = expertise.sort_values(
    ["first_observed_developer", "bug_count"],
    ascending=[True, False]
)

expertise.to_csv(
    OUTPUT_DIR / "developer_component_expertise.csv",
    index=False
)

# ---------------------------------------
# 3. Display summary
# ---------------------------------------

print("\n========== DEVELOPER PROFILE RESULTS ==========")

print("Unique developers:", len(profiles))

print("\nTop 15 developers by assigned bug count:")

print(
    profiles.head(15).to_string(index=False)
)

print("\nComponent expertise sample:")

print(
    expertise.head(20).to_string(index=False)
)

print("\nFiles created:")
print("1. developer_profile_summary.csv")
print("2. developer_component_expertise.csv")

print("\nDeveloper profile extraction completed!")
