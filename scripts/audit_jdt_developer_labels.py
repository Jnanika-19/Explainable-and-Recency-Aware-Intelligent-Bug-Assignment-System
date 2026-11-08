
import pandas as pd
import json
import os
import csv

from collections import Counter

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

FILE_PATH = "dataset/raw/JDT.csv"

OUTPUT_PATH = (
    "dataset/processed/jdt_assignment_label_audit.csv"
)

CHUNK_SIZE = 500

COLUMNS = [
    "ID",
    "Product",
    "Component",
    "Creation time",
    "Assigned to",
    "History/Activity Log"
]

OUTPUT_COLUMNS = [
    "bug_id",
    "product",
    "component",
    "creation_time",
    "current_assignee",
    "first_observed_developer",
    "first_assignment_time",
    "jdt_entry_time",
    "label_type",
    "candidate_evidence_type",
    "candidate_source",
    "first_added_developer",
    "first_added_time",
    "first_added_evidence",
    "first_removed_developer",
    "first_removed_time",
    "first_removed_evidence",
    "assignment_evidence",
    "history_status"
]


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def is_person(value):

    if not isinstance(value, str):
        return False

    value = value.strip().lower()

    if not value:
        return False

    excluded_patterns = [
        "inbox",
        "triaged",
        "triage"
    ]

    if any(pattern in value for pattern in excluded_patterns):
        return False

    return True


def parse_history(raw_history):

    if not isinstance(raw_history, str) or not raw_history.strip():
        return None

    try:

        activities = json.loads(raw_history)

        if not isinstance(activities, list):
            return None

        return sorted(
            activities,
            key=lambda event: event.get("when", "")
        )

    except (json.JSONDecodeError, TypeError, AttributeError):

        return None


def clean_value(value):

    if pd.isna(value):
        return ""

    return str(value).strip()


def evidence_json(event):

    if event is None:
        return ""

    return json.dumps(
        event,
        ensure_ascii=False
    )


# --------------------------------------------------
# INITIALIZE AUDIT
# --------------------------------------------------

stats = Counter()

developer_counts = Counter()

examples = {
    "direct_assignment": [],
    "previous_assignee_only": [],
    "no_candidate": []
}

os.makedirs(
    os.path.dirname(OUTPUT_PATH),
    exist_ok=True
)

print("Starting JDT developer-label audit...")
print("Reading data in chunks. Please wait...\n")


# --------------------------------------------------
# PROCESS CSV
# --------------------------------------------------

