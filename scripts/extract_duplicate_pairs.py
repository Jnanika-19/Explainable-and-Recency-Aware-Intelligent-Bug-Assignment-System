
import pandas as pd
from pathlib import Path

FILE_PATH = "dataset/raw/JDT.csv"
OUTPUT_PATH = "dataset/processed/duplicate_pairs.csv"

columns = ["ID", "Summary", "Resolution", "Dupe of"]

print("Loading JDT dataset...")

df = pd.read_csv(
    FILE_PATH,
    usecols=columns,
    dtype=str,
    low_memory=False
)

# Clean bug IDs
for col in ["ID", "Dupe of"]:
    df[col] = df[col].str.strip()

# Remove records without IDs
df = df.dropna(subset=["ID"])

# Build a lookup for original bug summaries
bug_lookup = (
    df.drop_duplicates(subset=["ID"])
    [["ID", "Summary"]]
    .rename(columns={
        "ID": "original_bug_id",
        "Summary": "original_summary"
    })
)

# Extract duplicate relationships
duplicates = df[
    df["Dupe of"].notna()
    & df["Dupe of"].ne("")
].copy()

# Create positive pairs
pairs = duplicates[
    ["ID", "Summary", "Resolution", "Dupe of"]
].rename(columns={
    "ID": "duplicate_bug_id",
    "Summary": "duplicate_summary",
    "Dupe of": "original_bug_id"
})

# Attach original bug summaries
pairs = pairs.merge(
    bug_lookup,
    on="original_bug_id",
    how="left"
)

# Identify missing original bug reports
missing = pairs["original_summary"].isna()

print("\n========== EXTRACTION RESULTS ==========")

print("Duplicate-linked records:", len(pairs))
print("Unique duplicate pairs:",
      pairs[["duplicate_bug_id", "original_bug_id"]]
      .drop_duplicates().shape[0])

print("Original bugs found in JDT:",
      (~missing).sum())

print("Original bugs missing from JDT:",
      missing.sum())

# Save all pairs, including missing original summaries
Path("dataset/processed").mkdir(
    parents=True, exist_ok=True
)

pairs.to_csv(OUTPUT_PATH, index=False)

print("\nSaved duplicate pairs to:", OUTPUT_PATH)

print("\n========== SAMPLE PAIRS ==========")

print(pairs.head(10).to_string(index=False))

print("\n========== COMPLETED ==========")
