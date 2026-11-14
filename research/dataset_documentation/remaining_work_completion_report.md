# Remaining Work Completion Report

Date: 2026-11-11

## 1. Tasks completed

- Inspected the existing dataset inventory, feature readiness audit, source
  probe, completion/extraction reports, project scaffold, script list, and
  relevant CSV headers. No raw JDT export was loaded or processed.
- Audited the 14,037 existing repository-aware identity-candidate rows and
  generated an unresolved, pair-deduplicated manual review file. Exact-email
  and exact-normalized-name queues are separate, with overlap visible.
- Generated repository-scoped identity cohort classifications for possible
  bots, possible service accounts, missing-email identities, candidate-linked
  authors, authors without cross-repository candidates, existing JDT clean
  exact-email evidence, and repositories without collected Bugzilla identity
  links. These are review classifications, not identity confirmations.
- Implemented reusable research utilities for cold-start policy, feature
  selection, evidence/confidence calibration support, score explanations,
  eligible Top-K ranking and metrics, strict point-in-time text retrieval and
  relation-classifier support, and point-in-time workload replay.
- Added architecture, data-contract, and evaluation-protocol documentation.
- Updated the project README, master dataset inventory, and nine-feature
  readiness audit to reflect the new utilities and the remaining evaluation
  gaps.

## 2. Tasks partially completed

- **Identity work:** candidate conflicts and heuristic cohorts are identified,
  but all 12,715 unique cross-repository candidate pairs remain unresolved.
  The existing 13 clean exact-email JDT mappings are noted only in their JDT
  context; no cross-repository identities were merged.
- **Cold start:** the policy distinguishes verified new developers,
  insufficient assignment evidence, unmatched Git contributors, and
  conflicting/incomplete records. No valid new-developer evaluation cohort
  or performance evaluation exists.
- **Confidence:** the module distinguishes qualitative evidence support from
  probabilities and supports held-out isotonic calibration. It was not fit to
  project predictions or evaluated on a test set.
- **Duplicate/related bugs:** point-in-time TF-IDF retrieval and a target-
  separate classifier interface are implemented. The classifier was only
  exercised on synthetic unit-test data; existing JDT pairs were not
  processed or used to train it.
- **Workload:** event replay is implemented and tested synthetically. No
  actual workload snapshot was derived from JDT assignment histories.

## 3. Tasks intentionally deferred to the JDT/Bugzilla phase

- No JDT raw CSV parsing, additional preprocessing, workload extraction, or
  new duplicate-pair processing was performed.
- No Platform/PDE Bugzilla request, retry, download, or data collection was
  performed. Existing source reports document shutdown HTML; product-level
  assignment labels and activity histories remain unavailable.
- No recommendation model was trained, no project-data probabilities were
  calibrated, and no model or feature performance metrics were computed.
- No API, frontend, or end-to-end recommendation integration was added.
- No identity review decisions were invented or prefilled.

## 4. New files created

**Reusable modules**

- `scoring_engine/cold_start/policy.py`
- `ml_model/feature_selection/adaptive.py`
- `scoring_engine/confidence/prediction_confidence.py`
- `scoring_engine/final_scoring/explainability.py`
- `ml_model/ranking/top_k.py`
- `bug_similarity/retrieval/point_in_time.py`
- `scoring_engine/workload/point_in_time.py`
- `scripts/prepare_eclipse_identity_review.py`

**Unit tests**

- `tests/unit/test_remaining_work_modules.py`
- `tests/unit/test_eclipse_identity_review.py`

**Documentation**

- `docs/architecture/remaining_work_architecture.md`
- `docs/methodology/data_contracts_and_features.md`
- `docs/methodology/evaluation_protocol.md`
- `research/dataset_documentation/remaining_work_completion_report.md`

**Additive identity-review outputs** under
`dataset/processed/cold_start/eclipse_all_repositories/identity_review/`

- `cross_repository_manual_review.csv`
- `exact_email_candidates.csv`
- `normalized_name_candidates.csv`
- `contributor_identity_cohorts.csv`
- `contributor_identity_cohorts_classified.csv`
- `identity_review_summary.md`
- `identity_review_queue_addendum.md`

The review CSVs contain personal identity information. Keep them access
restricted and do not publish their raw email/name fields.

## 5. Existing files modified

- `README.md` — current implementation status and unit-test command.
- `research/dataset_documentation/master_dataset_inventory.md` — added
  inventory entries/counts for the identity-review outputs.
- `research/dataset_documentation/eclipse_nine_feature_readiness.md` —
  updated feature readiness and remaining-work statements.

No existing dataset, repository, extraction script, raw JDT CSV, or Git
history was overwritten, deleted, or regenerated. The identity-review queue
files were newly created; the additive queue operation refuses to overwrite
an existing target.

## 6. Validation and test results

- Python syntax compilation passed for all new modules, scripts, and tests.
- Unit tests passed: **32 tests** using the repository’s available Python
  3.12 virtual environment. Tests cover cold-start boundaries, fixed/adaptive
  scoring and leakage guards, calibration split checks, explanation
  arithmetic, eligible Top-K ranking and metrics, point-in-time bug/text
  filtering, relation-target separation, chronological workload events, and
  identity-review classifications.
