# Member 2 Phase 8: ML Integration Contract

## Ownership boundary

Member 2 supplies leakage-safe developer relevance recommendations, underlying
expertise/recency evidence, and model/evidence explanations. Member 2 does not
make final assignment decisions or implement workload, availability, or
assignment-policy scoring. Member 3 consumes the recommendation list and
combines it with those constraints. Member 4 can call the same Python API from
the backend and serialize its structured result. No Member 3 or Member 4
modules are modified by this integration contract.

## Stable recommendation function

```python
from ml_model.developer_recommender import recommend_developers

result = recommend_developers(bug_report, top_k=3, candidates=None)
```

Default Phase 4 model, Phase 2 training-only history, and the fitted
similarity vectorizer are loaded from the project-root `models/` and
`data/processed/` folders and cached for the process. The optional
keyword-only `candidates` argument takes a trusted sequence of developer IDs.
If omitted, the function uses the saved 79-developer training roster. A
candidate with no eligible history remains in the list and is marked
`cold_start: true`; callers should not present this as history-backed
expertise.

### Input schema

`bug_report` is a mapping:

| Field | Requirement | Use |
|---|---|---|
| `bug_id` | Optional string/integer | Echoed in the response. |
| `title` | Optional string | Empty/missing title is treated as empty text. |
| `description` | Optional string | Empty/missing description is treated as empty text. |
| `component` or `module` | Required nonempty string | Component relevance and model metadata. |
| `prediction_timestamp` or `created_at` | Required valid timestamp | UTC prediction cutoff for historical evidence. |
| `product` | Optional string | Phase 4 metadata; defaults to training-history mode if missing. |
| `severity`, `priority` | Optional strings | Phase 4 metadata; empty when omitted. |

`top_k` must be a positive integer. Candidate identifiers must be nonempty
strings and unique after normalization. An empty candidate roster is an
explicit error, not an empty/success-shaped recommendation.

Example request (from a clearly marked unit-test fixture, not a real dataset
bug):

```json
{
  "bug_id": "BUG-001",
  "title": "Null pointer in editor",
  "description": "Editor throws a null pointer on refresh",
  "component": "Core",
  "severity": "major",
  "priority": "P1",
  "prediction_timestamp": "2020-01-10T00:00:00Z"
}
```

The fixture file is [member2_bug_report.json](../tests/fixtures/member2_bug_report.json).
It is a unit-test input only; it is not included in training or evaluation.

### Output schema

The function returns a JSON-serializable mapping containing `bug_id` and
`recommendations`. Each recommendation contains:

```json
{
  "developer_id": "<candidate identifier>",
  "rank": 1,
  "ml_score": "<uncalibrated LinearSVC decision margin>",
  "ml_score_type": "uncalibrated Phase 4 LinearSVC decision margin",
  "expertise_score": "<0..1>",
  "recency_score": "<0..1>",
  "component_relevance": "<0..1>",
  "similar_bug_experience_score": "<0..1>",
  "cold_start": false,
  "evidence": {
    "component": "<requested component>",
    "historical_verified_bug_count": "<count>",
    "verified_component_assignment_count": "<count>",
    "component_experience_share": "<ratio>",
    "similar_bug_count": "<count at cosine similarity >= 0.20>",
    "similar_bug_similarity_sum": "<cosine-similarity sum>",
    "max_similar_bug_cosine_similarity": "<0..1>",
    "recent_activity_count_30d": "<count>",
    "recent_activity_count_90d": "<count>",
    "recent_component_count_30d": "<count>",
    "recent_component_count_90d": "<count>",
    "days_since_last_component": "<days or null>"
  },
  "model_contribution": {
    "method": "LinearSVC additive grouped feature contributions (x_i * coefficient_i)",
    "feature_group_contributions": {
      "title_tfidf": "<signed margin contribution>",
      "description_tfidf": "<signed margin contribution>",
      "bug_metadata": "<signed margin contribution>",
      "developer_expertise_recency": "<signed margin contribution>"
    },
    "intercept": "<model intercept>",
    "decision_margin": "<same value as ml_score>",
    "reconstruction_error": "<approximately zero>"
  },
  "explanations": ["<legacy concise evidence reasons>"],
  "main_explanation": "<evidence-grounded summary>",
  "supporting_evidence": ["<computed facts>"],
  "component_experience": {},
  "similar_bug_evidence": {},
  "recent_activity_summary": {},
  "model_interpretation": "<margin group breakdown, not a causal claim>"
}
```

