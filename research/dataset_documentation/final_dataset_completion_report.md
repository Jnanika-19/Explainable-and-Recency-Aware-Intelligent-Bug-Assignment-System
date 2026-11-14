# Final Dataset Completion Report

Project: Explainable and Recency-Aware Intelligent Bug Assignment System

Assessment date: 2026-11-11

## Final remaining-work checklist

- [x] Inspect existing inventory, readiness, source probe, collection reports,
  processing scripts, and derived input schemas. Existing JDT and Git artifacts
  were preserved.
- [x] Resolve temporal-feature checksum discrepancy and validate strict cutoff
  semantics without regenerating the original files.
- [x] Audit exact-email and normalized-name identity evidence; create a
  conservative verified map and unresolved review files. No name-only identity
  merges were made.
- [x] Reuse the previously collected lifecycle evidence to generate
  experimental partial workload snapshots from the authorized 4,542-bug
  replay-clean verified-assignment cohort. Strict seed/chain checks retained
  228 source bugs; outputs are explicitly partial, not complete queue sizes.
- [x] Add a separate, strictly cutoff-filtered resolution-event activity
  sidecar using only verified assignees; preserve the original partial
  workload files.
- [x] Audit the 1,810 historical duplicate positives and their chronology.
- [ ] Complete duplicate/related retrieval. Historical text availability is
  unknown; no project TF-IDF vectors, cosine scores, related-pair labels, or
  negative examples were fabricated.
- [x] Prepare repository-aware contributor cohorts and historical cutoff
  cold-start scenarios. Genuine newness remains unknown; no unsupported
  fallback recommendation was invented.
- [x] Build the integrated JDT candidate dataset with explicit feature
  availability/readiness flags and separate target, context, identity, and
  evaluation-only tables.
- [x] Confirm Platform and PDE Bugzilla remain unavailable from the documented
  bounded requests. No retry or bulk request was made.
- [x] Run structural, temporal, identity, referential, leakage, output
  integrity, deterministic reproduction, and unit-test validation.
- [x] Update the master inventory, nine-feature readiness audit, and final
  validation report.
- [ ] Train or evaluate the final model. This remains deliberately deferred.

## Summary

All feasible safe preprocessing for the available local evidence is complete.
No new collection or scan of the original raw JDT export was performed in this
execution. Existing raw JDT data, source mappings, temporal files, duplicate
datasets, Git repositories, and previous extraction outputs were preserved.
New integration outputs are reproducible and refuse overwrite; the workload
and resolution sidecar remain explicitly partial. Generated datasets remain
under the existing `dataset/processed/*` ignore rule.

No recommendation model was trained. The current artifacts are not a
complete, evaluation-ready implementation of all nine features.

## Completed findings and outputs

### Temporal checksum discrepancy

The base, strict, and inclusive temporal CSVs are each 46,318,635 bytes with
the same SHA-256:

`d9bdf8eeea6ce11d583cbe33dc3d390563a209b2d6d756a4b7d8623f3cd8c622`

The existing generator creates the strict file and uses a strict
`committer_timestamp < bug_creation_time` cutoff. Its output was reconstructed
from existing processed inputs: 432,198 of 432,198 rows matched. The files are
byte-identical copies; there is no evidence that the base and inclusive names
represent separate semantics. Originals were left unchanged.

### Identity audit

- Existing exact-email source map: 13 rows; preserved unchanged.
- Conservative map: 9 rows with a single audited Bugzilla user ID, matching
  JDT roster email, and no existing bot/service heuristic flag.
- Four exact-email entries have no Bugzilla user ID in the available identity
  audit. No multi-user mapping was found. These entries remain unresolved.
- Normalized-name candidates remain review-only. The new unresolved queue has
  76 rows: 72 name candidates plus 4 exact-email entries without user-ID
  evidence. Reviewer decisions remain blank.
- The JDT Git contributor cohort has 254 repository-scoped keys. Its statuses
  include 9 conservatively verified mappings, 19 unresolved name-candidate
  keys, and 226 keys without a verified Bugzilla identity. These classes do
  not establish that a developer is new or is an assignment candidate.

### Point-in-time JDT features and labels

