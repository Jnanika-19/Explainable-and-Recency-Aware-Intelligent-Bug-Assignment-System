# Member 2 Phase 4: Combined Feature Model

## Objective and execution

Phase 4 compares the frozen Phase 2 Linear SVM baseline with candidate-level
models that combine title/description TF-IDF, bug metadata, and the verified
Phase 3 expertise and recency features. The script tunes only on an inner
chronological split of the Phase 2 training partition, then evaluates selected
models once on the existing chronological test partition:

```powershell
.\.venv\Scripts\python.exe -m ml_model.train_jdt_phase4
```

The script does not retrain or overwrite Phase 2 models. Phase 4 outputs use
new `jdt_phase4_*` names under `data/processed/` and `models/jdt_phase4/`.

## Candidate feature model

Each bug-candidate pair is a binary classification example. The positive label
means the candidate ID equals the verified target ID; the target and
candidate IDs are not included in the predictive matrix.

Predictive inputs:

- Separate TF-IDF vectorizers for bug title and description, unigram/bigram
  terms, each capped at 15,000 features.
- One-hot bug metadata: product, component, severity, and priority.
- All numeric Phase 3 expertise/recency features in
  `ml_model.jdt_recommendation.FEATURE_COLUMNS`.
- Missing elapsed-time indicators for last overall and last component
  assignment; absent elapsed values are numerically filled with zero and
  distinguished by those indicators.

The feature transformer (TF-IDF, one-hot encoder, and numeric scaler) is fit
only on the corresponding training partition. At each bug prediction time,
expertise history contains only verified training assignment events strictly
before that time. The evaluation candidate set is fixed to the 79 developers
observed in the outer training split. No provisional target or full-dataset
profile aggregate is used.

## Tuning protocol

The 1,298-row outer training partition is split chronologically again for
hyperparameter selection. TF-IDF vectorizers and metadata/numeric transformers
are fit only on the inner training portion. Expertise features for inner
validation are built from inner training assignments only. The existing
outer test split is not used to select parameters.

Both candidate models use balanced class weights to address the one-positive
per-bug versus many-negative-candidates imbalance; no synthetic oversampling
is used:

- `LinearSVC`, tuned over `C = 0.1, 1, 10`.
- `LogisticRegression` with `liblinear`, tuned over `C = 0.1, 1, 10`.

Mean Reciprocal Rank (MRR) on inner validation is the primary selection
metric. Top-5 accuracy and smaller `C` break ties. The Phase 2 Linear SVM is
the unchanged baseline and is evaluated using its saved classifier and
training-only vectorizer.

## Evaluation

Report Top-1, Top-3, Top-5, Precision@K, Recall@K, MRR, and top-1
classification precision/recall/F1 for:

- All 331 chronological test bugs.
- The 143 bugs assigned to developers seen in outer training.
- The 188 unseen-developer targets.

Unseen targets remain misses in overall evaluation; they are not removed from
the denominator. Candidate pair ranking cannot recommend developers outside
the fixed 79-developer candidate set.

Full results, selected hyperparameters, sample recommendations, and the
comparison against the Phase 2 baseline are recorded in
`data/processed/jdt_phase4_evaluation_report.md`,
`data/processed/jdt_phase4_model_comparison.csv`,
`data/processed/jdt_phase4_hyperparameter_tuning.csv`, and
`data/processed/jdt_phase4_test_predictions.csv`.

## Limitations

There are only 1,298 training bugs and substantial developer class imbalance.
The same bug is expanded to one candidate row per developer; pair rows from a
bug are kept together by the chronological split. Title/description version
history is unavailable, so point-in-time text availability cannot be proven.
The held-out candidate set has no cold-start roster for developers unseen
during training. Any improvement is limited to this one temporal holdout and
requires additional cutoffs before generalization claims.
