# Final Dataset Handover Report

**Historical snapshot:** Prepared on 2026-11-11 from the dataset audit then
available. In particular, its unit-test rerun status is historical, not the
result of the later code remediation; see the
[remediation report](../dataset_documentation/remediation_report.md) for that
separate verification. No dataset validation is implied by the code-test rerun.

**Project:** Explainable and Recency-Aware Intelligent Bug Assignment System
**Handover date:** 2026-11-11
**Prepared for:** Four-member implementation team
**Scope:** Dataset collection, preprocessing, validation, provenance, and documentation. No model training or evaluation was performed.

## Executive status

The existing JDT and Eclipse Git datasets have been audited against their documentation and actual local files. The handover provides a manifest with row counts, sizes, checksums, provenance, validation status, and sensitivity classification. Existing files are referenced in place; large data were not copied.

**Overall collection status: partially complete.** JDT Bugzilla and five local Git repositories are available. Platform/PDE Bugzilla data remain unavailable. **Preprocessing: completed for available inputs**, with partial workload and identity/text blockers clearly preserved. **Validation: completed for existing core outputs and actual processed CSV integrity**, with the unit test rerun blocked by missing `pytest`. **Documentation: completed** in this handover directory.

The full raw JDT export was not read, rescanned, or rehashed. Its recorded checksum is carried forward from the prior availability report; the current size matches. No original dataset was intentionally changed, and no model was trained or evaluated.

## Collection and file status

- Raw JDT Bugzilla source: `dataset/raw/JDT.csv`, **6,377,569,970 bytes**. The previously documented scan counted 63,266 unique bug IDs and extracted lifecycle evidence; this handover did not repeat the scan.
- Five local Git repositories: **183,742 commits** and **2,215,515 changed-path records** across JDT Core, Platform, SWT, UI, and PDE. The extracted commits and contributor identities are repository-scoped; Git is not Bugzilla assignment data.
- JDT primary/secondary training inputs: **33,246 primary rows** and **607 separate review rows**. Cleaned bug text contains 33,246 IDs but has no historical text-availability timestamps.
- Duplicate inputs: **10,875 source links**, **1,810 historical positive links**, and **9,366 family pairs**. No complete related/negative classification set exists.
- Partial workload: **299,214 developer/cutoff snapshots**, **33,246 coverage rows**, and **299,214 resolution-activity rows**, based on **228 eligible source histories**. It is not complete queue workload.
- Integrated tables: seven files under `dataset/processed/jdt_integrated/` with candidate features, repeated and normalized context, targets, cold-start scenarios, duplicate positives, and identity metadata.
- Processed file audit: **68 CSVs**, 6,773,047 rows including package copies/repeated rows, totaling **1,710,422,089 bytes**. Nine CSVs in `member1_dataset_files/` are exact package copies. The package ZIP is also a copy, not a new dataset.

Use [DATASET_INVENTORY.md](./DATASET_INVENTORY.md) and [dataset_file_manifest.csv](./dataset_file_manifest.csv) for per-file paths, exact row counts, sizes, and checksums.

The primary labels comprise 1,651 `known_entry` and 31,595 `provisional` rows; the separate secondary-review table comprises 33 `known_entry` and 574 `provisional` rows. The chronological bug split is 23,272 train, 4,987 validation, and 4,987 test bugs.

## Nine-feature dataset readiness

Readiness below describes data availability, not feature-model implementation or measured model quality. Exact input columns are documented in [DATA_DICTIONARY.md](./DATA_DICTIONARY.md).

