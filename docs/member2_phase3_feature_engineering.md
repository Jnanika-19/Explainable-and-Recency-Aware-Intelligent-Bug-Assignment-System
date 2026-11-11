# Member 2 Phase 3: Developer Expertise and Recency Features

## Objective

Build candidate-level developer expertise features for the existing JDT
chronological experiment. All historical assignment evidence comes from
verified `known_entry` events; provisional assignments are not used. This is
feature generation and analysis only: it does not train a new model or replace
Phase 2 artifacts.

Run from the repository root after Phase 2 preprocessing and baseline training:

```powershell
.\.venv\Scripts\python.exe -m ml_model.generate_jdt_phase3_features
```

The generator loads the Phase 2 training-fitted TF-IDF vectorizer and writes
only `jdt_phase3_feature_*` and `jdt_phase3_*` outputs under
`data/processed/`. It does not modify the source CSVs or Phase 2 model outputs.

## Features and calculation methods

Each candidate row retains bug text, component, candidate and target IDs,
prediction timestamp, and a binary ground-truth-candidate label. Identifiers
and labels are metadata for joining and evaluation; they are not predictive
features.

| Feature | Calculation |
|---|---|
| `historical_bug_count` | Count of the candidate's verified assignments with `assignment_time < prediction timestamp`. |
| `historical_active_days` | Number of distinct UTC calendar dates on which those prior assignments occurred. |
| `component_experience_count` | Prior verified assignments in the bug's component. |
| `component_experience_share` | Component count divided by total prior verified assignment count; zero when there is no history. |
| `recent_activity_count_30d`, `_90d`, `_365d` | Prior verified assignments in any component in `[prediction time - window, prediction time)`. |
| `recent_component_count_30d`, `_90d`, `_365d` | Prior verified assignments in the bug's component in the same inclusive-lower-bound time windows. |
| `days_since_last_activity` | Fractional days between prediction time and the candidate's most recent prior verified assignment. |
| `days_since_last_component` | Fractional days between prediction time and the most recent prior verified assignment in the current component. |
| `component_recency_score` | `exp(-days_since_last_component / 365)`; zero when no component history exists. |
| `similar_bug_count` | Count of the candidate's prior bug texts with training-vectorizer cosine similarity at least 0.20. |
| `similar_bug_similarity_sum` | Sum of positive cosine similarities to the candidate's prior bug texts. |
| `max_similar_bug_similarity` | Maximum positive cosine similarity to the candidate's prior bug texts. |
| `expertise_score` | `component_experience_count / (component_experience_count + 2)`; zero without component history. |
| `similarity_score` | `min(1, similarity_sum / max(1, sqrt(historical_bug_count)))`. |

Empty histories produce zero counts and scores. Time-since features remain
missing when there is no eligible prior event; they are not imputed with a
fabricated date or interval. Invalid prediction timestamps and invalid
timestamps on verified history cause explicit validation errors.

### Average resolution time

Not implemented. The source schema contains bug creation, assignment-event,
and JDT-entry timestamps, but no reliable resolution/closed timestamp.
Creation-to-assignment delay is not resolution time, and `jdt_entry_time` is
not documented as a resolution event. Reporting either as resolution duration
would be misleading.

## Leakage prevention

- The feature builder filters to `label_type=known_entry`.
- Every event is admitted only after the strict check
  `assignment_time < prediction_timestamp`; an assignment at the exact
  prediction instant is excluded.
- Training and evaluation features use training-partition events only.
  Evaluation labels never enter the expertise history, even for later test
  predictions. Since all training assignment events are before the split
  cutoff, they precede the evaluation prediction timestamps.
- Provisional assignments never enter history or targets.
- The Phase 2 TF-IDF vectorizer is loaded as-is; it was fitted on training text
  only. Evaluation bug text is transformed, not used to fit a vocabulary.
- Developer IDs, target IDs, bug IDs, components, timestamps, and
  ground-truth-candidate flags are identifiers/context/labels and must be
  excluded from numeric predictive inputs. Full-dataset profile and component
  aggregates are not used.
