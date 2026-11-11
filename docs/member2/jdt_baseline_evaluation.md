# JDT Text Baseline Evaluation

## Experiment

Run after preprocessing from the repository root:

```powershell
.\.venv\Scripts\python.exe -m ml_model.train_jdt_baselines
```

All three models use the same cleaned title-plus-description input and the same
TF-IDF matrix. TF-IDF is fitted only on the 1,298 training rows; it has a
30,000-feature cap and uses unigram/bigram terms. Class weights are enabled for
Logistic Regression and Linear SVM; Random Forest uses balanced subsample
weights. No resampling or SMOTE is used.

The chronological holdout has 1,298 training rows and 331 test rows. Training
contains 79 developer classes. Of the 331 test assignments, 143 belong to one
of those classes and 188 are assigned to a developer absent from training.
All rows remain in evaluation; an unseen developer is a failed closed-set
prediction, not a row dropped from the denominator.

## Classification metrics

Precision, recall, and F1 are measured on top-1 predictions across all 331 test
rows. Micro metrics equal exact-match accuracy in this single-label task.

| Model | Micro P/R/F1 | Macro precision | Macro recall | Macro F1 | Weighted precision | Weighted recall | Weighted F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| TF-IDF + Logistic Regression | 0.0211 | 0.0091 | 0.0109 | 0.0073 | 0.0498 | 0.0211 | 0.0232 |
| TF-IDF + Linear SVM | 0.0363 | 0.0136 | 0.0119 | 0.0098 | 0.0854 | 0.0363 | 0.0440 |
| TF-IDF + Random Forest | 0.0121 | 0.0044 | 0.0030 | 0.0027 | 0.0338 | 0.0121 | 0.0143 |

## Ranking metrics

Each bug has one relevant developer. Top-K accuracy/recall is the fraction of
all test rows whose actual developer appears in the first K candidates.
Precision@K divides the number of hits by K for each row, then averages.
MRR averages the reciprocal rank; an unseen developer has reciprocal rank zero.

| Model | Top-1 accuracy | Top-3 accuracy | Top-5 accuracy | Precision@1 | Recall@1 | Precision@3 | Recall@3 | Precision@5 | Recall@5 | MRR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| TF-IDF + Logistic Regression | 0.0211 | 0.0574 | 0.0967 | 0.0211 | 0.0211 | 0.0191 | 0.0574 | 0.0193 | 0.0967 | 0.0605 |
| TF-IDF + Linear SVM | 0.0363 | 0.0846 | 0.1269 | 0.0363 | 0.0363 | 0.0282 | 0.0846 | 0.0254 | 0.1269 | 0.0838 |
| TF-IDF + Random Forest | 0.0121 | 0.0393 | 0.0634 | 0.0121 | 0.0121 | 0.0131 | 0.0393 | 0.0127 | 0.0634 | 0.0446 |

The Linear SVM is the strongest of these three simple baselines on this holdout,
but its 12.69% top-5 accuracy over the complete test population is not evidence
of a successful or deployment-ready recommender. Coverage is the main structural
limitation: 56.8% of test rows have a target developer never observed in
training. Results are one chronological holdout without hyperparameter tuning.

## Artifacts

The ignored local `data/processed/` directory contains:

- `jdt_baseline_model_comparison.csv` — full-precision classification and
  ranking metrics for all three models.
- `jdt_baseline_test_predictions.csv` — top-1 and top-5 test predictions.
- `jdt_baseline_model_metadata.json` — counts, settings, and artifact paths.
- `jdt_model_evaluation_report.md` — detailed run report.

The ignored `models/` directory contains the fitted training-only TF-IDF
vectorizer and three holdout-trained classifiers:

- `jdt_tfidf_vectorizer.joblib`
- `jdt_baseline_logistic_regression.joblib`
- `jdt_baseline_linear_svm.joblib`
- `jdt_baseline_random_forest.joblib`

The classifiers and vectorizer remain tied to this split. They are not refitted
on the full dataset, since that would invalidate the held-out evaluation.

## Leakage and interpretation limits

The models use only title and description. Full-dataset developer profile and
component aggregates are validated but never passed to the classifiers. The
separate temporal expertise table is computed using only verified assignment
events strictly before each test bug's creation time and is not a baseline
feature. Provisional assignments never serve as supervised targets.

The data has no historical versions of title/description. Although labels and
the split are time-gated, point-in-time availability of the supplied text cannot
be verified from these CSVs alone. This limitation must be resolved before
claiming a fully point-in-time production evaluation.
