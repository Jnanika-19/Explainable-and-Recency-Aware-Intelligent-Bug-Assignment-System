# Member 4 application and integration contract

## Status

The React/Vite dashboard and FastAPI/SQLite application provide bug submission,
report history, developer profiles, recommendation rendering, explanations, and
assignment history. The recommendation adapter currently returns **DEMO ONLY**
placeholders. It reports no prediction, expertise, or recency scores and must not
be presented as an operational recommendation.

## Run locally

From the repository root, install the Python requirements and start the API:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn backend.api.main:app --reload
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). FastAPI's interactive
endpoint documentation is available at `http://127.0.0.1:8000/docs`.

The SQLite database is `data/bugwise.db` by default. Set `BUGWISE_DB` to use a
different database path during development or tests. Raw dataset files are not
modified by the application.

## API

- `POST /api/bugs` validates and stores a bug report and returns up to three
  clearly marked demo placeholders.
- `GET /api/bugs` supports `search`, `status`, `sort`, `order`, `limit`, and
  `offset`; `GET /api/bugs/{bug_id}` returns the report, recommendations, and
  assignment history.
- `POST /api/recommendations` exercises the recommendation response contract
  without saving a bug.
- `GET /api/developers` and `GET /api/developers/{developer_id}` return
  developer and expertise profiles. `POST /api/developers` supports local
  development/test profile registration.
- `POST /api/assignments` records an assignment for an existing bug and
  developer; `GET /api/assignments` supports search/status filtering.
- `GET /api/dashboard/stats` reports bug, developer, and recent assignment
  counts. `GET /api/dashboard` remains an alias.
- `GET /api/health` reports API status and current recommendation mode.

## Member 2 and Member 3 integration

Replace `backend/services/recommendations.py::recommend_demo` with an adapter
that calls the Member 2 candidate recommender and Member 3 ranking/scoring
engine. Keep the existing JSON shape:

```json
{
  "mode": "real",
  "disclaimer": null,
  "bug": {"title": "…", "component": "…"},
  "recommendations": [
    {
      "developer_id": "…",
      "rank": 1,
      "score": 0.0,
      "expertise_score": 0.0,
      "recency_score": 0.0,
      "explanation": "Evidence-backed reason",
      "evidence": {"feature_name": 0.0}
    }
  ]
}
```

Scores must come from the connected modules. Explanations must only cite evidence
returned for that candidate. Set `mode` to `real` only after genuine model and
scoring outputs are connected; do not remove the demo disclaimer while using
placeholders.

## Verification

Run backend API tests:

```powershell
pytest tests/integration/test_member4_api.py
```

Build the frontend:

```powershell
cd frontend
npm run build
```