| Output | Rows | Purpose and validation |
|---|---:|---|
| `dataset/processed/jdt_point_in_time/jdt_candidate_features.csv` | 299,214 | 33,246 bugs × 9 currently verified developers. Contains bug metadata, strictly prior Git activity, and prior direct-assignment counts/recency. Targets and raw identity values are excluded. |
| `dataset/processed/jdt_point_in_time/jdt_assignment_targets.csv` | 33,246 | Evaluation-only labels. 4,069 map into the conservative candidate pool; 29,177 remain outside it and have no target developer ID. |
| `dataset/processed/jdt_point_in_time/jdt_bug_splits.csv` | 33,246 | Bug-level chronological split: 23,272 train, 4,987 validation, 4,987 test. Candidate rows stay together by bug. |
| `dataset/processed/jdt_point_in_time/jdt_cold_start_scenarios.csv` | 206,990 | Bug/developer cutoffs with zero prior direct-assignment history. Every genuine-new-developer value is `unknown`; Git activity is not assignment evidence. |

Of the candidate feature rows, 92,224 have prior direct-assignment evidence
and are marked point-in-time eligible; the remaining 206,990 are not. Target
labels retain their existing tiers: 1,651 `known_entry` and 31,595
`provisional`. Keep those tiers distinct during evaluation. Out-of-pool labels
must not be treated as negatives.

Expected missingness is documented: assignment recency is blank for the
206,990 zero-history rows; Git recency is blank for 253,172 rows with no prior
contribution; target IDs are blank for the 29,177 out-of-pool labels.

### Workload and duplicate/related data

- A single approved read-only streaming scan processed all 63,266 rows in
  `dataset/raw/JDT.csv`, finding 287,917 tracked lifecycle changes. It wrote
  `dataset/processed/jdt_workload/jdt_assignment_lifecycle_events.csv`
  (287,917 rows) and
  `dataset/processed/jdt_workload/jdt_bug_history_coverage.csv` (63,266
  rows). The raw source size and last-write time were unchanged.
- Final state replay matched 47,959 bugs, mismatched 13,427, and could not
  test 1,880 because histories were empty/invalid. There were 45 source
  history events before bug creation, zero invalid event timestamps, zero
  duplicate bug IDs, and zero malformed CSV rows. The extracted-event
  validator passed: no invalid timestamps, duplicate event keys, orphan
  events, count mismatches, or exported events before creation.
- Experimental partial workload is available at
  `dataset/processed/jdt_workload_partial/`: 299,214 developer/cutoff
  snapshots and 33,246 cutoff coverage rows. It uses 228 histories after
  strict product/status/assignee seed, chain, and final-state checks from the
  authorized 4,542-bug replay-clean verified-assignment cohort. The other
  4,314 source candidates were excluded for missing state seeds or broken
  chains. Every row has `workload_scope=partial`; total queues, severity
  weights, and absent bugs are not inferred.
- `jdt_partial_resolution_activity.csv` adds 299,214 partial snapshots of
  resolution changes attributed only to verified assignees. It records 225
  qualifying changes across the observed subset, strictly before cutoff.
  Resolution events are activity evidence, not complete workload or labels.
- No complete workload is available: the full histories include 13,427
  replay mismatches and 1,880 incomplete/not-testable records. Partial data is
  suitable only for explicitly labeled exploratory experiments.
- Summary/description change metadata appeared 21,397 times, with both old
  and new value fields present; text values were not exported, and historical
  text snapshots remain unavailable.
- The 1,810-row duplicate-positive audit is in
  `dataset/processed/jdt_duplicate_retrieval/jdt_duplicate_positive_pairs_audit.csv`.
  Pair keys are unique, both bug IDs exist in the cleaned-text ID set, and
  every original bug predates its duplicate. Duplicate labels are explicitly
  evaluation targets only.
- No related-bug pairs, negatives, TF-IDF vectors, or cosine scores were
  generated. The cleaned text does not include a per-version availability
  timestamp, so using current text as historical input could leak future
  information.

### Integrated JDT feature dataset

The reproducible generator `scripts/build_jdt_integrated_dataset.py` writes
seven files under `dataset/processed/jdt_integrated/`:

