
import pandas as pd
import ast
from pathlib import Path
from collections import defaultdict

RAW_FILE = Path("dataset/raw/JDT.csv")
ALIAS_FILE = Path("dataset/processed/possible_developer_aliases.csv")
OUTPUT_FILE = Path("dataset/processed/developer_identity_audit.csv")

# Read the possible alias groups
aliases = pd.read_csv(ALIAS_FILE)

candidate_emails = set()

for value in aliases["email_addresses"]:
    candidate_emails.update(ast.literal_eval(value))

# Store Bugzilla IDs and real names for each email
identity_data = defaultdict(lambda: {
    "user_ids": set(),
    "real_names": set(),
    "records_found": 0
})

columns = ["Assigned to", "Assigned to detail"]

print("Starting Bugzilla identity audit...")
print("Candidate emails:", len(candidate_emails))

# Read the large CSV safely in chunks
for chunk in pd.read_csv(
    RAW_FILE,
    usecols=columns,
    chunksize=500,
    dtype=str,
    keep_default_na=False
):
    for _, row in chunk.iterrows():

        email = row["Assigned to"].strip()

        if email not in candidate_emails:
            continue

        detail = row["Assigned to detail"].strip()

        if not detail:
            continue

        try:
            info = ast.literal_eval(detail)

            if not isinstance(info, dict):
                continue

            user_id = info.get("id")
            real_name = info.get("real_name")

            if user_id is not None:
                identity_data[email]["user_ids"].add(str(user_id))

            if real_name:
                identity_data[email]["real_names"].add(
                    str(real_name).strip()
                )

            identity_data[email]["records_found"] += 1

        except (ValueError, SyntaxError):
            continue

# Prepare output
results = []

for email in sorted(candidate_emails):

    data = identity_data[email]

    results.append({
        "email": email,
        "bugzilla_user_ids": "; ".join(
            sorted(data["user_ids"])
        ),
        "real_names": "; ".join(
            sorted(data["real_names"])
        ),
        "number_of_user_ids": len(data["user_ids"]),
        "number_of_real_names": len(data["real_names"]),
        "records_found": data["records_found"]
    })

df = pd.DataFrame(results)

df.to_csv(OUTPUT_FILE, index=False)

print("\n========== IDENTITY AUDIT RESULTS ==========")
print("Emails inspected:", len(df))
print("Emails with user IDs:", (df["number_of_user_ids"] > 0).sum())

print("\nEmails with multiple Bugzilla IDs:")
print(
    df[df["number_of_user_ids"] > 1][
        ["email", "bugzilla_user_ids", "real_names"]
    ].to_string(index=False)
)

print("\nEmails with multiple real names:")
print(
    df[df["number_of_real_names"] > 1][
        ["email", "bugzilla_user_ids", "real_names"]
    ].to_string(index=False)
)

print("\nSaved:", OUTPUT_FILE)
print("Identity audit completed.")