with open(
    OUTPUT_PATH,
    "w",
    newline="",
    encoding="utf-8-sig"
) as output_file:

    writer = csv.DictWriter(
        output_file,
        fieldnames=OUTPUT_COLUMNS
    )

    writer.writeheader()

    for chunk in pd.read_csv(
        FILE_PATH,
        usecols=COLUMNS,
        chunksize=CHUNK_SIZE,
        low_memory=False,
        dtype={"ID": str}
    ):

        for _, row in chunk.iterrows():

            stats["total_bugs"] += 1

            bug_id = clean_value(row["ID"])
            product = clean_value(row["Product"])
            component = clean_value(row["Component"])
            creation_time = clean_value(row["Creation time"])
            current_assignee = clean_value(row["Assigned to"])

            raw_history = row["History/Activity Log"]

            # Default values
            candidate = ""
            first_assignment_time = ""
            jdt_entry_time = ""

            candidate_source = ""
            candidate_evidence_type = "no_candidate"

            first_added_developer = ""
            first_added_time = ""
            first_added_evidence = ""

            first_removed_developer = ""
            first_removed_time = ""
            first_removed_evidence = ""

            assignment_evidence = ""

            label_type = "no_candidate"
            history_status = "unreadable_or_missing"

            activities = parse_history(raw_history)

            # --------------------------------------------------
            # CASE 1: MISSING OR UNREADABLE HISTORY
            # --------------------------------------------------

            if activities is None:

                stats["missing_or_unreadable_history"] += 1

                if is_person(current_assignee):
                    stats["current_person_without_readable_history"] += 1

                assignment_evidence = (
                    "History missing or unreadable"
                )

            else:

                stats["readable_history"] += 1

                history_status = "readable"

                # --------------------------------------------------
                # STEP 1: FIND FIRST RECORDED JDT ENTRY
                # --------------------------------------------------

                for activity in activities:

                    for change in activity.get("changes", []):

                        if change.get("field_name") == "product":

                            new_product = str(
                                change.get("added", "")
                            ).strip().upper()

                            if new_product == "JDT":

                                jdt_entry_time = activity.get(
                                    "when", ""
                                )

                                break

                    if jdt_entry_time:
                        break

                if jdt_entry_time:

                    stats["bugs_with_recorded_jdt_entry"] += 1

                    category = "known_entry"

                else:

                    stats["bugs_without_recorded_jdt_entry"] += 1

                    category = "provisional"

                # --------------------------------------------------
                # STEP 2: COLLECT ASSIGNMENT EVENTS
                # --------------------------------------------------

                assignment_events = []

                for activity in activities:

                    for change in activity.get("changes", []):

                        if change.get("field_name") == "assigned_to":

                            assignment_events.append({

                                "when": activity.get("when", ""),

                                "old": change.get("removed"),

                                "new": change.get("added")

                            })

                if assignment_events:

                    stats["bugs_with_assignment_events"] += 1

                    stats["total_assignment_events"] += len(
                        assignment_events
                    )

                else:

                    stats["bugs_without_assignment_events"] += 1

                    if is_person(current_assignee):

                        stats[
                            "current_person_without_assignment_events"
                        ] += 1

                    assignment_evidence = (
                        "No assignment events in history"
                    )

                # --------------------------------------------------
                # STEP 3: SELECT ELIGIBLE ASSIGNMENTS
                # --------------------------------------------------

                eligible_events = []

                if jdt_entry_time:

                    for activity in activities:

                        event_time = activity.get("when", "")

                        if event_time < jdt_entry_time:
                            continue

                        assignment_changes = [
                            change
                            for change in activity.get("changes", [])
                            if change.get("field_name") == "assigned_to"
                        ]

                        product_changes = [
                            change
                            for change in activity.get("changes", [])
                            if change.get("field_name") == "product"
                        ]

                        for change in assignment_changes:

                            # During simultaneous product migration,
                            # do not use the previous product's assignee.

                            if (
                                product_changes
                                and event_time == jdt_entry_time
                            ):

                                eligible_events.append({

                                    "when": event_time,

                                    "old": None,

                                    "new": change.get("added")

                                })

                            else:

                                eligible_events.append({

                                    "when": event_time,

                                    "old": change.get("removed"),

                                    "new": change.get("added")

                                })

                else:

                    # No recorded JDT entry.
                    # These candidates remain provisional.

                    eligible_events = [

                        event
                        for event in assignment_events
                        if event["when"] >= creation_time

                    ]

                # --------------------------------------------------
                # STEP 4: FIND FIRST ADDED DEVELOPER
                # --------------------------------------------------

                first_added_event = None

                for event in eligible_events:

                    if is_person(event["new"]):

                        first_added_event = event

                        break

                # --------------------------------------------------
                # STEP 5: FIND FIRST REMOVED DEVELOPER
                # --------------------------------------------------

                first_removed_event = None

                for event in eligible_events:

                    if is_person(event["old"]):

                        first_removed_event = event

                        break

                # Save both evidence types independently.

                if first_added_event:

                    first_added_developer = (
                        first_added_event["new"].strip()
                    )

                    first_added_time = (
                        first_added_event["when"]
                    )

                    first_added_evidence = evidence_json(
                        first_added_event
                    )

                if first_removed_event:

                    first_removed_developer = (
                        first_removed_event["old"].strip()
                    )

                    first_removed_time = (
                        first_removed_event["when"]
                    )

                    first_removed_evidence = evidence_json(
                        first_removed_event
                    )

                # --------------------------------------------------
                # STEP 6: SELECT PRIMARY CANDIDATE
                # --------------------------------------------------

                if first_added_event:

                    # Higher-confidence evidence:
                    # developer newly assigned to the bug.

                    candidate = first_added_developer

                    first_assignment_time = first_added_time

                    candidate_source = "added"

                    candidate_evidence_type = "direct_assignment"

                    assignment_evidence = first_added_evidence

                elif first_removed_event:

                    # Lower-confidence evidence:
                    # developer was previously assigned,
                    # but no individual added event was found.

                    candidate = first_removed_developer

                    first_assignment_time = first_removed_time

                    candidate_source = "removed"

                    candidate_evidence_type = (
                        "previous_assignee_only"
                    )

                    assignment_evidence = first_removed_evidence

                else:

                    candidate_evidence_type = "no_candidate"

                    assignment_evidence = (
                        "No individual developer found "
                        "in eligible assignment events"
                    )

                # --------------------------------------------------
                # STEP 7: UPDATE LABEL STATISTICS
                # --------------------------------------------------

                if candidate:

                    label_type = category

                    stats[f"{category}_with_candidate"] += 1

                    stats[
                        f"{candidate_evidence_type}_count"
                    ] += 1

                    developer_counts[candidate] += 1

                else:

                    label_type = "no_candidate"

                    stats[f"{category}_without_candidate"] += 1

            # --------------------------------------------------
            # STEP 8: WRITE AUDIT ROW
            # --------------------------------------------------

            output_row = {

                "bug_id": bug_id,

                "product": product,

                "component": component,

                "creation_time": creation_time,

                "current_assignee": current_assignee,

                "first_observed_developer": candidate,

                "first_assignment_time": first_assignment_time,

                "jdt_entry_time": jdt_entry_time,

                "label_type": label_type,

                "candidate_evidence_type": candidate_evidence_type,

                "candidate_source": candidate_source,

                "first_added_developer": first_added_developer,

                "first_added_time": first_added_time,

                "first_added_evidence": first_added_evidence,

                "first_removed_developer": first_removed_developer,

                "first_removed_time": first_removed_time,

                "first_removed_evidence": first_removed_evidence,

                "assignment_evidence": assignment_evidence,

                "history_status": history_status

            }

            writer.writerow(output_row)

            # Save sample IDs.

            if len(examples[candidate_evidence_type]) < 10:

                examples[candidate_evidence_type].append(bug_id)


