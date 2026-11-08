
import pandas as pd
import json
from collections import Counter

file_path = "dataset/raw/JDT.csv"

columns = [
    "ID",
    "Creation time",
    "Assigned to",
    "History/Activity Log"
]

def is_person(value):
    value = str(value).strip().lower()
    return bool(value) and "inbox" not in value

stats = Counter()
delay_days = []
examples = []

print("Auditing assignment timing and product migration...")
print("Please wait...\n")

for chunk in pd.read_csv(
    file_path,
    usecols=columns,
    chunksize=1000,
    low_memory=False
):

    for _, row in chunk.iterrows():

        creation = pd.to_datetime(
            row["Creation time"],
            utc=True,
            errors="coerce"
        )

        history = row["History/Activity Log"]

        if pd.isna(history):
            activities = []
            stats["Missing history"] += 1
        else:
            try:
                activities = json.loads(history)
                stats["Readable history"] += 1
            except (json.JSONDecodeError, TypeError):
                activities = []
                stats["Unreadable history"] += 1

        assignment_events = []
        jdt_entry_date = None

        for activity in activities:

            event_date = pd.to_datetime(
                activity.get("when"),
                utc=True,
                errors="coerce"
            )

            for change in activity.get("changes", []):

                field = change.get("field_name")

                if field == "assigned_to":

                    assignment_events.append({
                        "date": event_date,
                        "removed": str(
                            change.get("removed", "")
                        ).strip(),
                        "added": str(
                            change.get("added", "")
                        ).strip()
                    })

                if (
                    field == "product"
                    and str(change.get("added", "")).strip().lower() == "jdt"
                ):
                    if (
                        jdt_entry_date is None
                        or (
                            not pd.isna(event_date)
                            and event_date < jdt_entry_date
                        )
                    ):
                        jdt_entry_date = event_date

        assignment_events.sort(
            key=lambda x: (
                pd.isna(x["date"]),
                x["date"] if not pd.isna(x["date"]) else pd.Timestamp.max.tz_localize("UTC")
            )
        )

        if not assignment_events:
            if is_person(row["Assigned to"]):
                stats["Current person without assignment event"] += 1
            else:
                stats["No assignment event and inbox current assignee"] += 1
            continue

        # Find the first individual developer added
        first_person_event = None

        for event in assignment_events:

            if is_person(event["added"]):
                first_person_event = event
                break

        # Check whether the first assignment event
        # starts with an individual developer.
        first_old = assignment_events[0]["removed"]

        if is_person(first_old):
            stats["First recorded previous assignee is a person"] += 1

        if first_person_event is None:
            stats["No individual developer added"] += 1
            continue

        stats["Bugs with individual developer added"] += 1

        assignment_date = first_person_event["date"]

        if pd.isna(assignment_date) or pd.isna(creation):
            stats["Cannot calculate assignment delay"] += 1
            continue

        days = (assignment_date - creation).total_seconds() / 86400

        if days < 0:
            stats["Assignment before creation date"] += 1
        else:
            stats["Assignment on or after creation"] += 1
            delay_days.append(days)

        if jdt_entry_date is not None and not pd.isna(jdt_entry_date):

            if assignment_date < jdt_entry_date:
                stats["Developer assignment before JDT entry"] += 1
            else:
                stats["Developer assignment on or after JDT entry"] += 1

        else:
            stats["No recorded product-to-JDT transition"] += 1

        if len(examples) < 20:
            examples.append({
                "Bug ID": row["ID"],
                "Creation": str(creation),
                "JDT entry": str(jdt_entry_date),
                "Developer assignment": str(assignment_date),
                "Delay in days": round(days, 2),
                "Developer": first_person_event["added"]
            })

print("\n========== TIMING AUDIT RESULTS ==========")

for name, count in stats.items():
    print(f"{name}: {count}")

if delay_days:

    series = pd.Series(delay_days)

    print("\n========== ASSIGNMENT DELAY ==========")
    print("Minimum days:", round(series.min(), 2))
    print("Median days:", round(series.median(), 2))
    print("Mean days:", round(series.mean(), 2))
    print("90th percentile:", round(series.quantile(0.90), 2))
    print("Maximum days:", round(series.max(), 2))

print("\n========== SAMPLE RECORDS ==========")

for item in examples:
    print(item)

print("\nTiming audit completed!")
