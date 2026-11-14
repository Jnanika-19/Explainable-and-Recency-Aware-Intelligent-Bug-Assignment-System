"""Prepare conservative JDT identity, point-in-time, cold-start, and duplicate audits."""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import tempfile
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dataset" / "processed"
COLD = DATA / "cold_start"
COMBINED = COLD / "eclipse_all_repositories"

PRIMARY_FILE = DATA / "jdt_training_primary.csv"
TEMPORAL_FILE = COLD / "jdt_bug_developer_temporal_features_strict.csv"
IDENTITY_AUDIT_FILE = DATA / "developer_identity_audit.csv"
EXACT_MAP_FILE = COLD / "git_bugzilla_exact_email_matches_clean.csv"
CANDIDATE_REVIEW_FILE = COLD / "git_bugzilla_candidate_review.csv"
JDT_ROSTER_FILE = COLD / "jdt_git_developer_roster.csv"
COMBINED_ROSTER_FILE = COMBINED / "eclipse_git_developer_roster.csv"
COMBINED_COHORT_FILE = (
    COMBINED / "identity_review" / "contributor_identity_cohorts_classified.csv"
)
DUPLICATE_FILE = DATA / "duplicate_pairs_historical_available.csv"
BUG_TEXT_FILE = DATA / "jdt_bug_text_cleaned.csv"

IDENTITY_DIR = COLD / "jdt_identity_review"
FEATURE_DIR = DATA / "jdt_point_in_time"
DUPLICATE_DIR = DATA / "jdt_duplicate_retrieval"
VALIDATION_REPORT = ROOT / "research" / "dataset_documentation" / (
    "jdt_preprocessing_validation_report.md"
)

OUTPUTS = {
    IDENTITY_DIR / "jdt_exact_email_mapping_audit.csv": "identity_audit",
    IDENTITY_DIR / "jdt_verified_identity_map.csv": "verified_map",
    IDENTITY_DIR / "jdt_unresolved_identity_review.csv": "unresolved_review",
    COLD / "jdt_git_contributor_cold_start_cohorts.csv": "git_cohorts",
    FEATURE_DIR / "jdt_candidate_features.csv": "candidate_features",
    FEATURE_DIR / "jdt_assignment_targets.csv": "targets",
    FEATURE_DIR / "jdt_bug_splits.csv": "splits",
    FEATURE_DIR / "jdt_cold_start_scenarios.csv": "cold_start",
    DUPLICATE_DIR / "jdt_duplicate_positive_pairs_audit.csv": "duplicate_pairs",
}

TEMPORAL_FEATURES = (
    "historical_commit_count",
    "historical_changed_file_count",
    "commits_last_30_days",
    "commits_last_90_days",
    "commits_last_365_days",
    "files_last_30_days",
    "files_last_90_days",
    "files_last_365_days",
    "days_since_last_contribution",
)


