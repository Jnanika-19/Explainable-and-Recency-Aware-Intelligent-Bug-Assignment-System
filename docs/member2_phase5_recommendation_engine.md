# Member 2 Phase 5: Developer Recommendation Engine

## Objective

Phase 5 exposes the validated Phase 4 combined Linear SVM as a callable
developer-recommendation interface. It returns an ML-ranked candidate list and
the verified expertise and recency evidence already calculated by the Phase 3
temporal feature builder. It does not make the final assignment decision or
apply Member 3 workload constraints.

## Architecture and candidate policy

The public entry point is
`ml_model.developer_recommender.recommend_developers(bug_report, top_k=3)`.
The default call loads the saved `combined_linear_svm.joblib`, the Phase 2
`known_entry` training history, and the training-fitted TF-IDF similarity
vectorizer. Dependencies are cached for later calls.

By default, candidates are the 79 developer IDs in the Phase 4 model artifact.
This intentionally matches the validated Phase 4 training roster; therefore,
the default call cannot return a developer outside that roster. Integrators
may pass `candidates=[...]` to score a broader, trusted roster. A candidate
with no verified assignment before the prediction cutoff remains eligible and
is returned with zero historical evidence and `cold_start: true`. The caller
is responsible for supplying an authorized candidate roster; the model does
not infer employees from provisional records or other unverified sources.

## Input contract

`bug_report` is a mapping with:

| Field | Required | Meaning |
|---|---|---|
| `title` | No | Bug title; absent/`None` becomes empty text. |
| `description` | No | Bug description; absent/`None` becomes empty text. |
| `component` or `module` | Yes | Component value corresponding to the training data. |
| `prediction_timestamp` or `created_at` | Yes | Time at which the recommendation is made; parsed as UTC. |
| `bug_id` | No | Returned as provided; numeric IDs are used internally by the feature pipeline. |
| `product`, `severity`, `priority` | No | Metadata for the Phase 4 model; missing product uses the training-history mode, while missing severity/priority are empty strings. |

`top_k` must be a positive integer. The optional keyword-only `candidates`
argument accepts candidate developer IDs. For testing or controlled
integration, `model_artifact`, `history`, and `similarity_vectorizer` can also
be supplied; normal application calls should use the saved defaults.

Example:

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

## Feature and ranking method

The Phase 3 feature builder is run at the supplied prediction timestamp for
each candidate. Its history consists only of verified `known_entry` training
events with `assignment_time < prediction_timestamp`; equal-time and future
events are excluded. The TF-IDF similarity vectorizer is the Phase 2
training-fitted vectorizer, and Phase 4 bug-text/metadata/numeric transforms
are reused without refitting. Developer IDs are candidate identifiers, not
predictive input columns.

The saved Phase 4 Linear SVM scores each bug-candidate pair. Recommendations
are sorted by descending `decision_function` margin, then ascending developer
ID for stable ties. No manually weighted combination is applied. The model
roster, transforms, and trained classifier are those selected and evaluated
in Phase 4; Phase 5 does not tune on test labels.

Returned numeric evidence:

| Output | Definition |
|---|---|
| `ml_score` | Raw, **uncalibrated** LinearSVC decision margin; it is not a probability and should not be compared as calibrated confidence across bugs. |
| `expertise_score` | Component assignment count divided by `(component assignment count + 2)`; bounded to `[0, 1]`. |
| `component_relevance` | Verified assignments in the bug component divided by all prior verified assignments; zero with no history. |
| `recency_score` | `exp(-days_since_last_component_assignment / 365)`; zero when no prior component assignment exists. |
| `similar_bug_experience_score` | Similarity sum scaled by the square root of prior verified bug count and capped at `1`; see `similar_bug_score_method` in evidence. |

`evidence` includes the underlying counts, component share, elapsed times,
recent 30/90-day counts, maximum cosine similarity, and score formulas.
`explanations` are generated only when supported by the computed history:
component assignment evidence, above-threshold similar bugs, elapsed time
since the last relevant assignment, or an explicit no-history statement.
No technical skills or expertise beyond the source data are inferred.

## Output contract

The result has a `bug_id` and a `recommendations` list, capped at `top_k` and
the number of candidates. Each recommendation contains:

```json
{
  "developer_id": "Dev-A",
  "rank": 1,
  "ml_score": 5.0,
  "ml_score_type": "uncalibrated Phase 4 LinearSVC decision margin",
  "expertise_score": 0.3333,
  "recency_score": 0.9783,
  "component_relevance": 1.0,
  "similar_bug_experience_score": 0.9658,
  "cold_start": false,
  "evidence": {},
  "explanations": ["1 verified prior assignment(s) in Core."]
}
```

The example is from a deterministic unit-test fixture with a fixed-margin
test double; its scores are illustrative and are **not** Phase 4 model
predictions.

## Member 3 integration boundary

- **Function:** `recommend_developers(bug_report, top_k=3, *, candidates=None, ...)`
- **Input:** Mapping described above; Member 3 may provide its eligible
  developer IDs through `candidates`.
- **Output:** Ranked ML candidates plus raw model margin and independently
  computed evidence scores.
- **Score interpretation:** The margin establishes model rank; expertise,
  recency, component, and similar-bug scores are separate evidence and are
  not combined into another final score here.
- **Ownership:** Member 3 remains responsible for combining recommendation
  evidence with workload, assignment policy, and final assignment decisions.
- **Errors:** Invalid request fields, timestamps, roster, history schema, or
  non-verified history raise `ValueError`. Missing default model/data/vectorizer
  files raise `FileNotFoundError`. Unexpected model/runtime errors are not
  hidden by fallback recommendations.

## Validation and limitations

Phase 5 tests exercise request validation, missing title/description,
component validation, empty/one/many candidates, Top-3/Top-5 truncation,
cold-start candidates, missing history, strict prediction-time cutoffs,
stable ties, invalid timestamps, and rejection of provisional history. The
captured test-fixture response is documented above. An additional end-to-end
smoke check loaded the actual saved Phase 4 model, training history, and
vectorizer and ranked a real chronological holdout bug; this is an inference
smoke check, not a new evaluation or a performance claim.

The default 79-person roster cannot recommend developers unseen during model
training; passing an external roster allows scoring them, but the model has no
learned positive examples for such IDs. Bug-description history is limited to
available training records and the frozen text vectorizer. The dataset does
not provide a dependable resolution-time field, so no resolution-duration
explanation is included. Point-in-time availability of historical bug text
cannot be established from the available snapshots.

## Files and test status

- Created `ml_model/developer_recommender.py`,
  `tests/ml/test_developer_recommender.py`, and this Phase 5 report.
- Updated the Member 2 workflow section in `README.md`.
- Focused Phase 5 validation: 15 passed.
- Full project suite: 56 passed.
