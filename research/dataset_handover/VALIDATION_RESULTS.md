# Validation Results

**Historical snapshot:** This records dataset validation evidence and the
unit-test status as of 2026-11-11. Its statement that tests were not rerun
applies only to that audit; see the
[remediation report](../dataset_documentation/remediation_report.md) for the
later code-test results. Dataset validations below were not rerun as part of
that code remediation.

**Audit date:** 2026-11-11. No model training or model evaluation was run.

## Actual-file audit

- Enumerated and read all **68 processed CSVs** (6,773,047 rows including package copies and intentional repeated rows); collected actual headers, row counts, blank-cell counts, timestamp-like values, file sizes, and SHA-256 checksums.
- Computed exact full-row duplicate checks for every processed CSV. No invalid values were found in nonblank timestamp-like columns under ISO datetime parsing.
- Nine `member1_dataset_files/` CSVs are byte-identical copies of existing processed CSVs.
- `jdt_integrated_bug_context_metadata.csv` has 265,968 exact repeated rows because each bug's export-time context is repeated across nine developer candidates. This is intentional; its normalized companion has 33,246 distinct bug/cutoff rows.
- `git_bugzilla_exact_email_matches.csv` contains one exact duplicate row among 14 candidate rows. The original was preserved. The separate cleaned 13-row file has no exact duplicate rows and is the safer candidate source; it still does not confirm identity.
- The prior `dataset_availability.md` file manifest matched current size, row count, and SHA-256 for 37 previously listed processed CSV entries. The ZIP size and SHA-256 also match its prior entry. The raw JDT file size matches the prior inventory, but its checksum was not recomputed.
- Across core integrated tables, missingness matches the known semantics: assignment recency blank for 206,990 zero-history candidates; Git recency blank for 253,172 candidates; target IDs blank for 29,177 out-of-pool labels; duplicate text snapshot time blank for all 1,810 positives; and partial-workload coverage fields blank for cutoffs with no eligible active bugs.

The checksums and row counts for the processed CSVs and ZIP are in [dataset_file_manifest.csv](./dataset_file_manifest.csv). This audit does not claim that generic exact-row uniqueness replaces each dataset's natural-key validation.

## Dataset-specific validators rerun

| Validation | Result |
|---|---|
| `scripts/build_jdt_integrated_dataset.py --validate-existing` | **PASS**; seven outputs validated and reproduced deterministically. |
| `scripts/prepare_jdt_point_in_time_datasets.py --validate-existing` | **PASS**; 9/9 point-in-time outputs byte-identical under temporary regeneration; source checksums matched. |
| `scripts/build_jdt_partial_resolution_activity.py --validate-existing` | **PASS**; 299,214 rows, 228 eligible source histories, 225 observed resolution events. |
| `scripts/validate_jdt_workload_outputs.py` | **PASS**; 63,266 coverage IDs, 287,917 unique event keys, exact count/reference agreement, no invalid timestamps, pre-creation events, or orphans. |
| `scripts/validate_jdt_partial_workload.py` | **PASS**; 299,214 snapshots, 33,246 coverage rows, 228 eligible source histories. |
| `scripts/validate_temporal_feature_variants.py --report <temporary path>` | **PASS**; strict reconstruction 432,198/432,198, no validation errors. The existing report was not overwritten. |
| `scripts/validate_training_dataset.py` | **PASS**; primary 33,246 unique bug IDs, secondary 607 unique bug IDs; source missingness measured, not imputed. |
| Existing combined Git extraction report | **PASS as previously documented**; 183,742 unique `(repository, commit_id)` keys, zero orphan changed-path rows, required fields and candidate references checked. The Git extraction itself was not rerun. |

Unit tests had previously passed 37/37 according to the final completion report. This audit attempted to rerun `pytest tests/unit`, but the selected `.venv-sbert` environment does not have `pytest` installed (`No module named pytest`). No dependency was installed; therefore **the unit suite was not rerun in this audit**.

## Integrity and scope boundaries

- The full raw JDT CSV was not read, scanned, copied, or rehashed. Its SHA-256 in the manifest is the earlier recorded value; current file size matches that record.
- No source file or dataset was intentionally modified. Validation used existing outputs and temporary regeneration modes.
- No final model, feature score, calibrated confidence, recommendation explanation, similarity score, Top-K rank, or held-out metric was created or inferred.
- Platform/PDE Bugzilla status reuses the documented four bounded shutdown-page responses; no endpoint retry was made.