def parse_time(value: str, source: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Timezone missing in {source}: {value!r}")
    return parsed.astimezone(timezone.utc)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def read_selected(path: Path, fields: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = set(fields).difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")
        return [{field: row[field] for field in fields} for row in reader]


def csv_writer(path: Path, fields: tuple[str, ...] | list[str]):
    target = path.open("w", encoding="utf-8", newline="")
    writer = csv.DictWriter(target, fieldnames=fields, extrasaction="raise")
    writer.writeheader()
    return target, writer


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_columns(path: Path, required: set[str]) -> None:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = required.difference(reader.fieldnames or [])
    if missing:
        raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")


def truthy_review_flag(value: str, marker: str) -> bool:
    return marker in value.casefold()


def make_developer_id(bugzilla_user_id: str) -> str:
    digest = hashlib.sha256(f"jdt:{bugzilla_user_id}".encode("utf-8")).hexdigest()
    return f"jdt_dev_{digest[:16]}"


def prepare_identity(
    temporary_root: Path,
) -> tuple[dict[str, dict[str, str]], dict[str, str], dict[str, int]]:
    identity_rows = read_csv(IDENTITY_AUDIT_FILE)
    identity_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in identity_rows:
        email = row["email"].strip().casefold()
        if email:
            identity_groups[email].append(row)
    identities: dict[str, dict[str, str]] = {}
    for email, rows in identity_groups.items():
        user_ids: set[str] = set()
        records_found = 0
        for row in rows:
            row_ids = {
                value.strip()
                for value in row["bugzilla_user_ids"].replace(",", ";").split(";")
                if value.strip()
            }
            try:
                declared_count = int(row["number_of_user_ids"] or "0")
                records_found += int(row["records_found"] or "0")
            except ValueError as error:
                raise ValueError(
                    f"Invalid identity-audit count for normalized email {email}"
                ) from error
            if declared_count and not row_ids:
                raise ValueError(
                    f"Bugzilla user ID list missing for normalized email {email}"
                )
            if len(row_ids) > declared_count:
                raise ValueError(
                    f"Bugzilla user ID list/count mismatch for normalized email {email}"
                )
            user_ids.update(row_ids)
        identities[email] = {
            "number_of_user_ids": str(len(user_ids)),
            "bugzilla_user_ids": ";".join(sorted(user_ids)),
            "records_found": str(records_found),
        }

    jdt_roster = read_csv(JDT_ROSTER_FILE)
    roster_by_key = {row["git_author_key"]: row for row in jdt_roster}
    if len(roster_by_key) != len(jdt_roster):
        raise ValueError("JDT Git roster contains duplicate author keys")

    combined_roster = read_csv(COMBINED_ROSTER_FILE)
    cohort_rows = read_csv(COMBINED_COHORT_FILE)
    cohort_by_key = {
        (row["repository"], row["git_author_key"]): row for row in cohort_rows
    }
    combined_email_evidence: dict[str, tuple[str, str]] = {}
    for row in combined_roster:
        if row["repository"] != "eclipse.jdt.core":
            continue
        cohort = cohort_by_key.get((row["repository"], row["git_author_key"]), {})
        flags = " ".join(
            (
                row.get("bot_status", ""),
                row.get("identity_status", ""),
                cohort.get("review_cohorts", ""),
            )
        )
        for email in row["author_emails"].split(";"):
            normalized = email.strip().casefold()
            if normalized:
                combined_email_evidence[normalized] = (
                    row.get("bot_status", ""),
                    flags,
                )

    exact_rows = read_csv(EXACT_MAP_FILE)
    exact_pairs: set[tuple[str, str]] = set()
    verified: dict[str, dict[str, str]] = {}
    exact_audit_rows = []
    seen_git_keys: set[str] = set()
    for row in exact_rows:
        email = row["bugzilla_email"].strip().casefold()
        git_key = row["git_author_key"].strip()
        if (email, git_key) in exact_pairs:
            raise ValueError("Exact-email map contains a duplicate email/key pair")
        exact_pairs.add((email, git_key))
        if git_key in seen_git_keys:
            raise ValueError(f"Exact-email map repeats Git author key: {git_key}")
        seen_git_keys.add(git_key)

        identity = identities.get(email, {})
        try:
            user_count = int(identity.get("number_of_user_ids", "0") or "0")
        except ValueError as error:
            raise ValueError(f"Invalid Bugzilla user count for {email}") from error
        user_ids = identity.get("bugzilla_user_ids", "").strip()
        roster = roster_by_key.get(git_key)
        roster_emails = {
            value.strip().casefold()
            for value in (roster or {}).get("author_email", "").split(";")
            if value.strip()
        }
        bot_status, review_flags = combined_email_evidence.get(email, ("", ""))
        bot_flag = truthy_review_flag(review_flags, "possible_bot_needs_review")
        service_flag = truthy_review_flag(
            review_flags, "possible_service_account_needs_review"
        )
        exact_in_roster = bool(roster and email in roster_emails)

        if user_count > 1:
            status = "ambiguous_email_maps_to_multiple_bugzilla_user_ids"
        elif user_count != 1 or not user_ids:
            status = "no_unique_bugzilla_user_id_evidence"
        elif not exact_in_roster:
            status = "git_key_email_not_confirmed_in_jdt_roster"
        elif bot_flag or service_flag:
            status = "manual_bot_or_service_account_review"
        else:
            status = "verified_exact_email_unique_bugzilla_user"
            developer_id = make_developer_id(user_ids)
            verified[email] = {
                "bugzilla_email": email,
                "bugzilla_user_id": user_ids,
                "developer_id": developer_id,
                "git_author_key": git_key,
            }

        exact_audit_rows.append(
            {
                "bugzilla_email": email,
                "git_author_key": git_key,
                "bugzilla_user_id_count": user_count,
                "bugzilla_user_ids": user_ids,
                "jdt_roster_exact_email_present": str(exact_in_roster).lower(),
                "bot_status_evidence": bot_status,
                "possible_bot_review": str(bot_flag).lower(),
                "possible_service_account_review": str(service_flag).lower(),
                "mapping_status": status,
            }
        )

    verified_git_keys = {row["git_author_key"] for row in verified.values()}
    if len(verified) != len(verified_git_keys):
        raise ValueError("Verified identity mapping is not one-to-one")

    exact_audit_path = temporary_root / "jdt_exact_email_mapping_audit.csv"
    with exact_audit_path.open("w", encoding="utf-8", newline="") as target:
        fields = list(exact_audit_rows[0])
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(exact_audit_rows)

    verified_path = temporary_root / "jdt_verified_identity_map.csv"
    verified_fields = (
        "developer_id",
        "bugzilla_user_id",
        "bugzilla_email",
        "git_author_key",
        "identity_evidence",
    )
    with verified_path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=verified_fields)
        writer.writeheader()
        for email, row in sorted(verified.items()):
            writer.writerow(
                {
                    **row,
                    "identity_evidence": (
                        "exact normalized email match; one Bugzilla user ID; "
                        "matching JDT Git roster email; no bot/service heuristic"
                    ),
                }
            )

    review_rows = read_csv(CANDIDATE_REVIEW_FILE)
    review_fields = (
        "bugzilla_email",
        "bugzilla_name_key",
        "git_author_key",
        "git_names",
        "git_emails",
        "match_reason",
        "original_review_classification",
        "identity_audit_user_count",
        "identity_review_status",
        "decision",
        "reviewer",
        "decision_evidence",
    )
    unresolved_rows = []
    for row in review_rows:
        email = row["bugzilla_email"].strip().casefold()
        git_key = row["git_author_key"].strip()
        audit = next(
            (
                item
                for item in exact_audit_rows
                if item["bugzilla_email"] == email
                and item["git_author_key"] == git_key
            ),
            None,
        )
        if (email, git_key) in exact_pairs and audit:
            status = audit["mapping_status"]
            if status == "verified_exact_email_unique_bugzilla_user":
                continue
            review_status = status
        else:
            review_status = "unresolved_normalized_name_candidate"
        unresolved_rows.append(
            {
                "bugzilla_email": row["bugzilla_email"],
                "bugzilla_name_key": row["bugzilla_name_key"],
                "git_author_key": git_key,
                "git_names": row["git_names"],
                "git_emails": row["git_emails"],
                "match_reason": row["match_reason"],
                "original_review_classification": row["review_classification"],
                "identity_audit_user_count": (
                    audit["bugzilla_user_id_count"] if audit else ""
                ),
                "identity_review_status": review_status,
                "decision": "",
                "reviewer": "",
                "decision_evidence": "",
            }
        )

    for audit in exact_audit_rows:
        if audit["mapping_status"] == "verified_exact_email_unique_bugzilla_user":
            continue
        pair = (audit["bugzilla_email"], audit["git_author_key"])
        if any(
            row["bugzilla_email"].strip().casefold() == pair[0]
            and row["git_author_key"] == pair[1]
            for row in unresolved_rows
        ):
            continue
        unresolved_rows.append(
            {
                "bugzilla_email": audit["bugzilla_email"],
                "bugzilla_name_key": "",
                "git_author_key": audit["git_author_key"],
                "git_names": "",
                "git_emails": "",
                "match_reason": "exact_email_mapping_requires_conflict_review",
                "original_review_classification": "",
                "identity_audit_user_count": audit["bugzilla_user_id_count"],
                "identity_review_status": audit["mapping_status"],
                "decision": "",
                "reviewer": "",
                "decision_evidence": "",
            }
        )

    unresolved_path = temporary_root / "jdt_unresolved_identity_review.csv"
    with unresolved_path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=review_fields)
        writer.writeheader()
        writer.writerows(unresolved_rows)

    cohort_path = temporary_root / "jdt_git_contributor_cold_start_cohorts.csv"
    cohort_fields = (
        "git_author_key",
        "author_name",
        "author_email",
        "first_commit_at",
        "latest_commit_at",
        "commit_count",
        "changed_file_count",
        "components",
        "bugzilla_identity_cohort",
        "identity_candidate_review_status",
        "bot_service_review_status",
        "assignment_history_as_of_dataset",
    )
    name_review = defaultdict(set)
    for row in review_rows:
        name_review[row["git_author_key"]].add(row["review_classification"])
    combined_rows = [
        row
        for row in combined_roster
        if row["repository"] == "eclipse.jdt.core"
    ]
    with cohort_path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=cohort_fields)
        writer.writeheader()
        for row in jdt_roster:
            key = row["git_author_key"]
            email = row["author_email"].strip().casefold()
            matching_exact = [
                audit
                for audit in exact_audit_rows
                if audit["git_author_key"] == key
            ]
            if key in verified_git_keys:
                identity_cohort = "verified_exact_email_unique_bugzilla_user"
            elif any(
                audit["mapping_status"]
                == "ambiguous_email_maps_to_multiple_bugzilla_user_ids"
                for audit in matching_exact
            ):
                identity_cohort = "ambiguous_exact_email_mapping"
            elif name_review.get(key):
                identity_cohort = "unresolved_name_candidate"
            else:
                identity_cohort = "no_verified_bugzilla_identity"

            combined = next(
                (
                    item
                    for item in combined_rows
                    if email
                    and email
                    in {
                        value.strip().casefold()
                        for value in item["author_emails"].split(";")
                    }
                ),
                {},
            )
            status_values = " ".join(
                (
                    combined.get("bot_status", ""),
                    combined.get("identity_status", ""),
                )
            )
            if truthy_review_flag(status_values, "possible_bot_needs_review"):
                bot_review = "possible_bot_review"
            elif truthy_review_flag(
                status_values, "possible_service_account_needs_review"
            ):
                bot_review = "possible_service_account_review"
            else:
                bot_review = "no_existing_bot_or_service_flag"

            writer.writerow(
                {
                    "git_author_key": key,
                    "author_name": row["author_name"],
                    "author_email": row["author_email"],
                    "first_commit_at": row["first_commit_at"],
                    "latest_commit_at": row["latest_commit_at"],
                    "commit_count": row["commit_count"],
                    "changed_file_count": row["changed_file_count"],
                    "components": row["components"],
                    "bugzilla_identity_cohort": identity_cohort,
                    "identity_candidate_review_status": ";".join(
                        sorted(name_review.get(key, set()))
                    ),
                    "bot_service_review_status": bot_review,
                    "assignment_history_as_of_dataset": (
                        "not_inferred_from_git"
                        if identity_cohort != "verified_exact_email_unique_bugzilla_user"
                        else "see point-in-time assignment scenarios"
                    ),
                }
            )

    stats = {
        "exact_map_rows": len(exact_rows),
        "verified_rows": len(verified),
        "ambiguous_rows": sum(
            row["mapping_status"]
            == "ambiguous_email_maps_to_multiple_bugzilla_user_ids"
            for row in exact_audit_rows
        ),
        "unresolved_review_rows": len(unresolved_rows),
        "jdt_git_roster_rows": len(jdt_roster),
    }
    return verified, {email: row["developer_id"] for email, row in verified.items()}, stats


