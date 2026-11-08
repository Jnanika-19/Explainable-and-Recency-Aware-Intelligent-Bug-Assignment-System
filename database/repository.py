"""Local SQLite persistence for recommendation request and response records."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class RecommendationStore:
    def __init__(self, path: str | Path = "database/recommendations.sqlite"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        schema = Path(__file__).parent / "schemas" / "sqlite.sql"
        with sqlite3.connect(self.path) as connection:
            connection.executescript(schema.read_text(encoding="utf-8"))

    def save(self, bug_id: str, request: dict, response: dict) -> int:
        with sqlite3.connect(self.path) as connection:
            cursor = connection.execute(
                "INSERT INTO recommendation_runs (bug_id, request_json, response_json) VALUES (?, ?, ?)",
                (bug_id, json.dumps(request), json.dumps(response)),
            )
            return int(cursor.lastrowid)
