
import pandas as pd
from collections import Counter

INPUT_PATH = "dataset/processed/duplicate_pairs.csv"
OUTPUT_PATH = "dataset/processed/duplicate_pairs_with_families.csv"

print("Loading duplicate pairs...")

df = pd.read_csv(INPUT_PATH, dtype=str)

# Keep only usable positive pairs
df = df.dropna(
    subset=[
        "duplicate_bug_id",
        "original_bug_id",
        "duplicate_summary",
        "original_summary"
    ]
).copy()

for col in ["duplicate_bug_id", "original_bug_id"]:
    df[col] = df[col].str.strip()

for col in ["duplicate_summary", "original_summary"]:
    df[col] = df[col].str.strip()

df = df[
    df["duplicate_bug_id"].ne("")
    & df["original_bug_id"].ne("")
    & df["duplicate_summary"].ne("")
    & df["original_summary"].ne("")
]

# Union-Find data structure
parent = {}

def find(x):
    if x not in parent:
        parent[x] = x

    if parent[x] != x:
        parent[x] = find(parent[x])

    return parent[x]


def union(a, b):
    root_a = find(a)
    root_b = find(b)

    if root_a != root_b:
        parent[root_b] = root_a


# Group connected duplicate reports
for _, row in df.iterrows():
    union(
        row["duplicate_bug_id"],
        row["original_bug_id"]
    )

# Assign family IDs
def family_id(bug_id):
    return find(bug_id)

df["family_id"] = df["duplicate_bug_id"].apply(family_id)

# Count bugs and relationships in each family
family_sizes = Counter()

for _, row in df.iterrows():
    family_sizes[row["family_id"]] += 1

df["family_pair_count"] = df["family_id"].map(family_sizes)

# Save results
df.to_csv(OUTPUT_PATH, index=False)

print("\n========== DUPLICATE FAMILY ANALYSIS ==========")

print("Usable duplicate pairs:", len(df))

print(
    "Unique duplicate families:",
    df["family_id"].nunique()
)

print(
    "Largest family (relationships):",
    df["family_pair_count"].max()
)

print("\nFamily size distribution:")

print(
    df.groupby("family_id")
    .size()
    .value_counts()
    .sort_index()
    .to_string()
)

print("\n========== LARGEST FAMILIES ==========")

print(
    df.groupby("family_id")
    .size()
    .sort_values(ascending=False)
    .head(10)
    .to_string()
)

print("\nSaved to:", OUTPUT_PATH)
print("\n========== COMPLETED ==========")
