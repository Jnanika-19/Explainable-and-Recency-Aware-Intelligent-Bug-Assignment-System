# Data Dictionary

Paths are repository-root-relative. Candidate features, labels, evaluation-only information, context, and identity metadata are intentionally separated. All keys and feature values should be interpreted with the scope and limitations in [KNOWN_LIMITATIONS.md](./KNOWN_LIMITATIONS.md).

## Core integrated tables

### Candidate feature table

**File:** `dataset/processed/jdt_integrated/jdt_integrated_candidate_features.csv`
**Rows:** 299,214 (33,246 bugs by 9 conservative candidate developers); **key:** `(bug_id, developer_id)` for each prediction cutoff.

**Columns:** `bug_id`, `prediction_cutoff`, `data_split`, `developer_id`, `point_in_time_candidate_eligible`, `prior_direct_assignment_count`, `prior_same_component_direct_assignment_count`, `days_since_last_direct_assignment`, `historical_commit_count`, `historical_changed_file_count`, `commits_last_30_days`, `commits_last_90_days`, `commits_last_365_days`, `files_last_30_days`, `files_last_90_days`, `files_last_365_days`, `days_since_last_contribution`, `workload_scope`, `suitable_for_experimental_use`, `severity_breakdown_supported`, `eligible_bug_cohort_size`, `eligible_bugs_created_before_cutoff`, `eligible_active_jdt_bug_count`, `eligible_active_verified_assignee_bug_count`, `eligible_active_unverified_or_unassigned_bug_count`, `active_assigned_bug_count_partial`, `assigned_event_count_partial`, `distinct_bugs_assigned_partial`, `reassignment_in_event_count_partial`, `distinct_bugs_reassigned_in_partial`, `reassignment_out_event_count_partial`, `distinct_bugs_reassigned_out_partial`, `terminalization_event_count_partial`, `distinct_bugs_terminalized_partial`, `reopened_event_count_partial`, `distinct_bugs_reopened_partial`, `state_events_applied_before_cutoff`, `latest_included_event_time`, `evidence_coverage_ratio_within_eligible_cohort`, `verified_candidate_pool_size`, `expertise_evidence_status`, `same_component_expertise_status`, `recency_evidence_status`, `workload_evidence_status`, `workload_coverage_status`, `explainability_status`, `cold_start_status`, `genuine_newness_status`, `adaptive_selection_status`, `prediction_confidence_status`, `duplicate_related_status`, `top_k_status`.

The status and availability columns are evidence/readiness indicators, not scores, probabilities, explanations, or ranks. Partial workload fields must not be interpreted as total queue size.

### Targets and chronological split

**File:** `dataset/processed/jdt_integrated/jdt_integrated_targets.csv`
**Rows:** 33,246; **key:** `bug_id`.
**Columns:** `bug_id`, `prediction_cutoff`, `data_split`, `target_developer_id`, `target_status`, `target_label_tier`, `label_event_time`, `label_event_type`.

**File:** `dataset/processed/jdt_point_in_time/jdt_bug_splits.csv`
**Rows:** 33,246; **key:** `bug_id`.
**Columns:** `bug_id`, `prediction_cutoff`, `data_split`.

Targets are labels, not candidate features. Out-of-pool target IDs are blank and must not be converted into negative candidate labels. Keep all candidates for a bug in the same split. `known_entry` and `provisional` tiers remain distinct.

### Context

**File:** `dataset/processed/jdt_integrated/jdt_integrated_bug_context_by_bug.csv`
**Rows:** 33,246; **key:** `(bug_id, prediction_cutoff)`.
**Columns:** `bug_id`, `prediction_cutoff`, `product_as_exported`, `component_as_exported`, `severity_as_exported`, `priority_as_exported`, `temporal_status`, `model_input_eligible`.

`jdt_integrated_bug_context_metadata.csv` has the same columns expanded to 299,214 candidate rows. Its repeated rows are by design; prefer the normalized table. Export-time context is marked temporally unverified and is not an eligible model input.

### Cold-start evaluation

**File:** `dataset/processed/jdt_integrated/jdt_integrated_cold_start_evaluation.csv`
**Rows:** 206,990.
**Columns:** `bug_id`, `prediction_cutoff`, `developer_id`, `data_split`, `prior_direct_assignment_count`, `evaluation_only_first_assignment_after_cutoff`, `prior_git_commit_count`, `cold_start_status`, `genuinely_new_developer`, `git_activity_is_assignment_evidence`, `fallback_status`, `evaluation_only`.

These are zero-prior-assignment scenarios. Genuine newness is `unknown`; Git contributions are not assignment evidence. This is evaluation-only information, not a confirmed new-developer cohort or a fallback candidate source.

### Duplicate positives and identity metadata

**File:** `dataset/processed/jdt_integrated/jdt_integrated_duplicate_evaluation_pairs.csv`
**Rows:** 1,810.
**Columns:** `duplicate_bug_id`, `original_bug_id`, `family_id`, `duplicate_creation_time`, `original_creation_time`, `product`, `component`, `duplicate_target_label`, `label_use`, `original_existed_before_cutoff`, `text_snapshot_time`, `retrieval_model_ready`, `evaluation_only`.