| # | Feature | Available data and key columns | Preprocessing and missingness | Limitations | Next-stage readiness |
|---:|---|---|---|---|---|
| 1 | Historical expertise | `jdt_integrated_candidate_features.csv`: `developer_id`, `prior_direct_assignment_count`, `prior_same_component_direct_assignment_count`; JDT Git profile/temporal tables. | Nine verified identities; point-in-time direct-assignment and Git contribution evidence integrated. Low/zero histories remain explicit. | One of nine has no prior direct-assignment evidence across observed cutoffs; two have at most one. Git is not assignment expertise. | **Partially ready** for conservative JDT implementation; evidence coverage is narrow. |
| 2 | Recency | Integrated candidate fields `days_since_last_direct_assignment`, `days_since_last_contribution`, and 30/90/365-day commit/file counts; strict temporal file has 432,198 rows. | Strict cutoff reconstruction passed 432,198/432,198. Temporal variants share one hash and only strict semantics are established. | Git recency is contribution evidence. Some values are missing when no prior event exists; no recommender evaluation exists. | **Data ready for implementation** with strict cutoff and missingness rules. |
| 3 | Workload | Partial snapshots, coverage, resolution sidecar; integrated partial count/coverage fields. | 228 of the 4,542 candidate histories qualified strict seed/chain checks. Future events excluded; outputs marked `partial`. | Does not account for all bugs/queues; 13,427 history mismatches and 1,880 incomplete histories exist in the full evidence. No severity breakdown. | **Partially ready for exploratory integration only**; not complete workload. |
| 4 | Explainability | Candidate counts, history features, and per-feature status flags. | Evidence is separated and retained; no recommendation explanation output is present. | No actual recommendation scorer/explanation data. | **Inputs available; explanation implementation remains future work.** |
| 5 | Cold-start | 206,990 zero-prior-assignment scenarios; 254 JDT Git contributor keys and identity review files. | Evaluation scenarios prepared; identity evidence conservatively separated. | Genuine newness is unknown; unresolved identities remain; no supported fallback candidate source. | **Partially ready** for unknown-aware handling, not a confirmed new-developer evaluation group. |
| 6 | Adaptive feature selection | Per-feature availability/status columns in the integrated candidate table. | Availability indicators integrated. | No measured fixed-versus-adaptive comparison or selected-feature outcomes. | **Inputs available; adaptive comparison not evaluated.** |
| 7 | Prediction confidence | Candidate history/coverage evidence and `prediction_confidence_status`. | No confidence values or probabilities fabricated. | No calibration set or fitted calibration model. | **Not data-ready for calibration**; evidence inputs alone are not calibrated confidence. |
| 8 | Duplicate/related bugs | 1,810 evaluation-only positive pairs; cleaned text for 33,246 IDs. | Pair chronology and text-ID references validated. | No timestamped historical text, TF-IDF/cosine scores, related labels, or defensible negatives. | **Blocked** for leakage-safe retrieval; retain positives as targets only. |
| 9 | Top-K ranking | 299,214 candidate rows; 33,246 separate targets and bug-level splits. | Candidate/target separation and grouped chronological split validated. | 29,177 target labels are outside the conservative candidate pool; no ranking output or metrics. | **Data available for ranking implementation** with explicit coverage handling; no evaluation performed. |

## Validation evidence and audit findings

Rerun validators passed for integrated outputs, point-in-time outputs, partial resolution activity, lifecycle events, partial workload, strict temporal variants, and primary/secondary training data. The combined Git extraction's natural-key and reference checks passed in its existing report; extraction was not repeated. The detailed commands/results and audit scope are in [VALIDATION_RESULTS.md](./VALIDATION_RESULTS.md).

Actual CSV reads confirmed headers, row counts, blank cells, file sizes, and SHA-256 for all 68 processed CSVs. No malformed nonblank values were detected in timestamp-like columns. Exact-record duplication found:

- 265,968 repeated rows in the candidate-expanded context table by design; use the 33,246-row normalized context table.
- One exact duplicate row in the 14-row unclean exact-email candidate file; the original was preserved. The separate cleaned 13-row file has no exact duplicate rows.
- Nine packaging copies are byte-identical to their source CSVs.

The prior availability manifest matched current bytes, row counts, and SHA-256 for 37 previously listed processed CSV entries. The ZIP size and SHA-256 also match its prior entry. The raw JDT file size matches the prior record, but its SHA-256 was not recomputed to avoid reopening the 6.38 GB source.

The existing report says 37 unit tests previously passed. The unit test rerun in this audit did not start because `pytest` is absent from `.venv-sbert`; no dependencies were installed.

## Limitations and future collection/manual review

