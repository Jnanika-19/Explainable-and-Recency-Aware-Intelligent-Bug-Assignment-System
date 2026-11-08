
import pandas as pd
import json
from collections import Counter

file_path = "dataset/raw/JDT.csv"

columns = [
    "ID",
    "Product",
    "Creation time",
    "Assigned to",
    "History/Activity Log"
]

def is_inbox(email):
    email = str(email).lower()
    return "inbox" in email

total_bugs = 0
bugs_with_history = 0
bugs_with_assignment_changes = 0
total_assignment_changes = 0

transition_types = Counter()
developer_counts = Counter()
sample_transitions = []

print("Analysing JDT assignment history...")
print("This may take several minutes.\n")

for chunk in pd.read_csv(
    file_path,
    usecols=columns,
    chunksize=1000,
    low_memory=False
):
    for _, row in chunk.iterrows():

        total_bugs += 1
        history = row["History/Activity Log"]

        if pd.isna(history):
            continue

        try:
            activities = json.loads(history)
            bugs_with_history += 1
        except (json.JSONDecodeError, TypeError):
            continue

        bug_has_assignment = False

        for activity in activities:

            for change in activity.get("changes", []):

                if change.get("field_name") != "assigned_to":
                    continue

                old = change.get("removed", "")
                new = change.get("added", "")

                old = str(old).strip()
                new = str(new).strip()

                total_assignment_changes += 1
                bug_has_assignment = True

                if is_inbox(old) and not is_inbox(new):
                    transition_types["Inbox to developer"] += 1

                elif not is_inbox(old) and is_inbox(new):
                    transition_types["Developer to inbox"] += 1

                elif not is_inbox(old) and not is_inbox(new):
                    transition_types["Developer to developer"] += 1

                else:
                    transition_types["Inbox to inbox"] += 1

                if new and not is_inbox(new):
                    developer_counts[new] += 1

                if len(sample_transitions) < 15:
                    sample_transitions.append({
                        "Bug ID": row["ID"],
                        "Date": activity.get("when", ""),
                        "Changed by": activity.get("who", ""),
                        "Previous assignee": old,
                        "New assignee": new
                    })

        if bug_has_assignment:
            bugs_with_assignment_changes += 1

print("\n========== ASSIGNMENT ANALYSIS ==========")

print("Total bugs:", total_bugs)
print("Bugs with readable history:", bugs_with_history)
print("Bugs with assignment changes:", bugs_with_assignment_changes)
print("Total assignment changes:", total_assignment_changes)

print("\nAssignment transition types:")
for name, count in transition_types.items():
    print(name, ":", count)

print("\nTop 15 developers appearing as new assignees:")
for developer, count in developer_counts.most_common(15):
    print(developer, ":", count)

print("\nSample assignment transitions:")
for item in sample_transitions:
    print("\n", item)

print("\nAnalysis completed!")
