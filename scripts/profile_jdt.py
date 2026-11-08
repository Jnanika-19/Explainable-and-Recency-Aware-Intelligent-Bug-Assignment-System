
import pandas as pd
from collections import Counter

# Original JDT dataset
file_path = "dataset/raw/JDT.csv"

# Columns we want to investigate
important_columns = [
    "Product",
    "Component",
    "Status",
    "Resolution",
    "Severity",
    "Priority",
    "Assigned to",
    "Creation time",
    "Last change time"
]

# Store results
total_rows = 0
missing_counts = Counter()
category_counts = {
    column: Counter()
    for column in [
        "Product",
        "Component",
        "Status",
        "Resolution",
        "Severity",
        "Priority",
        "Assigned to"
    ]
}

print("Starting JDT dataset profiling...")
print("Please wait. The file is large.")

# Read the dataset in chunks to save RAM
for chunk in pd.read_csv(
    file_path,
    chunksize=10000,
    low_memory=False
):
    total_rows += len(chunk)

    for column in important_columns:
        missing_counts[column] += chunk[column].isna().sum()

    for column in category_counts:
        values = (
            chunk[column]
            .dropna()
            .astype(str)
            .str.strip()
        )
        category_counts[column].update(values)

# Display results
print("\n========== DATASET SUMMARY ==========")
print("Total bug reports:", total_rows)
print("Total columns:", len(important_columns))

print("\n========== MISSING VALUES ==========")
for column in important_columns:
    print(column, ":", missing_counts[column])

print("\n========== TOP CATEGORIES ==========")

for column, counts in category_counts.items():
    print(f"\nTop 15 values in {column}:")
    for value, count in counts.most_common(15):
        print(f"{value}: {count}")

print("\n========== DEVELOPER SUMMARY ==========")
print(
    "Distinct assigned-to values:",
    len(category_counts["Assigned to"])
)

print("\nDataset profiling completed!")
