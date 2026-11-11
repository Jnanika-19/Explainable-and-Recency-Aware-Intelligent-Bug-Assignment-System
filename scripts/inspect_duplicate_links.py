
import pandas as pd

FILE_PATH = "dataset/raw/JDT.csv"

columns = ["ID", "Summary", "Resolution", "Dupe of"]

total_bugs = 0
duplicate_bugs = 0
examples = []

for chunk in pd.read_csv(
    FILE_PATH,
    usecols=columns,
    dtype=str,
    chunksize=500,
    low_memory=False
):
    total_bugs += len(chunk)

    duplicates = chunk[
        chunk["Dupe of"].notna()
        & chunk["Dupe of"].str.strip().ne("")
    ]

    duplicate_bugs += len(duplicates)

    remaining = 5 - len(examples)

    if remaining > 0:
        for _, row in duplicates.head(remaining).iterrows():
            examples.append({
                "bug_id": row["ID"],
                "summary": row["Summary"],
                "resolution": row["Resolution"],
                "duplicate_of": row["Dupe of"]
            })

print("\n========== DUPLICATE LINK ANALYSIS ==========")

print(f"Total bugs examined: {total_bugs}")
print(f"Bugs with duplicate links: {duplicate_bugs}")

if total_bugs:
    percentage = (duplicate_bugs / total_bugs) * 100
    print(f"Duplicate-linked bug percentage: {percentage:.2f}%")

print("\n========== SAMPLE DUPLICATE RECORDS ==========")

for example in examples:
    print("\nBug ID:", example["bug_id"])
    print("Summary:", example["summary"])
    print("Resolution:", example["resolution"])
    print("Duplicate of:", example["duplicate_of"])

print("\n========== ANALYSIS COMPLETED ==========")
