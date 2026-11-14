# Final Remaining Dataset Validation Report

Assessment date: 2026-11-11

Project: Explainable and Recency-Aware Intelligent Bug Assignment System

## Executive status

The available local datasets have been integrated and validated as far as
their provenance and point-in-time limits allow. No final recommendation
model was trained. Complete workload reconstruction and project-data duplicate
retrieval remain blocked; the partial workload is clearly labeled and kept
separate from complete workload claims.

The original raw JDT export was not rescanned in this execution. Existing
source data, collection outputs, temporal variants, identity maps, and
previous workload files were preserved. New derived outputs were generated
only in previously absent paths or as non-overwriting supplemental files.

## Remaining-work checklist

| Work item | Status | Result |
|---|---|---|
| Inspect existing inventories, reports, schemas, and scripts | Completed | Used the latest completion, inventory, readiness, workload, temporal, identity, and Bugzilla reports and inspected relevant generators/validators. |
| Resolve temporal variant hash discrepancy | Completed and validated | Base, strict, and inclusive files have identical SHA-256. The strict generator uses `committer_timestamp < bug_creation_time`; reconstructed 432,198/432,198 rows match. No variants were rewritten. |
| Reconstruct workload from authorized 4,542-bug subset | Completed as partial only | 228 histories passed strict state seed, event-chain, and product/status parity gates. Generated 299,214 developer/cutoff snapshots and 33,246 coverage rows. |
| Include resolution activity where supported | Completed as separate partial evidence | Added 299,214 resolution-activity rows; 225 resolution changes are attributed to verified assignees in the eligible subset. Strictly future events are excluded. |
| Complete duplicate/related retrieval | Blocked | Historical text snapshot/update timestamps are absent. Existing duplicate labels remain target-only; no TF-IDF, cosine, related labels, or assumed negatives were fabricated. |
| Review identities and cold-start cases | Partially completed | 9 exact-email identities meet the conservative one-user audit; 4 exact-email rows lack Bugzilla user-ID evidence; 72 name candidates remain review-only. |
| Check Platform/PDE Bugzilla | Blocked by source availability | Previously bounded requests returned temporary-shutdown HTML, not REST JSON. No further retry or collection was made. |
| Integrate nine feature datasets | Completed with explicit readiness flags | Candidate features, partial workload, targets, cold-start evaluation, duplicate targets, identity metadata, and temporally unverified context are separate. Unsupported scores/probabilities/ranks remain absent. |
| Final validation and documentation | Completed | Dataset validators, deterministic regeneration checks, checksums, and all 37 unit tests passed. The training validator was run separately in the environment with pandas. |
| Train/evaluate final model | Deferred | The user explicitly requested no final model training; the data also has material coverage and evaluation gates. |

## Collected and preprocessed dataset inventory

This table summarizes source and derived artifacts relevant to the nine
features. The [master inventory](./master_dataset_inventory.md) records the
broader repository, package-copy, Git-contributor, and audit-file inventory.
Row counts exclude CSV headers.

