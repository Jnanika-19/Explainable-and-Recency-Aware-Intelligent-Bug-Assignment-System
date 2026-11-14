"""Prepare non-destructive manual review files for Eclipse Git identities."""

from __future__ import annotations

import csv
import argparse
import re
import sys
import tempfile
import unicodedata
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "dataset/processed/cold_start/eclipse_all_repositories"
OUTPUT_DIR = SOURCE_DIR / "identity_review"
REVIEW_FIELDS = (
    "repository",
    "git_author_key",
    "author_names",
    "author_emails",
    "candidate_repository",
    "candidate_git_author_key",
    "candidate_names",
    "candidate_emails",
    "candidate_evidence",
    "email_name_conflict",
    "multiple_candidate_links",
    "possible_bot_in_pair",
    "manual_review_status",
    "review_decision",
    "reviewer",
    "reviewed_at_utc",
    "evidence_notes",
)
COHORT_FIELDS = (
    "repository",
    "git_author_key",
    "commit_count",
    "changed_file_count",
    "bot_status",
    "identity_status",
    "review_cohorts",
    "candidate_link_count",
    "review_status",
)
SERVICE_MARKERS = re.compile(
    r"(?:^|[^a-z0-9])(?:service|automation|build|releng|jenkins|teamcity|ci|bot)(?:$|[^a-z0-9])",
    re.IGNORECASE,
)


def normalize_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value).casefold()
    return "".join(character for character in decomposed if character.isalnum())


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader)


def prepare_review_rows(
    candidates: list[dict[str, str]],
) -> list[dict[str, str]]:
    reasons_by_pair: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    record_by_pair: dict[tuple[str, str, str, str], dict[str, str]] = {}
    degree: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    for row in candidates:
        left = (row["repository"], row["git_author_key"])
        right = (row["candidate_repository"], row["candidate_git_author_key"])
        if left[0] == right[0] or left == right:
            raise ValueError("Identity candidates must connect distinct repository identities")
        pair_left, pair_right = sorted((left, right))
        pair = (*pair_left, *pair_right)
        reasons_by_pair[pair].add(row["match_reason"])
        if left == pair_left:
            record_by_pair[pair] = row
        else:
            record_by_pair[pair] = {
                **row,
                "repository": row["candidate_repository"],
                "git_author_key": row["candidate_git_author_key"],
                "author_names": row["candidate_names"],
                "author_emails": row["candidate_emails"],
                "candidate_repository": row["repository"],
                "candidate_git_author_key": row["git_author_key"],
                "candidate_names": row["author_names"],
                "candidate_emails": row["author_emails"],
            }
        degree[left].add(right)
        degree[right].add(left)

    review_rows: list[dict[str, str]] = []
    for pair in sorted(reasons_by_pair):
        source_row = record_by_pair[pair]
        reasons = reasons_by_pair[pair]
        is_exact_email = "exact_email_candidate" in reasons
        is_exact_name = "exact_normalized_name_candidate" in reasons
        has_bot_flag = (
            "possible_bot" in source_row["bot_status"]
            or "possible_bot" in source_row["bot_status"].casefold()
        )
        left = (pair[0], pair[1])
        right = (pair[2], pair[3])
        review_rows.append({
            "repository": source_row["repository"],
            "git_author_key": source_row["git_author_key"],
            "author_names": source_row["author_names"],
            "author_emails": source_row["author_emails"],
            "candidate_repository": source_row["candidate_repository"],
            "candidate_git_author_key": source_row["candidate_git_author_key"],
            "candidate_names": source_row["candidate_names"],
            "candidate_emails": source_row["candidate_emails"],
            "candidate_evidence": ";".join(sorted(reasons)),
            "email_name_conflict": str(is_exact_email and not is_exact_name).lower(),
            "multiple_candidate_links": str(
                len(degree[left]) > 1 or len(degree[right]) > 1
            ).lower(),
            "possible_bot_in_pair": str(has_bot_flag).lower(),
            "manual_review_status": "unresolved_manual_review_required",
            "review_decision": "",
            "reviewer": "",
            "reviewed_at_utc": "",
            "evidence_notes": "",
        })
    return review_rows


