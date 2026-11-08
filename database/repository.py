"""SQLite connection and schema management for the BugWise application."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterator


DB_PATH = Path(os.getenv("BUGWISE_DB", "data/bugwise.db"))

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS bugs (
    bug_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    severity TEXT NOT NULL,
    priority TEXT NOT NULL,
    component TEXT NOT NULL,
    programming_language TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'OPEN',
    created_at TEXT NOT NULL,
    assigned_developer_id TEXT,
    FOREIGN KEY (assigned_developer_id) REFERENCES developers(developer_id)
);
CREATE TABLE IF NOT EXISTS developers (
    developer_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    technical_expertise TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS developer_expertise (
    expertise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    developer_id TEXT NOT NULL,
    component TEXT NOT NULL,
    bugs_handled INTEGER NOT NULL DEFAULT 0,
    resolved_bugs INTEGER NOT NULL DEFAULT 0,
    last_activity_at TEXT,
    UNIQUE (developer_id, component),
    FOREIGN KEY (developer_id) REFERENCES developers(developer_id)
);
CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bug_id INTEGER NOT NULL,
    developer_id TEXT NOT NULL,
    rank INTEGER NOT NULL,
    score REAL,
    expertise_score REAL,
    recency_score REAL,
    mode TEXT NOT NULL,
    explanation TEXT NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (bug_id) REFERENCES bugs(bug_id),
    UNIQUE (bug_id, rank)
);
CREATE TABLE IF NOT EXISTS assignments (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bug_id INTEGER NOT NULL,
    developer_id TEXT NOT NULL,
    assignment_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ASSIGNED',
    FOREIGN KEY (bug_id) REFERENCES bugs(bug_id),
    FOREIGN KEY (developer_id) REFERENCES developers(developer_id)
);
CREATE INDEX IF NOT EXISTS idx_bugs_created_at ON bugs(created_at);
CREATE INDEX IF NOT EXISTS idx_bugs_status ON bugs(status);
CREATE INDEX IF NOT EXISTS idx_assignments_date ON assignments(assignment_date);
"""


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    target = Path(path) if path is not None else DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(path: str | Path | None = None) -> None:
    with connect(path) as connection:
        connection.executescript(SCHEMA)
