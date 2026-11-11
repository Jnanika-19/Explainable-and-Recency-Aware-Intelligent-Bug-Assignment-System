# Initial ML Methodology

Historical assigned bugs are the labeled examples; the assigned developer is the target. Text features use a train-fitted TF-IDF vectorizer over title and description. Product, component, severity, and priority use train-fitted one-hot encoding when mapped into the canonical schema. Missing optional metadata is represented as empty/unknown input. Developer profiles and similar resolved bug evidence are built from the history available to the caller.

Evaluation uses a chronological split by `created_at`; developers absent from the training period cannot be predicted by a closed-set classifier and are excluded from the comparable evaluation rows. The fixed-feature Random Forest is compared with the same classifier after adaptive chi-square percentile selection. Metrics are Precision@5, Recall@5, MRR, and MAP. Training and prediction time are recorded. The pipeline is refit on all provided history only after validation, then saved for inference.

The current repository contains no source dataset. Therefore no performance result, selected feature list, or accuracy claim is available until a real dataset and explicit schema mapping are supplied. The present weighted scoring factors are initial transparent heuristics, not empirically optimized coefficients; the confidence label is a ranking-margin heuristic, not a calibrated probability.
