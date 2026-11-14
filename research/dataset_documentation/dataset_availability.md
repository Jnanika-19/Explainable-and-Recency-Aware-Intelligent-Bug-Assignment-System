# Dataset Availability Report

Generated: 2026-11-11T07:41:22.383266+00:00

## Scope

This is a read-only inventory of files under `dataset/`. It records file sizes,
SHA-256 checksums, CSV headers, and row counts for CSVs no larger than
250,000,000 bytes. Large CSVs are not scanned for row counts.
The `.git` metadata for the external JDT repository is excluded from this file
manifest; its commit-history status is summarized below.

## Existing JDT baseline

| File | Size (MiB) | Rows | Columns |
|---|---:|---:|---|
| `dataset/raw/JDT.csv` | 6082.12 | not counted (large file) | Issue URL; ID; Alias; Classification; Component; Product; Version; Platform; Op sys; Status; Resolution; Depends on; Dupe of; Blocks; Groups; Flags; Severity; Priority; Deadline; Target Milestone; Creator; Creator Detail; Creation time; Assigned to; Assigned to detail; CC; CC detail; Is CC accessible; Is confirmed; Is open; Is creator accessible; Summary; Description; URL; Whiteboard; Keywords; See also; Last change time; QA contact; History/Activity Log; Comments; Attachments |
| `dataset/processed/jdt_training_primary.csv` | 44.92 | 33,246 | bug_id; summary; description; product; component; severity; priority; creation_time; developer_label; label_event_time; label_event_type; label_type; candidate_evidence_type; jdt_entry_time; history_status |
| `dataset/processed/jdt_training_secondary_review.csv` | 0.47 | 607 | bug_id; summary; description; product; component; severity; priority; creation_time; developer_label; label_event_time; label_event_type; label_type; candidate_evidence_type; jdt_entry_time; history_status |
| `dataset/processed/duplicate_pairs.csv` | 1.42 | 10,875 | duplicate_bug_id; duplicate_summary; Resolution; original_bug_id; original_summary |
| `dataset/processed/duplicate_pairs_historical_available.csv` | 0.34 | 1,810 | duplicate_bug_id; duplicate_summary; original_bug_id; original_summary; family_id; duplicate_creation_time; original_creation_time; product; component |
| `dataset/processed/developer_identity_audit.csv` | 0.00 | 78 | email; bugzilla_user_ids; real_names; number_of_user_ids; number_of_real_names; records_found |
| `dataset/processed/cold_start/jdt_git_commits.csv` | 5.50 | 32,484 | commit_id; git_author_key; author_name; author_email; author_timestamp; committer_timestamp; subject |
| `dataset/processed/cold_start/jdt_git_commit_files.csv` | 60.20 | 279,322 | commit_id; git_author_key; author_name; author_email; author_timestamp; file_path; component |
| `dataset/processed/cold_start/jdt_git_developer_roster.csv` | 0.07 | 254 | git_author_key; author_name; author_email; first_commit_at; latest_commit_at; commit_count; changed_file_count; components |
| `dataset/processed/cold_start/git_verified_developer_commit_events.csv` | 0.25 | 1,418 | bugzilla_email; git_author_key; commit_id; author_timestamp; subject |
| `dataset/processed/cold_start/git_verified_developer_adjusted_contributions.csv` | 0.00 | 13 | bugzilla_email; git_author_key; raw_commit_count; unique_change_units; raw_changed_file_records; adjusted_changed_file_records; log_adjusted_file_contribution; first_git_contribution; latest_git_contribution |
| `dataset/processed/cold_start/git_unmatched_identity_review.csv` | 0.06 | 241 | git_author_key; git_names; git_emails; commit_count; changed_file_count; components; identity_status |
| `dataset/processed/cold_start/jdt_bug_developer_temporal_features_strict.csv` | 44.17 | 432,198 | bug_id; bug_creation_time; component; developer_email; is_assigned_developer; historical_commit_count; historical_changed_file_count; commits_last_30_days; commits_last_90_days; commits_last_365_days; files_last_30_days; files_last_90_days; files_last_365_days; days_since_last_contribution; label_type; candidate_evidence_type |

Verified current counts include 33,246 primary assignment examples,
607 secondary-review examples, 1,810 historically available duplicate pairs,
32,484 JDT commits, 279,322 commit-file records, and 1,418 verified developer
commit events. The clean exact-email identity file contains 13 verified
Bugzilla-to-Git identities. The strict temporal feature file contains 432,198
bug/developer rows. The Git roster contains 254 author keys; 241 are currently
unmatched and must remain unclassified as cold-start developers.

