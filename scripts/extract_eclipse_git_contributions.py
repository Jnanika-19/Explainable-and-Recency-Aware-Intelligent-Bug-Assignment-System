import csv
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "dataset/processed/cold_start/eclipse_all_repositories"
SEPARATOR = "\x1f"

REPOSITORIES = (
    ("eclipse.jdt.core", ROOT / "dataset/external/eclipse.jdt.core"),
    ("eclipse.platform", ROOT / "dataset/external/eclipse.platform"),
    ("eclipse.platform.swt", ROOT / "dataset/external/eclipse.platform.swt"),
    ("eclipse.platform.ui", ROOT / "dataset/external/eclipse.platform.ui"),
    ("eclipse.pde", ROOT / "dataset/external/eclipse.pde"),
)

COMMIT_FIELDS = (
    "repository",
    "commit_id",
    "git_author_key",
    "author_name",
    "author_email",
    "author_timestamp",
    "committer_timestamp",
    "subject",
)

FILE_FIELDS = COMMIT_FIELDS + ("file_path", "component")

ROSTER_FIELDS = (
    "repository",
    "git_author_key",
    "author_names",
    "author_emails",
    "first_author_timestamp",
    "latest_author_timestamp",
    "commit_count",
    "changed_file_count",
    "components",
    "bot_status",
    "identity_status",
)

IDENTITY_REVIEW_FIELDS = (
    "repository",
    "git_author_key",
    "author_names",
    "author_emails",
    "commit_count",
    "changed_file_count",
    "bot_status",
    "identity_status",
    "review_status",
)

CANDIDATE_FIELDS = (
    "repository",
    "git_author_key",
    "author_names",
    "author_emails",
    "candidate_repository",
    "candidate_git_author_key",
    "candidate_names",
    "candidate_emails",
    "match_reason",
    "bot_status",
    "review_status",
)

COMMIT_ID_PATTERN = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
BOT_MARKERS = ("[bot]", "bot@", "dependabot", "renovate", "github-actions")


def run_git(repository_path, arguments, *, capture=True, check=True):
    environment = os.environ.copy()
    environment["GIT_NO_LAZY_FETCH"] = "1"
    command = ["git", "-C", str(repository_path), *arguments]
    return subprocess.run(
        command,
        check=check,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
        encoding="utf-8",
        errors="strict",
        env=environment,
    )


def author_key(repository_name, email, author_name, commit_id):
    identity = email.strip().lower() or f"no-email:{commit_id}"
    value = f"{repository_name}\0{identity}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()[:20]


def parse_timestamp(value, commit_id, field_name):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(
            f"Invalid {field_name} for commit {commit_id}: {value!r}"
        ) from error
    if parsed.tzinfo is None:
        raise ValueError(
            f"Timezone missing in {field_name} for commit {commit_id}: {value!r}"
        )
    return parsed.astimezone(timezone.utc)


def component_for_path(file_path):
    return file_path.split("/", 1)[0] if "/" in file_path else "__root__"


def bot_status(name, email):
    identity = f"{name} {email}".casefold()
    return "possible_bot_needs_review" if any(
        marker in identity for marker in BOT_MARKERS
    ) else "not_flagged_unverified"


def identity_status(email):
    return "ambiguous_missing_email" if not email.strip() else "unreviewed_git_author"


def prepare_output_paths():
    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Output directory already exists; refusing to overwrite: {OUTPUT_DIR}"
        )
    OUTPUT_DIR.parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(
        prefix=".eclipse_all_repositories.stage-",
        dir=OUTPUT_DIR.parent,
    ))