| Output | Rows | Purpose |
|---|---:|---|
| `jdt_integrated_candidate_features.csv` | 299,214 | Strict historical assignment/Git evidence plus partial workload fields and per-feature availability/readiness indicators. Targets and raw identity values are excluded. |
| `jdt_integrated_bug_context_metadata.csv` | 299,214 | Export-time context repeated per candidate, marked temporally unverified and ineligible as model inputs; retained without overwriting. |
| `jdt_integrated_bug_context_by_bug.csv` | 33,246 | Normalized one-row-per-bug/cutoff context table; use this instead of the repeated form. Context remains temporally unverified and ineligible as model input. |
| `jdt_integrated_targets.csv` | 33,246 | Assignment labels and event timestamps, separate from candidate features. |
| `jdt_integrated_cold_start_evaluation.csv` | 206,990 | Evaluation-only zero-history scenarios, including any first assignment after cutoff; genuine newness remains unknown. |
| `jdt_integrated_duplicate_evaluation_pairs.csv` | 1,810 | Historical duplicate positives as evaluation-only targets; no retrieval scores or negatives. |
| `jdt_integrated_developer_identity_metadata.csv` | 9 | Verified JDT identity metadata; separate from predictors and restricted to local research use. |

Same-component assignment counts are retained with an explicit unverified
component-timestamp status and must not be used as time-safe model inputs
until component-at-cutoff evidence is established. The integrated table
does not manufacture explainability scores, adaptive scores, confidence
probabilities, duplicate similarities, or Top-K ranks. The separate
resolution-event sidecar can be joined by bug, cutoff, and developer keys.

### Platform and PDE Bugzilla availability

The previously documented bounded availability check made four requests:
product metadata and a one-record metadata-only probe for each product, using
a 25-second timeout:

| Product | Endpoint | Result |
|---|---|---|
| Platform | `https://bugs.eclipse.org/bugs/rest/product/Platform` | HTTP 200, `text/html`, temporary-shutdown HTML, invalid REST JSON |
| PDE | `https://bugs.eclipse.org/bugs/rest/product/PDE` | HTTP 200, `text/html`, temporary-shutdown HTML, invalid REST JSON |
| Platform minimal bug metadata | `https://bugs.eclipse.org/bugs/rest/bug?product=Platform&limit=1&include_fields=id,product,component` | HTTP 200, `text/html`, temporary-shutdown HTML, invalid REST JSON |
| PDE minimal bug metadata | `https://bugs.eclipse.org/bugs/rest/bug?product=PDE&limit=1&include_fields=id,product,component` | HTTP 200, `text/html`, temporary-shutdown HTML, invalid REST JSON |

All four returned HTTP 200 with `text/html` temporary-shutdown pages and invalid
REST JSON. No further requests, bulk downloads, bug records, or Platform/PDE
collections were made during this execution. The source remains unavailable.
Potential future alternatives require
independent provenance, completeness, terms/privacy review, and approval; Git
history or GitHub issues are not substitutes for Bugzilla assignment labels.

## Validation and reproducibility

`scripts/prepare_jdt_point_in_time_datasets.py` generates the new CSVs and
refuses to overwrite any existing output. Its `--validate-existing` mode
rebuilds the outputs in a temporary directory, validates the existing files,
compares source hashes, and checks deterministic output without rewriting the
generated datasets.

Results:

- Python AST syntax validation passed. Pylance syntax/diagnostic requests
  timed out, so no Pylance type-diagnostic result is claimed.
- `scripts/validate_jdt_workload_outputs.py` passed: 63,266 unique coverage
  bug IDs, 287,917 unique event keys, exact agreement with coverage change
  counts, no invalid timestamps, no pre-creation exported events, and no
  orphan events.
- Blank values were measured, not imputed: `current_resolution` is blank in
  4,646 coverage rows; `old_value` is blank in 63,896 events and `new_value`
  in 7,894. Blank entries may be valid empty/cleared values or missing source
  values and need field-level interpretation.
- The initial 9/9 JDT point-in-time CSVs reproduced byte-for-byte in temporary staging.
- Source hashes match the recorded values in
  `research/dataset_documentation/jdt_preprocessing_validation_report.md`.
- Candidate bug/developer keys, target bug IDs, split bug IDs, and duplicate
  pair IDs are unique; candidate coverage is exactly 9 rows per bug.
- Target references, timestamp ordering, strict temporal windows, split
  chronology, zero-history classifications, duplicate chronology, and
  source-text ID references passed.
- Those 9 point-in-time CSVs occupy 73,640,886 bytes (about 70.2 MiB).
- Temporal variants were rechecked: hashes are identical and the strict
  reconstruction matches 432,198/432,198 rows.