For unsupported model types in a test/injected artifact,
`model_contribution` and `model_interpretation` are `null`; the production
default Phase 4 LinearSVC returns additive group contributions. No attribution
library is used. Each contribution is the sparse feature value multiplied by
its LinearSVC coefficient and summed by feature group. The intercept plus
these group values reconstructs the raw decision margin. Positive/negative
signs describe movement in the candidate-positive margin, not probability or
causation.

### Score definitions

- `ml_score`: raw LinearSVC decision margin, used for ranking; not a
  probability or calibrated confidence.
- `expertise_score`: `component_count / (component_count + 2)`.
- `component_relevance`: `component_count / total_prior_verified_count`, or
  zero without history.
- `recency_score`: `exp(-days_since_last_component_assignment / 365)`, or
  zero without prior component history.
- `similar_bug_experience_score`:
  `min(1, similarity_sum / max(1, sqrt(prior_verified_bug_count)))`.
- `cold_start`: true precisely when the candidate has no prior verified
  assignment before the prediction timestamp.

The model margin ranks candidates; the evidence scores are separate. The
recommendation module does not blend them into a second weighted final score.

## Member 3 scoring-engine integration

Member 3 may pass its authorized candidate roster, then use the returned list
as evidence for its own workload, policy, and final score:

```python
ml_result = recommend_developers(
    bug_report,
    top_k=10,
    candidates=eligible_developer_ids,
)
final_result = member3_scoring_engine(ml_result["recommendations"], workload)
```

The final scoring function above is a placeholder for Member 3's existing
interface and must be replaced with its actual function name at integration.
Keep Member 3's weights, workload rules, and assignment decision outside
`ml_model/`.

## Member 4 backend integration

The Python backend should call the recommender inside its existing service
boundary after request validation, then return the result as JSON. It must not
retrain the model per request or expose an uncalibrated margin as confidence.

```python
from ml_model.developer_recommender import recommend_developers


def recommend_for_bug(request_data: dict) -> dict:
    return recommend_developers(
        {
            "bug_id": request_data.get("bug_id"),
            "title": request_data.get("title"),
            "description": request_data.get("description"),
            "component": request_data.get("component") or request_data.get("module"),
            "product": request_data.get("product"),
            "severity": request_data.get("severity"),
            "priority": request_data.get("priority"),
            "prediction_timestamp": request_data.get("created_at"),
        },
        top_k=5,
    )
```

Use the backend's established exception-to-HTTP mapping for `ValueError` and
`FileNotFoundError`; do not turn failures into a fake recommendation. Keep
model artifacts and processed training history available on the Python
service host. The function itself raises validation/resource errors and does
not make HTTP assumptions.

## Explanation and privacy guarantees

Explanations are generated from the same candidate evidence used by the
ranker. They distinguish `supporting_evidence` from `model_interpretation`,
identify cold-start candidates, and avoid inventing skills or exposing past
bug IDs/descriptions. Developer IDs are returned because the integration
contract requires an identifier; the backend must apply the team's existing
authorization and visibility policy before exposing identities.

The structured explanation reports historical verified assignment counts,
same-component history, similarity counts and cosine values, recent activity,
elapsed time since relevant activity, and expertise/recency scores. Explanation
validation rejects inconsistent score/evidence pairs.

## Error behavior

- `ValueError`: invalid bug report fields, timestamp, top-K, candidate roster,
  history schema/label type, invalid evidence, or score inconsistency.
- `FileNotFoundError`: required model, training history, or vectorizer absent.
- Unexpected model/runtime exceptions: propagate; no silent or success-shaped
  fallback is returned.

## Demonstration and team handoff

Run an actual inference demonstration against one existing chronological
holdout bug:

```powershell
.\.venv\Scripts\python.exe -m ml_model.demo_member2_integration --top-k 3
```

The script selects an existing holdout record, calls the saved model, and
redacts developer IDs in printed output. It is an inference demonstration,
not an additional evaluation sample or metric. The fixture request above is
for unit tests only. Phase 7's final metrics, performance, error analysis, and
limitations are in [member2_phase7_final_evaluation.md](./member2_phase7_final_evaluation.md).

At team integration, validate the eligible roster source, service resource
paths, authentication/identity visibility, error mapping, and latency under
the actual backend concurrency model. Workload and assignment-policy
integration remains with Member 3.