The pairs are positive historical duplicate targets only. `text_snapshot_time` is blank; no TF-IDF or cosine feature is available.

**File:** `dataset/processed/jdt_integrated/jdt_integrated_developer_identity_metadata.csv`
**Rows:** 9; **columns:** `developer_id`, `bugzilla_user_id`, `bugzilla_email`, `git_author_key`, `identity_evidence`, `metadata_use`.
This is restricted identity metadata and must not be used as an unreviewed predictor or shared externally.

## Workload evidence

**File:** `dataset/processed/jdt_workload_partial/jdt_partial_workload_snapshots.csv`
**Rows:** 299,214; **key:** `(prediction_bug_id, prediction_cutoff, developer_id)`.
Columns: `prediction_bug_id`, `prediction_cutoff`, `data_split`, `developer_id`, `workload_scope`, `suitable_for_experimental_use`, `severity_breakdown_supported`, `eligible_bug_cohort_size`, `eligible_bugs_created_before_cutoff`, `eligible_active_jdt_bug_count`, `eligible_active_verified_assignee_bug_count`, `eligible_active_unverified_or_unassigned_bug_count`, `verified_developer_pool_size`, `developers_with_active_observed_bugs_at_cutoff`, `active_assigned_bug_count_partial`, `assigned_event_count_partial`, `distinct_bugs_assigned_partial`, `reassignment_in_event_count_partial`, `distinct_bugs_reassigned_in_partial`, `reassignment_out_event_count_partial`, `distinct_bugs_reassigned_out_partial`, `terminalization_event_count_partial`, `distinct_bugs_terminalized_partial`, `reopened_event_count_partial`, `distinct_bugs_reopened_partial`, `state_events_applied_before_cutoff`, `latest_included_event_time`, `evidence_coverage_ratio_within_eligible_cohort`, `known_limitations`.

`jdt_partial_workload_coverage.csv` has one record per bug/cutoff and records cohort coverage and exclusions. `jdt_partial_resolution_activity.csv` has the key plus `data_split`, `workload_scope`, `resolution_event_count_partial`, `resolution_set_event_count_partial`, `resolution_clear_event_count_partial`, `distinct_bugs_with_resolution_change_partial`, `latest_included_resolution_event_time`, and `resolution_attribution_scope`. These outputs are partial evidence, not complete workload totals.

## Point-in-time, text, label, and lifecycle source tables

- `dataset/processed/jdt_point_in_time/jdt_candidate_features.csv`: 299,214 rows; raw candidate feature schema before integration; includes bug context fields, developer ID, direct-assignment history, and prior Git activity.
- `dataset/processed/jdt_point_in_time/jdt_assignment_targets.csv`: 33,246 target-only rows with `bug_id`, `target_developer_id`, `target_status`, `target_label_tier`, `label_event_time`, and `label_event_type`.
- `dataset/processed/jdt_point_in_time/jdt_cold_start_scenarios.csv`: 206,990 evaluation scenarios; same core columns as the integrated cold-start table.
- `dataset/processed/cold_start/jdt_bug_developer_temporal_features_strict.csv`: 432,198 rows; 16 columns covering bug creation, component, candidate email, prior commit/file counts, 30/90/365-day activity, and evidence tiers. The base and inclusive filenames are byte-identical copies.
- `dataset/processed/jdt_training_primary.csv`: 33,246 rows; columns `bug_id`, `summary`, `description`, `product`, `component`, `severity`, `priority`, `creation_time`, `developer_label`, `label_event_time`, `label_event_type`, `label_type`, `candidate_evidence_type`, `jdt_entry_time`, `history_status`.
- `dataset/processed/jdt_training_secondary_review.csv`: same columns, 607 review-only rows; keep separate from primary targets.
- `dataset/processed/jdt_bug_text_cleaned.csv`: 33,246 rows; `bug_id`, `summary_clean`, `description_clean`, `combined_text`. No text-version availability timestamps are supplied.
- `dataset/processed/jdt_workload/jdt_assignment_lifecycle_events.csv`: 287,917 event rows; `record_index`, `bug_id`, creation/event times, activity/change indices, lifecycle field and old/new values.
- `dataset/processed/jdt_workload/jdt_bug_history_coverage.csv`: 63,266 bug rows with export-time state, history parse status, event counts, and replay status. Do not equate export-time state with state at a historical cutoff.

## Git and identity evidence

`dataset/processed/cold_start/eclipse_all_repositories/eclipse_git_commits.csv` contains 183,742 rows with `repository`, `commit_id`, repository-scoped author key, author name/email and timestamps, and subject. `eclipse_git_commit_files.csv` contains 2,215,515 path rows. The developer roster has 7,332 repository-scoped keys. The identity review/candidate files are candidate evidence only. Names, emails, author keys, and manual-review queues are restricted.

Existing JDT-only Git tables under `dataset/processed/cold_start/` include commit, changed-path, developer-roster, verified commit-event, component-expertise, and strict temporal-feature data. These are code-contribution evidence, not assignment labels.