def extract_repository(repository_name, repository_path, commits_writer, files_writer):
    if not (repository_path / ".git").exists():
        raise FileNotFoundError(
            f"Git metadata not found for {repository_name}: {repository_path}"
        )

    expected_count = int(run_git(repository_path, [
        "rev-list", "--all", "--count",
    ]).stdout.strip())

    command = [
        "git", "-C", str(repository_path),
        "-c", "core.quotePath=true",
        "log",
        "--all",
        "--root",
        "--no-renames",
        "--diff-merges=first-parent",
        "--encoding=UTF-8",
        f"--format=%H{SEPARATOR}%an{SEPARATOR}%ae{SEPARATOR}%aI{SEPARATOR}%cI{SEPARATOR}%s",
        "--name-only",
    ]
    environment = os.environ.copy()
    environment["GIT_NO_LAZY_FETCH"] = "1"
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=None,
        text=True,
        encoding="utf-8",
        errors="strict",
        env=environment,
    )

    authors = {}
    commit_count = 0
    file_count = 0
    current = None

    try:
        for raw_line in process.stdout:
            line = raw_line.rstrip("\r\n")
            if not line:
                continue

            if SEPARATOR in line:
                parts = line.split(SEPARATOR, 5)
                if (
                    len(parts) != 6
                    or not COMMIT_ID_PATTERN.fullmatch(parts[0])
                ):
                    raise ValueError(
                        f"Malformed commit record in {repository_name}: {line!r}"
                    )

                commit_id, name, email, author_time, committer_time, subject = parts
                author_date = parse_timestamp(author_time, commit_id, "author time")
                parse_timestamp(committer_time, commit_id, "committer time")
                key = author_key(repository_name, email, name, commit_id)

                current = {
                    "repository": repository_name,
                    "commit_id": commit_id,
                    "git_author_key": key,
                    "author_name": name,
                    "author_email": email,
                    "author_timestamp": author_time,
                    "committer_timestamp": committer_time,
                    "subject": subject,
                }
                commits_writer.writerow(current)
                commit_count += 1

                author_record = authors.setdefault(
                    key,
                    {
                        "names": set(),
                        "emails": set(),
                        "components": set(),
                        "first": author_date,
                        "latest": author_date,
                        "commits": 0,
                        "files": 0,
                        "bot_status": bot_status(name, email),
                        "identity_status": identity_status(email),
                    },
                )
                author_record["names"].add(name)
                if email.strip():
                    author_record["emails"].add(email)
                author_record["first"] = min(author_record["first"], author_date)
                author_record["latest"] = max(author_record["latest"], author_date)
                author_record["commits"] += 1
                continue

            if current is None:
                raise ValueError(
                    f"File path without a preceding commit in {repository_name}: {line!r}"
                )

            file_path = line
            component = component_for_path(file_path)
            files_writer.writerow({
                **current,
                "file_path": file_path,
                "component": component,
            })
            author_record = authors[current["git_author_key"]]
            author_record["files"] += 1
            author_record["components"].add(component)
            file_count += 1

        process.stdout.close()
        return_code = process.wait()
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, command)
    except BaseException:
        if process.poll() is None:
            process.terminate()
            process.wait()
        raise

    if commit_count != expected_count:
        raise RuntimeError(
            f"{repository_name}: git log emitted {commit_count} commits, "
            f"but rev-list reports {expected_count}"
        )

    return {
        "repository": repository_name,
        "commit_count": commit_count,
        "file_count": file_count,
        "developer_count": len(authors),
        "authors": authors,
    }


def write_rosters(repository_results, roster_writer, identity_review_writer):
    for result in repository_results:
        for key, author in sorted(result["authors"].items()):
            names = "; ".join(sorted(author["names"]))
            emails = "; ".join(sorted(author["emails"]))
            first = author["first"].isoformat()
            latest = author["latest"].isoformat()
            components = "; ".join(sorted(author["components"]))

            roster_writer.writerow({
                "repository": result["repository"],
                "git_author_key": key,
                "author_names": names,
                "author_emails": emails,
                "first_author_timestamp": first,
                "latest_author_timestamp": latest,
                "commit_count": author["commits"],
                "changed_file_count": author["files"],
                "components": components,
                "bot_status": author["bot_status"],
                "identity_status": author["identity_status"],
            })
            identity_review_writer.writerow({
                "repository": result["repository"],
                "git_author_key": key,
                "author_names": names,
                "author_emails": emails,
                "commit_count": author["commits"],
                "changed_file_count": author["files"],
                "bot_status": author["bot_status"],
                "identity_status": author["identity_status"],
                "review_status": "manual_review_required",
            })


