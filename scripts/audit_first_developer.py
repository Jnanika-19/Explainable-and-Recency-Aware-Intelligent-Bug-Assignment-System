
import pandas as pd
import json
from collections import Counter

file_path = "dataset/raw/JDT.csv"

columns = [
    "ID",
    "Creation time",
    "Component",
    "Assigned to",
    "History/Activity Log"
]

def is_inbox(email):
    email = str(email).lower()
    return "inbox" in email or not email.strip()

total_bugs = 0
bugs_with_candidate = 0
bugs_without_candidate = 0
candidate_developers = Counter()
examples = []

print("Auditing first individual developer assignments...")

for chunk in pd.read_csv(
    file_path,
    usecols=columns,
    chunksize=1000,
    low_memory=False
):

    for _, row in chunk.iterrows():

        total_bugs += 1

        history = row["History/Activity Log"]
        first_developer = None
        first_assignment_date = None

        if not pd.isna(history):

            try:
                activities = json.loads(history)

                # Ensure events are processed chronologically
                activities.sort(
                    key=lambda x: x.get("when", "")
                )

                for activity in activities:

                    for change in activity.get("changes", []):

                        if change.get("field_name") != "assigned_to":
                            continue

                        new_assignee = str(
                            change.get("added", "")
                        ).strip()

                        if new_assignee and not is_inbox(new_assignee):

                            first_developer = new_assignee
                            first_assignment_date = activity.get("when")
                            break

                    if first_developer:
                        break

            except (json.JSONDecodeError, TypeError):
                pass

        if first_developer:

            bugs_with_candidate += 1
            candidate_developers[first_developer] += 1

            if len(examples) < 20:
                examples.append({
                    "Bug ID": row["ID"],
                    "Creation time": row["Creation time"],
                    "Component": row["Component"],
                    "First developer candidate": first_developer,
                    "Assignment date": first_assignment_date,
                    "Current assignee": row["Assigned to"]
                })

        else:
            bugs_without_candidate += 1

print("\n========== FIRST DEVELOPER AUDIT ==========")

print("Total bugs:", total_bugs)
print("Bugs with a first developer candidate:", bugs_with_candidate)
print("Bugs without a candidate:", bugs_without_candidate)

print(
    "Distinct candidate email addresses:",
    len(candidate_developers)
)

print("\nTop 20 candidate developers:")

for developer, count in candidate_developers.most_common(20):
    print(developer, ":", count)

print("\nSample candidate assignments:")

for example in examples:
    print("\n", example)

print("\nAudit completed!")