- Partial workload validation passed after deterministic regeneration:
  299,214 snapshots, 33,246 coverage rows, and 228 eligible source histories.
- Partial resolution activity validation and byte-for-byte regeneration
  passed for 299,214 snapshots.
- Integrated dataset validation and deterministic regeneration passed for
  all 7 outputs (299,214 candidate rows, 33,246 normalized contexts and
  targets, 206,990
  cold-start rows, 1,810 duplicate evaluation pairs, 9 identity rows).
- All 37 unit tests passed using the project environment with scikit-learn
  available.
- `scripts/validate_training_dataset.py` passed: primary 33,246 and secondary
  607 rows had unique bug IDs; missing summary/description values were
  measured and not imputed.
- Platform/PDE endpoint status was not re-probed; the bounded shutdown-page
  responses already documented in `bugzilla_retry_results.md` were reused.
- Existing source files and original datasets remain unchanged.

For detailed hashes, row counts, missingness, and validation rules, see
[`jdt_preprocessing_validation_report.md`](./jdt_preprocessing_validation_report.md).

## Nine-feature readiness

| Feature | Data status | Processing/model/evaluation status |
|---|---|---|
| Historical developer expertise | JDT assignment profiles, 9 conservative identity links, Git contribution evidence | Processed candidate features; no trained/evaluated recommender. Platform/PDE have Git-only evidence. |
| Recency-aware recommendation | Strict Git contribution features and prior assignment-event recency | Engineered in candidate features; no recommendation evaluation. |
| Workload-aware scoring | Partial JDT active-bug, assignment/reassignment, terminalization/reopen, and resolution activity evidence; 228 source histories | Partially completed, strictly validated, and not a complete queue; no project-data workload evaluation. |
| Explainable recommendations | Raw historical evidence and workload coverage joined in integrated candidate rows; reusable explanation utility | Implemented inputs only; no real recommendation explanation or scorer evaluated. |
| Cold-start handling | 206,990 zero-prior-assignment scenarios and repository-scoped Git cohorts | Genuine newness unknown; no supported fallback candidate source or cold-start evaluation. |
| Adaptive feature selection | Feature families and reusable adaptive scoring utility | No project-data comparison or evaluation. |
| Prediction confidence | Identity and history evidence; reusable calibration helper | No fitted confidence model or calibration evaluation. |
| Duplicate/related detection | 1,810 historical positive targets, separated into evaluation-only output | Retrieval blocked by missing historical text snapshots; no TF-IDF, cosine, related labels, justified negatives, or project evaluation. |
| Top-K developer ranking | Separated candidate features and assignment targets | Ranking utility exists; no project-data ranking metrics or evaluated ranker. |

## Remaining gates before model training

1. **Workload:** investigate why 13,427 event histories fail current-state
   replay and whether the 1,880 incomplete/not-testable histories can be
   resolved from an approved authoritative source. Existing snapshots are
   experimental partial-scope evidence only. Do not represent them as total
   queues or repeat the full raw scan without approval.
2. **Identity:** manually resolve the 76-row review queue only with reliable
   evidence. Do not merge on names alone; preserve repository scope and the
   four exact-email entries without a Bugzilla ID as unresolved unless new
   evidence is supplied.
3. **Platform/PDE:** wait for valid REST JSON or an approved, provenance- and
   terms-checked archive. Request approval before any large collection.
4. **Duplicate/related:** establish text-at-cutoff evidence and an eligible
   historical retrieval corpus before constructing TF-IDF features or
   negatives. Keep final duplicate links as evaluation targets only.
5. **Evaluation:** define candidate eligibility and use label tiers
   deliberately; split by bug and time, preserve all candidate rows per bug,
   report coverage outside the nine-developer pool, and evaluate each feature
   with held-out project data before claiming completion.

## Operation boundaries

- A prior approved streaming read of the raw JDT export is documented; it was
  not repeated in this execution. No network download was performed.
- No original dataset was regenerated, deleted, or overwritten. New derived
  lifecycle-evidence and coverage outputs were created in previously absent
  paths.
- No existing Git repository, source mapping, or training dataset was changed.
- No commit or push was created.
- The prior bounded Platform/PDE availability check made four read-only
  requests as documented above; no network requests were made in this final
  execution.
