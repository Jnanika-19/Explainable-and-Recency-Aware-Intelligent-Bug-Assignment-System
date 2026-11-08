# Machine Learning and Developer Expertise

This module turns mapped historical assignments into developer profiles, a TF-IDF and metadata recommendation model, validation metrics, and a top-five ranking interface.

## Dataset contract

Use a CSV and a JSON schema file mapping canonical names to the dataset's exact column names. Copy `research/dataset_documentation/schema.template.json`, edit it after inspecting the real CSV headers, and remove mappings for optional columns that are not present. Required canonical fields are `bug_id`, `developer_id`, `title`, and `description`. Chronological evaluation also requires a valid `created_at` timestamp on every usable row. Configure `resolved_values` only after confirming the dataset's actual status values.

To inspect a dataset without assuming column names:

```powershell
python -c "from preprocessing.data_cleaning.schema import inspect_csv; print(inspect_csv('data/processed/bugs.csv'))"
```

## Train and compare

```powershell
python -m ml_model.train_model --data data/processed/bugs.csv --schema research/dataset_documentation/schema.json --artifact models/developer_recommender.joblib --results results
```

Training compares fixed features with adaptive chi-square selection on a chronological holdout, records ranking metrics and timing in `results/model_metrics.csv`, saves feature importance outputs, then refits the selected pipeline on all supplied history. No result files are included until training is run on real data.

## Rank a new bug

Create a JSON file with the canonical keys `bug_id`, `title`, `description`, and optional metadata. Then run:

```powershell
python -m ml_model.rank_developers --bug new_bug.json --artifact models/developer_recommender.joblib --output results/developer_rankings.csv
```

The Python integration function is `ml_model.rank_developers.rank_developers(bug, bundle, top_k=5)`. It returns `{"bug_id": ..., "recommendations": [...]}` with developer IDs, model relevance scores, component/product experience, similar bug IDs, and counts. Member 3 can pass that response to `scoring_engine.final_scoring.apply_intelligent_scoring`.

## Limits

The classifier recommends only developers represented in its training history. New developer cold start needs a roster/profile source. Similarity evidence is TF-IDF cosine retrieval. Workload is neutral unless supplied to the scoring function. Feature importance is Random Forest impurity importance and should be interpreted cautiously. There is currently no dataset, so the model and metrics have not yet been produced.