| Dataset | Path / source | Rows or size | Provenance and status |
|---|---|---:|---|
| Raw JDT Bugzilla export | `dataset/raw/JDT.csv` | 6,377,569,970 bytes; a prior scan found 63,266 unique bug IDs | Existing source. One read-only streaming scan is documented in `jdt_workload_event_scan_report.md`; it was not repeated here. |
| Primary JDT assignment dataset | `dataset/processed/jdt_training_primary.csv` | 33,246 | Existing processed JDT data; direct assignment labels with source evidence and label tiers. |
| Secondary JDT review dataset | `dataset/processed/jdt_training_secondary_review.csv` | 607 | Existing review-only records; not merged into primary targets. |
| JDT cleaned text | `dataset/processed/jdt_bug_text_cleaned.csv` | 33,246 | Existing cleaned summary/description text. Per-version text availability is not recorded. |
| Duplicate source/family data | `dataset/processed/duplicate_pairs.csv`, `dataset/processed/duplicate_pairs_historical_available.csv`, `dataset/processed/duplicate_pairs_with_families.csv` | 10,875 source links; 1,810 historical-available positives; 9,366 family pairs | Existing JDT duplicate relationships and family derivation. Do not treat family edges as independent negative/related labels. |
| JDT lifecycle events | `dataset/processed/jdt_workload/jdt_assignment_lifecycle_events.csv` | 287,917 | Derived in the prior approved one-pass JDT scan. 0 invalid timestamps, pre-creation events, duplicate event keys, or orphan event references. |
| JDT history coverage | `dataset/processed/jdt_workload/jdt_bug_history_coverage.csv` | 63,266 | One coverage record per raw bug. Replay: 47,959 pass, 13,427 mismatch, 1,880 incomplete/not testable. |
| JDT Git contributions | `dataset/processed/cold_start/jdt_git_commits.csv`, `jdt_git_commit_files.csv`, and roster | 32,484 commits; changed-path and roster counts in the master inventory | Existing JDT Git evidence; contribution is not assignment history. |
| Combined Eclipse Git contributions | `dataset/processed/cold_start/eclipse_all_repositories/eclipse_git_commits.csv`, `eclipse_git_commit_files.csv`, developer roster | 183,742 commits; 2,215,515 changed paths; 7,332 repository-scoped author keys | Derived from locally available Git histories for JDT, Platform, SWT, UI, and PDE. Git-only evidence; no issue assignment labels are inferred. |
| Strict temporal features | `dataset/processed/cold_start/jdt_bug_developer_temporal_features{,_strict,_inclusive}.csv` | 432,198 rows per file | 13 source-map identities. Byte-identical files; only strict generation semantics are established and reconstructed. |
| Conservative identity review | `dataset/processed/cold_start/jdt_identity_review/` | 13 exact-email audit rows; 9 verified mappings; 76 unresolved review rows | Exact normalized email, one audited Bugzilla user ID, matching JDT roster evidence, and no existing bot/service heuristic flag are required for verification. No name-only merges. |
| Point-in-time candidate features | `dataset/processed/jdt_point_in_time/jdt_candidate_features.csv` | 299,214 (33,246 bugs × 9 candidates) | Existing point-in-time direct-assignment counts and strict prior Git features. 92,224 rows have prior assignment evidence; 206,990 do not. |
| Assignment targets and bug splits | `dataset/processed/jdt_point_in_time/jdt_assignment_targets.csv`, `jdt_bug_splits.csv` | 33,246 each | Separate targets and chronological bug-level train/validation/test splits; all candidates for a bug remain together. |
| Cold-start scenarios | `dataset/processed/jdt_point_in_time/jdt_cold_start_scenarios.csv` | 206,990 | Zero prior direct-assignment scenarios. `genuinely_new_developer=unknown`; no fallback assignment source. |
| Duplicate-positive audit | `dataset/processed/jdt_duplicate_retrieval/jdt_duplicate_positive_pairs_audit.csv` | 1,810 | Unique positive pairs; original bug creation predates duplicate creation. Target-only; no historical text snapshot time. |
| Partial workload | `dataset/processed/jdt_workload_partial/jdt_partial_workload_snapshots.csv`; `jdt_partial_workload_coverage.csv` | 299,214 snapshots; 33,246 cutoff coverage rows | 228 eligible source histories from the authorized 4,542-bug replay-clean verified-assignment subset. Partial-only; unsupported bugs outside the cohort are not assumed absent. |
| Partial resolution activity | `dataset/processed/jdt_workload_partial/jdt_partial_resolution_activity.csv` | 299,214 | 225 observed resolution changes attributed only to verified assignees; strictly before cutoff. Activity counts are not complete queues. |
| Integrated candidate and metadata tables | `dataset/processed/jdt_integrated/` | 7 CSVs; individual counts and hashes below | Generated by `scripts/build_jdt_integrated_dataset.py`; labels, cold-start evaluation, identity metadata, and bug context are separate from predictors. |

### Git repository sources

| Repository | Official remote | Local processed commit count |
|---|---|---:|
| Eclipse JDT Core | `https://github.com/eclipse-jdt/eclipse.jdt.core.git` | 32,484 |
| Eclipse Platform | `https://github.com/eclipse-platform/eclipse.platform.git` | 46,304 |
| Eclipse Platform SWT | `https://github.com/eclipse-platform/eclipse.platform.swt.git` | 35,391 |
| Eclipse Platform UI | `https://github.com/eclipse-platform/eclipse.platform.ui.git` | 48,171 |
| Eclipse PDE | `https://github.com/eclipse-pde/eclipse.pde.git` | 21,392 |

