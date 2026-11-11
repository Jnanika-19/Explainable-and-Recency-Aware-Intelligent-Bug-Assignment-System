# Member 2: Machine Learning and Developer Expertise

This module contains a verified JDT assignment experiment and older generic
BugWise helpers. The workflow below refers specifically to the JDT `known_entry`
dataset and artifacts; do not use `ml_model.train_model` or profiles computed
from an unrestricted full dataset as substitutes for the leakage-safe JDT
pipeline.

## Responsibilities and architecture

Member 2 owns text preprocessing for the JDT experiment, verified-assignment
expertise and recency features, candidate ranking models, evaluation, and
evidence-grounded ML explanations. Member 2 returns ranked ML recommendations
and evidence; Member 3 owns workload-aware scoring and final assignment.
Member 4 may call the same recommendation function from the backend without
copying the model or feature logic.

```text
Bug report
  -> title/description normalization
  -> training-fitted title and description TF-IDF
  -> strictly prior verified expertise and recency features
  -> saved Phase 4 combined LinearSVC
  -> ranked candidate recommendations
  -> evidence explanation + additive model contribution
  -> structured response to Member 3 / Member 4
```

## Dataset and preprocessing

The inspected source has 33,246 JDT records: 1,651 verified `known_entry`
assignments and 31,595 `provisional` assignments. Only verified labels enter
supervised training and history; provisional records are excluded. The
chronological experiment uses 1,298 training bugs and 331 holdout bugs; 22
records are excluded because their assignment events were unavailable at the
split cutoff. The separate developer profile and component expertise CSVs
are not used as full-dataset predictive aggregates.

`ml_model.preprocess_jdt` normalizes IDs, text, label types, and timestamps
without changing source CSVs. The chronological split keeps only labels
available before the prediction cutoff. Text transforms fit on training data
and are reused, not refit, at evaluation/inference time.

```powershell
.\.venv\Scripts\python.exe -m ml_model.preprocess_jdt
.\.venv\Scripts\python.exe -m ml_model.train_jdt_baselines
.\.venv\Scripts\python.exe -m ml_model.generate_jdt_phase3_features
.\.venv\Scripts\python.exe -m ml_model.run_jdt_phase3
.\.venv\Scripts\python.exe -m ml_model.train_jdt_phase4
```

## Expertise and recency

`ml_model.jdt_recommendation.build_temporal_candidate_features` maintains
point-in-time candidate evidence using only `known_entry` training assignments
whose `assignment_time` is strictly earlier than the bug prediction timestamp.
It computes total prior verified bugs, distinct active days, component count
and share, similar historical bug-text counts/similarities, 30/90/365-day
activity, time since last overall/component assignment, expertise, and
component recency. No-history counts/scores are zero; elapsed times remain
missing rather than receiving fabricated dates.

Key score calculations:

- Expertise: `component_count / (component_count + 2)`.
- Component relevance: `component_count / historical_bug_count`, or zero
  without prior history.
- Recency: `exp(-days_since_last_component / 365)`, or zero without component
  history.
- Similar-bug experience: `min(1, similarity_sum / max(1, sqrt(history_count)))`;
  a historical description counts as similar at cosine similarity `>= 0.20`.

The dataset has no dependable resolution timestamp, so resolution-time
features are not calculated. Historical text snapshots are unavailable, so
point-in-time availability of old bug text cannot be proven.

## Models and evaluation

Phase 2 trained Logistic Regression, LinearSVC, and Random Forest on
training-only title/description TF-IDF; LinearSVC is the text-only baseline.
Phase 4 tuned combined candidate-pair LinearSVC and Logistic Regression over
an inner chronological validation split of training data only. The saved
LinearSVC artifact combines text, product/component/severity/priority metadata,
and numeric Phase 3 candidate features. Candidate/target IDs are not model
inputs. Balanced class weights are used; no oversampling is applied.

The final report evaluates 331 chronological test bugs (143 seen-target rows,
188 targets outside the fixed 79-developer roster) and separates all, seen,
and unseen cohorts. The combined LinearSVC achieved overall Top-1 0.1178,
Top-3 0.1994, Top-5 0.2175, and MRR 0.1841; the Phase 2 SVM achieved 0.0363,
0.0846, 0.1269, and 0.0838 respectively. Unseen-target ranking metrics are
zero because the closed candidate set cannot return developers absent from
training. Phase 5 uses the same Phase 4 ranker; explanations do not create a
new model or an independent performance gain.

Run final reproducibility checks without training or overwriting prior model
artifacts:

```powershell
.\.venv\Scripts\python.exe -m ml_model.evaluate_member2_final
.\.venv\Scripts\python.exe -m pytest -q tests
```

See `docs/member2_phase7_final_evaluation.md` and the `jdt_phase7_*` processed
outputs for full metrics, per-bug error categories, and local API timing.

## Recommender and explainability

```python
from ml_model.developer_recommender import recommend_developers

result = recommend_developers(
    {
        "bug_id": "BUG-001",
        "title": "Null pointer in editor",
        "description": "Editor throws a null pointer on refresh",
        "component": "Core",
        "severity": "major",
        "priority": "P1",
        "prediction_timestamp": "2020-01-10T00:00:00Z",
    },
    top_k=3,
)
```

`result` is a mapping with `bug_id` and a ranked `recommendations` list.
Each item contains the developer ID/rank, uncalibrated LinearSVC margin,
expertise/recency/component/similar-bug scores, cold-start status, underlying
counts/times, supporting evidence, and a main explanation. The default
candidate set is the saved 79-developer roster. Callers can supply a trusted
`candidates` roster; developers without history stay eligible and are marked
cold-start. The API requires a component (or module) and prediction timestamp;
title/description may be empty.

`ml_model.explainability` validates evidence and score consistency. Because
the selected model is binary LinearSVC, it also decomposes the raw decision
margin additively into title TF-IDF, description TF-IDF, bug metadata, and
developer expertise/recency feature groups. The group contributions plus the
intercept reconstruct the margin. This is model interpretation, not a
probability, causal explanation, or assertion that a developer has a skill.
No SHAP/LIME dependency is required.

## Team integration

Member 3 may take `recommendations` as candidate relevance/evidence input and
apply workload, assignment policy, and final scoring separately. Member 4's
Python backend can call `recommend_developers` directly, pass the structured
mapping to its JSON response, and keep final assignment logic outside this
module. Default model/data/vectorizer paths are relative to the project root;
missing artifacts raise `FileNotFoundError`, invalid request/history data
raise `ValueError`, and unexpected model errors are not converted into fake
success responses.

Run a real-data demonstration with developer IDs redacted from printed output:

```powershell
.\.venv\Scripts\python.exe -m ml_model.demo_member2_integration --top-k 3
```

The demonstration reads an existing holdout bug and performs inference only;
it is not a new metric calculation. The clearly marked unit-test request
fixture is `tests/fixtures/member2_bug_report.json` and is not a real dataset
record or model evaluation example.

## Documentation and limitations

- `docs/member2_phase3_feature_engineering.md`
- `docs/member2_phase4_modeling.md`
- `docs/member2_phase5_recommendation_engine.md`
- `docs/member2_phase7_final_evaluation.md`
- `docs/member2_phase8_integration.md`
- `docs/member2_final_contribution.md`

The candidate ranker is closed-set by default, has limited verified labels
and one evaluation cutoff, cannot establish historical text visibility, and
does not provide calibrated probabilities. The measured full-roster inference
latency is local and is not a production service-level guarantee. A
production candidate roster, extra temporal evaluation cutoffs, calibration,
and backend/load testing remain team integration work.
