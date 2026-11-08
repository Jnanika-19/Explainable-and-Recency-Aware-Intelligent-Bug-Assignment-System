
import pandas as pd
import re
from pathlib import Path

INPUT_FILE = Path("dataset/processed/jdt_assignment_label_audit.csv")
OUTPUT_DIR = Path("dataset/processed")

df = pd.read_csv(INPUT_FILE, low_memory=False)

# Keep only direct assignment evidence.
df = df[
    df["candidate_evidence_type"] == "direct_assignment"
].copy()

df["first_observed_developer"] = (
    df["first_observed_developer"].astype(str).str.strip()
)

# -----------------------------------
# 1. Compare known and provisional data
# -----------------------------------

known = df[df["label_type"] == "known_entry"].copy()
all_records = df.copy()

known_profiles = known.groupby(
    "first_observed_developer"
).size()

all_profiles = all_records.groupby(
    "first_observed_developer"
).size()

print("\n========== DATA RELIABILITY ==========")
print("Known-entry assignment records:", len(known))
print("Provisional assignment records:", 
      len(df[df["label_type"] == "provisional"]))

print("Developers with known-entry evidence:", len(known_profiles))
print("Developers with any direct evidence:", len(all_profiles))

# -----------------------------------
# 2. Developer experience distribution
# -----------------------------------

def experience_category(count):
    if count == 1:
        return "1 bug"
    elif count <= 5:
        return "2-5 bugs"
    elif count <= 10:
        return "6-10 bugs"
    else:
        return "More than 10 bugs"

distribution = all_profiles.map(
    experience_category
).value_counts()

print("\n========== EXPERIENCE DISTRIBUTION ==========")
print(distribution.to_string())

# -----------------------------------
# 3. Case-insensitive email duplicates
# -----------------------------------

df["normalized_email"] = (
    df["first_observed_developer"].str.lower()
)

case_duplicates = (
    df.groupby("normalized_email")["first_observed_developer"]
    .nunique()
)

print("\n========== CASE-INSENSITIVE IDENTITY CHECK ==========")
print(
    "Normalized emails with multiple original spellings:",
    int((case_duplicates > 1).sum())
)

# -----------------------------------
# 4. Possible aliases for manual review
# -----------------------------------

def normalize_name(email):
    local_part = email.split("@")[0].lower()
    return re.sub(r"[^a-z0-9]", "", local_part)

df["possible_name_key"] = df[
    "first_observed_developer"
].map(normalize_name)

aliases = (
    df.groupby("possible_name_key")
    ["first_observed_developer"]
    .agg(lambda x: sorted(set(x)))
    .reset_index(name="email_addresses")
)

aliases["number_of_addresses"] = aliases[
    "email_addresses"
].map(len)

aliases = aliases[
    aliases["number_of_addresses"] > 1
].copy()

aliases.to_csv(
    OUTPUT_DIR / "possible_developer_aliases.csv",
    index=False
)

print("\n========== POSSIBLE EMAIL ALIASES ==========")
print("Candidate name groups:", len(aliases))

if len(aliases):
    print(aliases.head(20).to_string(index=False))

# -----------------------------------
# 5. Save known-only developer profiles
# -----------------------------------

known_summary = known.groupby(
    "first_observed_developer"
).agg(
    known_entry_bugs=("bug_id", "count"),
    components=("component", "nunique")
).reset_index()

known_summary = known_summary.sort_values(
    "known_entry_bugs",
    ascending=False
)

known_summary.to_csv(
    OUTPUT_DIR / "known_entry_developer_profiles.csv",
    index=False
)

print("\nFiles created:")
print("- possible_developer_aliases.csv")
print("- known_entry_developer_profiles.csv")

print("\nProfile quality audit completed!")