Collection details, ref counts, and clone validation remain in the
per-repository reports linked from the master inventory. Git authorship is
contribution evidence only; it is not confirmed assignment history.

## Integrated outputs, row counts, and SHA-256

All paths below are under `dataset/processed/`. Checksums describe the
generated bytes in this execution. The candidate-expanded context table
repeats bug-level context once per developer candidate for compatibility;
the normalized context table is the unique bug-level representation.

| File | Rows | Bytes | SHA-256 |
|---|---:|---:|---|
| `jdt_integrated/jdt_integrated_candidate_features.csv` | 299,214 | 167,227,877 | `82b136a2898e43b6a41998f705939bd4a93033bc6362f9801510e0a3089dc419` |
| `jdt_integrated/jdt_integrated_bug_context_metadata.csv` | 299,214 | 28,274,781 | `8f464118ec7190afba8fa306fcc1e95771e1e0ea8620d8c9a00e698f37036218` |
| `jdt_integrated/jdt_integrated_bug_context_by_bug.csv` | 33,246 | 3,141,773 | `2dad2295c29d236d40b71337eede67d3f981b66b359c17eef331f7a825623f55` |
| `jdt_integrated/jdt_integrated_targets.csv` | 33,246 | 4,336,516 | `4ea02ce3db19916a6346a15365e6f384d6fb9c3567188c321b94bfe7b6ff7feb` |
| `jdt_integrated/jdt_integrated_cold_start_evaluation.csv` | 206,990 | 38,472,297 | `d78e52c9ef56c46444aa64ebf92c97e5f3582e23d8cbfd5a9cfaa80e3f5b091b` |
| `jdt_integrated/jdt_integrated_duplicate_evaluation_pairs.csv` | 1,810 | 205,207 | `14fab2691a56f93194f0829698edd9abed91c6dfd70933f9fa800dcf473ac464` |
| `jdt_integrated/jdt_integrated_developer_identity_metadata.csv` | 9 | 2,093 | `4d7c6f61be21565de2649314e6eac13ec38918ab28d749ac5acee7dc602fe808` |
| `jdt_workload_partial/jdt_partial_resolution_activity.csv` | 299,214 | 43,129,587 | `5b977efa863924af413311e7dd74298df8bc9f2f4a4d1026335e2e970814876e` |

Checksums of existing processed outputs revalidated in this execution:

| File | Rows | SHA-256 |
|---|---:|---|
| `jdt_workload_partial/jdt_partial_workload_snapshots.csv` | 299,214 | `f04b2e66438f218645f8ddb4adbbaf2be14e12fd17f62c8c7dc209adbb828109` |
| `jdt_workload_partial/jdt_partial_workload_coverage.csv` | 33,246 | `0a3db851564fe30b62502d7003ece432eb75e11bb26e6503df68d59f333b0b7c` |
| `jdt_point_in_time/jdt_candidate_features.csv` | 299,214 | `4754bf1c4731ffa1443748c0bbab6c023fe3a5feed70990fa8486572f79c4be4` |
| `jdt_point_in_time/jdt_assignment_targets.csv` | 33,246 | `2ce7c2dfd36b379b88882e79d87e2df8f0a432a1de74134fae6842c7c2a7400a` |
| `jdt_point_in_time/jdt_bug_splits.csv` | 33,246 | `444fb98a0a413ba193d89f472803497a1ccd677d925d271e860593c4df9d6d76` |
| `jdt_point_in_time/jdt_cold_start_scenarios.csv` | 206,990 | `caa196a4306574f90d8a8d0aa63599ed595661202d74b45488494e76a741072d` |
| `jdt_duplicate_retrieval/jdt_duplicate_positive_pairs_audit.csv` | 1,810 | `5ee31abf4d5117ed0847d64187438bdba0a638c6682369fe42c2f49c2e88738d` |
| `cold_start/jdt_identity_review/jdt_verified_identity_map.csv` | 9 | `6f31547ef3e35bc5bc32c827d32fc79000abde3c53cd24ddfc6f18e3a3bbaae1` |
| `cold_start/jdt_identity_review/jdt_exact_email_mapping_audit.csv` | 13 | `253ada00bc89604f738ac71c30184f83ade0d034fc04f7f6a0f5eb8bf50f445f` |

