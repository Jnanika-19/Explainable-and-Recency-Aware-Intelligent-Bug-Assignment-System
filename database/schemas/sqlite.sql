CREATE TABLE IF NOT EXISTS recommendation_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bug_id TEXT NOT NULL,
    request_json TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
