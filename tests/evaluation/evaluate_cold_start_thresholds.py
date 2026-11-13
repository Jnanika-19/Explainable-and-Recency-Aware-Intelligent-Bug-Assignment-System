import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scoring_engine.recency.recency_calculator import parse_timestamp
from scoring_engine.cold_start.cold_start_handler import (
    classify_developer_history,
    evaluate_limited_history_component_evidence,
    build_cold_start_assessment,
)

DATA = ROOT / "data" / "processed"
ROSTER_FILE = DATA / "developer_profile_summary.csv"
HISTORY_FILE = DATA / "jdt_known_entry_preprocessed.csv"

OUTPUT = ROOT / "results" / "member3" / "cold_start"

TARGET_BUG_IDS = ["29860", "97323", "259247", "578388"]
THRESHOLDS = [3, 5, 10]


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")

    with open(path, encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows, columns):
    with open(path, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def percentage(count, total):
    return round(count * 100 / total, 2) if total else 0.0


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    print("Loading verified Cold-start evaluation data...")

    profiles = read_csv(ROSTER_FILE)
    history_rows = read_csv(HISTORY_FILE)

    # The profile file supplies identities only.
    roster = [
        row["first_observed_developer"].strip()
        for row in profiles
        if row["first_observed_developer"].strip()
    ]

    if len(roster) != len(set(roster)):
        raise ValueError("Duplicate developer IDs in profile roster.")

    if not roster:
        raise ValueError("Developer roster is empty.")

    # Only verified known_entry assignment records are accepted.
    events = []
    skipped_records = 0
    seen_bug_ids = set()

    for row in history_rows:
        if row.get("label_type") != "known_entry":
            raise ValueError(
                "Non-known_entry record found in verified history file."
            )

        bug_id = row["bug_id"].strip()
        developer = row["developer_id"].strip()

        if not bug_id or not developer:
            skipped_records += 1
            continue

        if bug_id in seen_bug_ids:
            raise ValueError(f"Duplicate historical bug ID: {bug_id}")

        seen_bug_ids.add(bug_id)

        # Parse now to reject invalid timestamps before evaluation.
        parse_timestamp(row["created_at"])
        parse_timestamp(row["assignment_time"])

        events.append({
            "bug_id": bug_id,
            "developer_label": developer,
            "label_event_time": row["assignment_time"],
            "label_event_type": "assignment_added",
            "component": row["component"],
        })

    if not events:
        raise ValueError("No verified historical assignment events found.")

    # Locate the four target bugs.
    targets = {}

    for row in history_rows:
        bug_id = row["bug_id"]

        if bug_id in TARGET_BUG_IDS:
            if bug_id in targets:
                raise ValueError(f"Duplicate target bug: {bug_id}")

            if row["label_type"] != "known_entry":
                raise ValueError(f"Target bug is not known_entry: {bug_id}")

            targets[bug_id] = row

    missing_targets = set(TARGET_BUG_IDS) - set(targets)

    if missing_targets:
        raise ValueError(
            f"Target bugs not found: {sorted(missing_targets)}"
        )

    # The full fixed roster is used only for retrospective diagnostics.
    roster_set = set(roster)
    profile_zero_known = sum(
        int(row["known_entry_bugs"]) == 0
        for row in profiles
    )

    summary_rows = []
    candidate_rows = []
    detailed_validation = []

    print(f"Verified assignment events: {len(events)}")
    print(f"Fixed developer roster: {len(roster)}")
    print(f"Prediction points: {len(TARGET_BUG_IDS)}")

    for bug_id in TARGET_BUG_IDS:
        target = targets[bug_id]
        reference_date = parse_timestamp(target["created_at"])
        component = target["component"].strip()
        actual_developer = target["developer_id"].strip()

        if actual_developer not in roster_set:
            actual_roster_status = False
        else:
            actual_roster_status = True

        print(
            f"\nPrediction point: {bug_id} | "
            f"{reference_date.isoformat()} | Component: {component}"
        )

        for threshold in THRESHOLDS:

            history = classify_developer_history(
                assignment_events=events,
                reference_date=reference_date,
                candidate_developers=roster,
                minimum_history=threshold,
                exclude_bug_id=bug_id,
            )

            component_evidence = (
                evaluate_limited_history_component_evidence(
                    assignment_events=events,
                    reference_date=reference_date,
                    developer_history=history,
                    target_component=component,
                    exclude_bug_id=bug_id,
                )
            )

            assessments = build_cold_start_assessment(
                history_results=history,
                component_results=component_evidence,
            )

            counts = {
                "sufficient_history": 0,
                "limited_history": 0,
                "no_assignment_history": 0,
            }

            evidence_counts = {
                "component_match_found": 0,
                "no_component_match": 0,
                "component_data_unavailable": 0,
            }

            supported_count = 0
            limited_additional_count = 0
            external_evidence_count = 0

            for developer in roster:
                h = history[developer]
                a = assessments[developer]
                c = component_evidence.get(developer, {})

                counts[h["history_status"]] += 1

                if h["history_status"] == "limited_history":
                    evidence_status = c["component_evidence_status"]
                    evidence_counts[evidence_status] += 1

                    if (
                        a["recommendation_path"]
                        == "limited_history_component_supported"
                    ):
                        supported_count += 1

                    if a["additional_evidence_required"]:
                        limited_additional_count += 1

                elif h["history_status"] == "no_assignment_history":
                    external_evidence_count += 1

                candidate_rows.append({
                    "target_bug_id": bug_id,
                    "prediction_timestamp_utc": reference_date.isoformat(),
                    "target_component": component,
                    "history_threshold": threshold,
                    "candidate_developer_id": developer,
                    "history_count": h["history_count"],
                    "distinct_historical_components": h["distinct_components"],
                    "history_status": h["history_status"],
                    "component_observation_count": c.get(
                        "component_observation_count", ""
                    ),
                    "component_match_count": c.get(
                        "component_match_count", ""
                    ),
                    "component_experience_share": c.get(
                        "component_experience_share", ""
                    ),
                    "component_evidence_status": a[
                        "component_evidence_status"
                    ],
                    "recommendation_path": a["recommendation_path"],
                    "additional_evidence_required": a[
                        "additional_evidence_required"
                    ],
                    "is_actual_assignee": (
                        developer == actual_developer
                    ),
                })

            actual_history = history.get(actual_developer)

            if actual_history is None:
                actual_history_status = "outside_fixed_roster"
                actual_history_count = ""
            else:
                actual_history_status = actual_history["history_status"]
                actual_history_count = actual_history["history_count"]

            total = len(roster)
            limited_count = counts["limited_history"]
            no_history_count = counts["no_assignment_history"]

            row = {
                "target_bug_id": bug_id,
                "prediction_timestamp_utc": reference_date.isoformat(),
                "target_component": component,
                "history_threshold": threshold,
                "fixed_roster_size": total,
                "sufficient_history_count": counts["sufficient_history"],
                "sufficient_history_pct": percentage(
                    counts["sufficient_history"], total
                ),
                "limited_history_count": limited_count,
                "limited_history_pct": percentage(limited_count, total),
                "no_history_count": no_history_count,
                "no_history_pct": percentage(no_history_count, total),
                "limited_component_match_count": evidence_counts[
                    "component_match_found"
                ],
                "limited_no_component_match_count": evidence_counts[
                    "no_component_match"
                ],
                "limited_component_unavailable_count": evidence_counts[
                    "component_data_unavailable"
                ],
                "limited_component_supported_count": supported_count,
                "limited_additional_evidence_required_count": (
                    limited_additional_count
                ),
                "external_evidence_required_count": external_evidence_count,
                "actual_assignee": actual_developer,
                "actual_assignee_in_fixed_roster": actual_roster_status,
                "actual_assignee_history_count": actual_history_count,
                "actual_assignee_history_status": actual_history_status,
            }

            summary_rows.append(row)

            detailed_validation.append({
                "target_bug_id": bug_id,
                "prediction_timestamp_utc": reference_date.isoformat(),
                "target_component": component,
                "threshold": threshold,
                "classification_counts": counts,
                "component_evidence_counts_for_limited_history": evidence_counts,
                "limited_component_supported": supported_count,
                "limited_additional_evidence_required": limited_additional_count,
                "no_history_external_evidence_required": external_evidence_count,
                "actual_assignee": actual_developer,
                "actual_assignee_in_fixed_roster": actual_roster_status,
                "actual_assignee_history_status": actual_history_status,
                "actual_assignee_history_count": actual_history_count,
            })

            print(
                f"Threshold={threshold:>2} | "
                f"Sufficient={counts['sufficient_history']:>3} | "
                f"Limited={limited_count:>3} | "
                f"No history={no_history_count:>3} | "
                f"Component supported={supported_count:>3}"
            )

    summary_fields = list(summary_rows[0].keys())
    candidate_fields = list(candidate_rows[0].keys())

    summary_path = OUTPUT / "member3_cold_start_threshold_summary.csv"
    candidate_path = OUTPUT / "member3_cold_start_candidate_evaluation.csv"
    validation_path = OUTPUT / "member3_cold_start_validation.json"

    write_csv(summary_path, summary_rows, summary_fields)
    write_csv(candidate_path, candidate_rows, candidate_fields)

    validation = {
        "status": "completed",
        "dataset": "jdt_known_entry_preprocessed.csv",
        "historical_evidence_policy": (
            "Only known_entry assignment records; assignment_time; "
            "strictly before prediction timestamp; target bug excluded."
        ),
        "profile_file_use": (
            "Developer identities only. Profile assignment counts and "
            "provisional activity were not used as historical evidence."
        ),
        "verified_assignment_event_count": len(events),
        "skipped_records": skipped_records,
        "fixed_roster_size": len(roster),
        "unique_roster_ids": len(roster_set),
        "profile_rows_with_zero_known_entry_bugs": profile_zero_known,
        "target_bug_ids": TARGET_BUG_IDS,
        "thresholds_evaluated": THRESHOLDS,
        "candidate_evaluation_rows": len(candidate_rows),
        "expected_candidate_evaluation_rows": (
            len(TARGET_BUG_IDS) * len(THRESHOLDS) * len(roster)
        ),
        "roster_limitation": (
            "The full 335-developer profile roster is fixed across all "
            "historical prediction points. Developers first observed after "
            "a prediction point may be classified as having no verified "
            "history. These are retrospective evidence diagnostics, not "
            "proof that all roster members were historically eligible."
        ),
        "results": detailed_validation,
        "interpretation_limitations": [
            "Component match is evidence of prior assignment to the target component, not proof of developer expertise.",
            "A single component match is not equivalent to strong expertise.",
            "No-history developers require external evidence; this evaluation does not provide that evidence.",
            "The evaluation measures historical assignment evidence, not recommendation accuracy.",
        ],
    }

    write_json(validation_path, validation)

    print("\n========== COLD-START EVALUATION COMPLETED ==========")
    print("Summary:", summary_path)
    print("Candidate details:", candidate_path)
    print("Validation:", validation_path)


if __name__ == "__main__":
    main()
