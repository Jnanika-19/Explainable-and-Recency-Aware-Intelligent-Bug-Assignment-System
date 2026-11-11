# Member 2 Phase 7: Final Chronological Evaluation

## Scope and reproducibility

This evaluation reuses the saved Phase 2 baseline, Phase 4 model, and Phase 5
public API. It does not retrain, tune, overwrite previous phase results, or
modify original CSVs. The chronological test split has 331 verified
`known_entry` bugs; the training partition has 1298 verified bugs and
79 candidate developers. Training assignments are strictly
before the first test prediction timestamp. Test labels are used only for
final evaluation, never for features, model selection, or explanation history.

The evaluator independently reconstructs Phase 2 and Phase 4 rankings, checks
Phase 4 Top-5 against its frozen prediction output, then calls
`recommend_developers` on every test bug with the full roster. The Phase 5 API
rank order matched Phase 4 for all 331 bugs. Its reported metrics
therefore describe the exact Phase 5 implementation, not a separately trained
model. All results are checked against the saved Phase 4 comparison before
writing these new Phase 7 outputs.

## Results

Top-K accuracy/recall is the fraction of bug targets found in the first K
positions. Precision@K is hit fraction divided by K. Top-1 micro precision,
recall, and F1 equal Top-1 accuracy for this single-target task. MRR averages
the reciprocal rank over the complete 79-candidate ranking; targets outside
the roster count as zero.

| Model | Cohort (n) | Top-1 | Top-3 | Top-5 | P@5 | R@5 | MRR | Top-1 P/R/F1 |
|---|---|---|---|---|---|---|---|---|
| phase2_linear_svm | all_test_records (331) | 0.0363 | 0.0846 | 0.1269 | 0.0254 | 0.1269 | 0.0838 | 0.0363 / 0.0363 / 0.0363 |
| phase2_linear_svm | seen_developer_targets (143) | 0.0839 | 0.1958 | 0.2937 | 0.0587 | 0.2937 | 0.1939 | 0.0839 / 0.0839 / 0.0839 |
| phase2_linear_svm | unseen_developer_targets (188) | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 / 0.0000 / 0.0000 |
| phase4_combined_linear_svm | all_test_records (331) | 0.1178 | 0.1994 | 0.2175 | 0.0435 | 0.2175 | 0.1841 | 0.1178 / 0.1178 / 0.1178 |
| phase4_combined_linear_svm | seen_developer_targets (143) | 0.2727 | 0.4615 | 0.5035 | 0.1007 | 0.5035 | 0.4261 | 0.2727 / 0.2727 / 0.2727 |
| phase4_combined_linear_svm | unseen_developer_targets (188) | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 / 0.0000 / 0.0000 |
| phase5_developer_recommender | all_test_records (331) | 0.1178 | 0.1994 | 0.2175 | 0.0435 | 0.2175 | 0.1841 | 0.1178 / 0.1178 / 0.1178 |
| phase5_developer_recommender | seen_developer_targets (143) | 0.2727 | 0.4615 | 0.5035 | 0.1007 | 0.5035 | 0.4261 | 0.2727 / 0.2727 / 0.2727 |
| phase5_developer_recommender | unseen_developer_targets (188) | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 / 0.0000 / 0.0000 |

### Baseline versus improved model

Across all test bugs, Phase 4 combined SVM Top-5 is
0.2175
versus Phase 2's
0.1269;
MRR is
0.1841
versus
0.0838.
Phase 5 is the same Phase 4 ranker wrapped with validated explanations; it is
not an independent model improvement.

## Seen and unseen developer performance

There are 143 seen-developer test targets and 188 targets
outside the 79-developer training roster. Seen-target metrics
are reported separately and must not be presented as overall performance.
Every unseen target is an unavoidable closed-roster miss for all three
systems; the overall denominator retains those rows.

## Error analysis

Phase 5 target-rank categories across the test set:

| Category | Bugs |
|---|---:|
| correct_at_rank_1 | 39 |
| seen_target_below_top_5 | 71 |
| seen_target_in_top_5_but_not_rank_1 | 33 |
| unseen_target_outside_candidate_roster | 188 |

Detailed bug-level ranks and categories are saved in
`data/processed/jdt_phase7_error_analysis.csv`. The test partition has
2 blank descriptions and 0 blank
components. Missing descriptions are accepted by the API as empty text;
missing component and invalid prediction timestamp are rejected and covered
by tests. The original processed test data are not altered.

## Leakage, missing values, and ranking checks

- Both partitions contain `known_entry` labels only; train/test bug IDs are
  disjoint and ordered chronologically.
- Every training assignment timestamp precedes the first test creation time.
- Phase 3 history is generated from verified training events only and admits
  events strictly earlier than each prediction timestamp.
- The Phase 4 artifact metadata records developer/target IDs as excluded from
  predictive inputs and the test split as excluded from tuning.
- Text and metadata transforms are loaded from fitted artifacts and never
  refit during final evaluation.
- The Phase 5 API's full ranked list matched the Phase 4 ranking for every
  holdout bug, including deterministic score-tie ordering.
- The explainability layer validates expertise, recency, similarity, and
  additive model-margin consistency. No missing history is imputed as an
  invented assignment.

## Runtime

The measured workload made 331 sequential API calls (the first includes
artifact loading; later calls reuse cached resources), each returning
explanations for the complete 79-developer roster over the chronological test
set:

| Measurement | Seconds |
|---|---:|
| Total | 262.1693 |
| Mean/query | 0.792052 |
| Median/query | 0.785060 |
| P95/query | 0.870277 |
| Maximum/query | 1.337437 |
| First query (includes cached artifact load) | 1.128497 |

This is a local sequential measurement, not a production latency guarantee.
Top-5 API responses construct fewer explanation payloads than this
full-roster measurement; all candidates must still be scored.

## Scenario validation and tests

The suite covers complete bug input, missing title/description, missing
component, invalid timestamps, empty and singleton candidate sets, new
cold-start developers, extensive verified history, old versus recent
component activity, stable ties, model contribution arithmetic, score
consistency, and rejection of provisional history. Phase 7 also executes the
public API on every real holdout row. The complete test suite result is
67 passed, 0 failed (`pytest -q tests` with an isolated workspace temp
directory).

## Limitations

There is one chronological holdout with 331 bugs, and 188 (56.8%) targets
are outside the candidate roster. Thus seen-developer performance is not
overall deployment performance. The task has a highly imbalanced one-positive
candidate-pair label. Historical bug-text snapshots are unavailable, so
point-in-time text visibility cannot be proven. The dataset has no reliable
resolution timestamp; resolution-time features remain unavailable. More
temporal cutoffs, a vetted cold-start roster, calibration, and real integration
load testing are needed before operational claims.

## Generated files

- `data/processed/jdt_phase7_final_model_comparison.csv`
- `data/processed/jdt_phase7_error_analysis.csv`
- `data/processed/jdt_phase7_performance.json`
- `docs/member2_phase7_final_evaluation.md`
