# Eclipse Nine-Feature Readiness Audit

Assessment date: 2026-11-11

## Status definitions

- **Collected:** source material is present locally.
- **Processed:** structured data has been derived from a source.
- **Engineered:** a feature table or explicit model feature has been produced.
- **Model implemented:** a model/scorer using the feature exists.
- **Evaluated:** the feature/model has been measured on a valid held-out
  evaluation.

The status below separates these stages. Collected Git commits do not by
themselves establish recommendation features, assignment labels, or model
quality.

## Readiness matrix

| Feature | JDT | Platform, SWT, UI | PDE | Current conclusion |
|---|---|---|---|---|
| 1. Historical developer expertise | JDT assignment profiles and strict Git evidence; 9 exact-email mappings meet the conservative one-user audit. | Git commit/path evidence and repository-scoped author rosters; no Bugzilla assignment labels. | Same Git-only evidence; no Bugzilla assignment labels. | **Partially completed:** evidence for nine identities. One has no prior direct-assignment history across observed cutoffs and two have at most one; no sufficiency threshold or project-data ranker was evaluated. Git is not assignment expertise. |
| 2. Recency-aware recommendation | 432,198 strict temporal rows for 13 source-map identities; 299,214 candidate rows use 9 conservative identities. All three named variants are byte-identical; strict reconstruction passes. | Git timestamps/paths processed; no linked assignment-time features or evaluation. | Git timestamps/paths processed; no linked assignment-time features or evaluation. | **Completed and validated as feature data; not evaluated as a recommender.** |
| 3. Workload-aware scoring | 299,214 partial snapshots, 33,246 cutoff coverage rows, 228 eligible histories; separate 299,214-row resolution-activity sidecar attributes 225 observed changes to verified assignees. | No assignment events/queue state. | No assignment events/queue state. | **Partially completed:** cutoff and reproduction checks pass. Not total queue coverage; 13,427 mismatches, 1,880 incomplete histories, and other bugs are absent. Severity breakdown unsupported. |
| 4. Explainable recommendations | Raw historical evidence and workload coverage are integrated; no integrated recommendation scorer. | No assignment inputs. | No assignment inputs. | **Implemented but not evaluated:** utility and feature evidence exist, but no real recommendation explanation/scorer is produced. |
| 5. Cold-start handling | 254 repository-scoped keys; 9 conservative mappings, 19 unresolved name candidates, 226 keys without verified Bugzilla identity; 206,990 zero-prior-assignment scenarios. Genuine newness is unknown. | Contributor identity cohorts and manual candidates prepared; no Bugzilla linkage. | Same limitation. | **Partially completed:** evaluation groups prepared; no confirmed new-developer cohort or supported fallback source. Git-only contributors are not assignment candidates. |
| 6. Adaptive feature selection | Feature availability indicators are in the integrated data; no measured comparison. | Git evidence only. | Git evidence only. | **Implemented but not evaluated:** utility is unit-tested; no project-data comparison was run. |
| 7. Prediction confidence | No real calibration set; integrated data states `uncalibrated_no_probability`. | No assignment labels. | No assignment labels. | **Implemented but not evaluated:** helper is tested, but no project calibrator or probability is fit or claimed. |
| 8. Duplicate and related bug detection | 1,810 historical duplicate positives are target-only; source-text IDs and chronology pass. No text snapshot time is available. | No bug/duplicate data. | No bug/duplicate data. | **Blocked:** no project TF-IDF/cosine features, related-pair labels, or defensible negatives. Current text could contain post-cutoff edits. |
| 9. Top-K developer ranking | 33,246 targets are separate from 299,214 candidate rows; 4,069 labels fall in the conservative pool and 29,177 are outside. | Git histories only; no assignment labels. | Git histories only; no assignment labels. | **Implemented but not evaluated:** ranking utility is unit-tested; no project-data metrics or ranker evaluation. |

## Integrated JDT dataset

`scripts/build_jdt_integrated_dataset.py` produces seven reproducible tables in
`dataset/processed/jdt_integrated/`: candidate features (299,214 rows),
candidate-expanded bug-context metadata (299,214) and its normalized
bug-level equivalent (33,246), assignment targets (33,246), cold-start
evaluation scenarios (206,990), duplicate evaluation pairs (1,810), and
verified identity metadata (9). Candidate features have no target or raw
identity fields. The context table retains exported product/component/
severity/priority values but marks them as temporally unverified and
ineligible as model inputs; prefer the normalized context table. The partial
resolution-activity sidecar is in
`dataset/processed/jdt_workload_partial/jdt_partial_resolution_activity.csv`
and joins on prediction bug, cutoff, and developer.

Feature readiness flags do not represent scores. Explainability has evidence
but no generated explanation; adaptive selection has availability indicators
but no comparison; confidence remains uncalibrated; duplicate/related
retrieval is blocked; Top-K candidates are not ranked. Same-component
assignment counts are retained for audit but component-at-cutoff timing is
unverified.

## Repository state

All five Git repositories are present and reported non-shallow locally:

| Repository | Commits across local refs | Collection status | Contribution processing status |
|---|---:|---|---|
| `eclipse.jdt.core` | 32,484 (availability report) | Present; partial `blob:none` history, unusual checkout artifacts noted | Existing JDT files preserved; separate combined extraction has 32,484 commit rows and 312,493 changed-path rows |
| `eclipse.platform` | 46,304 | Collected and validated | Combined extraction has 46,304 commits and 392,472 changed-path rows |
| `eclipse.platform.swt` | 35,391 | Collected and validated | Combined extraction has 35,391 commits and 326,899 changed-path rows |
| `eclipse.platform.ui` | 48,171 | Collected and validated | Combined extraction has 48,171 commits and 884,467 changed-path rows |
| `eclipse.pde` | 21,392 | Collected and validated | Combined extraction has 21,392 commits and 299,184 changed-path rows |

The combined extraction also has 7,332 repository-scoped Git author keys,
7,332 identity-review rows, and 14,037 candidate evidence rows. A separate
identity review preparation deduplicates these to 12,715 unresolved pairs:
1,353 exact-email queue entries and 12,684 exact-normalized-name queue
entries, with 1,322 pairs in both. The queues are candidate evidence, not
verified people or assignment candidates. See
[`identity_review`](../../dataset/processed/cold_start/eclipse_all_repositories/identity_review/)
for separate queues, conflict markers, cohorts, and review fields. The
extraction counts and validation are in
[`eclipse_git_extraction_report.md`](../../dataset/processed/cold_start/eclipse_all_repositories/eclipse_git_extraction_report.md).

JDT Bugzilla is the only project source here with existing issue labels and
activity data. The four non-JDT repositories provide Git contributions, not
Platform/PDE bug-report text, assignee history, workload, or duplicate links.
The existing Bugzilla reports say the Platform/PDE REST requests received
shutdown HTML.

## Required next data work

1. **Completed:** generate the repository-aware contribution dataset from
   local Git refs; preserve existing JDT CSVs and keys as-is.
2. Keep developer identities repository-scoped. Candidate records and bot
   heuristics must be review states, never assignment labels.
3. If Platform/PDE recommendation labels are later required, collect approved
   bug and assignment-history sources separately; Git alone cannot supply
   those labels.
4. Expand reliable JDT lifecycle-history coverage and reconcile replay
   mismatches before making stronger workload claims. Existing partial
   snapshots may only be used with their partial-scope indicators and strict
   point-in-time cutoff semantics; do not treat them as complete workload.
5. **Implemented as reusable utilities, not experimentally validated:**
   scoring, ranking, explanations, adaptive selection, confidence calibration
   interface, point-in-time retrieval, workload event replay, and cold-start
   policy. Follow the temporal evaluation protocol before claiming any model
   result.

No recommendation model was trained, no project-data confidence calibration
was fit, and no feature or ranking evaluation was performed. The new unit
tests validate utility behavior only.

## Current preprocessing evidence

- The JDT source exact-email map has 13 rows. The conservative audit finds 9
  unique Bugzilla user IDs with matching JDT roster emails; 4 mappings have
  no Bugzilla user ID in the available identity audit. No multi-user email
  mapping was found. The original source map was not edited.
- The integrated input table has 299,214 rows (33,246 bugs × 9 currently
  verified candidates). Candidate eligibility is explicitly point-in-time:
  92,224 rows have prior direct-assignment evidence; 206,990 have none.
- Targets are separate: 4,069 resolve to the conservative candidate pool;
  29,177 remain outside it. There are 1,651 `known_entry` and 31,595
  `provisional` labels overall. Do not treat out-of-pool labels as negatives
  or pool tiers as equally certain.
- Chronological bug split: 23,272 train, 4,987 validation, 4,987 test.
  Candidate rows remain grouped by bug via the separate split table.
- The 206,990 cold-start scenarios are retrospective and identity-verified
  using the current audit. They do not prove developers were genuinely new
  at those cutoffs, and no valid fallback candidate source is available.
- The new 1,810 duplicate-positive audit contains no negatives. As historical
  text availability is unknown, it is not retrieval-model-ready.
- One approved read-only scan of `dataset/raw/JDT.csv` processed 63,266 bug
  rows and 287,917 lifecycle changes. Replay matched 47,959 rows; 13,427
  mismatched and 1,880 were incomplete/not testable. The event and coverage
  files pass structural, timestamp, uniqueness, count, and referential
  validation.
- A separate experimental partial workload now uses only 228 histories from
  the replay-clean verified-assignment subset after strict state-seed, event
  chain, and final product/status checks. It contains 299,214 developer
  snapshots and 33,246 cutoff coverage rows; all rows are marked partial and
  exclude target labels. The standalone validator passes strict no-future
  checks, identity and split checks, event-chain validation, and byte-for-byte
  regeneration. This is not a reconstruction of actual total developer
  workloads; severity counts are omitted because safe baseline severity is
  unavailable.
- The 9 point-in-time CSVs reproduce byte-for-byte in temporary staging; source
  input hashes match the validation report. Total output size is 73,640,886
  bytes and existing processed-data ignore rules apply.
- The previously documented bounded four-request Platform/PDE Bugzilla check
  returned HTTP 200 with `text/html` temporary-shutdown HTML and invalid REST
  JSON. No Platform/PDE bug data was collected or retried in this execution.

See
[`jdt_preprocessing_validation_report.md`](./jdt_preprocessing_validation_report.md)
for file paths, hashes, row counts, missingness, and validation details.
