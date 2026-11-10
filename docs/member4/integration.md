# Member 4 application and integration contract

## Current status

The Member 4 branch provides a React/Vite dashboard, FastAPI service, and
SQLite persistence for bugs, developers, recommendations, and assignments.
Dashboard metrics, priority/severity distributions, trends, workload, bug
status, and assignment history use records in the application database.

Recommendation requests call the Member 2 adapter and never return demo
predictions. Final scoring is deliberately not calculated in Member 4: this
branch does not contain Member 3's executable scoring module. A recommendation
is evidence for a human decision, not an automatic assignment.

## Runtime prerequisites

At the time of this integration, `feature/member-4-fullstack` does not contain
the Member 2 recommender source or these runtime assets:

- `ml_model/developer_recommender.py` and its Phase 2–6 supporting modules.
- `models/jdt_phase4/combined_linear_svm.joblib`.
- `models/jdt_tfidf_vectorizer.joblib`.
- `data/processed/jdt_known_entry_train.csv`.

The Python adapter imports `ml_model.developer_recommender` lazily. Missing
source or model resources produce HTTP 503; they are not replaced with sample
or synthetic recommendations. Keep generated model/data artifacts out of Git.
Member 3's actual scoring function, input/output contract, and workload policy
must be supplied by that team before a final assignment score can be exposed.

## Run locally

From the repository root, install requirements and start FastAPI:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn backend.api.main:app --reload
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). OpenAPI documentation is
at `http://127.0.0.1:8000/docs`. SQLite uses `data/bugwise.db` by default;
override with `BUGWISE_DB` for tests or local runs.

## HTTP API

- `GET /api/health`: reports API status, recommendation resource readiness,
  and whether final assignment scoring is available.
- `POST /api/bugs`: validates the request, obtains recommendations, then
  transactionally stores the bug and recommendation evidence. It does not
  store a bug if model resources are unavailable or no developer candidates
  have been registered.
- `POST /api/recommendations`: performs a non-persistent recommendation using
  the registered developer IDs as the candidate roster.
- `GET /api/bugs`, `GET /api/bugs/{bug_id}`: search/list and retrieve bug
  details, recommendation explanations, and assignment history.
- `PATCH /api/bugs/{bug_id}`: update status. `ASSIGNED` and `IN_PROGRESS`
  require a current assigned developer.
- `GET /api/developers`, `GET /api/developers/{developer_id}`,
  `POST /api/developers`: browse, inspect, and register developers.
- `GET /api/workloads`: compute assigned, in-progress, completed, and active
  counts from saved assignment records.
- `POST /api/assignments`, `GET /api/assignments`: manually record and review
  assignment decisions. Member 4 does not choose a final developer
  automatically.
- `GET /api/dashboard/stats`, `GET /api/dashboard/analytics`: provide counts,
  distributions, monthly trends, and recorded developer performance.

`ValueError` is returned as HTTP 422, unavailable Member 2 code/model resources
as HTTP 503, and missing records as HTTP 404. Database errors on bug submission
are surfaced as HTTP 503 and logged.

## Member 2 mapping

The service calls:

```python
recommend_developers(bug_report, top_k=3, candidates=registered_developer_ids)
```

The request includes title, description, component, severity, priority, and
the validated submission timestamp as `created_at`. Returned `ml_score` stays
an uncalibrated LinearSVC decision margin, and its `ml_score_type`, explanation,
supporting evidence, model contribution, expertise/recency scores, component
relevance, similar-bug score, and cold-start marker are preserved. The legacy
`score` database column is left null; UI copy never labels the raw margin as a
probability or final assignment score.

## Member 3 boundary

Member 3's executable scorer is missing from this branch. The response reports
`assignment_status: awaiting_member3` and `assignment_score: null`. No
Member 3 weights or workload formulas are reimplemented. Assignment creation
is an explicit manual user action and is persisted separately from ML output.

## Frontend

The dashboard includes overview metrics and distributions, bug submission,
bug list/detail and status editing, developer directory, workload, assignment
history/results, recommendation evidence, explainability, and reports/
analytics. It displays unavailable-resource errors instead of fabricating
scores. Assignment actions are explicitly manual.

## Verification

```powershell
python -m pytest -q tests/integration/test_member4_api.py
cd frontend
npm run build
```

API tests inject a controlled test recommender; this verifies adapter mapping
and persistence behavior but does not constitute a real-model smoke test. A
real end-to-end recommendation/assignment run remains blocked until Member 2
resources and Member 3's executable scoring interface are provided.
