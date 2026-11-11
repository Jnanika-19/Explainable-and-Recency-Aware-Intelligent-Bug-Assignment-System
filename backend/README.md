# Backend and Integration
Run the API from the repository root after training a model:

```powershell
uvicorn backend.api.main:app --reload
```

The browser form is served at `/`. OpenAPI documentation is available at `/docs`. `POST /api/recommend` accepts a bug report and optional workload counts. Member 3's scoring engine is called after the ML ranker. Each request and response is logged to a local SQLite database; generated database files are ignored by Git. The endpoint returns HTTP 503 until a model artifact exists.
