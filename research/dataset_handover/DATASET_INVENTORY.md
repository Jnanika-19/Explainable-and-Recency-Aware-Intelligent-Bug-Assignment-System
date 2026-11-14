# Dataset Inventory

All paths below are repository-root-relative. Counts exclude CSV header rows. The [manifest](./dataset_file_manifest.csv) lists every processed CSV found in the local dataset directory (including packaging copies), the package ZIP, and the raw JDT export.

## Collection overview

| Source or dataset | Local location | Scope and status |
|---|---|---|
| Eclipse JDT Bugzilla export | `dataset/raw/JDT.csv` | Existing 6,377,569,970-byte source; 63,266 bugs were counted during a prior approved scan. This handover did not reopen or recount it. |
| JDT assignment labels and text | `dataset/processed/jdt_training_primary.csv`; `jdt_training_secondary_review.csv`; `jdt_bug_text_cleaned.csv` | 33,246 primary assignment examples, 607 separate secondary-review examples, and cleaned text for 33,246 bug IDs. |
| Duplicate relationships | `dataset/processed/duplicate_pairs.csv`; `duplicate_pairs_historical_available.csv`; `duplicate_pairs_with_families.csv` | 10,875 source links, 1,810 historically available positive links, and 9,366 derived family pairs. These are not a complete duplicate/related classification dataset. |
| JDT Git evidence | `dataset/processed/cold_start/` | JDT commit/path histories and contributor roster; contribution is not assignment evidence. |
| Combined Eclipse Git evidence | `dataset/processed/cold_start/eclipse_all_repositories/` | Five local repositories: 183,742 commits, 2,215,515 changed paths, and 7,332 repository-scoped author keys. |
| JDT point-in-time data | `dataset/processed/jdt_point_in_time/` | 299,214 bug/developer candidate rows, 33,246 targets and bug splits, and 206,990 zero-prior-assignment scenarios. |
| JDT lifecycle evidence | `dataset/processed/jdt_workload/` | 287,917 lifecycle changes and 63,266 history-coverage rows, derived in the prior one-pass JDT scan. Not sufficient for complete workload reconstruction. |
| JDT partial workload | `dataset/processed/jdt_workload_partial/` | 299,214 partial snapshots, 33,246 cutoff-coverage rows, and 299,214 resolution-activity sidecar rows. Only 228 histories passed strict eligibility. |
| Integrated JDT tables | `dataset/processed/jdt_integrated/` | Seven tables: 299,214 candidate rows, 299,214 repeated context rows, 33,246 normalized context rows, 33,246 targets, 206,990 cold-start rows, 1,810 duplicate positives, and 9 identity rows. |
| JDT identity review | `dataset/processed/cold_start/jdt_identity_review/` | 13 exact-email audit rows, 9 conservative verified mappings, and 76 unresolved review rows. Identity data is restricted. |
| Platform/SWT/UI/PDE Git | `dataset/external/` and `dataset/processed/cold_start/eclipse_all_repositories/` | Git history and contribution evidence only. No Platform/PDE Bugzilla reports, assignments, or workload histories were collected. |

## Five local Git repositories

Commit counts are from the existing repository inventory and extraction report. They describe locally reachable refs, not hidden/unadvertised server refs.

| Repository | Local path | Commit rows | Changed-path rows |
|---|---|---:|---:|
| JDT Core | `dataset/external/eclipse.jdt.core/` | 32,484 | 312,493 in combined extraction |
| Platform | `dataset/external/eclipse.platform/` | 46,304 | 392,472 |
| Platform SWT | `dataset/external/eclipse.platform.swt/` | 35,391 | 326,899 |
| Platform UI | `dataset/external/eclipse.platform.ui/` | 48,171 | 884,467 |
| PDE | `dataset/external/eclipse.pde/` | 21,392 | 299,184 |

Combined files include repository identity, author/committer timestamps, and first-parent merge paths. The older JDT-only changed-file table has 279,322 rows; it is not expected to match the combined JDT subset because the merge-diff policy differs.

## File totals and duplicate package copies

- The processed directory contains **68 CSV files**, **6,773,047 total rows**, and **1,710,422,089 bytes**. These totals include repeated tables and package copies and are not counts of unique bugs or unique information.
- **Nine** CSVs under `dataset/processed/member1_dataset_files/` are byte-identical copies of corresponding top-level processed CSVs. Excluding those copies leaves 59 CSV files and 1,639,831,009 bytes.
- `dataset/processed/member1_dataset_files.zip` is a packaging copy; it is not a new dataset.
- The candidate-expanded integrated context table repeats each bug's context across candidate rows by design. Use the normalized one-row-per-bug table for context joins.
- The unclean `git_bugzilla_exact_email_matches.csv` has 14 rows and one exact duplicate row. Prefer the separate 13-row `_clean.csv` output for reviewed exact-email candidates; neither file itself establishes identity.

The manifest contains actual file sizes and computed SHA-256 values for the processed CSVs and ZIP. The JDT raw file uses its previously recorded checksum and is explicitly marked as not rehashed in this audit.
