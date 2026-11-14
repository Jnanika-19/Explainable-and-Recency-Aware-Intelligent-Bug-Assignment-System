# Pre-Push GitHub Safety Audit

**Historical snapshot:** This records the pre-push review and Git state observed
on 2026-11-11. Its synchronization, proposal, and test results are not current
verification; see the [remediation report](../dataset_documentation/remediation_report.md)
for the later controlled remediation and rerun results.

**Audit date:** 2026-11-11
**Repository:** `Jnanika-19/Explainable-and-Recency-Aware-Intelligent-Bug-Assignment-System`
**Scope:** Pre-push review. Nothing was staged, committed, pushed, deleted, or overwritten. This report is the only new file created for this review; two proposed documentation files had local absolute paths replaced with repository-relative wording.

## Git state

- **Branch:** `feature/jdt-dataset-collection`
- **Upstream:** `origin/feature/jdt-dataset-collection`
- **Fetch/push URL:** `https://github.com/Jnanika-19/Explainable-and-Recency-Aware-Intelligent-Bug-Assignment-System.git`
- **HEAD:** `b1e4d2e3b19d4a362e167a4365803f99385f8b9e` — `Add JDT developer contribution and temporal feature extraction`
- **Fetched remote tip:** `a3abf2ef8481d07c800642a5a03d6458dbe3169c`
- **Local versus fetched remote:** one commit ahead, zero behind (`git rev-list --left-right --count HEAD...origin/feature/jdt-dataset-collection` reported `1 0`). A fetch updated remote-tracking information only; there was no merge or rebase.
- **Index:** no staged changes.
- **Tracked worktree changes:** `README.md` modified; no tracked deletions. The existing documentation files `research/dataset_documentation/eclipse_pde_collection_report.md` and `research/dataset_documentation/master_dataset_inventory.md` were also edited to remove absolute local paths.
- **Untracked changes:** source, tests, research documents and the dataset handover package listed below. No ignored dataset files were selected.

The working tree changes are additive except for the existing README edit. The current commit history is intact. A future commit that adds the approved paths will not remove existing commits or tracked files. Do not force-push or rewrite history as part of this proposal.

## Existing ahead-commit review and publish blocker

The complete diff of the one local commit was inspected. Commit `b1e4d2e`, relative to fetched origin, adds **8 files and 996 lines**:

- `.gitignore`
- `scripts/audit_bulk_git_commits.py`
- `scripts/clean_git_bugzilla_identity_matches.py`
- `scripts/create_adjusted_git_contributions.py`
- `scripts/create_temporal_bug_developer_features.py`
- `scripts/extract_jdt_git_contributions.py`
- `scripts/extract_verified_git_features.py`
- `scripts/match_git_bugzilla_identities.py`

The diff adds generated-data ignore coverage and scripts for JDT Git contribution extraction, exact-email/name candidate preparation, bulk-commit review, temporal feature generation, and adjusted contribution summaries. The diff contains no raw dataset or generated CSV contents and no personal absolute Windows path or credential-pattern match. The scripts do process developer names/emails when run; their data outputs are under ignored `dataset/processed/`.

**Privacy blocker:** the existing ahead commit's author and committer metadata contain the configured personal email address. It is embedded in the commit object, even though it is not reproduced here. Pushing this branch would publish that metadata. This audit did not amend or recreate the commit because history rewriting was prohibited. **Do not push until you explicitly decide whether publishing that commit identity is acceptable or authorize a separate privacy-safe history remedy.** The proposed uncommitted file list does not remove this existing commit from the branch.

## `.gitignore` review

The current `.gitignore` excludes:

- `dataset/raw/*`, `dataset/processed/*`, and `dataset/external/*`, while preserving `.gitkeep` placeholders and a small sample-data exception.
- `.venv/`, `.venv-sbert/`, other common virtual environments, Python bytecode/caches, and pytest artifacts.
- `.env`, `.env.*` (except the explicitly permitted `.env.example` template), logs, temporary files, build/dist output, model binaries, and experiment/checkpoint output.