1. **Platform/PDE Bugzilla:** obtain usable official REST responses or an approved archive; verify provenance, completeness, terms, and privacy before collection. Existing four requests returned shutdown HTML. Do not substitute GitHub issues or commits for assignment histories.
2. **Workload:** investigate replay mismatches and obtain authoritative complete histories before claiming full queues. Do not impute absent bugs or zero workload from the partial cohort.
3. **Identity:** manually resolve only with reliable evidence. Keep four exact-email rows without Bugzilla IDs and 72 name candidates unresolved until reviewed; never merge by name alone.
4. **Historical text:** obtain timestamped text snapshots before retrieval, related-bug labels, or negative-pair preparation.
5. **Temporal context:** establish historical product/component/severity/priority values before using export-time metadata or same-component counts as model inputs.
6. **Evaluation policy:** define candidate coverage, label-tier treatment, insufficient-history policy, and temporal split protocol in a later implementation/evaluation phase. This handover does not run that phase.

See [KNOWN_LIMITATIONS.md](./KNOWN_LIMITATIONS.md) for safe-use rules and [PREPROCESSING_METHODOLOGY.md](./PREPROCESSING_METHODOLOGY.md) for methods and provenance.

## Source evidence

- [Dataset availability and prior file manifest](../dataset_documentation/dataset_availability.md)
- [JDT preprocessing validation](../dataset_documentation/jdt_preprocessing_validation_report.md)
- [JDT workload event scan](../dataset_documentation/jdt_workload_event_scan_report.md); a separate identity-linked replay-mismatch analysis remains local and is excluded from the proposed public release.
- [Temporal feature variant audit](../dataset_documentation/temporal_feature_variant_audit.md)
- [Platform Bugzilla availability probe](../dataset_documentation/eclipse_project_source_probe.md) and [bounded retry results](../dataset_documentation/bugzilla_retry_results.md)
- [Platform](../dataset_documentation/eclipse_platform_collection_report.md), [SWT](../dataset_documentation/eclipse_platform_swt_collection_report.md), [Platform UI](../dataset_documentation/eclipse_platform_ui_collection_report.md), and [PDE](../dataset_documentation/eclipse_pde_collection_report.md) Git collection reports
- [Combined Git extraction report](../../dataset/processed/cold_start/eclipse_all_repositories/eclipse_git_extraction_report.md)

## Team responsibilities

| Member | Proposed responsibility | Handover summary |
|---|---|---|
| Member 1 | Dataset collection, preprocessing, validation, documentation | **Completed for available sources and documented blockers.** New source collection remains gated on availability and approval. |
| Member 2 | Historical expertise and recency-based recommendation | Use strict candidate history and Git recency fields; preserve nine-identity scope and distinguish contribution from assignment. |
| Member 3 | Workload-aware scoring, cold-start, adaptive feature integration | Use partial workload and cold-start fields with `partial`/`unknown` semantics; do not infer total queues or newness. |
| Member 4 | Explainability, prediction confidence, duplicate/related-bug integration | Evidence inputs exist, but explanation and confidence outputs are absent; duplicate retrieval is blocked pending historical text/labels. |

Top-K ranking and overall integration are shared. Preserve candidate/target separation and keep candidate rows grouped by bug. Full input paths, columns, dependencies, and expected outputs are in [TEAM_HANDOVER_MATRIX.md](./TEAM_HANDOVER_MATRIX.md).

## Access and use instructions

1. Do not copy large source files; access the repository-local paths referenced in the inventory and manifest.
2. Begin with the integrated candidate table, then load targets and splits separately. Do not join targets into prediction-time features.
3. Prefer normalized context. Treat current/export-time context as ineligible until point-in-time provenance is established.
4. Keep identity metadata restricted; use opaque developer IDs outside approved identity review.
5. Keep partial workload in its own scope and carry unknown/missing status through downstream interfaces.
6. Run only the non-destructive validation commands listed in `VALIDATION_RESULTS.md`. Inspect legacy script behavior before any rerun.

## Final responsibility checklist

- Dataset collection: **Partially complete** — JDT and Git sources exist; Platform/PDE Bugzilla remains blocked.
- Preprocessing: **Completed for available sources; partial/blocked outputs are labeled**.
- Validation: **Completed for existing core datasets and file-level audit**; unit tests were not rerun because `pytest` is unavailable.
- Documentation and handover: **Completed** in `research/dataset_handover/`.
