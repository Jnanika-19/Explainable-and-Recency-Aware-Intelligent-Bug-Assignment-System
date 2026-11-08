
import pandas as pd
from pathlib import Path

FILES = {
    "Primary": Path("dataset/processed/jdt_training_primary.csv"),
    "Secondary": Path("dataset/processed/jdt_training_secondary_review.csv")
}

CHUNK_SIZE = 1000

for dataset_name, file_path in FILES.items():

    print(f"\n========== {dataset_name.upper()} DATASET ==========")

    total_rows = 0
    bug_ids = set()
    missing_counts = {}
    label_counts = {}

    for chunk in pd.read_csv(
        file_path,
        chunksize=CHUNK_SIZE,
        dtype=str,
        keep_default_na=False
    ):

        total_rows += len(chunk)

        # Check duplicate bug IDs
        for bug_id in chunk["bug_id"]:
            bug_ids.add(bug_id)

        # Count missing important fields
        important_fields = [
            "bug_id",
            "summary",
            "description",
            "component",
            "creation_time",
            "developer_label"
        ]

        for column in important_fields:
            missing_counts[column] = (
                missing_counts.get(column, 0)
                + (chunk[column].str.strip() == "").sum()
            )

        # Count evidence categories
        for label, count in chunk["label_type"].value_counts().items():
            label_counts[label] = (
                label_counts.get(label, 0) + count
            )

    print("Total rows:", total_rows)
    print("Unique bug IDs:", len(bug_ids))
    print("Duplicate bug IDs:", total_rows - len(bug_ids))

    print("\nMissing important fields:")
    for column, count in missing_counts.items():
        print(column, ":", count)

    print("\nLabel distribution:")
    for label, count in label_counts.items():
        print(label, ":", count)

print("\nDataset validation completed.")