`git check-ignore -v` confirmed the raw JDT export, processed integrated CSVs, external Git clone metadata, `.env.local`, `.venv` Python executable, and build output are ignored. A narrow exception permits `dataset/processed/member1_dataset_files/README.md`; the data files in that package directory remain ignored. Existing duplicated/repeated ignore entries are untidy but the checked protections are effective. `.gitignore` itself is unchanged and is not proposed for this commit.

The two personal absolute project-root paths found in proposed documentation were replaced with `repository root (.)`. The proposed documentation no longer contains personal Windows user/Desktop paths.

## Exclusion and size checks

- `dataset/raw/JDT.csv` (6,377,569,970 bytes), `dataset/external/` clones, and `dataset/processed/` generated datasets are ignored and excluded.
- No virtual environment, build output, `.env` file, credential file, or private-key file is included in the proposed paths.
- Existing tracked dataset paths in `HEAD` are only the zero-byte raw/processed placeholders and the small `member1_dataset_files/README.md`; no large dataset blob is tracked.
- No proposed file exceeds the 100 MiB GitHub large-file threshold. All 60 proposed files total 689,504 bytes; the largest is 58,971 bytes. Git LFS is installed, but no LFS attributes apply and LFS is not needed for this proposal.

## Secret and identity scan

No staged changes existed. A local pattern scan covered all 60 proposed files. It found no private-key blocks, AWS access-key patterns, GitHub token patterns, credential assignments, private email addresses, or stable JDT developer/assignee identity tokens. Eight email-pattern matches occur only in `tests/unit/test_eclipse_identity_review.py` and use reserved `example.test` fixture values. Personal absolute project paths were found in the two documentation files named above and have been replaced; a repeat scan found no personal Windows user/Desktop paths in the proposal.

The untracked report `research/dataset_documentation/jdt_workload_replay_mismatch_analysis.md` contains individual stable pseudonymous developer/assignee keys. It is intentionally excluded from the proposed first commit to avoid publishing identity-linked per-developer mismatch details. Other raw identity maps and generated identity CSVs are ignored under `dataset/processed/`; the handover package records file metadata and sensitivity classifications, not identity values.

Secret scanning is heuristic and is not a guarantee against every credential format. Review any future new or modified file before staging.

## Available validation

- Documented unit command, using `.venv-sbert`:
  `python -m unittest discover -s tests\unit -p "test_*.py" -v`
  **PASS: 37 tests.**
- `pytest` is unavailable in both checked Python environments (`No module named pytest`). No package was installed.
- `git diff --check`: **PASS** after path cleanup. An additional whitespace scan of all proposed files found no trailing whitespace. All 60 proposed files exist; the proposal count and paths match exactly.
- Dataset validators most recently rerun for the handover passed for integrated data, point-in-time outputs, partial resolution activity, lifecycle events, partial workload, temporal variants, and primary/secondary training tables. Details are in `research/dataset_handover/VALIDATION_RESULTS.md`.

## Exact proposed first-commit paths

The following **60 paths** are the proposed contents after this report is saved. This is a review list only; none is staged. The identity-bearing replay-mismatch report described above is deliberately omitted.

```text
README.md
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
research/dataset_documentation/temporal_feature_variant_audit.md
research/dataset_handover/DATA_DICTIONARY.md
research/dataset_handover/DATASET_HANDOVER_README.md
research/dataset_handover/DATASET_INVENTORY.md
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
```

## Approval gate

This list is a proposal, not a staging instruction. No Git operation that changes the index or remote was performed. Review the exact list, the README change, the intentional identity-report exclusion, and the existing commit metadata blocker above before authorizing any stage or commit. **Push approval is not recommended until the commit-email privacy issue is resolved.**
