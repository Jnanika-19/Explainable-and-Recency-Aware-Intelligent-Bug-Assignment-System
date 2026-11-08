
import pandas as pd
from pathlib import Path

FILE = Path("dataset/processed/developer_identity_audit.csv")

df = pd.read_csv(FILE, dtype=str).fillna("")

# Convert the saved ID and name lists into individual values
df["bugzilla_user_ids"] = df["bugzilla_user_ids"].apply(
    lambda x: [v.strip() for v in x.split(";") if v.strip()]
)

df["real_names"] = df["real_names"].apply(
    lambda x: [v.strip().lower() for v in x.split(";") if v.strip()]
)

# Find Bugzilla IDs shared by different email addresses
id_groups = {}

for _, row in df.iterrows():
    for user_id in row["bugzilla_user_ids"]:
        id_groups.setdefault(user_id, []).append(row["email"])

# Find real names shared by different email addresses
name_groups = {}

for _, row in df.iterrows():
    for name in row["real_names"]:
        name_groups.setdefault(name, []).append(row["email"])

print("\n========== SAME BUGZILLA ID ==========")

found = False

for user_id, emails in id_groups.items():
    if len(emails) > 1:
        found = True
        print("ID:", user_id)
        print("Emails:", emails)

if not found:
    print("No shared Bugzilla IDs found.")

print("\n========== SAME REAL NAME ==========")

found = False

for name, emails in name_groups.items():
    if len(emails) > 1:
        found = True
        print("Name:", name)
        print("Emails:", emails)

if not found:
    print("No shared real names found.")

print("\nIdentity comparison completed.")
