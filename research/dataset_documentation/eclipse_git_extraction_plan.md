# Combined Eclipse Git Extraction Plan

Prepared: 2026-11-11

## Execution status

The script was run once after explicit user approval. It completed extraction
and validation for all five local repositories. The original JDT contribution
files and all repository histories were preserved. Outputs and detailed
results are in
[`eclipse_all_repositories`](../../dataset/processed/cold_start/eclipse_all_repositories/)
and its `eclipse_git_extraction_report.md`. No bug or comment collection was
performed.

## Resource preflight

The five local repositories contain 183,742 commits reachable from their
current local refs (32,484 JDT, 46,304 Platform, 35,391 SWT, 48,171 UI, and
21,392 PDE). A bounded, read-only sample of the latest 500 commits in each
repository, using `--diff-merges=first-parent`, counted 2,500 commits and
17,196 changed-path rows in 0.86 seconds total. This sample did not create
files and is not a full-history runtime benchmark.

| Resource | Planning estimate | Basis and uncertainty |
|---|---|---|
| Output disk | Budget at least 1 GiB free in addition to the existing repositories. A rough scenario is 0.3–0.6 GiB for commit, per-file, and roster/candidate CSVs. | JDT's existing commit-file CSV averages about 226 bytes/row and has 279,322 rows. Applying the five-repository sample's 6.88 changed paths/commit would imply about 1.26 million file rows; actual older history, long paths, subjects, and merge differences can materially change the result. The estimate must be replaced with actual output sizes after the approved run. Staging and final output share the same volume; the script stages one copy then renames it. |
| Processing time | Likely minutes, but not guaranteed; budget up to tens of minutes for extraction plus connectivity checks. | The 2,500-commit sample took 0.86 seconds, but full refs, CSV writes, older tree objects, and five `fsck` passes add overhead. The sample is too small to promise a completion time. |
| Memory | Designed for streaming commit/path rows; author aggregation is retained in memory and scales with distinct repo-scoped Git author keys, not commit/file history. Plan for several hundred MiB and keep 1 GiB headroom. | No full author-cardinality measurement was performed. Worst case is bounded by the 183,742 commits, but long/varied aliases increase memory. No full extraction benchmark has run. |

The repositories are partial clones with blobs omitted. The script sets
`GIT_NO_LAZY_FETCH=1`, uses Git log/tree metadata only, and fails rather than
fetching omitted blobs. If a necessary commit/tree object is missing, extraction
will stop and leave the staging directory for inspection.

### Actual run

The five generated CSVs and report total 750,478,237 bytes (about 715.5 MiB),
slightly above the rough 0.3–0.6 GiB output scenario; the planned 1 GiB free
space budget remains an appropriate minimum. Exact row counts and repository
validation are in the extraction report. No full-run duration or peak-memory
measurement was captured, so the planning estimates for those resources
remain unverified.

## Proposed script behavior

New script: `scripts/extract_eclipse_git_contributions.py`.

- Processes the five repositories independently and writes the repository
  name into every commit, file, roster, and identity-review row.
- Reads all commits reachable from the repositories' local refs once per
  repository. It does not fetch or update refs.
- Includes roots. Merge commits are included once; their changed paths are
  computed against the first parent (`--diff-merges=first-parent`). Rename
  detection is disabled, so rename paths are represented as delete/add
  records. This is a fixed, explicit convention for reproducibility.
- Retains commit ID, author name/email and both timestamps, subject, changed
  path, and top-level path component (`__root__` for root-level files).
- Uses repository-scoped author keys. It does not join same-name/email
  contributors across repositories or call Git authors verified
  Bugzilla-assignment candidates.
- Emits a repository-scoped contributor identity-review roster and separate
  cross-repository exact-email/exact-normalized-name candidate pairs for
  manual review. Candidate matching never merges identities. Authors without
  email are keyed per commit rather than grouped by name.
- Flags possible bots using transparent name/email heuristics; the flag does
  not filter or verify any record.