The identity-metadata output contains personal identifiers and is for
restricted local research use. Do not publish it without an applicable
privacy and licensing review.

## Workload coverage and limitations

- The replay-clean assignment subset contains 4,542 source bugs. Strict
  first-old seeding, per-field chain validation, pre-creation rejection, and
  product/status parity retain 228; 4,314 are excluded for incomplete seeds
  or broken chains.
- The prediction grid has 33,246 bug cutoffs × 9 verified developers =
  299,214 rows. Every output is marked `workload_scope=partial`.
- Each cutoff includes only source events with `event_time < prediction_cutoff`.
  The workload validator confirmed strict cutoff, unique keys, valid
  identities, split grouping, event chains, and byte-for-byte regeneration.
- Only the eligible subset is counted. Bugs absent from that subset are
  unknown, not zero-workload cases. Coverage ratios are conditional on this
  partial cohort. No severity-weighted measure was emitted.
- The resolution sidecar reports 225 observed verified-assignee resolution
  changes and set/clear activity. It is not a complete queue or outcome label.
- Complete workload remains blocked by 13,427 replay mismatches, 1,880
  incomplete histories, and the lack of full historical coverage evidence.

## Duplicate and related-bug coverage

- The 1,810 positive duplicate links are unique, target-only, and chronologically
  checked; the original bug existed before the duplicate query bug.
- Existing cleaned text covers 33,246 bug IDs, but does not provide text
  version/update availability times. Bug creation before a cutoff does not
  prove the currently cleaned text was available then.
- `bug_similarity/retrieval/point_in_time.py` requires both bug creation and
  text availability before the cutoff; its temporal behavior is unit-tested
  synthetically. Project-data retrieval was therefore not run.
- No related-bug labels or defensible negatives are present. Non-duplicate
  pairs cannot be assumed unrelated, and family membership does not create
  independent labels.
- No final duplicate resolution field is used as a model input.

## Developer identity and cold-start coverage

- 13 exact-email map entries were audited. 9 have a single audited Bugzilla
  user ID, matching JDT roster email, and no current bot/service heuristic
  flag; 4 have no Bugzilla user ID in the available audit.
- No multi-user exact-email mapping was found. All 13 audit rows have no
  current bot/service heuristic flag, which is not proof that an account is a
  human. Name-only candidates remain unverified.
- The unresolved review queue has 76 rows: 72 name-based candidates and 4
  exact-email mappings without Bugzilla user-ID evidence. No identities were
  merged based only on names.
- The JDT Git contributor cohort has 254 repository-scoped keys: 9 verified,
  19 unresolved name-candidate keys, and 226 without verified Bugzilla
  identity. Git activity does not prove assignment experience.
- Of the nine verified candidate identities, one has no prior direct
  assignment evidence over the observed cutoffs, and two have at most one
  observed prior assignment. No policy threshold for “insufficient” history
  was specified; these low-evidence cases must be treated conservatively.
- The 206,990 zero-history scenarios are evaluation-only. Genuine newness is
  `unknown`, and no fallback assignment evidence is available.

## Platform/PDE Bugzilla collection status

The documented bounded availability check made four requests: product
metadata and a one-record metadata-only probe for Platform and PDE. All four
returned HTTP 200 with `text/html` temporary-shutdown pages, not REST JSON.
The result is recorded in `bugzilla_retry_results.md`. No bug records,
assignment histories, comments, or raw responses were collected. No retry
was made in this execution. Platform/PDE collection is blocked until an
official endpoint or an approved, provenance- and terms-checked archive is
available. GitHub repositories and issues are not substitutes for Bugzilla
assignment histories.

## Nine-feature status

