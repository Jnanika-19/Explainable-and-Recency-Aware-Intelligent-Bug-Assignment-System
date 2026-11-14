# Final Read-Only Pre-Commit Audit

**Audit date:** 2026-11-13
**Repository:** `Jnanika-19/Explainable-and-Recency-Aware-Intelligent-Bug-Assignment-System`
**Branch:** `feature/jdt-dataset-collection`
**Scope:** Independent verification of the controlled remediation and all local changed paths. No files were staged, committed, pushed, deleted, restored, or otherwise intentionally modified, except creation of this requested report.

## 1. Executive verdict

**NOT READY TO COMMIT as a public commit at this time.**

The exact A-list below passed the source, test, documentation, and changed-file privacy checks and is the candidate set safe to include **if committed separately from every B-list path**. The mismatch analysis must remain excluded. Before a public commit, resolve the previously documented commit-author/committer identity concern; it is a Git metadata issue, not a changed file, and was not changed or re-evaluated here. The five ignored external clones also have large existing dirty states, so their pre-audit state cannot be certified.

No finding supports claiming that the recommendation system or model evaluation is complete. These are tested reusable utilities, not an integrated or evaluated recommender.

## 2. Git state and synchronization

At the initial audit inventory, before this report was created:

- Branch: `feature/jdt-dataset-collection`
- HEAD: `b1e4d2e3b19d4a362e167a4365803f99385f8b9e`
- Remote tracking branch: `origin/feature/jdt-dataset-collection`
- Remote branch tip: `b1e4d2e3b19d4a362e167a4365803f99385f8b9e`
- Ahead/behind: **0 / 0**; local HEAD and remote tracking tip are synchronized.
- Modified tracked paths: **1** (`README.md`)
- Untracked paths: **65**
- Staged paths: **0**
- Deleted paths: **0**
- Renamed paths: **0**
- Total changed paths: **66**

This report is the only permitted new path. After its creation, the expected
inventory is **67 changed paths**: one modified tracked file and 66 untracked
files, still with no staged, deleted, or renamed paths. No Git state was changed.

The exact complete changed-path inventory is represented by the union of
**SAFE TO COMMIT** and **MUST REMAIN EXCLUDED** below. There are no changed
paths in **NEEDS USER DECISION**.

## 3. Remediation claims independently verified

| Claim | Verification |
|---|---|
| README paths and team responsibilities | README uses `dataset/`, not the former `data/` layout. It distinguishes broad folder ownership from the separate four-member dataset handover matrix. |
| Reassignment severity | A reassignment with `severity=None` retains the bug's prior severity; a supplied severity replaces it. The regression test verifies the retained weighted count. |
| Explanation consistency | `explain_recommendation` rejects non-finite score/contribution values and a contribution sum that does not reconcile to the supplied score. The regression test covers a mismatched total. Per-feature contribution/value arithmetic is also checked. |
| Retrieval query-time provenance | `search` requires a timezone-aware `query_text_available_at` strictly before the fitted cutoff and requires the query ID bound during `fit`. This validates the caller-supplied timestamp; it cannot independently prove that the supplied text is the historical text version. |
| Retrieval self-exclusion | The query bug ID is filtered before TF-IDF fitting. The regression test verifies both that it is absent from fitted documents and that its unique token is absent from the fitted vocabulary. |
| Recency and cutoff | The utility computes `2 ** (-age_days / half_life_days)`, defaults to a 90-day half-life, rejects invalid/nonpositive half-lives and naive timestamps, and requires evidence availability strictly before cutoff. Missing evidence returns `None`. The default is not empirically tuned. |
| Historical report labels | The second audit, pre-push audit, validation-results report, and final handover report identify their 2026-11-11 findings as historical and point to the remediation or distinguish code-test reruns from dataset validation. Other dated dataset reports remain dated evidence and were not re-certified here. |
| VS Code interpreter | `.vscode/settings.json` parses as JSON and selects `${workspaceFolder}/.venv-sbert/Scripts/python.exe`, consistent with the README's Windows instructions. |

No material code correction claimed by `remediation_report.md` was found missing.
One minor documentation qualification: a whitespace scan found six Markdown
hard-break trailing-space lines—three in the remediation report itself and
three in the historical second audit. They are documentation formatting, not
Python/source whitespace. The tracked `git diff --check` passes.

## 4. Tests and Python syntax/import checks

The requested complete suite was run exactly with the project environment:

```powershell
.\.venv-sbert\Scripts\python.exe -B -m unittest discover -s tests\unit -p "test_*.py" -v
```

**PASS — 44 tests, 0 failures, 0 errors.**

All **30 changed Python files** parsed with `.venv-sbert` Python's `ast` module.
All **30** also imported successfully, including tests and the changed scripts
loaded as modules rather than invoked as script entry points. The script import
check found only the scripts' guarded path-setup code at module scope; no
collection, extraction, validation, or dataset-writing entry point was run.
The `-B` flag prevented bytecode-cache writes.