def normalized_name(value):
    decomposed = unicodedata.normalize("NFKD", value).casefold()
    return "".join(character for character in decomposed if character.isalnum())


def write_identity_candidates(repository_results, writer):
    authors = []
    for result in repository_results:
        for key, author in result["authors"].items():
            authors.append({
                "repository": result["repository"],
                "git_author_key": key,
                "author_names": "; ".join(sorted(author["names"])),
                "author_emails": "; ".join(sorted(author["emails"])),
                "names": {
                    normalized_name(value)
                    for value in author["names"]
                    if normalized_name(value)
                },
                "emails": {
                    value.strip().casefold()
                    for value in author["emails"]
                    if value.strip()
                },
                "bot_status": author["bot_status"],
            })

    email_groups = defaultdict(list)
    name_groups = defaultdict(list)
    for index, author in enumerate(authors):
        for email in author["emails"]:
            email_groups[email].append(index)
        for name in author["names"]:
            name_groups[name].append(index)

    candidates = {}
    for reason, groups in (
        ("exact_email_candidate", email_groups),
        ("exact_normalized_name_candidate", name_groups),
    ):
        for group in groups.values():
            for left_position in range(len(group)):
                for right_position in range(left_position + 1, len(group)):
                    left = authors[group[left_position]]
                    right = authors[group[right_position]]
                    if left["repository"] == right["repository"]:
                        continue
                    pair = sorted(
                        (left, right),
                        key=lambda author: (
                            author["repository"], author["git_author_key"]
                        ),
                    )
                    candidate_key = (
                        pair[0]["repository"],
                        pair[0]["git_author_key"],
                        pair[1]["repository"],
                        pair[1]["git_author_key"],
                        reason,
                    )
                    candidates[candidate_key] = (
                        pair[0], pair[1], reason
                    )

    for candidate_key in sorted(candidates):
        left, right, reason = candidates[candidate_key]
        bot_marked = (
            left["bot_status"] == "possible_bot_needs_review"
            or right["bot_status"] == "possible_bot_needs_review"
        )
        writer.writerow({
            "repository": left["repository"],
            "git_author_key": left["git_author_key"],
            "author_names": left["author_names"],
            "author_emails": left["author_emails"],
            "candidate_repository": right["repository"],
            "candidate_git_author_key": right["git_author_key"],
            "candidate_names": right["author_names"],
            "candidate_emails": right["author_emails"],
            "match_reason": reason,
            "bot_status": (
                "possible_bot_in_pair_needs_review"
                if bot_marked else "not_flagged_unverified"
            ),
            "review_status": "manual_review_required",
        })
    return len(candidates)


def validate_csv(path, expected_fields, *, required_nonempty):
    rows = 0
    missing = {field: 0 for field in required_nonempty}
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != list(expected_fields):
            raise ValueError(f"Unexpected columns in {path}: {reader.fieldnames}")
        for row in reader:
            rows += 1
            for field in required_nonempty:
                if not row[field].strip():
                    missing[field] += 1
    return rows, missing


def count_blank_values(path, field):
    count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            if not row[field].strip():
                count += 1
    return count


