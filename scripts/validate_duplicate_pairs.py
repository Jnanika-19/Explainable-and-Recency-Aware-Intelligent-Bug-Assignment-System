
import pandas as pd

JDT_PATH = "dataset/raw/JDT.csv"
PAIRS_PATH = "dataset/processed/duplicate_pairs.csv"

print("Loading datasets...")

jdt = pd.read_csv(
    JDT_PATH,
    usecols=["ID", "Summary"],
    dtype=str,
    low_memory=False
)

pairs = pd.read_csv(
    PAIRS_PATH,
    dtype=str,
    low_memory=False
)

# Clean IDs
jdt["ID"] = jdt["ID"].str.strip()
pairs["duplicate_bug_id"] = pairs["duplicate_bug_id"].str.strip()
pairs["original_bug_id"] = pairs["original_bug_id"].str.strip()

# Create set of all bug IDs available in JDT
available_ids = set(jdt["ID"].dropna())

# Check whether original bug IDs exist
pairs["original_id_exists"] = (
    pairs["original_bug_id"].isin(available_ids)
)

# Check whether original summaries are available
pairs["original_summary_available"] = (
    pairs["original_summary"].notna()
    & pairs["original_summary"].str.strip().ne("")
)

# Check duplicate summaries
pairs["duplicate_summary_available"] = (
    pairs["duplicate_summary"].notna()
    & pairs["duplicate_summary"].str.strip().ne("")
)

print("\n========== VALIDATION RESULTS ==========")

print("Total duplicate pairs:", len(pairs))

print(
    "Original bug IDs found in JDT:",
    pairs["original_id_exists"].sum()
)

print(
    "Original bug IDs not found in JDT:",
    (~pairs["original_id_exists"]).sum()
)

print(
    "Original summaries available:",
    pairs["original_summary_available"].sum()
)

print(
    "Original summaries missing:",
    (~pairs["original_summary_available"]).sum()
)

print(
    "Duplicate summaries available:",
    pairs["duplicate_summary_available"].sum()
)

print(
    "Duplicate summaries missing:",
    (~pairs["duplicate_summary_available"]).sum()
)

# Identify usable positive pairs
usable = pairs[
    pairs["original_id_exists"]
    & pairs["original_summary_available"]
    & pairs["duplicate_summary_available"]
]

print("\nUsable positive pairs:", len(usable))

print("\n========== SAMPLE USABLE PAIRS ==========")

print(
    usable[
        [
            "duplicate_bug_id",
            "duplicate_summary",
            "original_bug_id",
            "original_summary"
        ]
    ].head(10).to_string(index=False)
)

print("\n========== VALIDATION COMPLETED ==========")
