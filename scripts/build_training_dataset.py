
import pandas as pd
from pathlib import Path
from collections import Counter

# --------------------------------------------------
# 1. FILE LOCATIONS
# --------------------------------------------------

RAW_FILE = Path("dataset/raw/JDT.csv")

AUDIT_FILE = Path(
    "dataset/processed/jdt_assignment_label_audit.csv"
)

OUTPUT_DIR = Path("dataset/processed")

PRIMARY_OUTPUT = OUTPUT_DIR / "jdt_training_primary.csv"

SECONDARY_OUTPUT = (
    OUTPUT_DIR / "jdt_training_secondary_review.csv"
)

CHUNK_SIZE = 500

# --------------------------------------------------
# 2. COLUMNS REQUIRED FROM RAW DATASET
# --------------------------------------------------

RAW_COLUMNS = [
    "ID",
    "Product",
    "Component",
    "Severity",
    "Priority",
    "Creation time",
    "Summary",
    "Description"
]

OUTPUT_COLUMNS = [
    "bug_id",
    "summary",
    "description",
    "product",
    "component",
    "severity",
    "priority",
    "creation_time",
    "developer_label",
    "label_event_time",
    "label_event_type",
    "label_type",
    "candidate_evidence_type",
    "jdt_entry_time",
    "history_status"
]

# --------------------------------------------------
# 3. PREPARE OUTPUT FOLDER
# --------------------------------------------------

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Remove previous outputs so reruns don't append
# duplicate records to old files.
for output_file in [PRIMARY_OUTPUT, SECONDARY_OUTPUT]:
    if output_file.exists():
        output_file.unlink()

# --------------------------------------------------
# 4. LOAD SMALL AUDIT FILE
# --------------------------------------------------

print("Loading assignment audit...")

audit = pd.read_csv(
    AUDIT_FILE,
    dtype=str,
    keep_default_na=False
)

audit["bug_id"] = audit["bug_id"].str.strip()

audit_lookup = audit.set_index("bug_id").to_dict(
    orient="index"
)

print("Audit records:", len(audit_lookup))

# --------------------------------------------------
# 5. PREPARE COUNTERS
# --------------------------------------------------

primary_count = 0
secondary_count = 0

primary_labels = Counter()
secondary_labels = Counter()

primary_written = False
secondary_written = False

# --------------------------------------------------
# 6. READ LARGE RAW FILE IN SMALL CHUNKS
# --------------------------------------------------

print("\nReading JDT data in chunks...")
print("Please wait...")

for chunk in pd.read_csv(
    RAW_FILE,
    usecols=RAW_COLUMNS,
    chunksize=CHUNK_SIZE,
    dtype=str,
    keep_default_na=False
):

    primary_rows = []
    secondary_rows = []

    for _, row in chunk.iterrows():

        bug_id = row["ID"].strip()

        audit_row = audit_lookup.get(bug_id)

        if audit_row is None:
            continue

        evidence = audit_row["candidate_evidence_type"]

        # Ignore records without a developer label
        if evidence not in [
            "direct_assignment",
            "previous_assignee_only"
        ]:
            continue

        developer = audit_row[
            "first_observed_developer"
        ].strip()

        if not developer:
            continue

        # Direct assignment evidence
        if evidence == "direct_assignment":

            event_time = audit_row["first_added_time"]

            event_type = "assignment_added"

        # Weaker previous-assignee evidence
        else:

            event_time = audit_row["first_removed_time"]

            event_type = "previous_assignee_removed"

        record = {
            "bug_id": bug_id,
            "summary": row["Summary"],
            "description": row["Description"],
            "product": row["Product"],
            "component": row["Component"],
            "severity": row["Severity"],
            "priority": row["Priority"],
            "creation_time": row["Creation time"],
            "developer_label": developer,
            "label_event_time": event_time,
            "label_event_type": event_type,
            "label_type": audit_row["label_type"],
            "candidate_evidence_type": evidence,
            "jdt_entry_time": audit_row["jdt_entry_time"],
            "history_status": audit_row["history_status"]
        }

        if evidence == "direct_assignment":

            primary_rows.append(record)

            primary_labels[audit_row["label_type"]] += 1

        else:

            secondary_rows.append(record)

            secondary_labels[audit_row["label_type"]] += 1

    # --------------------------------------------------
    # 7. SAVE PRIMARY DATASET
    # --------------------------------------------------

    if primary_rows:

        output_df = pd.DataFrame(
            primary_rows,
            columns=OUTPUT_COLUMNS
        )

        output_df.to_csv(
            PRIMARY_OUTPUT,
            mode="a",
            header=not primary_written,
            index=False
        )

        primary_written = True
        primary_count += len(primary_rows)

    # --------------------------------------------------
    # 8. SAVE SECONDARY DATASET
    # --------------------------------------------------

    if secondary_rows:

        output_df = pd.DataFrame(
            secondary_rows,
            columns=OUTPUT_COLUMNS
        )

        output_df.to_csv(
            SECONDARY_OUTPUT,
            mode="a",
            header=not secondary_written,
            index=False
        )

        secondary_written = True
        secondary_count += len(secondary_rows)

    print(
        f"Processed {primary_count + secondary_count} "
        "candidate records...",
        end="\r"
    )

# --------------------------------------------------
# 9. DISPLAY FINAL RESULTS
# --------------------------------------------------

print("\n\n========== DATASET BUILD RESULTS ==========")

print("\nPrimary dataset:")
print("Direct assignment records:", primary_count)
print("Known-entry records:", primary_labels["known_entry"])
print("Provisional records:", primary_labels["provisional"])
print("Saved:", PRIMARY_OUTPUT)

print("\nSecondary review dataset:")
print("Previous-assignee-only records:", secondary_count)
print("Saved:", SECONDARY_OUTPUT)

print("\nTotal candidate records:", primary_count + secondary_count)

print("\nDataset construction completed successfully!")