No packages were installed and no dependency files were changed.

## 5. Implementation readiness by feature

| Feature | Finding |
|---|---|
| Point-in-time workload | Replay ignores events at or after cutoff when constructing state; it preserves known severity when a reassignment omits severity. The caller still supplies `history_complete`, and the utility is not a source of complete queues. |
| Explanation arithmetic | Supplied score and contributions must be finite and sum consistently; used-feature values must match their weighted contributions. This is a tested utility contract, not an integrated recommendation explanation. |
| Retrieval | Corpus creation excludes the query ID before fitting and filters by creation and text-availability cutoffs. Query text availability is caller-attested through its timestamp; no historical JDT text snapshots are present for project evaluation. |
| Recency | Strict-cutoff exponential decay utility is tested. Its 90-day half-life is a documented default, not a trained or empirically selected value, and it is not integrated into a recommendation flow. |
| Cold start | Policy utility and synthetic tests distinguish verified history, insufficient evidence, unmatched Git evidence, and manual review. There is no project integration or confirmed-new-developer ground truth. |
| Confidence | Evidence summaries remain explicitly uncalibrated; the held-out isotonic calibrator is a utility. No project calibration set or held-out calibration evaluation exists. |
| Adaptive selection | Fixed/adaptive weighted scoring and missing-signal behavior are utility-tested; no project-data comparison has been performed. |
| Top-K | Stable ranking and metric helpers are synthetic-unit-tested; no project ranking output or held-out metrics exist. |
| Duplicate/related retrieval | Similarity and label separation are utility-tested. No project fit/evaluation is justified without timestamped text, complete labels, and a valid split. |
| Overall system | No orchestrator, complete recommendation application, trained assignment model, or project model evaluation was verified or claimed. |

The new tests exercise the requested regressions and existing utility contracts.
They do not constitute dataset-backed integration or end-to-end tests.

## 6. Dataset integrity and file safety

- The 73-entry handover manifest was read as metadata. All **73 referenced
  paths exist** and all recorded file sizes match current filesystem metadata;
  no missing paths or size mismatches were found.
- This check used file metadata only. The 6,377,569,970-byte raw
  `dataset/raw/JDT.csv` was not opened, parsed, scanned, copied, or hashed.
  Processed dataset contents, row counts, and checksums were not recomputed.
  Thus, the manifest's current path/size agreement is verified, but a full
  byte-for-byte unchanged claim cannot be established from this audit alone.
- No collection, extraction, validation, or dataset-writing command was run.
  No generated dataset file appears among the changed paths. No temporary
  output or duplicate report was introduced; the only new file is this report.
- `dataset/raw/`, `dataset/processed/`, and `dataset/external/` are ignored,
  not part of the changed-path inventory, and are not proposed for release.
- **External-clone limitation:** read-only status checks found existing dirty
  states in all five ignored Eclipse clones: `eclipse.jdt.core` (10,856
  deletions and 3 untracked entries), `eclipse.pde` (10,878 deletions),
  `eclipse.platform` (11,352 deletions), `eclipse.platform.swt` (3,669
  deletions), and `eclipse.platform.ui` (11,940 deletions). No clone file was
  changed or restored by this audit. Without a recorded pre-audit baseline,
  these current states do not establish when or how those deletions occurred;
  their integrity remains unresolved and they must stay outside the commit.

## 7. Security and privacy

The pattern scan covered every modified and untracked file in the initial
66-path inventory. It found:

- No credential-like assignments, private-key blocks, or embedded
  credential-bearing URLs.
- No personal absolute Windows user paths.
- Eight email-pattern occurrences, all synthetic test fixtures using the
  reserved `example.test` domain in
  `tests/unit/test_eclipse_identity_review.py`.
- No private identity-mapping rows in the changed documents. Generic
  `developer_id`/`assignee` schema names, repository-scoped cohort summaries,
  and manifest checksums are not personal identity values.
- `research/dataset_documentation/jdt_workload_replay_mismatch_analysis.md`
  remains the confirmed exception: it contains stable pseudonymous,
  per-developer mismatch/activity information. It is explicitly excluded
  below and was not modified.

The identity-review scripts contain transformation logic, not the ignored
identity-review datasets. Restricted raw/processed data and external clones
are not candidate changed paths. Heuristic text scanning cannot guarantee
detection of every possible secret format.

The historical `PRE_PUSH_AUDIT.md` also records a pre-existing author/committer
metadata privacy concern for the already-synchronized HEAD. That metadata is
not part of the proposed file set and was not changed here. Obtain approval for
the identity that will appear in any new public commit before proceeding.

## 8. Exact public-release file lists

### A. SAFE TO COMMIT

These exact changed paths passed this file-level review. This list includes the
requested audit report and excludes every B-list path.