- Candidate universe is the 79-developer Phase 2 training class set. A
  developer without prior evidence at a particular training timestamp has
  zero-valued history features. Evaluation targets outside this candidate
  universe remain cold-start misses; they are not dropped from the evaluation
  bug set.

## Dataset and feature analysis

The generated datasets contain 1,298 training bugs and 331 evaluation bugs.
Each bug has one row for each of the 79 training candidates:

- Training: 102,542 candidate rows, with 1,298 positive candidate labels.
- Evaluation: 26,149 candidate rows, with 143 positive labels and 188 bugs
  whose target is not in the candidate universe.

The feature missingness report shows empty descriptions on 158 candidate rows
per partition because the two source bugs with empty descriptions in each
partition are repeated for each of the 79 candidates. Missing elapsed-time
features are expected for candidates without prior overall or component
history; count/score features use zero for that no-history case.

The Spearman correlation analysis is computed over numeric evaluation features
only. Developer expertise distribution is a snapshot at the latest training
prediction timestamp for the 79 training candidates. Activity-group comparison
labels developers at or above the snapshot's median historical bug count as
`high_activity`, and those below it as `low_activity`.

### Example generated evaluation feature row

This is an actual seen-target candidate row from the generated evaluation
dataset. It is an illustration of the feature schema, not a model result.

| Field | Value |
|---|---|
| `bug_id` | 308612 |
| `prediction_timestamp_utc` | 2010-04-09T07:54:03Z |
| `component` | Text |
| `candidate_developer_id` | `daniel_megert@ch.ibm.com` |
| `is_ground_truth_candidate` | true |
| `historical_bug_count` | 55 |
| `historical_active_days` | 53 |
| `component_experience_count` | 24 |
| `component_experience_share` | 0.4364 |
| `recent_activity_count_30d` / `_90d` | 0 / 1 |
| `recent_component_count_30d` / `_90d` | 0 / 0 |
| `days_since_last_activity` | 31.3450 |
| `days_since_last_component` | 120.6768 |
| `similar_bug_count` | 0 |

## Generated files

All CSV/JSON outputs below are local processed artifacts:

- `data/processed/jdt_phase3_feature_train.csv`
- `data/processed/jdt_phase3_feature_evaluation.csv`
- `data/processed/jdt_phase3_feature_summary.csv`
- `data/processed/jdt_phase3_feature_missingness.csv`
- `data/processed/jdt_phase3_feature_correlations.csv`
- `data/processed/jdt_phase3_developer_expertise_distribution.csv`
- `data/processed/jdt_phase3_activity_group_comparison.csv`
- `data/processed/jdt_phase3_feature_metadata.json`

Implementation and test changes:

- Added `ml_model/generate_jdt_phase3_features.py`.
- Extended `ml_model/jdt_recommendation.py` with active-day and 30/90-day
  overall/component activity features; recommendation evidence includes them.
- Extended `tests/ml/test_jdt_pipeline.py` for activity windows, exact cutoff,
  timestamp validation, and feature-table identifier/label handling.
- Updated the root `README.md` and the existing Phase 3 evaluation report with
  the feature-generation command and artifacts.

## Validation and limitations

- Focused Member 2 pipeline tests: 13 passed.
- Complete repository test suite: 37 passed.
- Python compilation and `git diff --check`: passed.
- Existing chronological split remains 1,298 training / 331 evaluation bugs;
  no Phase 2 model training was run as part of this phase.
- The data lacks historical versions of bug titles/descriptions, so the exact
  text visible at each prediction timestamp cannot be verified.
- The evaluation candidate set does not include developers unseen during
  training. The 188 such evaluation targets remain cold-start cases.
- Feature rows cover the 79-developer training candidate set, not all 335
  identities in the aggregate source profiles. Other verified developers
  remain evaluation cold-start targets rather than candidates with invented
  or provisional history.
- Assignment-event timing is used as the point at which historical expertise
  becomes available; this assumption follows the verified dataset but may not
  reflect any additional source-system ingestion delay.
