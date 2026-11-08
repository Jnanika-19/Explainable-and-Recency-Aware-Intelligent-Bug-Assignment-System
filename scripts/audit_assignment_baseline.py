
import pandas as pd
import json
from collections import Counter, defaultdict

file_path = "dataset/raw/JDT.csv"

columns = [
    "ID",
    "Creation time",
    "Component",
    "Assigned to",
    "History/Activity Log"
]

def is_inbox(value):
    value = str(value).strip().lower()

    if not value:
        return True

    return "inbox" in value

def is_person(value):
    value = str(value).strip()

    return bool(value) and not is_inbox(value)

counts = Counter()
examples = defaultdict(list)

print("Auditing assignment history and initial assignees...")
print("Please wait...\n")

for chunk in pd.read_csv(
    file_path,
    usecols=columns,
    chunksize=1000,
    low_memory=False
):

    for _, row in chunk.iterrows():

        bug_id = row["ID"]
        current = str(row["Assigned to"]).strip()
        history = row["History/Activity Log"]

        if pd.isna(history):
            activities = []
            history_readable = False
        else:
            try:
                activities = json.loads(history)
                history_readable = True
            except (json.JSONDecodeError, TypeError):
                activities = []
                history_readable = False

        events = []

        for activity in activities:
            for change in activity.get("changes", []):

                if change.get("field_name") == "assigned_to":

                    events.append({
                        "date": activity.get("when", ""),
                        "removed": str(
                            change.get("removed", "")
                        ).strip(),
                        "added": str(
                            change.get("added", "")
                        ).strip()
                    })

        events.sort(key=lambda x: x["date"])

        candidate = None
        source = None
        candidate_date = None

        if events:

            # The earliest event's removed value
            # represents the assignee before that change.
            first_old = events[0]["removed"]

            if is_person(first_old):
                candidate = first_old
                source = "First event's previous assignee"

            else:
                # Otherwise, look for the first individual
                # developer assigned in the event sequence.
                for event in events:

                    if is_person(event["added"]):
                        candidate = event["added"]
                        candidate_date = event["date"]
                        source = "First individual assignee added"
                        break

            # Compare the final recorded assignment
            # with the current Assigned to field.
            last_new = events[-1]["added"]

            if last_new and current:
                if last_new.lower() != current.lower():
                    counts["History/current mismatch"] += 1
                else:
                    counts["History/current match"] += 1

            if candidate:
                counts["Candidate from history"] += 1
                counts[source] += 1

                if len(examples[source]) < 5:
                    examples[source].append({
                        "Bug ID": bug_id,
                        "Candidate": candidate,
                        "Candidate date": candidate_date,
                        "Current assignee": current
                    })

            else:
                counts["History exists but no individual candidate"] += 1

                if len(examples["No individual candidate"]) < 5:
                    examples["No individual candidate"].append({
                        "Bug ID": bug_id,
                        "Current assignee": current
                    })

        else:

            if is_person(current):
                counts["Person in current field, no assignment events"] += 1

                if len(examples["Current person only"]) < 5:
                    examples["Current person only"].append({
                        "Bug ID": bug_id,
                        "Current assignee": current,
                        "History readable": history_readable
                    })

            else:
                counts["No individual assignment evidence"] += 1

print("\n========== BASELINE AUDIT RESULTS ==========")

for name, count in counts.items():
    print(f"{name}: {count}")

print("\n========== EXAMPLES ==========")

for category, items in examples.items():

    print("\n", category)

    for item in items:
        print(item)

print("\nAudit completed!")
