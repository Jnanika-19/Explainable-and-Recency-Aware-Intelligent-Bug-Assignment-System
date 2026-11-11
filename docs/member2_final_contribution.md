# Member 2: Final Contribution

## Problem addressed

Member 2 provides a leakage-aware ML ranking of developers for a new JDT bug,
uses verified historical assignments for expertise and recency evidence,
explains each recommendation from computed facts, and exposes a structured
interface for Member 3's scoring engine and Member 4's backend.

## Work completed by phase

| Phase | Contribution |
|---|---|
| 1 — Inspection | Inspected the original JDT datasets, labels, timestamp and developer-ID fields, missingness, duplicates, and trainable verified records. Original CSVs remain unchanged. |
| 2 — Preprocessing/baselines | Created a `known_entry`-only chronological split, training-only TF-IDF, and Logistic Regression, LinearSVC, and Random Forest baselines with class weighting. |
| 3 — Expertise/recency | Added candidate-level counts, component expertise, similar historical bug text, recent 30/90/365-day activity, and elapsed-time features with a strict prior-assignment cutoff. |
| 4 — Combined model | Tuned LinearSVC and Logistic Regression on an inner chronological training/validation split; evaluated once on the frozen outer holdout. |
| 5 — Recommendation | Added `recommend_developers`, a stable ranked output with raw model margin, relevance evidence, cold-start handling, and Member 3 integration boundary. |
| 6 — Explainability | Added structured evidence explanations and exact additive LinearSVC feature-group margin contributions with score/evidence consistency checks. |
| 7 — Final evaluation | Reconstructed Phase 2/4 rankings, invoked the Phase 5 API on all 331 holdout bugs, validated exact rank parity, and wrote new comparison, error-analysis, performance, and report artifacts. |
| 8 — Integration/docs | Documented Member 3/4 contracts, added a marked request fixture and redacted real-data demo, updated the ML README, and wrote this contribution summary. |

## Algorithms and techniques

- Title and description unigram/bigram TF-IDF fitted only on the applicable
  chronological training partition.
- Balanced class weights to address candidate-pair imbalance; no SMOTE or
  synthetic oversampling.
- Phase 2 text-only Logistic Regression, Linear SVM, and Random Forest
  baselines.
- Phase 4 candidate-pair combined LinearSVC and Logistic Regression using
  bug text, bug metadata, and prior verified expertise/recency.
- Strict historical event eligibility:
  `assignment_time < prediction_timestamp`.
- Phase 6 exact linear decomposition `feature_value * coefficient`, grouped
  into title TF-IDF, description TF-IDF, bug metadata, and developer
  expertise/recency. Group sums plus intercept reconstruct the raw margin.
- No SHAP/LIME package, because the saved binary LinearSVC supports exact
  additive contributions directly.
- Model rank comes from the uncalibrated LinearSVC margin; evidence scores
  are returned separately and are not combined into a duplicate Member 3
  score.

## Data and final model results

The source dataset contains 33,246 rows: 1,651 verified `known_entry`
assignments and 31,595 provisional assignments. The supervised split uses
1,298 training bugs and 331 holdout bugs; 22 earlier-created records are
excluded because their assignment events were unavailable at the cutoff.
Provisional records are not supervised targets or history features.

The frozen test set has 143 seen-developer targets and 188 unseen-developer
targets. Overall results (unseen targets remain misses):

| Model | Top-1 | Top-3 | Top-5 | MRR |
|---|---:|---:|---:|---:|
| Phase 2 text-only Linear SVM | 0.0363 | 0.0846 | 0.1269 | 0.0838 |
| Phase 4 combined LinearSVC | 0.1178 | 0.1994 | 0.2175 | 0.1841 |
| Phase 5 recommendation API | 0.1178 | 0.1994 | 0.2175 | 0.1841 |

Phase 4 and Phase 5 share the same trained ranker; the equality is expected,
and Phase 5 is not a new model-performance gain. Seen-developer Top-5 is
0.2937 for the Phase 2 SVM and 0.5035 for Phase 4/5. All unseen-target
ranking metrics are zero because those target IDs are outside the fixed
79-developer roster.

Full results, precision/recall, cohorts, error categories, and local latency
are in `docs/member2_phase7_final_evaluation.md` and the `jdt_phase7_*` files
under `data/processed/`. The public API ranking exactly matched the Phase 4
ranking on all 331 test bugs. The measured full-roster API median was
0.785 seconds/query and P95 was 0.870 seconds/query in a local sequential
run; these values are not a production SLA.

## Files created in Phases 6–8

- `ml_model/explainability.py`
- `ml_model/evaluate_member2_final.py`
- `ml_model/demo_member2_integration.py`
- `tests/ml/test_explainability.py`
- `tests/fixtures/member2_bug_report.json` — marked unit-test-only fixture.
- `docs/member2_phase7_final_evaluation.md`
- `docs/member2_phase8_integration.md`
- `docs/member2_final_contribution.md`
- `data/processed/jdt_phase7_final_model_comparison.csv`
- `data/processed/jdt_phase7_error_analysis.csv`
- `data/processed/jdt_phase7_performance.json`

## Files modified in Phases 6–8

- `ml_model/developer_recommender.py` — exposes structured explanations and
  exact model contribution details while preserving Phase 5 ranking order.
- `tests/ml/test_developer_recommender.py` — reads the marked request fixture.
- `ml_model/README.md` — documents the current verified JDT workflow and
  integrations.

Existing Phase 2–5 scripts, tests, reports, and model artifacts were inspected
and reused; they were not retrained or overwritten during Phase 6–8.

## Testing

The initial Phase 3–5 preflight suite passed 56 tests. Phase 6 added tests for
evidence-grounded explanation text, cold start, old and extensive verified
history, score consistency, invalid inputs, and exact additive LinearSVC
margin reconstruction. A focused recommender/explainability run passed 26
tests. Final complete suite: **67 passed, 0 failed**.

## Individual contribution and limitations

Member 2 owns the dataset-specific ML preprocessing, candidate feature
engineering, baseline and combined models, ranking interface, explanation
payload, and isolated evaluation/docs. Member 2 does not own the original
source data, Member 3's final score, or Member 4's backend/frontend.

The experiment uses one chronological holdout with 331 bugs and a closed
79-developer roster. Cold-start targets cannot be recommended without a
separately vetted roster/source and suitable training evidence. The dataset
does not provide reliable resolution times or historical text snapshots.
Linear margins are uncalibrated. Additional temporal cutoffs, probability
calibration if needed, backend identity authorization, workload integration,
and concurrent load testing remain future/team integration work.