def validate_repository(repository_name, repository_path):
    commit_count = int(run_git(repository_path, [
        "rev-list", "--all", "--count",
    ]).stdout.strip())
    refs = run_git(repository_path, [
        "for-each-ref", "--format=%(refname)|%(symref)", "refs/remotes",
    ]).stdout.splitlines()
    branches = [
        item.split("|", 1)[0]
        for item in refs
        if item.startswith("refs/remotes/")
        and not item.split("|", 1)[1]
    ]
    tags = run_git(repository_path, [
        "for-each-ref", "--format=%(refname)", "refs/tags",
    ]).stdout.splitlines()
    remotes = run_git(repository_path, ["remote", "--verbose"]).stdout.splitlines()
    shallow = run_git(repository_path, [
        "rev-parse", "--is-shallow-repository",
    ]).stdout.strip()
    promisor = run_git(repository_path, [
        "config", "--get", "remote.origin.promisor",
    ]).stdout.strip()
    filter_spec = run_git(repository_path, [
        "config", "--get", "remote.origin.partialclonefilter",
    ]).stdout.strip()
    object_storage = run_git(repository_path, [
        "count-objects", "-vH",
    ]).stdout.splitlines()
    fsck = run_git(repository_path, [
        "fsck", "--full", "--connectivity-only", "--no-reflogs",
    ])
    fsck_output = fsck.stdout + fsck.stderr
    fsck_issues = [
        line for line in fsck_output.splitlines()
        if re.search(r"^(?:error:|fatal:|missing )", line)
    ]

    if shallow != "false":
        raise RuntimeError(f"{repository_name} is shallow: {shallow}")
    if promisor.lower() != "true" or filter_spec != "blob:none":
        raise RuntimeError(
            f"{repository_name} has unexpected partial-clone configuration: "
            f"promisor={promisor!r}, filter={filter_spec!r}"
        )
    if fsck.returncode != 0 or fsck_issues:
        raise RuntimeError(
            f"{repository_name} fsck failed (exit {fsck.returncode}): "
            f"{fsck_issues[:10]}"
        )

    remote_head_result = run_git(
        repository_path,
        ["symbolic-ref", "-q", "refs/remotes/origin/HEAD"],
        check=False,
    )
    return {
        "repository": repository_name,
        "commit_count": commit_count,
        "branch_count": len(branches),
        "tag_count": len(tags),
        "remote_head": remote_head_result.stdout.strip(),
        "remote_urls": remotes,
        "shallow": shallow,
        "promisor": promisor,
        "filter": filter_spec,
        "object_storage": object_storage,
        "fsck_exit": fsck.returncode,
        "fsck_issue_count": len(fsck_issues),
        "fsck_output_lines": len(fsck_output.splitlines()),
    }


