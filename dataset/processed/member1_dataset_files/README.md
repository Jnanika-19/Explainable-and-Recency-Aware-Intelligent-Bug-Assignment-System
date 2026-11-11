# Explainable and Recency-Aware Intelligent Bug Assignment System
## JDT Dataset Documentation

### 1. Dataset Overview

This folder contains the processed Eclipse JDT (Java Development Tools) bug-report dataset prepared for the Intelligent Bug Assignment System.

The dataset contains historical bug reports, developer assignment evidence, developer profiles, component expertise information, and duplicate-bug relationships.

The project uses this data to support:
- Historical developer expertise analysis.
- Recency-aware developer recommendation.
- Workload-aware developer ranking.
- Explainable Top-K developer recommendations.
- Duplicate and related bug detection.
- Cold-start handling and confidence estimation.

**Dataset scope:** Eclipse JDT only.  
**Raw source file:** `JDT.csv`  
**Raw records examined:** 63,266.

### 2. Files Included

| File | Description |
|---|---|
| `jdt_training_primary.csv` | Main training dataset containing direct assignment evidence. |
| `jdt_training_secondary_review.csv` | Records containing previous-assignee-only evidence; retained separately for review. |
| `jdt_assignment_label_audit.csv` | Assignment history and evidence audit for all 63,266 bugs. |
| `developer_profile_summary.csv` | Developer-level assignment and component activity summary. |
| `developer_component_expertise.csv` | Developer experience distribution across components. |
| `known_entry_developer_profiles.csv` | Developer profiles based on known JDT-entry evidence. |
| `duplicate_pairs_with_families.csv` | Duplicate relationships grouped into connected families. |
| `developer_identity_audit.csv` | Audit of developer email, user-ID and real-name identity consistency. |
| `possible_developer_aliases.csv` | Potential developer aliases requiring manual verification. |

### 3. Training Dataset Statistics

#### Primary dataset

- Total records: 33,246
- Unique bug IDs: 33,246
- Missing bug IDs: 0
- Missing developer labels: 0
- Missing summaries: 2
- Missing descriptions: 215
- Known-entry records: 1,651
- Provisional records: 31,595

#### Secondary review dataset

- Total records: 607
- Unique bug IDs: 607
- Missing bug IDs: 0
- Missing developer labels: 0
- Missing summaries: 0
- Missing descriptions: 5
- Known-entry records: 33
- Provisional records: 574

The primary and secondary datasets are kept separate because their assignment evidence has different strengths.

### 4. Assignment Label Methodology

Two label categories are used.

**Known-entry**

The bug history contains a recorded product transition into JDT. Assignment events at or after the JDT-entry timestamp are considered eligible evidence.

**Provisional**

No recorded transition into JDT was found in the available history. Assignment events at or after bug creation are considered eligible, but the exact JDT-entry point cannot be established.

Two evidence types are used:

- `direct_assignment`: A developer appears in an assignment-added event. These records form the primary dataset.
- `previous_assignee_only`: A developer is identified only through a previous-assignee removal event. These records are retained in the secondary review dataset.

**Important:** Provisional does not mean that the assignment evidence is false. It means that the available history does not establish the bug's exact entry into JDT. Known-entry and provisional labels should remain distinguishable during model training and evaluation.

### 5. Duplicate and Related Bug Data

The duplicate analysis identified:

- Bugs with duplicate links: 10,875.
- Duplicate relationships whose original bug IDs were available in the current JDT file: 9,366.
- Original bug IDs unavailable in the current JDT file: 1,509.
- Connected duplicate families: 5,322.

The file `duplicate_pairs_with_families.csv` contains:

| Column | Meaning |
|---|---|
| `duplicate_bug_id` | ID of the bug marked as a duplicate. |
| `duplicate_summary` | Summary of the duplicate bug. |
| `Resolution` | Resolution recorded for the duplicate bug. |
| `original_bug_id` | ID of the original bug referenced by the duplicate. |
| `original_summary` | Summary of the original bug. |
| `family_id` | Identifier for the connected duplicate family. |
| `family_pair_count` | Number of duplicate relationships associated with that family. |

These relationships can support duplicate and related-bug detection.

The 1,509 unavailable original IDs should not be described as globally missing bugs; they were not found in the current JDT dataset.

### 6. Developer Profile Data

Developer information is provided through three main files.

**`developer_profile_summary.csv`**

Contains:
- `first_observed_developer`
- `total_assigned_bugs`
- `components_worked_on`
- `known_entry_bugs`
- `provisional_bugs`
- `first_recorded_assignment`
- `latest_recorded_assignment`

**`developer_component_expertise.csv`**

Contains:
- `first_observed_developer`
- `component`
- `bug_count`
- `share_within_developer`

**`known_entry_developer_profiles.csv`**

Contains:
- `first_observed_developer`
- `known_entry_bugs`
- `components`

The profile audit identified 131 developers with known-entry evidence and 335 developers with some direct assignment evidence.

Potential aliases are not automatically merged. The alias file contains candidates for manual verification only.

### 7. Data Validation and Quality Checks

The following checks were performed:

1. Primary and secondary datasets were checked for unique bug IDs.
2. Missing values were examined in important training columns.
3. Assignment history was examined to identify direct and previous-assignee-only evidence.
4. Developer identity inconsistencies and possible aliases were audited.
5. Duplicate relationships and connected families were extracted.
6. Timestamp fields were checked using UTC-aware datetime parsing.

Timestamp validation results:

| Timestamp column | Available values | Invalid values |
|---|---:|---:|
| `creation_time` | 63,266 | 0 |
| `first_assignment_time` | 33,853 | 0 |
| `jdt_entry_time` | 3,811 | 0 |

All available values in these three columns passed datetime parsing.

### 8. Important Limitations

- The dataset represents historical JDT records, not a live bug-tracking system.
- Provisional labels have uncertain JDT-entry timing.
- Previous-assignee-only evidence is weaker than direct assignment evidence.
- Developer aliases are possible matches, not confirmed identities.
- Historical assignment counts should not be interpreted as current workload.
- Missing original bug IDs in the current JDT file do not establish that the bugs are absent from all Bugzilla records.
- Historical assignments do not guarantee that the same developer is available or suitable for a new bug.
- Timestamp parsing validation does not independently prove every assignment label is semantically correct.

### 9. Suggested Usage by Project Team

| Project activity | Relevant files |
|---|---|
| Training and developer recommendation | `jdt_training_primary.csv` |
| Secondary label review | `jdt_training_secondary_review.csv` |
| Historical expertise analysis | `developer_profile_summary.csv`, `developer_component_expertise.csv` |
| Recency analysis | `jdt_training_primary.csv`, `jdt_assignment_label_audit.csv` |
| Duplicate and related bug detection | `duplicate_pairs_with_families.csv` |
| Explainability and evidence tracing | `jdt_assignment_label_audit.csv`, developer profile files |
| Cold-start analysis | Developer profiles and assignment history |
| Developer identity quality checks | `developer_identity_audit.csv`, `possible_developer_aliases.csv` |

### 10. Important Instructions

- Keep known-entry and provisional labels distinguishable.
- Do not automatically combine possible developer aliases.
- Do not treat historical assignment totals as real-time workload.
- Use chronological train/test splitting when evaluating recency-aware models.
- Avoid using information that would only become available after the prediction time.
- Preserve the original processed CSV files when experimenting with model features.
- Keep raw developer identity information within the authorized project team.

**Prepared for:** Explainable and Recency-Aware Intelligent Bug Assignment System  
**Dataset scope:** Eclipse JDT  
**Package:** Member 1 – Dataset Collection, Preparation and Validation