| # | Feature | Final status | Evidence and remaining limit |
|---:|---|---|---|
| 1 | Historical developer expertise | Partially completed | JDT assignment/Git evidence for 9 conservative identities; one has zero prior assignment evidence and two have at most one. Other repos are Git-only. |
| 2 | Recency-aware recommendation | Completed and validated as feature data | Strict 30/90/365-day Git and prior-assignment features; not evaluated as a recommender. |
| 3 | Workload-aware recommendation | Partially completed | 228-history partial replay and a resolution sidecar; no total queue, severity weights, or workload evaluation. |
| 4 | Explainable recommendations | Implemented but not evaluated | Feature evidence and explanation utility exist; no real recommendation scores/explanations generated. |
| 5 | Cold-start handling | Partially completed | 206,990 zero-history scenarios, but newness unknown and no fallback source. |
| 6 | Adaptive feature selection | Implemented but not evaluated | Availability-aware utility and indicators; no project-data comparison. |
| 7 | Prediction confidence | Implemented but not evaluated | Calibration helper is tested; no fitted calibrator or probability is provided. |
| 8 | Duplicate and related-bug detection | Blocked | No historical text snapshots, TF-IDF/cosine features, related labels, or defensible negatives. |
| 9 | Top-K developer ranking | Implemented but not evaluated | Ranking utility and targets exist; no project-data ranking metrics. |

## Validation results

| Check | Result |
|---|---|
| Temporal variant SHA-256 and semantics | PASS: all three hashes equal; strict row reconstruction 432,198/432,198; no regeneration. |
| Existing point-in-time dataset and deterministic regeneration | PASS: 9/9 generated outputs byte-identical; source hashes match the existing preprocessing report. |
| Lifecycle event/coverage validator | PASS: 63,266 unique coverage bugs; 287,917 unique events; exact counts/references; zero invalid timestamps, pre-creation events, or orphans. |
| Partial workload validator | PASS: 299,214 snapshots, 33,246 coverage rows, 228 eligible source histories; strict cutoffs, identity, chain, labels, splits, and reproducibility checked. |
| Partial resolution activity | PASS: 299,214 rows; 225 verified-assignee resolution changes; strict cutoff and byte-for-byte regeneration. |
| Integrated dataset | PASS: 7 files reproduce byte-for-byte; candidate and evaluation keys, references, timestamps, labels, partial-scope indicators, and target separation checked. |
| Missingness and duplicate keys | PASS with documented source-semantic blanks: candidate Git recency 253,172, assignment recency 206,990; workload latest event/coverage 32,148 each when no eligible bugs are active; target IDs 29,177 outside pool; duplicate text time 1,810; no duplicate candidate, target, cold-start, duplicate-pair, identity, normalized-context, or resolution keys. Candidate-expanded context repeats exactly nine times per bug by design. |
| Context metadata | PASS: 33,246 unique normalized bug/cutoff records; export-time values explicitly prohibited as model inputs. The candidate-expanded copy is intentionally repeated across nine candidates and has a normalized equivalent. |
| Chronological/leakage checks | PASS for direct-assignment and Git features, strict workload cutoff, and historical duplicate IDs/creation ordering. Context timestamps and historical text snapshots remain unresolved, so those values are not model inputs. |
| Unit tests | PASS: 37 tests. |
| Python syntax check | PASS for the changed dataset scripts. |
| Training dataset validator | PASS: primary 33,246 and secondary 607 rows have unique IDs. Measured missingness: primary summary 2/description 215; secondary description 5. |

The existing JDT event scan report records source and output provenance.
New integration outputs were compared against deterministic temporary
regeneration. No raw JDT file was read while running these checks.

## Remaining blockers and model-training readiness

1. Reconcile replay mismatches and obtain reliable historical coverage before
   claiming complete workload.
2. Obtain timestamped historical text versions before project TF-IDF/cosine
   retrieval, related-bug labels, or negative-pair construction.
3. Resolve the 76 identity review rows only with reliable evidence; do not
   infer identities from names or treat Git contribution as assignment.
4. Obtain usable Platform/PDE Bugzilla history or another approved source.
5. Establish point-in-time component/severity/priority values before using
   the export-time context or same-component counts as model inputs.
6. Define candidate eligibility, label-tier treatment, insufficient-history
   policy, and held-out temporal evaluation before training.

**Model-training readiness: not ready for a final nine-feature model or
performance claim.** The current data supports cautious exploratory work on
strict historical assignment/Git evidence and explicitly partial workload.
Out-of-pool labels, provisional labels, uncertain identities, incomplete
workload, temporally unverified context, and absent historical text must be
handled as limitations rather than silently converted into negatives or
features.