The raw JDT export is approximately 6.08 GiB and contains bug fields, current
assignee/status/resolution, activity history, comments, and duplicate links.
The primary training file is a derived subset and does not include every raw
field. Existing data remains in its current locations; this report does not
regenerate or modify it.

## Feature and data gaps

- Historical assignment events are present in the raw JDT activity log, but
  there is no normalized per-event history/workload dataset in the inventory.
- Active assignment queues have not been reconstructed. Any future workload
  feature must be rebuilt from events available at each prediction cutoff.
- The existing strict temporal feature file covers only the 13 verified
  identities; its script uses commit committer timestamps and a strict
  before-bug-creation cutoff.
- Existing commit CSVs contain commit subjects, not complete commit messages.
  File paths and author/committer timestamps are present; file-change counts
  can be derived. Existing component labels use the first path segment.
- Historical duplicate pairs include creation times, but raw duplicate pairs
  are not themselves a prediction-time-filtered related-bug feature table.
- No confidence calibration, ranking-margin, top-K evaluation, adaptive vs.
  fixed-weight comparison, or integrated recommendation feature dataset was
  found in the current dataset tree.

The local JDT Git repository has 32,484 commits across available refs and is
not marked shallow. It is a partial clone (`blob:none`); its checkout currently
reports 10,859 tracked paths as deleted. Its checkout also contains three
non-Git root files, including one with a Git-extraction error message in its
name. The Git metadata and checkout are left untouched.

## Sources and licensing status