def write_report(
    stage_dir, repository_results, repository_validations, output_counts, validation
):
    total_commits = sum(item["commit_count"] for item in repository_results)
    total_files = sum(item["file_count"] for item in repository_results)
    total_developers = sum(item["developer_count"] for item in repository_results)

    lines = [
        "# Eclipse Git Contribution Extraction Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Scope and method",
        "",
        "This extraction reads all commits reachable from local refs in each of",
        "the five listed repositories. It does not fetch, check out, or modify",
        "repositories. `GIT_NO_LAZY_FETCH=1` is set for Git subprocesses.",
        "Commits are emitted once per repository. Changed paths for merge",
        "commits use a first-parent diff; root commits are included; renames are",
        "not followed, so rename paths are represented as delete/add evidence.",
        "",
        "Git author keys are scoped to repository and are not Bugzilla identities.",
        "All contributor identity rows require manual review; bot indicators are",
        "heuristics and do not remove or suppress any records.",
        "",
        "## Repository extraction counts",
        "",
        "| Repository | Git commits reachable from local refs | Commit rows | Changed-file rows | Git author keys |",
        "|---|---:|---:|---:|---:|",
    ]
    for item in repository_results:
        lines.append(
            f"| `{item['repository']}` | {item['commit_count']} | "
            f"{item['commit_count']} | {item['file_count']} | "
            f"{item['developer_count']} |"
        )
    lines.extend([
        f"| **Total (repository-scoped; not identity-deduplicated)** | "
        f"**{total_commits}** | **{total_commits}** | **{total_files}** | "
        f"**{total_developers}** |",
        "",
        "## Repository validation",
        "",
        "| Repository | Remote URL(s) | Remote branches | Tags | Shallow | Filter | Object storage | `fsck` |",
        "|---|---|---:|---:|---|---|---|---|",
    ])
    for item in repository_validations:
        remote_urls = "; ".join(
            line.split("\t", 1)[1].split(" ", 1)[0]
            for line in item["remote_urls"]
            if "\t" in line
        )
        storage = "; ".join(
            value for value in item["object_storage"]
            if value.startswith(("in-pack:", "packs:", "size-pack:", "garbage:"))
        )
        lines.append(
            f"| `{item['repository']}` | `{remote_urls}` | "
            f"{item['branch_count']} | {item['tag_count']} | "
            f"`{item['shallow']}` | `{item['filter']}` | "
            f"{storage} | exit {item['fsck_exit']}, "
            f"{item['fsck_issue_count']} errors/missing |"
        )
    lines.extend([
        "",
        "All `fsck` checks run with `GIT_NO_LAZY_FETCH=1`; intentional",
        "promisor-blob omissions are not fetched. Dangling objects are reported",
        "by Git but are not removed.",
        "",
        "## Output validation",
        "",
        "| Output | Data rows | Validation |",
        "|---|---:|---|",
    ])
    for filename, rows in output_counts.items():
        lines.append(f"| `{filename}` | {rows} | header and required fields checked |")
    lines.extend([
        "",
        f"Commit CSV unique `(repository, commit_id)` keys: {validation['unique_commit_keys']}.",
        f"File rows with no corresponding commit row: {validation['orphan_file_rows']}.",
        f"Commit author keys missing from roster: {validation['unrostered_commit_author_keys']}.",
        f"Invalid identity-candidate references: {validation['invalid_candidate_references']}.",
        f"Required commit/file/roster fields missing: {validation['missing_required_fields']}.",
        "",
        "Optional blank metadata values are preserved rather than dropped:",
        *[
            f"- `{field}`: {count}"
            for field, count in validation["optional_blank_values"].items()
            if count
        ],
        "",
        "## Identity and interpretation limits",
        "",
        "- Exact or similar names/emails are not used to merge authors across",
        "  repositories.",
        "- Existing JDT Bugzilla identity work remains in its original files and",
        "  is not copied into a cross-project assignment map.",
        "- Possible bot accounts are flagged for review only; ambiguous and",
        "  unmatched authors remain represented.",
        "- Git contributions support code expertise, recency, and an",
        "  unlinked-contributor roster. They do not prove Bugzilla assignment",
        "  eligibility, issue expertise, workload, or a bug-fix label.",
        "- The inventory covers local refs in the collected clones, not hidden",
        "  or unreachable server refs. Blob contents remain omitted in the",
        "  partial clones.",
        "",
        "Validation completed before publishing these files. If the process",
        "fails before final publication, its staging directory is retained for",
        "inspection and no existing output is overwritten.",
        "",
    ])
    (stage_dir / "eclipse_git_extraction_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main():
    stage_dir = prepare_output_paths()
    repository_results = []
    try:
        with (
            (stage_dir / "eclipse_git_commits.csv").open(
                "w", encoding="utf-8-sig", newline=""
            ) as commits_file,
            (stage_dir / "eclipse_git_commit_files.csv").open(
                "w", encoding="utf-8-sig", newline=""
            ) as files_file,
            (stage_dir / "eclipse_git_developer_roster.csv").open(
                "w", encoding="utf-8-sig", newline=""
            ) as roster_file,
            (stage_dir / "eclipse_git_identity_review.csv").open(
                "w", encoding="utf-8-sig", newline=""
            ) as identity_file,
            (stage_dir / "eclipse_git_identity_candidates.csv").open(
                "w", encoding="utf-8-sig", newline=""
            ) as candidates_file,
        ):
            commits_writer = csv.DictWriter(
                commits_file, fieldnames=COMMIT_FIELDS
            )
            files_writer = csv.DictWriter(
                files_file, fieldnames=FILE_FIELDS
            )
            roster_writer = csv.DictWriter(
                roster_file, fieldnames=ROSTER_FIELDS
            )
            identity_review_writer = csv.DictWriter(
                identity_file, fieldnames=IDENTITY_REVIEW_FIELDS
            )
            candidates_writer = csv.DictWriter(
                candidates_file, fieldnames=CANDIDATE_FIELDS
            )
            commits_writer.writeheader()
            files_writer.writeheader()
            roster_writer.writeheader()
            identity_review_writer.writeheader()
            candidates_writer.writeheader()

            for repository_name, repository_path in REPOSITORIES:
                print(f"Extracting {repository_name}...")
                repository_results.append(extract_repository(
                    repository_name,
                    repository_path,
                    commits_writer,
                    files_writer,
                ))

            write_rosters(
                repository_results, roster_writer, identity_review_writer
            )
            candidate_count = write_identity_candidates(
                repository_results, candidates_writer
            )

        repository_validations = []
        for repository_name, repository_path in REPOSITORIES:
            print(f"Validating {repository_name}...")
            repository_validation = validate_repository(
                repository_name, repository_path
            )
            extracted = next(
                item for item in repository_results
                if item["repository"] == repository_name
            )
            if repository_validation["commit_count"] != extracted["commit_count"]:
                raise ValueError(
                    f"{repository_name}: extracted commit count "
                    f"{extracted['commit_count']} differs from validation count "
                    f"{repository_validation['commit_count']}"
                )
            repository_validations.append(repository_validation)

        commit_rows, commit_missing = validate_csv(
            stage_dir / "eclipse_git_commits.csv",
            COMMIT_FIELDS,
            required_nonempty=(
                "repository", "commit_id", "git_author_key",
                "author_timestamp", "committer_timestamp",
            ),
        )
        file_rows, file_missing = validate_csv(
            stage_dir / "eclipse_git_commit_files.csv",
            FILE_FIELDS,
            required_nonempty=(
                "repository", "commit_id", "git_author_key",
                "file_path", "component",
            ),
        )
        roster_rows, roster_missing = validate_csv(
            stage_dir / "eclipse_git_developer_roster.csv",
            ROSTER_FIELDS,
            required_nonempty=("repository", "git_author_key", "commit_count"),
        )
        identity_rows, identity_missing = validate_csv(
            stage_dir / "eclipse_git_identity_review.csv",
            IDENTITY_REVIEW_FIELDS,
            required_nonempty=("repository", "git_author_key", "review_status"),
        )
        candidate_rows, candidate_missing = validate_csv(
            stage_dir / "eclipse_git_identity_candidates.csv",
            CANDIDATE_FIELDS,
            required_nonempty=(
                "repository", "git_author_key", "candidate_repository",
                "candidate_git_author_key", "match_reason", "review_status",
            ),
        )
        if candidate_rows != candidate_count:
            raise ValueError(
                f"Identity candidate CSV has {candidate_rows} rows; "
                f"expected {candidate_count}"
            )

        commit_keys = set()
        commit_author_keys = set()
        with (stage_dir / "eclipse_git_commits.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as source:
            for row in csv.DictReader(source):
                key = (row["repository"], row["commit_id"])
                if key in commit_keys:
                    raise ValueError(f"Duplicate repository/commit key: {key}")
                commit_keys.add(key)
                commit_author_keys.add(
                    (row["repository"], row["git_author_key"])
                )

        orphan_file_rows = 0
        with (stage_dir / "eclipse_git_commit_files.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as source:
            for row in csv.DictReader(source):
                if (row["repository"], row["commit_id"]) not in commit_keys:
                    orphan_file_rows += 1
        if orphan_file_rows:
            raise ValueError(f"Found {orphan_file_rows} file rows without commits")

        missing_required = sum(
            sum(values.values())
            for values in (
                commit_missing, file_missing, roster_missing, identity_missing,
                candidate_missing,
            )
        )
        if missing_required:
            raise ValueError(
                f"Found {missing_required} missing required CSV field values"
            )

        expected_commits = sum(item["commit_count"] for item in repository_results)
        expected_files = sum(item["file_count"] for item in repository_results)
        expected_developers = sum(
            item["developer_count"] for item in repository_results
        )
        if commit_rows != expected_commits:
            raise ValueError(
                f"Commit CSV has {commit_rows} rows; expected {expected_commits}"
            )
        if file_rows != expected_files:
            raise ValueError(
                f"Commit-file CSV has {file_rows} rows; expected {expected_files}"
            )
        if roster_rows != expected_developers:
            raise ValueError(
                f"Roster has {roster_rows} rows; expected {expected_developers}"
            )
        if roster_rows != identity_rows:
            raise ValueError(
                "Developer roster and identity-review row counts differ"
            )

        roster_keys = set()
        with (stage_dir / "eclipse_git_developer_roster.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as source:
            for row in csv.DictReader(source):
                key = (row["repository"], row["git_author_key"])
                if key in roster_keys:
                    raise ValueError(f"Duplicate repository/author key: {key}")
                roster_keys.add(key)
        unrostered_commit_author_keys = len(commit_author_keys - roster_keys)
        if unrostered_commit_author_keys:
            raise ValueError(
                f"Found {unrostered_commit_author_keys} commit author keys "
                "missing from the developer roster"
            )

        invalid_candidate_references = 0
        with (stage_dir / "eclipse_git_identity_candidates.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as source:
            for row in csv.DictReader(source):
                source_key = (row["repository"], row["git_author_key"])
                candidate_key = (
                    row["candidate_repository"],
                    row["candidate_git_author_key"],
                )
                if (
                    source_key not in roster_keys
                    or candidate_key not in roster_keys
                    or row["repository"] == row["candidate_repository"]
                ):
                    invalid_candidate_references += 1
        if invalid_candidate_references:
            raise ValueError(
                f"Found {invalid_candidate_references} invalid identity "
                "candidate references"
            )

        output_counts = {
            "eclipse_git_commits.csv": commit_rows,
            "eclipse_git_commit_files.csv": file_rows,
            "eclipse_git_developer_roster.csv": roster_rows,
            "eclipse_git_identity_review.csv": identity_rows,
            "eclipse_git_identity_candidates.csv": candidate_rows,
        }
        validation = {
            "unique_commit_keys": len(commit_keys),
            "orphan_file_rows": orphan_file_rows,
            "unrostered_commit_author_keys": unrostered_commit_author_keys,
            "invalid_candidate_references": invalid_candidate_references,
            "missing_required_fields": missing_required,
            "optional_blank_values": {
                "commit_author_email": count_blank_values(
                    stage_dir / "eclipse_git_commits.csv", "author_email"
                ),
                "commit_subject": count_blank_values(
                    stage_dir / "eclipse_git_commits.csv", "subject"
                ),
                "file_author_email": count_blank_values(
                    stage_dir / "eclipse_git_commit_files.csv", "author_email"
                ),
                "file_subject": count_blank_values(
                    stage_dir / "eclipse_git_commit_files.csv", "subject"
                ),
                "roster_author_emails": count_blank_values(
                    stage_dir / "eclipse_git_developer_roster.csv",
                    "author_emails",
                ),
                "roster_components": count_blank_values(
                    stage_dir / "eclipse_git_developer_roster.csv",
                    "components",
                ),
            },
        }
        write_report(
            stage_dir,
            repository_results,
            repository_validations,
            output_counts,
            validation,
        )

        if OUTPUT_DIR.exists():
            raise FileExistsError(
                f"Output directory appeared during extraction; refusing to "
                f"overwrite: {OUTPUT_DIR}"
            )
        stage_dir.replace(OUTPUT_DIR)
    except BaseException:
        print(
            f"Extraction stopped. Staging files, if any, were retained at: "
            f"{stage_dir}",
            file=sys.stderr,
        )
        raise

    print(f"Extraction and validation completed: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