```text
README.md
.vscode/settings.json
bug_similarity/retrieval/__init__.py
bug_similarity/retrieval/point_in_time.py
docs/architecture/remaining_work_architecture.md
docs/methodology/data_contracts_and_features.md
docs/methodology/evaluation_protocol.md
ml_model/feature_selection/__init__.py
ml_model/feature_selection/adaptive.py
ml_model/ranking/__init__.py
ml_model/ranking/top_k.py
research/dataset_documentation/bugzilla_retry_results.md
research/dataset_documentation/dataset_availability.md
research/dataset_documentation/eclipse_dataset_completion_plan.md
research/dataset_documentation/eclipse_git_collection_plan.md
research/dataset_documentation/eclipse_git_extraction_plan.md
research/dataset_documentation/eclipse_nine_feature_readiness.md
research/dataset_documentation/eclipse_pde_collection_report.md
research/dataset_documentation/eclipse_platform_collection_report.md
research/dataset_documentation/eclipse_platform_swt_collection_report.md
research/dataset_documentation/eclipse_platform_ui_collection_report.md
research/dataset_documentation/eclipse_project_source_probe.md
research/dataset_documentation/final_dataset_completion_report.md
research/dataset_documentation/final_remaining_dataset_validation_report.md
research/dataset_documentation/jdt_preprocessing_validation_report.md
research/dataset_documentation/jdt_workload_event_scan_report.md
research/dataset_documentation/master_dataset_inventory.md
research/dataset_documentation/remaining_work_completion_report.md
research/dataset_documentation/remediation_report.md
research/dataset_documentation/second_pre_commit_audit_report.md
research/dataset_documentation/temporal_feature_variant_audit.md
research/dataset_handover/DATASET_HANDOVER_README.md
research/dataset_handover/DATASET_INVENTORY.md
research/dataset_handover/DATA_DICTIONARY.md
research/dataset_handover/FINAL_DATASET_HANDOVER_REPORT.md
research/dataset_handover/KNOWN_LIMITATIONS.md
research/dataset_handover/PREPROCESSING_METHODOLOGY.md
research/dataset_handover/PRE_PUSH_AUDIT.md
research/dataset_handover/TEAM_HANDOVER_MATRIX.md
research/dataset_handover/VALIDATION_RESULTS.md
research/dataset_handover/dataset_file_manifest.csv
scoring_engine/cold_start/__init__.py
scoring_engine/cold_start/policy.py
scoring_engine/confidence/__init__.py
scoring_engine/confidence/prediction_confidence.py
scoring_engine/final_scoring/__init__.py
scoring_engine/final_scoring/explainability.py
scoring_engine/recency/__init__.py
scoring_engine/recency/point_in_time.py
scoring_engine/workload/__init__.py
scoring_engine/workload/point_in_time.py
scripts/build_jdt_integrated_dataset.py
scripts/build_jdt_partial_resolution_activity.py
scripts/extract_eclipse_git_contributions.py
scripts/extract_jdt_workload_events.py
scripts/inventory_dataset_availability.py
scripts/prepare_eclipse_identity_review.py
scripts/prepare_jdt_point_in_time_datasets.py
scripts/reconstruct_jdt_partial_workload.py
scripts/validate_jdt_partial_workload.py
scripts/validate_jdt_workload_outputs.py
scripts/validate_temporal_feature_variants.py
tests/unit/test_eclipse_identity_review.py
tests/unit/test_jdt_partial_workload.py
tests/unit/test_remaining_work_modules.py
research/dataset_documentation/final_pre_commit_audit_report.md
```

### B. MUST REMAIN EXCLUDED

```text
research/dataset_documentation/jdt_workload_replay_mismatch_analysis.md
```

Reason: stable pseudonymous developer identifiers and per-developer activity
details; explicit release approval or a separate privacy review is required.

The following ignored data/environment paths are also not release candidates;
they were not changed paths in this audit:

```text
dataset/raw/JDT.csv
dataset/processed/
dataset/external/
.venv/
.venv-sbert/
```

### C. NEEDS USER DECISION

**No changed file is placed in this category.** The non-file release decisions
still outstanding are approval of future public commit identity metadata and
how to treat the pre-existing dirty external clone worktrees. Neither changes
the exact A/B path classification.

## 9. Unresolved issues

1. The identity-linked mismatch report remains excluded.
2. The external clones' existing large deletion sets have no recorded baseline;
   this audit cannot certify that they predate this work.
3. Raw and processed dataset contents were not rehashed or fully revalidated;
   only manifest paths and file sizes were checked. No dataset validation is
   implied by the 44 code unit tests.
4. The next public commit's author/committer identity requires user approval.
5. The query text timestamp is supplied by the caller and is not independently
   verified against an immutable historical text snapshot.
6. The 90-day recency half-life is a default only. No integrated recommender,
   project-data calibration, retrieval evaluation, ranking evaluation, or
   model performance claim is supported.

## 10. Final recommendation

**NOT READY TO COMMIT as a public commit until the author/committer identity
decision is resolved.** The A-list is the exact reviewed candidate set for a
later explicitly approved commit; the B-list must remain excluded. No staging,
commit, push, cleanup, restoration, or other Git-changing operation was
performed. Stop here pending user approval.
