# JDT Identity and Point-in-Time Preprocessing Validation

Generated: 2026-11-11 11:44:07Z

## Results

- Identity audit: 13 exact-email map rows, 9 conservatively verified mappings, 0 ambiguous multi-user emails, and 76 unresolved review rows.
- Contributor cohort: 254 repository-scoped JDT Git keys; Git contributors are not treated as assignment candidates.
- Point-in-time candidate features: 299214 rows for 33246 bugs and 9 conservatively verified developers.
- Prior-assignment eligible candidate rows: 92224; the remainder have no prior direct-assignment evidence at cutoff.
- Targets: 4069 target labels in the verified pool; 29177 outside it.
- Cold-start scenarios: 206990 candidate/cutoff rows with zero prior direct assignments. They are marked `genuinely_new_developer=unknown`.
- Historical duplicate positives: 1810 unique positive pairs; no negatives were invented and no TF-IDF was generated.

## Validation

- Unique exact-email mapping, verified developer, bug/developer, and bug split keys: PASS.
- Every candidate feature row is strictly before the bug prediction cutoff: PASS by strict temporal source and event-time bisect.
- Assignment history uses only direct `assignment_added` events whose timestamps are before the bug cutoff; this is an observed-history proxy, not a complete lifecycle history.
- Candidate rows remain grouped by bug in the separate chronological 70/15/15 split file: PASS.
- Nonnegative temporal counts and recency, target/feature separation, and cold-start classification checks: PASS.
- Original duplicate pair chronology and bug text referential coverage: PASS.
- Duplicate target fields are evaluation-only; text snapshot timing is unavailable, so retrieval-ready is false: PASS.
- Source files were hashed before processing and remained unchanged: PASS.
- Expanded integrity checks (complete candidate coverage, target references and cutoff order, split chronology, cold-start references, and nested temporal windows): PASS.
- Deterministic regeneration in temporary staging matched all 9 generated files byte-for-byte; existing outputs were not rewritten: PASS.

## Row counts, missingness, and storage

- Chronological bug splits: train 23,272; validation 4,987; test 4,987.
- Target label tiers: 1,651 `known_entry`; 31,595 `provisional`.
- Candidate-feature missing values: 206,990 blank assignment-recency values (no prior direct assignment at cutoff) and 253,172 blank Git-recency values (no prior contribution at cutoff). Required bug, developer, and cutoff fields are populated.
- Target IDs are blank for 29,177 bugs because their labels are outside the conservative nine-developer pool; these are not treated as candidate negatives.
- The unresolved identity queue has 76 rows: 72 normalized-name candidates and 4 exact-email mappings with no Bugzilla user ID in the available identity audit. Decisions remain blank.
- Duplicate `text_snapshot_time` is blank for all 1,810 pairs because no historical text-availability timestamp is present.
- The nine generated CSVs occupy 73,640,886 bytes in total (about 70.2 MiB).

## Source SHA-256

| Source | SHA-256 |
|---|---|
| `dataset/processed/cold_start/eclipse_all_repositories/eclipse_git_developer_roster.csv` | `34f7f2f7338bc9513957f494994ad04fba6097611ecda37ef205361ce0c1a9cc` |
| `dataset/processed/cold_start/eclipse_all_repositories/identity_review/contributor_identity_cohorts_classified.csv` | `8daa570f227d1f1dd77e22e11fef04ad11d4433b3106fc42795bd0b2a833e1ca` |
| `dataset/processed/cold_start/git_bugzilla_candidate_review.csv` | `43f94a54a8a9bc9a11db6e69598327541330e7783358d6b2e83272d0688f0565` |
| `dataset/processed/cold_start/git_bugzilla_exact_email_matches_clean.csv` | `31b58223f57204ad6f6b82821f99846bc7585e546fefcc309ad2b29b4e5265e1` |
| `dataset/processed/cold_start/jdt_bug_developer_temporal_features_strict.csv` | `d9bdf8eeea6ce11d583cbe33dc3d390563a209b2d6d756a4b7d8623f3cd8c622` |
| `dataset/processed/cold_start/jdt_git_developer_roster.csv` | `7ee6f00b2c22655738206928d5dd90c1d9c4be60548e79cd6b33652d53e80113` |
| `dataset/processed/developer_identity_audit.csv` | `72e78fa7a4bcfc9bb0927c6766361a1b6bcfbf0e53f8f5f2cf4917d608440b45` |
| `dataset/processed/duplicate_pairs_historical_available.csv` | `c93423048d35af5acedad67ea0cc70c1e8cedebc56ebffdf79e1ebc5c94747fc` |
| `dataset/processed/jdt_bug_text_cleaned.csv` | `9c56184a98e3413057a12192a76d40d86887df89221cf9866d7866374e015c9c` |
| `dataset/processed/jdt_training_primary.csv` | `ce3f70d1835b66a5bdcb1798ff880df77db36dd51ec2e5ef02c539e5b7153ec9` |

## Generated outputs

- `dataset/processed/cold_start/jdt_identity_review/jdt_exact_email_mapping_audit.csv`
- `dataset/processed/cold_start/jdt_identity_review/jdt_verified_identity_map.csv`
- `dataset/processed/cold_start/jdt_identity_review/jdt_unresolved_identity_review.csv`
- `dataset/processed/cold_start/jdt_git_contributor_cold_start_cohorts.csv`
- `dataset/processed/jdt_point_in_time/jdt_candidate_features.csv`
- `dataset/processed/jdt_point_in_time/jdt_assignment_targets.csv`
- `dataset/processed/jdt_point_in_time/jdt_bug_splits.csv`
- `dataset/processed/jdt_point_in_time/jdt_cold_start_scenarios.csv`
- `dataset/processed/jdt_duplicate_retrieval/jdt_duplicate_positive_pairs_audit.csv`

## Limitations and gates

- Four exact-email mappings had no Bugzilla user ID in the available identity audit and remain unresolved; the audit found no mapping to multiple Bugzilla user IDs.
- Primary labels include both `known_entry` and `provisional` tiers; the tier is kept in the target table and should be respected in evaluation.
- Historical assignment counts are not active workload. The retained audit does not contain all reassignment, resolution, closure, and reopening events.
- Git contribution is evidence of code activity only, not Bugzilla assignment experience or a fallback assignment label.
- Historical identity verification uses the currently audited mapping and is metadata, not a point-in-time feature. Cold-start scenarios are not a deployable candidate pool.
- Current cleaned bug text has no per-version availability timestamp; TF-IDF/cosine candidate features and related-bug negatives remain blocked to prevent leakage.
- Platform and PDE Bugzilla endpoints were checked once separately; the current result is recorded in the final completion report.