- Bugzilla REST API documentation describes current bug fields and access
  methods: [Bugzilla API: Bugs](https://bugzilla.readthedocs.io/en/latest/api/core/v1/bug.html).
- The Eclipse Bugzilla site currently reports a temporary shutdown:
  [Eclipse Bugzilla](https://bugs.eclipse.org/bugs/page.cgi?id=about.html).
  Endpoint availability, activity history, and public access must be rechecked
  before any project data is collected.
- The PDE repository identifies EPL-2.0 for its source code:
  [eclipse-pde/eclipse.pde](https://github.com/eclipse-pde/eclipse.pde).
- The Platform project spans repositories. The selected scope is all
  component-mapped repositories; the mapping and repository terms remain to be
  validated before collection.
- Repository code licensing does not establish a license for Bugzilla records.
  Bug report text and contributor identifiers require separate terms/privacy
  review. Comments are excluded from the initial collection.

The repository `.gitignore` already excludes the large `dataset/raw/`,
`dataset/processed/`, and `dataset/external/` contents. This stage made no
changes to ignore rules.

## File manifest

| File | Size (bytes) | SHA-256 | CSV rows | CSV columns |
|---|---:|---|---:|---|
| `dataset/external/eclipse.jdt.core/e RuntimeError(Git history extraction failed.)` | 5,497 | `d567abdc6580719f247cc0738fd300010d605a5851839e934b59ac3207552c8c` | — | — |
| `dataset/external/eclipse.jdt.core/hlib` | 16,653 | `cf718647dd4f91e50c34cb771e852919ee3b24217fbbfa07c62fcc8edd0d3fd7` | — | — |
| `dataset/external/eclipse.jdt.core/v` | 2,230 | `02e00c3156697911a60ac7bf6bdafecf1cbce0dce3e02d8d12bce261e272f586` | — | — |
| `dataset/processed/.gitkeep` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | — | — |
| `dataset/processed/cold_start/git_bugzilla_candidate_matches.csv` | 11,916 | `6b1bb798f34dad002a2f37bd8e0c9cff5bb4f1f1812cc2890262093e6ae356dd` | 85 | bugzilla_email; bugzilla_name_key; git_author_key; git_names; git_emails; match_reason; review_status |
| `dataset/processed/cold_start/git_bugzilla_candidate_review.csv` | 14,311 | `43f94a54a8a9bc9a11db6e69598327541330e7783358d6b2e83272d0688f0565` | 85 | bugzilla_email; bugzilla_name_key; git_author_key; git_names; git_emails; match_reason; review_status; review_classification |
| `dataset/processed/cold_start/git_bugzilla_exact_email_matches.csv` | 1,743 | `2b2c5547d941ddfb2112fc201eb46900366709365146cabe2d1844934080a1ae` | 14 | bugzilla_email; git_author_key; git_names; matched_email; match_type; review_status |
| `dataset/processed/cold_start/git_bugzilla_exact_email_matches_clean.csv` | 1,631 | `31b58223f57204ad6f6b82821f99846bc7585e546fefcc309ad2b29b4e5265e1` | 13 | bugzilla_email; git_author_key; git_names; matched_email; match_type; review_status |
| `dataset/processed/cold_start/git_bulk_commit_audit.csv` | 57,566 | `75b4ea80b86940f9acc4e125fed87d908c96fb37b428d13749b86af2c47bfd06` | 229 | commit_id; git_author_key; author_name; author_timestamp; changed_file_count; subject; large_commit_flag; classification; patch_id; verified_duplicate_group; notes |
| `dataset/processed/cold_start/git_unmatched_identity_review.csv` | 62,305 | `969851cabf2ca557879813be00df74b6ca06ca98c841c83af1c6f989e2a28878` | 241 | git_author_key; git_names; git_emails; commit_count; changed_file_count; components; identity_status |
| `dataset/processed/cold_start/git_verified_developer_adjusted_contributions.csv` | 1,687 | `47cb992cc1b8265402764ff1ef7050f41f2c492cb7eb1adad9721ce02738243e` | 13 | bugzilla_email; git_author_key; raw_commit_count; unique_change_units; raw_changed_file_records; adjusted_changed_file_records; log_adjusted_file_contribution; first_git_contribution; latest_git_contribution |
| `dataset/processed/cold_start/git_verified_developer_commit_events.csv` | 265,217 | `3e76abe45d8c57fb17962a22e3ba1e65ce046fed14efc3f1576f25e1500fd732` | 1,418 | bugzilla_email; git_author_key; commit_id; author_timestamp; subject |
| `dataset/processed/cold_start/git_verified_developer_component_expertise.csv` | 14,171 | `eccd1fe016ef0834e1cfa9187f9e8e6cfb4f1e1334914226866302a93388b7d0` | 127 | bugzilla_email; component; commit_count; changed_file_count; first_component_contribution; latest_component_contribution |
| `dataset/processed/cold_start/git_verified_developer_summary.csv` | 5,235 | `501f81f69b44d97f4aff01cf4848cd297340100ad661feb322a8acd33d7ec864` | 13 | bugzilla_email; git_author_key; git_commit_count; changed_file_count; components_worked_on; first_git_contribution; latest_git_contribution |
| `dataset/processed/cold_start/jdt_bug_developer_temporal_features.csv` | 46,318,635 | `d9bdf8eeea6ce11d583cbe33dc3d390563a209b2d6d756a4b7d8623f3cd8c622` | 432,198 | bug_id; bug_creation_time; component; developer_email; is_assigned_developer; historical_commit_count; historical_changed_file_count; commits_last_30_days; commits_last_90_days; commits_last_365_days; files_last_30_days; files_last_90_days; files_last_365_days; days_since_last_contribution; label_type; candidate_evidence_type |
| `dataset/processed/cold_start/jdt_bug_developer_temporal_features_inclusive.csv` | 46,318,635 | `d9bdf8eeea6ce11d583cbe33dc3d390563a209b2d6d756a4b7d8623f3cd8c622` | 432,198 | bug_id; bug_creation_time; component; developer_email; is_assigned_developer; historical_commit_count; historical_changed_file_count; commits_last_30_days; commits_last_90_days; commits_last_365_days; files_last_30_days; files_last_90_days; files_last_365_days; days_since_last_contribution; label_type; candidate_evidence_type |
| `dataset/processed/cold_start/jdt_bug_developer_temporal_features_strict.csv` | 46,318,635 | `d9bdf8eeea6ce11d583cbe33dc3d390563a209b2d6d756a4b7d8623f3cd8c622` | 432,198 | bug_id; bug_creation_time; component; developer_email; is_assigned_developer; historical_commit_count; historical_changed_file_count; commits_last_30_days; commits_last_90_days; commits_last_365_days; files_last_30_days; files_last_90_days; files_last_365_days; days_since_last_contribution; label_type; candidate_evidence_type |
| `dataset/processed/cold_start/jdt_git_commit_files.csv` | 63,123,625 | `3a764d42f1eba7422bf37b9d134787faa6395f418ed59bac7e1c182d4ad8d27f` | 279,322 | commit_id; git_author_key; author_name; author_email; author_timestamp; file_path; component |
| `dataset/processed/cold_start/jdt_git_commits.csv` | 5,762,933 | `6845d0ae5643cc3c149e44de548585622c7dc61b5d4a46548f2799fa644b75b1` | 32,484 | commit_id; git_author_key; author_name; author_email; author_timestamp; committer_timestamp; subject |
| `dataset/processed/cold_start/jdt_git_developer_roster.csv` | 69,878 | `7ee6f00b2c22655738206928d5dd90c1d9c4be60548e79cd6b33652d53e80113` | 254 | git_author_key; author_name; author_email; first_commit_at; latest_commit_at; commit_count; changed_file_count; components |
| `dataset/processed/developer_component_expertise.csv` | 27,936 | `ee6f9b60dbbf2c0f1555d0479735c988d37c6c00c600094361c94a0d8ba4b422` | 640 | first_observed_developer; component; bug_count; share_within_developer |
| `dataset/processed/developer_identity_audit.csv` | 3,149 | `72e78fa7a4bcfc9bb0927c6766361a1b6bcfbf0e53f8f5f2cf4917d608440b45` | 78 | email; bugzilla_user_ids; real_names; number_of_user_ids; number_of_real_names; records_found |
| `dataset/processed/developer_profile_summary.csv` | 28,467 | `3966680d4d63bd64a974da297dc45d1bb25efc5dc56ef9b0997fa66926530c51` | 335 | first_observed_developer; total_assigned_bugs; components_worked_on; known_entry_bugs; provisional_bugs; first_recorded_assignment; latest_recorded_assignment |
| `dataset/processed/duplicate_pairs.csv` | 1,485,877 | `b07966cc6eadc2af6087d39913dca3adab8d53470df6edb086a3f1b7872af606` | 10,875 | duplicate_bug_id; duplicate_summary; Resolution; original_bug_id; original_summary |
| `dataset/processed/duplicate_pairs_historical_available.csv` | 355,089 | `c93423048d35af5acedad67ea0cc70c1e8cedebc56ebffdf79e1ebc5c94747fc` | 1,810 | duplicate_bug_id; duplicate_summary; original_bug_id; original_summary; family_id; duplicate_creation_time; original_creation_time; product; component |
| `dataset/processed/duplicate_pairs_with_families.csv` | 1,449,166 | `443b029b7e4b281490419487ba327612fe7d2d2798976b0a0eafcac653ca99ec` | 9,366 | duplicate_bug_id; duplicate_summary; Resolution; original_bug_id; original_summary; family_id; family_pair_count |
| `dataset/processed/jdt_assignment_label_audit.csv` | 21,483,527 | `801a63a921cdaf8e8ff762ae0eccfce419fed6306956eacf8625b211776328bf` | 63,266 | bug_id; product; component; creation_time; current_assignee; first_observed_developer; first_assignment_time; jdt_entry_time; label_type; candidate_evidence_type; candidate_source; first_added_developer; first_added_time; first_added_evidence; first_removed_developer; first_removed_time; first_removed_evidence; assignment_evidence; history_status |
| `dataset/processed/jdt_bug_text_cleaned.csv` | 77,071,870 | `9c56184a98e3413057a12192a76d40d86887df89221cf9866d7866374e015c9c` | 33,246 | bug_id; summary_clean; description_clean; combined_text |
| `dataset/processed/jdt_training_primary.csv` | 47,097,204 | `ce3f70d1835b66a5bdcb1798ff880df77db36dd51ec2e5ef02c539e5b7153ec9` | 33,246 | bug_id; summary; description; product; component; severity; priority; creation_time; developer_label; label_event_time; label_event_type; label_type; candidate_evidence_type; jdt_entry_time; history_status |
| `dataset/processed/jdt_training_secondary_review.csv` | 495,179 | `48b8b6dd4f856b6fa3894a7b622749763126154bb7e3a8592703561bc71ae857` | 607 | bug_id; summary; description; product; component; severity; priority; creation_time; developer_label; label_event_time; label_event_type; label_type; candidate_evidence_type; jdt_entry_time; history_status |
| `dataset/processed/known_entry_developer_profiles.csv` | 3,733 | `47f8e4c2ffbbf16993b862fe06b94e71720b7c533ecbb1015d06d4e3f9ffadd5` | 131 | first_observed_developer; known_entry_bugs; components |
| `dataset/processed/member1_dataset_files/developer_component_expertise.csv` | 27,936 | `ee6f9b60dbbf2c0f1555d0479735c988d37c6c00c600094361c94a0d8ba4b422` | 640 | first_observed_developer; component; bug_count; share_within_developer |
| `dataset/processed/member1_dataset_files/developer_identity_audit.csv` | 3,149 | `72e78fa7a4bcfc9bb0927c6766361a1b6bcfbf0e53f8f5f2cf4917d608440b45` | 78 | email; bugzilla_user_ids; real_names; number_of_user_ids; number_of_real_names; records_found |
| `dataset/processed/member1_dataset_files/developer_profile_summary.csv` | 28,467 | `3966680d4d63bd64a974da297dc45d1bb25efc5dc56ef9b0997fa66926530c51` | 335 | first_observed_developer; total_assigned_bugs; components_worked_on; known_entry_bugs; provisional_bugs; first_recorded_assignment; latest_recorded_assignment |
| `dataset/processed/member1_dataset_files/duplicate_pairs_with_families.csv` | 1,449,166 | `443b029b7e4b281490419487ba327612fe7d2d2798976b0a0eafcac653ca99ec` | 9,366 | duplicate_bug_id; duplicate_summary; Resolution; original_bug_id; original_summary; family_id; family_pair_count |
| `dataset/processed/member1_dataset_files/jdt_assignment_label_audit.csv` | 21,483,527 | `801a63a921cdaf8e8ff762ae0eccfce419fed6306956eacf8625b211776328bf` | 63,266 | bug_id; product; component; creation_time; current_assignee; first_observed_developer; first_assignment_time; jdt_entry_time; label_type; candidate_evidence_type; candidate_source; first_added_developer; first_added_time; first_added_evidence; first_removed_developer; first_removed_time; first_removed_evidence; assignment_evidence; history_status |
| `dataset/processed/member1_dataset_files/jdt_training_primary.csv` | 47,097,204 | `ce3f70d1835b66a5bdcb1798ff880df77db36dd51ec2e5ef02c539e5b7153ec9` | 33,246 | bug_id; summary; description; product; component; severity; priority; creation_time; developer_label; label_event_time; label_event_type; label_type; candidate_evidence_type; jdt_entry_time; history_status |
| `dataset/processed/member1_dataset_files/jdt_training_secondary_review.csv` | 495,179 | `48b8b6dd4f856b6fa3894a7b622749763126154bb7e3a8592703561bc71ae857` | 607 | bug_id; summary; description; product; component; severity; priority; creation_time; developer_label; label_event_time; label_event_type; label_type; candidate_evidence_type; jdt_entry_time; history_status |
| `dataset/processed/member1_dataset_files/known_entry_developer_profiles.csv` | 3,733 | `47f8e4c2ffbbf16993b862fe06b94e71720b7c533ecbb1015d06d4e3f9ffadd5` | 131 | first_observed_developer; known_entry_bugs; components |
| `dataset/processed/member1_dataset_files/possible_developer_aliases.csv` | 2,719 | `76b54b6829468c8db2475a7bc2abe50d3f044fce51f4aba9823b18e3f0bce71e` | 34 | possible_name_key; email_addresses; number_of_addresses |
| `dataset/processed/member1_dataset_files/README.md` | 8,526 | `b39069d9334b66a261e83b190428d5bc7ae800723612d0e441c6ec3666970aa0` | — | — |
| `dataset/processed/member1_dataset_files.zip` | 13,278,702 | `606b51a0149816f6c0e17ec8d61a9429dab9ddc3a792ecaf917cb10848eab5c7` | — | — |
| `dataset/processed/possible_developer_aliases.csv` | 2,719 | `76b54b6829468c8db2475a7bc2abe50d3f044fce51f4aba9823b18e3f0bce71e` | 34 | possible_name_key; email_addresses; number_of_addresses |
| `dataset/raw/.gitkeep` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | — | — |
| `dataset/raw/JDT.csv` | 6,377,569,970 | `f80a77b5fba844f8223cc0bbd47e2b51a2f1cc2353a978dda6bc011205222385` | not counted (large file) | Issue URL; ID; Alias; Classification; Component; Product; Version; Platform; Op sys; Status; Resolution; Depends on; Dupe of; Blocks; Groups; Flags; Severity; Priority; Deadline; Target Milestone; Creator; Creator Detail; Creation time; Assigned to; Assigned to detail; CC; CC detail; Is CC accessible; Is confirmed; Is open; Is creator accessible; Summary; Description; URL; Whiteboard; Keywords; See also; Last change time; QA contact; History/Activity Log; Comments; Attachments |
