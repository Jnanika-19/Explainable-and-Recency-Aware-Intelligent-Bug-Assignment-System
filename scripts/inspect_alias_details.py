
import pandas as pd
import ast
from pathlib import Path

RAW_FILE = Path("dataset/raw/JDT.csv")
ALIAS_FILE = Path("dataset/processed/possible_developer_aliases.csv")

# Read candidate email addresses.
aliases = pd.read_csv(ALIAS_FILE)

candidate_emails = set()

for value in aliases["email_addresses"]:
    candidate_emails.update(ast.literal_eval(value))

# Collect up to 3 examples for each email.
examples = {email: [] for email in candidate_emails}

columns = [
    "ID",
    "Product",
    "Component",
    "Assigned to",
    "Assigned to detail",
    "Summary"
]

print("Inspecting developer details...")
print("Candidate email addresses:", len(candidate_emails))

for chunk in pd.read_csv(
    RAW_FILE,
    usecols=columns,
    chunksize=500,
    dtype=str,
    keep_default_na=False
):
    for _, row in chunk.iterrows():
        email = row["Assigned to"].strip()

        if email in examples and len(examples[email]) < 3:
            examples[email].append({
                "bug_id": row["ID"],
                "email": email,
                "assigned_to_detail": row["Assigned to detail"],
                "component": row["Component"],
                "summary": row["Summary"][:100]
            })

    if all(len(items) >= 3 for items in examples.values()):
        break

print("\n========== ASSIGNEE DETAIL SAMPLES ==========")

for email, records in examples.items():
    if records:
        print("\nEmail:", email)

        for record in records:
            print(record)

print("\nInspection completed.")