- Identity review validation:
  - 14,037 source candidate rows became 12,715 unique unresolved pairs.
  - Exact-email queue: 1,353 pairs.
  - Exact-normalized-name queue: 12,684 pairs.
  - Overlap: 1,322 pairs.
  - 31 exact-email pairs have no exact normalized-name match.
  - 12,576 pairs involve an identity with multiple candidate links.
  - Cohort outputs contain 7,332 unique repository-scoped contributors.
  - 37 possible-bot and 45 possible-service-account heuristic flags;
    5,349 missing-email identities; 1,149 identities with no
    cross-repository candidate link; 13 JDT clean mapping evidence rows;
    7,078 non-JDT contributor identities without Bugzilla linkage in the
    collected local evidence.
- The identity cohorts and manual review CSVs use existing derived Git
  contribution data only. No raw Bugzilla rows were parsed.
- `git diff --check` passed for tracked changes. The new generated dataset
  outputs remain covered by existing `dataset/processed/*` ignore rules.

All unit-test cases use small synthetic data. Passing tests validate utility
behavior, not research effectiveness or model quality.

## 7. Known limitations

- Cross-repository identity candidates are exact normalized name/email
  signals only; neither establishes personhood. Service-account and bot
  markers can produce false positives.
- Git commit/path activity is not a Bugzilla assignment, bug expertise label,
  active workload value, or proof of assignment eligibility.
- Cold-start fallback and adaptive scoring rules are scaffolding that require
  policy review and temporal experiments before production use.
- Confidence is uncalibrated unless fit on a separate approved calibration
  period and subsequently evaluated. The utility test is not a calibration
  result.
- Duplicate/related classifier inputs, label definitions, negative sampling,
  duplicate-family grouping, and evaluation split remain to be designed with
  approved data. The existing 1,810 historical-available pairs are not a
  complete positive/negative dataset.
- Workload replay requires complete event history and an agreed definition of
  active status/severity weighting. No actual workload values were created.
- Application/API/frontend integration and user-facing privacy controls are
  not implemented.

## 8. Exact next steps for the JDT/Bugzilla phase

1. Review and manually adjudicate candidate identity pairs in
   `cross_repository_manual_review.csv`. Record evidence, reviewer, UTC time,
   and decision. Do not merge on name similarity alone.
2. Obtain approval for any further JDT/Bugzilla processing. Before Platform
   or PDE collection, separately confirm service availability, product and
   component metadata, source terms, privacy constraints, and an approved
   collection scope. Do not retry the old probe without approval.
3. On an approved small sample, validate Bugzilla event types, timestamps,
   assignment/reassignment/closure semantics, identity fields, history
   completeness, and target-label policy. Preserve primary and weaker label
   tiers separately.
4. Only after schema and policy validation, derive assignment-event snapshots
   and workload at strict prediction cutoffs. Validate snapshots against
   manually audited bugs; do not infer workload from Git commits.
5. Build project-scoped assignment expertise and recency features using only
   evidence strictly before bug creation/prediction time. Preserve JDT’s
   existing source files and reconcile temporal-variant provenance before
   selecting a preferred feature table.
6. Prepare time-safe duplicate and related-bug pairs with explicit
   point-in-time text availability, duplicate-family grouping, and a
   defensible negative-sampling plan. Keep final resolution as a target only.
7. Freeze chronological train/validation/calibration/test splits. Group
   duplicate families across splits where applicable; prevent identity or
   future-event leakage.
8. Compare fixed and adaptive scoring on the same held-out candidate sets.
   Report coverage and per-project results alongside ranking metrics.
9. Fit confidence calibration only on a separate calibration period; report
   calibration metrics on an untouched test period.
10. Evaluate Top-1/3/5 with Precision@K, Recall@K, and MRR, and evaluate
    duplicate retrieval/classification separately from developer ranking.
    Record data provenance, label tier, cutoff policy, and limitations.
11. Integrate the validated modules into the backend/API and UI only after
    model and privacy requirements are approved.

## 9. Nine-feature status

Statuses describe implementation/readiness, not research success.

| # | Feature | Status | Evidence and remaining gap |
|---:|---|---|---|
| 1 | Historical developer expertise | **Partially completed** | JDT assignment profiles and 13 clean exact-email mappings exist; all five Git histories are processed. Platform/PDE assignment labels and model evaluation are missing. |
| 2 | Recency-aware recommendation | **Partially completed** | Existing JDT temporal feature tables and Git timestamps exist. Identity coverage/provenance needs review; no integrated evaluated model. |
| 3 | Workload-aware scoring | **Implemented but not evaluated** | Event-driven cutoff replay is implemented/tested; actual assignment-history processing is deferred. |
| 4 | Explainable recommendations | **Implemented but not evaluated** | Score-decomposition and evidence output are implemented/tested; no real recommendation integration or explanation audit. |
| 5 | Cold-start handling | **Implemented but not evaluated** | Policy distinguishes new, unmatched, insufficient-history, and review outcomes; no verified new-user test cohort or evaluation. |
| 6 | Adaptive feature selection | **Implemented but not evaluated** | Missingness/quality-aware scoring and fixed-mode comparator are implemented/tested; no temporal comparison. |
| 7 | Prediction confidence | **Implemented but not evaluated** | Evidence summary and held-out calibration helper are implemented/tested; no project calibration fit or test. |
| 8 | Duplicate and related bug detection | **Implemented but not evaluated** | Strict point-in-time TF-IDF retrieval and target-separated classifier interface are implemented/tested synthetically; no project training/evaluation. |
| 9 | Top-K developer ranking | **Implemented but not evaluated** | Eligibility-guarded ranker and Precision@K/Recall@K/MRR functions are implemented/tested; no real-data metrics. |