# --------------------------------------------------
# FINAL AUDIT RESULTS
# --------------------------------------------------

print("\n" + "=" * 65)

print("JDT DEVELOPER-LABEL AUDIT RESULTS")

print("=" * 65)

print("\nBASIC COUNTS")

print("Total bugs:", stats["total_bugs"])

print("Readable histories:", stats["readable_history"])

print(
    "Missing/unreadable histories:",
    stats["missing_or_unreadable_history"]
)

print("\nPRODUCT HISTORY")

print(
    "Recorded JDT entry:",
    stats["bugs_with_recorded_jdt_entry"]
)

print(
    "No recorded JDT entry:",
    stats["bugs_without_recorded_jdt_entry"]
)

print("\nASSIGNMENT HISTORY")

print(
    "Bugs with assignment events:",
    stats["bugs_with_assignment_events"]
)

print(
    "Bugs without assignment events:",
    stats["bugs_without_assignment_events"]
)

print(
    "Total assignment events:",
    stats["total_assignment_events"]
)

print("\nPRIMARY CANDIDATE LABELS")

print(
    "Known-entry candidates:",
    stats["known_entry_with_candidate"]
)

print(
    "Provisional candidates:",
    stats["provisional_with_candidate"]
)

print(
    "Known-entry without candidate:",
    stats["known_entry_without_candidate"]
)

print(
    "Provisional without candidate:",
    stats["provisional_without_candidate"]
)

print("\nEVIDENCE STRENGTH")

print(
    "Direct assignment candidates:",
    stats["direct_assignment_count"]
)

print(
    "Previous-assignee-only candidates:",
    stats["previous_assignee_only_count"]
)

print("\nTOP 15 PRIMARY DEVELOPER CANDIDATES")

for developer, count in developer_counts.most_common(15):

    print(developer, ":", count)

print("\nSAMPLE BUG IDS")

for category, records in examples.items():

    print("\n", category)

    for record in records:

        print(record)

print("\nOUTPUT FILE")

print(OUTPUT_PATH)

print("\nAudit completed successfully!")