def prepare_cohort_rows(
    roster: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    clean_jdt_matches: list[dict[str, str]],
) -> list[dict[str, str]]:
    degree: dict[tuple[str, str], int] = defaultdict(int)
    for row in review_rows:
        degree[(row["repository"], row["git_author_key"])] += 1
        degree[(row["candidate_repository"], row["candidate_git_author_key"])] += 1

    clean_emails = {
        row["matched_email"].strip().casefold()
        for row in clean_jdt_matches
        if row.get("matched_email", "").strip()
    }

    output: list[dict[str, str]] = []
    for row in roster:
        repository = row["repository"]
        key = row["git_author_key"]
        name_and_email = f"{row['author_names']} {row['author_emails']}"
        emails = {
            email.strip().casefold()
            for email in row["author_emails"].split(";")
            if email.strip()
        }
        bot_flagged = "possible_bot" in row["bot_status"].casefold()
        service_candidate = bool(SERVICE_MARKERS.search(name_and_email))
        tags = []
        if bot_flagged:
            tags.append("possible_bot_needs_review")
        if service_candidate:
            tags.append("possible_service_account_needs_review")
        if not emails:
            tags.append("missing_email_ambiguous")
        if degree[(repository, key)]:
            tags.append("cross_repository_candidate_link")
        else:
            tags.append("no_cross_repository_candidate_link")
        if repository == "eclipse.jdt.core" and emails & clean_emails:
            tags.append("jdt_clean_exact_email_mapping_evidence")
        elif repository == "eclipse.jdt.core":
            tags.append("no_jdt_clean_exact_email_mapping_evidence")
        else:
            tags.append("bugzilla_identity_link_unavailable_for_component")
        tags.append("git_identity_not_automatically_verified")
        output.append({
            "repository": repository,
            "git_author_key": key,
            "commit_count": row["commit_count"],
            "changed_file_count": row["changed_file_count"],
            "bot_status": row["bot_status"],
            "identity_status": row["identity_status"],
            "review_cohorts": ";".join(tags),
            "candidate_link_count": str(degree[(repository, key)]),
            "review_status": "manual_review_required",
        })
    return output