- Leaves all existing JDT CSVs untouched and refuses if
  `dataset/processed/cold_start/eclipse_all_repositories/` exists.
- Writes to a unique staging directory, validates outputs, and renames the
  directory into place only after success. On failure it retains staging data
  and prints the path; it does not delete or overwrite files.

Outputs on a later approved run:

1. `eclipse_git_commits.csv`
2. `eclipse_git_commit_files.csv`
3. `eclipse_git_developer_roster.csv`
4. `eclipse_git_identity_review.csv`
5. `eclipse_git_identity_candidates.csv`
6. `eclipse_git_extraction_report.md`

The proposed final output directory was absent at planning time. It is ignored
by the existing `dataset/processed/*` rule, so no `.gitignore` change is
proposed.

## Validation planned in the script

Before publishing staged outputs, the script will:

1. Compare each emitted commit row count with `git rev-list --all --count`.
2. Check exact CSV headers and required nonempty identifiers/timestamps.
3. Check uniqueness of `(repository, commit_id)` in the commit CSV.
4. Check every commit-file row references a commit row in the same repository.
5. Check roster/candidate row-count agreement and require every repository to
   have a source path.
6. For each repository, record remote URL(s), remote branches, tags, shallow
   status, partial-clone filter, object storage, and a connectivity check.
7. Run `git fsck --full --connectivity-only --no-reflogs` with
   `GIT_NO_LAZY_FETCH=1`; fail on command errors, missing objects, or
   connectivity errors. Dangling objects alone are retained and reported as
   non-fatal.

Post-run checks completed:

- The generated report and independent audit agree on per-repository commit
  and changed-path counts; all five repositories are represented.
- Required fields, unique `(repository, commit_id)` keys, roster keys,
  commit-file references, and candidate-to-roster references passed.
- Independent optional-blank counts: 5,349 commit author emails, 2 commit
  subjects, and 7 roster component lists are blank. Corresponding file-row
  blanks repeat commit metadata (22,482 email cells, 1,062 subject cells).
- Root commits were included; merge commit paths use the stated first-parent
  rule. Repository-scoped author keys remain separate.
- The combined JDT changed-path count is 312,493 versus 279,322 in the old
  JDT-only CSV. The old script did not specify a merge-diff policy; both
  datasets were preserved and the difference is recorded for provenance.
- Do not use the roster as a verified Bugzilla developer list.
- Keep the candidate identity file separate from the existing JDT verified
  mapping. No cross-project identity union is performed by this script.

## Phase 1 inventory findings

The complete file-level inventory is
[`master_dataset_inventory.md`](./master_dataset_inventory.md). The nine-feature
audit is [`eclipse_nine_feature_readiness.md`](./eclipse_nine_feature_readiness.md).
Important findings:

- Existing JDT processed files and extraction scripts must be preserved.
  `extract_jdt_git_contributions.py` is JDT-only and writes directly over
  existing CSVs if rerun; it is not used by the new pipeline.
- The JDT availability manifest reports identical SHA-256 values for the base,
  inclusive, and strict temporal-feature CSVs. Preserve all variants until the
  provenance discrepancy is resolved.
- `member1_dataset_files/` and its ZIP duplicate top-level JDT outputs.
- All five Git repositories exist locally and are non-shallow. Separate
  collection reports are available for Platform, SWT, UI, and PDE. JDT has no
  standalone collection report; use the availability report for its count and
  partial-clone/checkout caveats.
- Platform/PDE Bugzilla collection remains unavailable; the four bounded
  probes returned shutdown HTML. Their Git histories cannot produce bug labels,
  queue workload, or duplicate Bugzilla relationships.
- No model implementation or evaluation for all nine project features was
  found in the repository README or dataset inventory.

## Remaining feature work

Git histories now support repository-specific contribution and recency
evidence. Platform/PDE recommendation labels and assignment-history data are
still unavailable; all nine-feature model, scoring, temporal evaluation,
calibration, explanation, adaptive-selection, workload, and ranking work
remains separate from this extraction.