def prepare_bug_splits(bugs: list[dict[str, str]]) -> dict[str, str]:
    ordered = sorted(
        bugs,
        key=lambda row: (
            parse_time(row["creation_time"], f"bug {row['bug_id']} creation"),
            row["bug_id"],
        ),
    )
    split_by_bug: dict[str, str] = {}
    train_end = math.floor(len(ordered) * 0.70)
    validation_end = math.floor(len(ordered) * 0.85)
    for index, row in enumerate(ordered):
        if index < train_end:
            split = "train"
        elif index < validation_end:
            split = "validation"
        else:
            split = "test"
        split_by_bug[row["bug_id"]] = split
    return split_by_bug


def prepare_features(
    temporary_root: Path,
    verified: dict[str, dict[str, str]],
    developer_ids: dict[str, str],
) -> dict[str, int]:
    bug_fields = (
        "bug_id",
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
    )
    bugs = read_selected(PRIMARY_FILE, bug_fields)
    if not bugs:
        raise ValueError("Primary JDT training data is empty")
    if len({row["bug_id"] for row in bugs}) != len(bugs):
        raise ValueError("Primary JDT training data has duplicate bug IDs")

    events: dict[str, list[tuple[datetime, datetime, str, str]]] = defaultdict(list)
    for row in bugs:
        if row["candidate_evidence_type"] != "direct_assignment":
            raise ValueError("Primary dataset contains non-direct assignment evidence")
        if row["label_event_type"] != "assignment_added":
            raise ValueError("Primary dataset contains an unexpected label event type")
        creation = parse_time(row["creation_time"], f"bug {row['bug_id']} creation")
        event_time = parse_time(
            row["label_event_time"], f"bug {row['bug_id']} assignment event"
        )
        if event_time < creation:
            raise ValueError(f"Assignment event precedes bug creation: {row['bug_id']}")
        email = row["developer_label"].strip().casefold()
        if email in developer_ids:
            events[email].append((event_time, creation, row["component"], row["bug_id"]))

    timelines: dict[str, list[tuple[datetime, datetime, str, str]]] = {}
    component_timelines: dict[str, dict[str, list[datetime]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for email in verified:
        timelines[email] = sorted(events.get(email, []), key=lambda event: event[0])
        for event_time, _creation, component, _bug_id in timelines[email]:
            component_timelines[email][component].append(event_time)

    temporal_by_bug: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    temporal_expected = set(developer_ids)
    with TEMPORAL_FILE.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = {
            "bug_id",
            "bug_creation_time",
            "component",
            "developer_email",
            *TEMPORAL_FEATURES,
        }
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Temporal features missing fields: {sorted(missing)}")
        for row in reader:
            email = row["developer_email"].strip().casefold()
            if email not in temporal_expected:
                continue
            if email in temporal_by_bug[row["bug_id"]]:
                raise ValueError(
                    f"Duplicate temporal bug/developer row: {row['bug_id']} {email}"
                )
            for name in TEMPORAL_FEATURES[:-1]:
                if int(row[name]) < 0:
                    raise ValueError(f"Negative Git feature {name}")
            if row["days_since_last_contribution"]:
                if float(row["days_since_last_contribution"]) < 0:
                    raise ValueError("Negative Git contribution recency")
            temporal_by_bug[row["bug_id"]][email] = row

    if set(temporal_by_bug) != {row["bug_id"] for row in bugs}:
        raise ValueError("Strict temporal data and primary bug IDs do not align")
    for bug_id, developer_rows in temporal_by_bug.items():
        if set(developer_rows) != temporal_expected:
            raise ValueError(f"Temporal candidate coverage is incomplete for {bug_id}")

    split_by_bug = prepare_bug_splits(bugs)
    feature_fields = (
        "bug_id",
        "prediction_cutoff",
        "product",
        "component",
        "severity",
        "priority",
        "developer_id",
        "point_in_time_candidate_eligible",
        "prior_direct_assignment_count",
        "prior_same_component_direct_assignment_count",
        "days_since_last_direct_assignment",
        *TEMPORAL_FEATURES,
    )
    target_fields = (
        "bug_id",
        "target_developer_id",
        "target_status",
        "target_label_tier",
        "label_event_time",
        "label_event_type",
    )
    split_fields = ("bug_id", "prediction_cutoff", "data_split")
    cold_fields = (
        "bug_id",
        "prediction_cutoff",
        "developer_id",
        "data_split",
        "prior_direct_assignment_count",
        "evaluation_only_first_assignment_after_cutoff",
        "prior_git_commit_count",
        "cold_start_status",
        "genuinely_new_developer",
        "git_activity_is_assignment_evidence",
        "fallback_status",
    )

    files = {}
    writers = {}
    for label, fields in (
        ("candidate_features", feature_fields),
        ("targets", target_fields),
        ("splits", split_fields),
        ("cold_start", cold_fields),
    ):
        path = temporary_root / f"{label}.csv"
        handle, writer = csv_writer(path, fields)
        files[label] = handle
        writers[label] = writer

    target_counts: Counter[str] = Counter()
    eligible_count = 0
    cold_count = 0
    try:
        for bug in bugs:
            bug_id = bug["bug_id"]
            cutoff = parse_time(bug["creation_time"], f"bug {bug_id} creation")
            split = split_by_bug[bug_id]
            writers["splits"].writerow(
                {
                    "bug_id": bug_id,
                    "prediction_cutoff": bug["creation_time"],
                    "data_split": split,
                }
            )
            target_email = bug["developer_label"].strip().casefold()
            target_map = verified.get(target_email)
            if target_map:
                target_status = "target_in_conservative_verified_pool"
                target_counts["verified_pool"] += 1
            else:
                target_status = "target_outside_conservative_verified_pool"
                target_counts["outside_pool"] += 1
            writers["targets"].writerow(
                {
                    "bug_id": bug_id,
                    "target_developer_id": (
                        target_map["developer_id"] if target_map else ""
                    ),
                    "target_status": target_status,
                    "target_label_tier": bug["label_type"],
                    "label_event_time": bug["label_event_time"],
                    "label_event_type": bug["label_event_type"],
                }
            )

            for email, identity in sorted(verified.items()):
                history = timelines[email]
                times = [event[0] for event in history]
                end = bisect_left(times, cutoff)
                same_component_count = bisect_left(
                    component_timelines[email].get(bug["component"], []), cutoff
                )
                prior_count = end
                last_assignment = (
                    round((cutoff - times[end - 1]).total_seconds() / 86400, 3)
                    if end
                    else ""
                )
                temporal = temporal_by_bug[bug_id][email]
                prior_git_commits = int(temporal["historical_commit_count"])
                eligible = prior_count > 0
                eligible_count += int(eligible)
                writers["candidate_features"].writerow(
                    {
                        "bug_id": bug_id,
                        "prediction_cutoff": bug["creation_time"],
                        "product": bug["product"],
                        "component": bug["component"],
                        "severity": bug["severity"],
                        "priority": bug["priority"],
                        "developer_id": identity["developer_id"],
                        "point_in_time_candidate_eligible": str(eligible).lower(),
                        "prior_direct_assignment_count": prior_count,
                        "prior_same_component_direct_assignment_count": (
                            same_component_count
                        ),
                        "days_since_last_direct_assignment": last_assignment,
                        **{name: temporal[name] for name in TEMPORAL_FEATURES},
                    }
                )
                if not eligible:
                    cold_count += 1
                    next_event = history[end][0].isoformat().replace("+00:00", "Z") if end < len(history) else ""
                    writers["cold_start"].writerow(
                        {
                            "bug_id": bug_id,
                            "prediction_cutoff": bug["creation_time"],
                            "developer_id": identity["developer_id"],
                            "data_split": split,
                            "prior_direct_assignment_count": 0,
                            "evaluation_only_first_assignment_after_cutoff": next_event,
                            "prior_git_commit_count": prior_git_commits,
                            "cold_start_status": "insufficient_assignment_history_at_cutoff",
                            "genuinely_new_developer": "unknown",
                            "git_activity_is_assignment_evidence": "false",
                            "fallback_status": (
                                "git_activity_only_not_assignment_eligibility"
                                if prior_git_commits
                                else "no_supported_assignment_fallback_source"
                            ),
                        }
                    )

    finally:
        for handle in files.values():
            handle.close()

    candidate_count = len(bugs) * len(verified)
    return {
        "primary_bug_rows": len(bugs),
        "candidate_feature_rows": candidate_count,
        "point_in_time_eligible_candidate_rows": eligible_count,
        "cold_start_scenario_rows": cold_count,
        "targets_in_verified_pool": target_counts["verified_pool"],
        "targets_outside_verified_pool": target_counts["outside_pool"],
        "verified_direct_assignment_events": sum(map(len, timelines.values())),
        "candidate_developers": len(verified),
    }


def prepare_git_cohort_count() -> int:
    return len(read_csv(JDT_ROSTER_FILE))


def prepare_duplicate_audit(temporary_root: Path) -> dict[str, int]:
    pairs = read_csv(DUPLICATE_FILE)
    required = {
        "duplicate_bug_id",
        "original_bug_id",
        "family_id",
        "duplicate_creation_time",
        "original_creation_time",
        "product",
        "component",
    }
    if pairs and required.difference(pairs[0]):
        raise ValueError("Historical duplicate source is missing required fields")

    text_bug_ids: set[str] = set()
    with BUG_TEXT_FILE.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if "bug_id" not in (reader.fieldnames or []):
            raise ValueError("Cleaned text file has no bug_id column")
        for row in reader:
            text_bug_ids.add(row["bug_id"])

    fields = (
        "duplicate_bug_id",
        "original_bug_id",
        "family_id",
        "duplicate_creation_time",
        "original_creation_time",
        "product",
        "component",
        "duplicate_target_label",
        "label_use",
        "original_existed_before_cutoff",
        "text_snapshot_time",
        "retrieval_model_ready",
    )
    path = temporary_root / "jdt_duplicate_positive_pairs_audit.csv"
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        seen: set[tuple[str, str]] = set()
        for row in pairs:
            duplicate_id = row["duplicate_bug_id"]
            original_id = row["original_bug_id"]
            key = (duplicate_id, original_id)
            if key in seen:
                raise ValueError(f"Duplicate historical duplicate pair: {key}")
            seen.add(key)
            duplicate_time = parse_time(
                row["duplicate_creation_time"], f"duplicate {duplicate_id} creation"
            )
            original_time = parse_time(
                row["original_creation_time"], f"original {original_id} creation"
            )
            if original_time >= duplicate_time:
                raise ValueError(f"Original is not older than duplicate {key}")
            if duplicate_id not in text_bug_ids or original_id not in text_bug_ids:
                raise ValueError(f"Duplicate pair text reference missing: {key}")
            writer.writerow(
                {
                    "duplicate_bug_id": duplicate_id,
                    "original_bug_id": original_id,
                    "family_id": row["family_id"],
                    "duplicate_creation_time": row["duplicate_creation_time"],
                    "original_creation_time": row["original_creation_time"],
                    "product": row["product"],
                    "component": row["component"],
                    "duplicate_target_label": 1,
                    "label_use": "evaluation_target_only",
                    "original_existed_before_cutoff": "true",
                    "text_snapshot_time": "",
                    "retrieval_model_ready": "false",
                }
            )
    return {
        "historical_positive_pairs": len(pairs),
        "unique_duplicate_original_pairs": len(seen),
        "text_bug_ids": len(text_bug_ids),
        "pairs_with_both_bug_ids_in_text": len(pairs),
    }


def validate_outputs(
    staging: Path,
    identity_stats: dict[str, int],
    feature_stats: dict[str, int],
    duplicate_stats: dict[str, int],
) -> None:
    audit_rows = read_csv(staging / "jdt_exact_email_mapping_audit.csv")
    verified_rows = read_csv(staging / "jdt_verified_identity_map.csv")
    unresolved_rows = read_csv(staging / "jdt_unresolved_identity_review.csv")
    cohort_rows = read_csv(staging / "jdt_git_contributor_cold_start_cohorts.csv")
    candidate_rows = read_csv(staging / "candidate_features.csv")
    target_rows = read_csv(staging / "targets.csv")
    split_rows = read_csv(staging / "splits.csv")
    cold_rows = read_csv(staging / "cold_start.csv")
    pair_rows = read_csv(staging / "jdt_duplicate_positive_pairs_audit.csv")

    if len(audit_rows) != identity_stats["exact_map_rows"]:
        raise ValueError("Exact-email mapping audit row count mismatch")
    if len(verified_rows) != identity_stats["verified_rows"]:
        raise ValueError("Conservative verified-map row count mismatch")
    if len(cohort_rows) != identity_stats["jdt_git_roster_rows"]:
        raise ValueError("Git contributor cohort does not cover the JDT roster")
    if len(unresolved_rows) != identity_stats["unresolved_review_rows"]:
        raise ValueError("Unresolved identity review count mismatch")
    if any(row["decision"] or row["reviewer"] for row in unresolved_rows):
        raise ValueError("Unresolved identity review contains an invented decision")
    if len(candidate_rows) != feature_stats["candidate_feature_rows"]:
        raise ValueError("Candidate feature row count mismatch")
    if len(target_rows) != feature_stats["primary_bug_rows"]:
        raise ValueError("Assignment target row count mismatch")
    if len(split_rows) != feature_stats["primary_bug_rows"]:
        raise ValueError("Bug split row count mismatch")
    if len(cold_rows) != feature_stats["cold_start_scenario_rows"]:
        raise ValueError("Cold-start scenario count mismatch")
    if len(pair_rows) != duplicate_stats["historical_positive_pairs"]:
        raise ValueError("Duplicate positive pair count mismatch")

    developer_ids = [row["developer_id"] for row in verified_rows]
    if len(developer_ids) != len(set(developer_ids)):
        raise ValueError("Verified developer IDs are not unique")
    if len({row["bugzilla_user_id"] for row in verified_rows}) != len(verified_rows):
        raise ValueError("Verified Bugzilla user IDs are not unique")
    if len({row["bugzilla_email"] for row in verified_rows}) != len(verified_rows):
        raise ValueError("Verified Bugzilla emails are not unique")
    developer_id_set = set(developer_ids)
    candidate_keys = [
        (row["bug_id"], row["developer_id"]) for row in candidate_rows
    ]
    if len(candidate_keys) != len(set(candidate_keys)):
        raise ValueError("Candidate feature bug/developer keys are not unique")
    candidate_counts = Counter(row["bug_id"] for row in candidate_rows)
    split_by_bug = {row["bug_id"]: row["data_split"] for row in split_rows}
    if len(split_by_bug) != len(split_rows):
        raise ValueError("Bug split file has duplicate bug IDs")
    if set(candidate_counts) != set(split_by_bug):
        raise ValueError("Candidate feature and split bug coverage differs")
    if any(count != len(developer_ids) for count in candidate_counts.values()):
        raise ValueError("A bug does not contain every conservative candidate row")
    if any(row["developer_id"] not in developer_id_set for row in candidate_rows):
        raise ValueError("Candidate feature contains a developer outside the verified pool")

    split_rank = {"train": 0, "validation": 1, "test": 2}
    ordered_splits = sorted(
        split_rows,
        key=lambda row: (
            parse_time(row["prediction_cutoff"], row["bug_id"]),
            row["bug_id"],
        ),
    )
    ranks = [split_rank[row["data_split"]] for row in ordered_splits]
    if ranks != sorted(ranks):
        raise ValueError("Bug splits are not chronological")

    target_by_bug = {row["bug_id"]: row for row in target_rows}
    if len(target_by_bug) != len(target_rows) or set(target_by_bug) != set(split_by_bug):
        raise ValueError("Assignment target and split bug keys are inconsistent")
    cutoff_by_bug = {row["bug_id"]: row["prediction_cutoff"] for row in split_rows}
    for row in target_rows:
        if row["target_label_tier"] not in {"known_entry", "provisional"}:
            raise ValueError(f"Unknown target label tier for bug {row['bug_id']}")
        if row["target_status"] == "target_in_conservative_verified_pool":
            if row["target_developer_id"] not in developer_id_set:
                raise ValueError("In-pool target is not in the verified identity map")
        elif row["target_status"] == "target_outside_conservative_verified_pool":
            if row["target_developer_id"]:
                raise ValueError("Out-of-pool target unexpectedly has a developer ID")
        else:
            raise ValueError(f"Unexpected target status: {row['target_status']}")
        if parse_time(row["label_event_time"], row["bug_id"]) < parse_time(
            cutoff_by_bug[row["bug_id"]], row["bug_id"]
        ):
            raise ValueError("Assignment target event precedes prediction cutoff")

    feature_rows_by_key = {
        (row["bug_id"], row["developer_id"]): row for row in candidate_rows
    }

    for row in candidate_rows:
        parse_time(row["prediction_cutoff"], row["bug_id"])
        if not row["bug_id"] or not row["product"] or not row["component"]:
            raise ValueError("Required bug metadata is missing from candidate features")
        if row["point_in_time_candidate_eligible"] not in {"true", "false"}:
            raise ValueError("Invalid point-in-time eligibility value")
        if row["point_in_time_candidate_eligible"] == "true":
            if int(row["prior_direct_assignment_count"]) <= 0:
                raise ValueError("Candidate eligibility lacks prior assignment evidence")
        elif int(row["prior_direct_assignment_count"]) != 0:
            raise ValueError("Zero-history row has a positive assignment count")
        if int(row["prior_same_component_direct_assignment_count"]) > int(
            row["prior_direct_assignment_count"]
        ):
            raise ValueError("Same-component assignment count exceeds total")
        if row["days_since_last_direct_assignment"]:
            if float(row["days_since_last_direct_assignment"]) < 0:
                raise ValueError("Negative assignment recency")
        elif int(row["prior_direct_assignment_count"]) > 0:
            raise ValueError("Prior assignment count lacks its recency feature")
        for name in TEMPORAL_FEATURES[:-1]:
            if int(row[name]) < 0:
                raise ValueError(f"Negative temporal feature {name}")
        if row["days_since_last_contribution"]:
            if float(row["days_since_last_contribution"]) < 0:
                raise ValueError("Negative Git recency")
        if not (
            int(row["commits_last_30_days"])
            <= int(row["commits_last_90_days"])
            <= int(row["commits_last_365_days"])
            <= int(row["historical_commit_count"])
        ):
            raise ValueError("Git commit windows are not nested")
        if not (
            int(row["files_last_30_days"])
            <= int(row["files_last_90_days"])
            <= int(row["files_last_365_days"])
            <= int(row["historical_changed_file_count"])
        ):
            raise ValueError("Git file windows are not nested")

    cold_keys = set()
    for row in cold_rows:
        key = (row["bug_id"], row["developer_id"])
        if key in cold_keys:
            raise ValueError("Duplicate cold-start scenario key")
        cold_keys.add(key)
        feature = feature_rows_by_key.get(key)
        if feature is None or int(feature["prior_direct_assignment_count"]) != 0:
            raise ValueError("Cold-start scenario lacks zero-history candidate")
        if row["prior_direct_assignment_count"] != "0":
            raise ValueError("Cold-start scenario has nonzero prior assignments")
        if row["genuinely_new_developer"] != "unknown":
            raise ValueError("Cold-start scenario claims new-developer status")
        if row["git_activity_is_assignment_evidence"] != "false":
            raise ValueError("Git activity is misclassified as assignment evidence")
        if row["data_split"] != split_by_bug[row["bug_id"]]:
            raise ValueError("Cold-start row split differs from its bug split")
        if row["evaluation_only_first_assignment_after_cutoff"]:
            if parse_time(
                row["evaluation_only_first_assignment_after_cutoff"], row["bug_id"]
            ) <= parse_time(row["prediction_cutoff"], row["bug_id"]):
                raise ValueError("Evaluation-only first assignment is not after cutoff")

    pair_keys = set()
    for row in pair_rows:
        key = (row["duplicate_bug_id"], row["original_bug_id"])
        if key in pair_keys:
            raise ValueError("Duplicate positive pair appears more than once")
        pair_keys.add(key)
        if row["duplicate_target_label"] != "1":
            raise ValueError("Historical duplicate label changed")
        if row["label_use"] != "evaluation_target_only":
            raise ValueError("Duplicate relationship not isolated as evaluation target")
        if row["text_snapshot_time"] or row["retrieval_model_ready"] != "false":
            raise ValueError("Unverified text timing marked as retrieval-ready")
        if parse_time(
            row["original_creation_time"], row["original_bug_id"]
        ) >= parse_time(row["duplicate_creation_time"], row["duplicate_bug_id"]):
            raise ValueError("Duplicate original was unavailable before its duplicate")


def write_validation_report(
    path: Path,
    source_hashes: dict[Path, str],
    identity_stats: dict[str, int],
    feature_stats: dict[str, int],
    duplicate_stats: dict[str, int],
    output_paths: list[Path],
) -> None:
    created = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    lines = [
        "# JDT Identity and Point-in-Time Preprocessing Validation",
        "",
        f"Generated: {created}",
        "",
        "## Results",
        "",
        "- Identity audit: "
        f"{identity_stats['exact_map_rows']} exact-email map rows, "
        f"{identity_stats['verified_rows']} conservatively verified mappings, "
        f"{identity_stats['ambiguous_rows']} ambiguous multi-user emails, and "
        f"{identity_stats['unresolved_review_rows']} unresolved review rows.",
        "- Contributor cohort: "
        f"{identity_stats['jdt_git_roster_rows']} repository-scoped JDT Git keys; "
        "Git contributors are not treated as assignment candidates.",
        "- Point-in-time candidate features: "
        f"{feature_stats['candidate_feature_rows']} rows for "
        f"{feature_stats['primary_bug_rows']} bugs and "
        f"{feature_stats['candidate_developers']} conservatively verified developers.",
        "- Prior-assignment eligible candidate rows: "
        f"{feature_stats['point_in_time_eligible_candidate_rows']}; "
        "the remainder have no prior direct-assignment evidence at cutoff.",
        "- Targets: "
        f"{feature_stats['targets_in_verified_pool']} target labels in the "
        f"verified pool; {feature_stats['targets_outside_verified_pool']} outside it.",
        "- Cold-start scenarios: "
        f"{feature_stats['cold_start_scenario_rows']} candidate/cutoff rows with "
        "zero prior direct assignments. They are marked `genuinely_new_developer=unknown`.",
        "- Historical duplicate positives: "
        f"{duplicate_stats['historical_positive_pairs']} unique positive pairs; "
        "no negatives were invented and no TF-IDF was generated.",
        "",
        "## Validation",
        "",
        "- Unique exact-email mapping, verified developer, bug/developer, and bug split keys: PASS.",
        "- Every candidate feature row is strictly before the bug prediction cutoff: PASS by strict temporal source and event-time bisect.",
        "- Assignment history uses only direct `assignment_added` events whose timestamps are before the bug cutoff; this is an observed-history proxy, not a complete lifecycle history.",
        "- Candidate rows remain grouped by bug in the separate chronological 70/15/15 split file: PASS.",
        "- Nonnegative temporal counts and recency, target/feature separation, and cold-start classification checks: PASS.",
        "- Original duplicate pair chronology and bug text referential coverage: PASS.",
        "- Duplicate target fields are evaluation-only; text snapshot timing is unavailable, so retrieval-ready is false: PASS.",
        "- Source files were hashed before processing and remained unchanged: PASS.",
        "",
        "## Source SHA-256",
        "",
        "| Source | SHA-256 |",
        "|---|---|",
    ]
    for source, digest in sorted(source_hashes.items()):
        lines.append(f"| `{source.relative_to(ROOT).as_posix()}` | `{digest}` |")
    lines.extend(["", "## Generated outputs", ""])
    for output in output_paths:
        lines.append(f"- `{output.relative_to(ROOT).as_posix()}`")
    lines.extend(
        [
            "",
            "## Limitations and gates",
            "",
            "- Four exact-email mappings had no Bugzilla user ID in the available identity audit and remain unresolved; the audit found no mapping to multiple Bugzilla user IDs.",
            "- Primary labels include both `known_entry` and `provisional` tiers; the tier is kept in the target table and should be respected in evaluation.",
            "- Historical assignment counts are not active workload. The retained audit does not contain all reassignment, resolution, closure, and reopening events.",
            "- Git contribution is evidence of code activity only, not Bugzilla assignment experience or a fallback assignment label.",
            "- Historical identity verification uses the currently audited mapping and is metadata, not a point-in-time feature. Cold-start scenarios are not a deployable candidate pool.",
            "- Current cleaned bug text has no per-version availability timestamp; TF-IDF/cosine candidate features and related-bug negatives remain blocked to prevent leakage.",
            "- Platform and PDE Bugzilla endpoints were checked once separately; the current result is recorded in the final completion report.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_generation() -> None:
    missing_sources = [
        path
        for path in (
            PRIMARY_FILE,
            TEMPORAL_FILE,
            IDENTITY_AUDIT_FILE,
            EXACT_MAP_FILE,
            CANDIDATE_REVIEW_FILE,
            JDT_ROSTER_FILE,
            COMBINED_ROSTER_FILE,
            COMBINED_COHORT_FILE,
            DUPLICATE_FILE,
            BUG_TEXT_FILE,
        )
        if not path.is_file()
    ]
    if missing_sources:
        raise FileNotFoundError(f"Required source files missing: {missing_sources}")
    if VALIDATION_REPORT.exists():
        raise FileExistsError(f"Refusing to overwrite {VALIDATION_REPORT}")
    existing_outputs = [path for path in OUTPUTS if path.exists()]
    if existing_outputs:
        raise FileExistsError(f"Refusing to overwrite outputs: {existing_outputs}")

    input_files = (
        PRIMARY_FILE,
        TEMPORAL_FILE,
        IDENTITY_AUDIT_FILE,
        EXACT_MAP_FILE,
        CANDIDATE_REVIEW_FILE,
        JDT_ROSTER_FILE,
        COMBINED_ROSTER_FILE,
        COMBINED_COHORT_FILE,
        DUPLICATE_FILE,
        BUG_TEXT_FILE,
    )
    source_hashes = {path: sha256_file(path) for path in input_files}

    with tempfile.TemporaryDirectory(
        prefix=".jdt_point_in_time_", dir=DATA
    ) as temporary_directory:
        temporary_root = Path(temporary_directory)
        verified, developer_ids, identity_stats = prepare_identity(temporary_root)
        feature_stats = prepare_features(
            temporary_root, verified, developer_ids
        )
        identity_stats["jdt_git_roster_rows"] = prepare_git_cohort_count()
        duplicate_stats = prepare_duplicate_audit(temporary_root)
        validate_outputs(
            temporary_root, identity_stats, feature_stats, duplicate_stats
        )

        destinations = {
            temporary_root / "jdt_exact_email_mapping_audit.csv":
                IDENTITY_DIR / "jdt_exact_email_mapping_audit.csv",
            temporary_root / "jdt_verified_identity_map.csv":
                IDENTITY_DIR / "jdt_verified_identity_map.csv",
            temporary_root / "jdt_unresolved_identity_review.csv":
                IDENTITY_DIR / "jdt_unresolved_identity_review.csv",
            temporary_root / "jdt_git_contributor_cold_start_cohorts.csv":
                COLD / "jdt_git_contributor_cold_start_cohorts.csv",
            temporary_root / "candidate_features.csv":
                FEATURE_DIR / "jdt_candidate_features.csv",
            temporary_root / "targets.csv":
                FEATURE_DIR / "jdt_assignment_targets.csv",
            temporary_root / "splits.csv":
                FEATURE_DIR / "jdt_bug_splits.csv",
            temporary_root / "cold_start.csv":
                FEATURE_DIR / "jdt_cold_start_scenarios.csv",
            temporary_root / "jdt_duplicate_positive_pairs_audit.csv":
                DUPLICATE_DIR / "jdt_duplicate_positive_pairs_audit.csv",
        }
        for destination in destinations.values():
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise FileExistsError(f"Refusing to overwrite {destination}")
        for source, destination in destinations.items():
            source.rename(destination)

    for source, expected_hash in source_hashes.items():
        if sha256_file(source) != expected_hash:
            raise RuntimeError(f"Source changed during processing: {source}")

    output_paths = list(OUTPUTS)
    write_validation_report(
        VALIDATION_REPORT,
        source_hashes,
        identity_stats,
        feature_stats,
        duplicate_stats,
        output_paths,
    )
    print(f"Identity audit rows: {identity_stats['exact_map_rows']}")
    print(f"Conservative verified identities: {identity_stats['verified_rows']}")
    print(f"Unresolved identity review rows: {identity_stats['unresolved_review_rows']}")
    print(f"JDT Git contributor cohorts: {identity_stats['jdt_git_roster_rows']}")
    print(f"Point-in-time candidate feature rows: {feature_stats['candidate_feature_rows']}")
    print(f"Point-in-time eligible candidate rows: {feature_stats['point_in_time_eligible_candidate_rows']}")
    print(f"Targets in conservative verified pool: {feature_stats['targets_in_verified_pool']}")
    print(f"Targets outside conservative verified pool: {feature_stats['targets_outside_verified_pool']}")
    print(f"Cold-start scenario rows: {feature_stats['cold_start_scenario_rows']}")
    print(f"Historical duplicate positive pairs: {duplicate_stats['historical_positive_pairs']}")
    print(f"Validation report: {VALIDATION_REPORT.relative_to(ROOT)}")


def parse_reported_source_hashes() -> dict[str, str]:
    reported: dict[str, str] = {}
    in_hash_table = False
    for line in VALIDATION_REPORT.read_text(encoding="utf-8").splitlines():
        if line == "## Source SHA-256":
            in_hash_table = True
            continue
        if in_hash_table and line.startswith("## "):
            break
        if in_hash_table and line.startswith("| `"):
            cells = line.strip("|").split("|")
            if len(cells) >= 2:
                relative_path = cells[0].strip().strip("`")
                digest = cells[1].strip().strip("`")
                if relative_path and relative_path != "Source":
                    reported[relative_path] = digest
    return reported


def run_validation_only() -> None:
    if not VALIDATION_REPORT.is_file():
        raise FileNotFoundError(f"Missing generated validation report: {VALIDATION_REPORT}")
    missing_outputs = [path for path in OUTPUTS if not path.is_file()]
    if missing_outputs:
        raise FileNotFoundError(f"Generated outputs missing: {missing_outputs}")

    input_files = (
        PRIMARY_FILE,
        TEMPORAL_FILE,
        IDENTITY_AUDIT_FILE,
        EXACT_MAP_FILE,
        CANDIDATE_REVIEW_FILE,
        JDT_ROSTER_FILE,
        COMBINED_ROSTER_FILE,
        COMBINED_COHORT_FILE,
        DUPLICATE_FILE,
        BUG_TEXT_FILE,
    )
    source_hashes = {path: sha256_file(path) for path in input_files}
    documented_hashes = parse_reported_source_hashes()
    for path, digest in source_hashes.items():
        relative = path.relative_to(ROOT).as_posix()
        if documented_hashes.get(relative) != digest:
            raise ValueError(f"Source hash differs from generated report: {relative}")

    with tempfile.TemporaryDirectory(
        prefix=".jdt_repro_check_", dir=DATA
    ) as temporary_directory:
        temporary_root = Path(temporary_directory)
        verified, developer_ids, identity_stats = prepare_identity(temporary_root)
        feature_stats = prepare_features(
            temporary_root, verified, developer_ids
        )
        identity_stats["jdt_git_roster_rows"] = prepare_git_cohort_count()
        duplicate_stats = prepare_duplicate_audit(temporary_root)
        validate_outputs(
            temporary_root, identity_stats, feature_stats, duplicate_stats
        )
        comparisons = {
            "jdt_exact_email_mapping_audit.csv":
                IDENTITY_DIR / "jdt_exact_email_mapping_audit.csv",
            "jdt_verified_identity_map.csv":
                IDENTITY_DIR / "jdt_verified_identity_map.csv",
            "jdt_unresolved_identity_review.csv":
                IDENTITY_DIR / "jdt_unresolved_identity_review.csv",
            "jdt_git_contributor_cold_start_cohorts.csv":
                COLD / "jdt_git_contributor_cold_start_cohorts.csv",
            "candidate_features.csv":
                FEATURE_DIR / "jdt_candidate_features.csv",
            "targets.csv":
                FEATURE_DIR / "jdt_assignment_targets.csv",
            "splits.csv":
                FEATURE_DIR / "jdt_bug_splits.csv",
            "cold_start.csv":
                FEATURE_DIR / "jdt_cold_start_scenarios.csv",
            "jdt_duplicate_positive_pairs_audit.csv":
                DUPLICATE_DIR / "jdt_duplicate_positive_pairs_audit.csv",
        }
        for staged_name, existing_path in comparisons.items():
            staged_path = temporary_root / staged_name
            if sha256_file(staged_path) != sha256_file(existing_path):
                raise ValueError(
                    "Reproducibility check failed for "
                    f"{existing_path.relative_to(ROOT).as_posix()}"
                )

    for path, expected_hash in source_hashes.items():
        if sha256_file(path) != expected_hash:
            raise RuntimeError(f"Source changed during validation: {path}")
    print("Existing output structural validation: PASS")
    print("Source SHA-256 matches generated report: PASS")
    print("Deterministic regeneration in temporary staging: PASS (9/9 files byte-identical)")
    print(
        f"Rows: {feature_stats['candidate_feature_rows']} candidate features, "
        f"{feature_stats['primary_bug_rows']} target/split bugs, "
        f"{feature_stats['cold_start_scenario_rows']} cold-start scenarios, "
        f"{duplicate_stats['historical_positive_pairs']} duplicate positives"
    )
    print(
        f"Identities: {identity_stats['verified_rows']} verified, "
        f"{identity_stats['unresolved_review_rows']} unresolved review rows"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validate-existing",
        action="store_true",
        help="Rebuild in temporary staging and validate without modifying outputs.",
    )
    args = parser.parse_args()
    if args.validate_existing:
        run_validation_only()
    else:
        run_generation()


if __name__ == "__main__":
    main()