def write_csv(
    path: Path,
    fields: tuple[str, ...],
    rows: list[dict[str, str]],
    *,
    exclusive: bool = False,
) -> None:
    mode = "x" if exclusive else "w"
    with path.open(mode, encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_summary(
    path: Path,
    candidates: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    cohort_rows: list[dict[str, str]],
) -> None:
    exact_email = sum(
        "exact_email_candidate" in row["candidate_evidence"]
        for row in review_rows
    )
    exact_name = sum(
        "exact_normalized_name_candidate" in row["candidate_evidence"]
        for row in review_rows
    )
    overlap = sum(
        "exact_email_candidate" in row["candidate_evidence"]
        and "exact_normalized_name_candidate" in row["candidate_evidence"]
        for row in review_rows
    )
    email_name_conflicts = sum(
        row["email_name_conflict"] == "true" for row in review_rows
    )
    multi_link = sum(
        row["multiple_candidate_links"] == "true" for row in review_rows
    )
    bots = sum(
        "possible_bot_needs_review" in row["review_cohorts"]
        for row in cohort_rows
    )
    service = sum(
        "possible_service_account_needs_review" in row["review_cohorts"]
        for row in cohort_rows
    )
    missing_email = sum(
        "missing_email_ambiguous" in row["review_cohorts"]
        for row in cohort_rows
    )
    no_candidate = sum(
        "no_cross_repository_candidate_link" in row["review_cohorts"]
        for row in cohort_rows
    )
    jdt_clean_match = sum(
        "jdt_clean_exact_email_mapping_evidence" in row["review_cohorts"]
        for row in cohort_rows
    )
    content = [
        "# Eclipse Git Identity Review Preparation",
        "",
        "This report describes candidate evidence only. No candidate pair is",
        "confirmed, no identities are merged, and Git authors are not treated",
        "as Bugzilla developers. Exact emails and normalized names are",
        "personal identity evidence; keep the accompanying CSV access",
        "restricted to the project team and do not publish raw emails.",
        "",
        "## Candidate-pair inventory",
        "",
        f"- Input candidate rows: {len(candidates)} (candidate reasons may repeat a pair).",
        f"- Unique cross-repository pairs in manual review file: {len(review_rows)}.",
        f"- Pairs with exact-email evidence: {exact_email}.",
        f"- Pairs with exact-normalized-name evidence: {exact_name}.",
        f"- Pairs with both kinds of evidence: {overlap}.",
        f"- Exact-email pairs without a normalized-name match (conflict requiring review): {email_name_conflicts}.",
        f"- Pairs where either identity has multiple candidate links: {multi_link}.",
        f"- All {len(review_rows)} unique pairs remain unresolved and require manual review.",
        "",
        "## Identity cohorts",
        "",
        f"- Repository-scoped contributor rows: {len(cohort_rows)}.",
        f"- Possible bots by the existing heuristic: {bots}; not verified bots.",
        f"- Possible service/automation accounts by name/email marker: {service}; false positives are possible.",
        f"- Missing-email identities: {missing_email}; the extraction keys these per commit.",
        f"- Identities without a cross-repository candidate link: {no_candidate}; this does not imply a new person or unmatched Bugzilla identity.",
        f"- JDT Git keys with exact-email evidence in the existing clean JDT mapping: {jdt_clean_match}; this remains JDT-only evidence and is not extended across repositories.",
        "",
        "## Review guidance",
        "",
        "- `cross_repository_manual_review.csv` keeps email and names from the",
        "  candidate source for authorized human review. Review decisions are",
        "  blank initially; record evidence, reviewer, and UTC date before",
        "  deciding whether identities are the same or distinct.",
        "- `exact_email_candidates.csv` and `normalized_name_candidates.csv`",
        "  provide separate review queues. A pair may appear in both when both",
        "  evidence types are present.",
        "- `email_name_conflict=true` identifies same-email candidates without",
        "  matching normalized names. This may indicate aliases, shared/service",
        "  accounts, or a genuine conflict; it is not an automatic rejection.",
        "- `multiple_candidate_links=true` marks a pair when either author",
        "  participates in more than one cross-repository candidate pair.",
        "- `contributor_identity_cohorts.csv` separates bot, service-account,",
        "  missing-email, candidate-linked, no-candidate, JDT exact-email,",
        "  JDT-without-clean-match, and non-JDT-without-Bugzilla-link cohorts.",
        "  Heuristics remain unverified.",
        "- Do not use any output as an assignment-label table. Do not combine",
        "  author keys across repositories without reviewed identity evidence.",
        "",
        "The reviewed mapping, if one is later approved, must be a separate",
        "versioned artifact with explicit evidence and provenance.",
        "",
    ]
    path.write_text("\n".join(content), encoding="utf-8")


def add_review_queues() -> None:
    review_rows = _read_csv(OUTPUT_DIR / "cross_repository_manual_review.csv")
    roster = _read_csv(SOURCE_DIR / "eclipse_git_developer_roster.csv")
    candidates = _read_csv(SOURCE_DIR / "eclipse_git_identity_candidates.csv")
    clean_matches = _read_csv(
        ROOT / "dataset/processed/cold_start/git_bugzilla_exact_email_matches_clean.csv"
    )
    targets = (
        OUTPUT_DIR / "exact_email_candidates.csv",
        OUTPUT_DIR / "normalized_name_candidates.csv",
        OUTPUT_DIR / "contributor_identity_cohorts_classified.csv",
        OUTPUT_DIR / "identity_review_queue_addendum.md",
    )
    existing = [str(path) for path in targets if path.exists()]
    if existing:
        raise FileExistsError(
            "Refusing to overwrite review addendum output(s): "
            + ", ".join(existing)
        )

    email_rows = [
        row for row in review_rows
        if "exact_email_candidate" in row["candidate_evidence"]
    ]
    name_rows = [
        row for row in review_rows
        if "exact_normalized_name_candidate" in row["candidate_evidence"]
    ]
    cohort_rows = prepare_cohort_rows(roster, review_rows, clean_matches)
    write_csv(targets[0], REVIEW_FIELDS, email_rows, exclusive=True)
    write_csv(targets[1], REVIEW_FIELDS, name_rows, exclusive=True)
    write_csv(targets[2], COHORT_FIELDS, cohort_rows, exclusive=True)
    overlap = sum(
        "exact_email_candidate" in row["candidate_evidence"]
        and "exact_normalized_name_candidate" in row["candidate_evidence"]
        for row in review_rows
    )
    with targets[3].open("x", encoding="utf-8") as report:
        report.write(
            "\n".join([
                "# Identity Review Queue Addendum",
                "",
                "This addendum separates review queues without changing the original",
                "candidate source or existing review files.",
                "",
                f"- Exact-email candidate pairs: {len(email_rows)}.",
                f"- Exact-normalized-name candidate pairs: {len(name_rows)}.",
                f"- Pairs present in both queues: {overlap}.",
                f"- Classified repository-scoped contributor rows: {len(cohort_rows)}.",
                "- Every candidate remains unresolved; matching is not identity confirmation.",
                "- The classified cohort file retains possible-bot/service-account",
                "  heuristics, missing-email ambiguity, no-link status, and the limited",
                "  existing JDT clean exact-email evidence as separate tags.",
                "",
            ])
        )
    print(f"Added review queues and classified cohort file under {OUTPUT_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--add-review-queues",
        action="store_true",
        help="Add separate exact-email/name queues and cohort classification "
        "beside an existing review output without overwriting it",
    )
    args = parser.parse_args()
    if args.add_review_queues:
        add_review_queues()
        return
    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Review output already exists; refusing to overwrite: {OUTPUT_DIR}"
        )
    candidates = _read_csv(SOURCE_DIR / "eclipse_git_identity_candidates.csv")
    roster = _read_csv(SOURCE_DIR / "eclipse_git_developer_roster.csv")
    clean_matches = _read_csv(
        ROOT / "dataset/processed/cold_start/git_bugzilla_exact_email_matches_clean.csv"
    )
    review_rows = prepare_review_rows(candidates)
    cohort_rows = prepare_cohort_rows(roster, review_rows, clean_matches)

    stage = Path(tempfile.mkdtemp(
        prefix=".identity_review.stage-",
        dir=SOURCE_DIR,
    ))
    try:
        write_csv(stage / "cross_repository_manual_review.csv", REVIEW_FIELDS, review_rows)
        write_csv(
            stage / "exact_email_candidates.csv",
            REVIEW_FIELDS,
            [
                row for row in review_rows
                if "exact_email_candidate" in row["candidate_evidence"]
            ],
        )
        write_csv(
            stage / "normalized_name_candidates.csv",
            REVIEW_FIELDS,
            [
                row for row in review_rows
                if "exact_normalized_name_candidate" in row["candidate_evidence"]
            ],
        )
        write_csv(stage / "contributor_identity_cohorts.csv", COHORT_FIELDS, cohort_rows)
        write_summary(stage / "identity_review_summary.md", candidates, review_rows, cohort_rows)
        if OUTPUT_DIR.exists():
            raise FileExistsError(
                f"Review output appeared during generation; refusing to overwrite: {OUTPUT_DIR}"
            )
        stage.replace(OUTPUT_DIR)
    except BaseException:
        print(f"Review staging output retained at: {stage}", file=sys.stderr)
        raise
    print(f"Prepared {len(review_rows)} unresolved pairs at {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
