"""FastAPI endpoints for bug reports, developer profiles and assignment history."""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.services.recommendations import recommend_demo
from database import repository


logger = logging.getLogger(__name__)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: str | None) -> str:
    if not value:
        return utc_now()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise HTTPException(status_code=422, detail="submission_date must be an ISO 8601 timestamp") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class BugInput(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    description: str = Field(default="", max_length=20000)
    severity: str = Field(default="normal", min_length=1, max_length=80)
    priority: str = Field(default="unknown", min_length=1, max_length=80)
    component: str = Field(min_length=1, max_length=120)
    programming_language: str = Field(default="", max_length=120)
    submission_date: str | None = None


class RecommendationInput(BugInput):
    top_k: int = Field(default=3, ge=1, le=3)


class AssignmentInput(BaseModel):
    bug_id: int = Field(gt=0)
    developer_id: str = Field(min_length=1, max_length=200)
    assignment_date: str | None = None
    status: Literal["ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"] = "ASSIGNED"


class DeveloperInput(BaseModel):
    developer_id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    technical_expertise: str = Field(default="", max_length=4000)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    repository.init_db()
    yield


app = FastAPI(title="BugWise Bug Assignment API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def save_recommendations(connection, bug_id: int, bug: dict, top_k: int = 3) -> dict:
    result = recommend_demo(bug, top_k=top_k)
    created_at = utc_now()
    for item in result["recommendations"]:
        connection.execute(
            """INSERT INTO recommendations
               (bug_id,developer_id,rank,score,expertise_score,recency_score,mode,
                explanation,evidence_json,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                bug_id,
                item["developer_id"],
                item["rank"],
                item["score"],
                item["expertise_score"],
                item["recency_score"],
                result["mode"],
                item["explanation"],
                json.dumps(item["evidence"]),
                created_at,
            ),
        )
    return result


@app.get("/api/health")
def health():
    return {"status": "ok", "recommendation_mode": "demo"}


@app.post("/api/bugs", status_code=201)
def submit_bug(request: BugInput):
    payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()
    title = payload["title"].strip()
    component = payload["component"].strip()
    if len(title) < 3 or not component:
        raise HTTPException(status_code=422, detail="Title and component must not be blank")
    created_at = parse_timestamp(payload.pop("submission_date"))
    payload.update({"title": title, "component": component, "created_at": created_at})
    try:
        with repository.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO bugs
                   (title,description,severity,priority,component,programming_language,status,created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    title,
                    payload["description"].strip(),
                    payload["severity"],
                    payload["priority"],
                    component,
                    payload["programming_language"].strip(),
                    "OPEN",
                    created_at,
                ),
            )
            bug_id = int(cursor.lastrowid)
            recommendations = save_recommendations(connection, bug_id, payload)
    except Exception:
        logger.exception("Could not save bug report")
        raise
    return {
        **recommendations,
        "bug": {"bug_id": bug_id, **payload, "status": "OPEN"},
    }


@app.get("/api/bugs")
def list_bugs(
    search: str = "",
    status: str | None = None,
    sort: Literal["created_at", "title", "severity", "status"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    where, params = [], []
    if search.strip():
        term = f"%{search.strip()}%"
        where.append("(b.title LIKE ? OR b.description LIKE ? OR b.component LIKE ?)")
        params.extend([term, term, term])
    if status:
        where.append("UPPER(b.status)=UPPER(?)")
        params.append(status)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    direction = order.upper()
    with repository.connect() as connection:
        rows = connection.execute(
            f"""SELECT b.*, COUNT(DISTINCT r.recommendation_id) AS recommendation_count
                FROM bugs b LEFT JOIN recommendations r USING(bug_id)
                {clause} GROUP BY b.bug_id ORDER BY b.{sort} {direction}
                LIMIT ? OFFSET ?""",
            (*params, limit, offset),
        ).fetchall()
        total = connection.execute(f"SELECT COUNT(*) FROM bugs b {clause}", params).fetchone()[0]
    return {"total": total, "items": [dict(row) for row in rows]}


@app.get("/api/bugs/{bug_id}")
def get_bug(bug_id: int):
    with repository.connect() as connection:
        bug = connection.execute("SELECT * FROM bugs WHERE bug_id=?", (bug_id,)).fetchone()
        if bug is None:
            raise HTTPException(status_code=404, detail="Bug report not found")
        recommendations = connection.execute(
            """SELECT recommendation_id,developer_id,rank,score,expertise_score,recency_score,
                      mode,explanation,evidence_json,created_at
               FROM recommendations WHERE bug_id=? ORDER BY rank""",
            (bug_id,),
        ).fetchall()
        assignments = connection.execute(
            """SELECT a.*,d.name AS developer_name FROM assignments a
               JOIN developers d USING(developer_id) WHERE a.bug_id=?
               ORDER BY a.assignment_date DESC""",
            (bug_id,),
        ).fetchall()
    result = []
    for row in recommendations:
        item = dict(row)
        item["evidence"] = json.loads(item.pop("evidence_json"))
        result.append(item)
    return {
        "bug": dict(bug),
        "recommendations": result,
        "assignments": [dict(row) for row in assignments],
    }


@app.post("/api/recommendations")
def recommend(request: RecommendationInput):
    payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()
    return recommend_demo(payload, top_k=payload["top_k"])


@app.get("/api/developers")
def list_developers(search: str = "", limit: int = Query(default=100, ge=1, le=500)):
    with repository.connect() as connection:
        rows = connection.execute(
            """SELECT d.developer_id,d.name,d.email,d.technical_expertise,
                      COUNT(DISTINCT a.assignment_id) AS bugs_handled,
                      SUM(CASE WHEN UPPER(a.status) IN ('RESOLVED','CLOSED') THEN 1 ELSE 0 END)
                          AS resolved_bugs
               FROM developers d LEFT JOIN assignments a USING(developer_id)
               WHERE (?='' OR d.developer_id LIKE ? OR d.name LIKE ?)
               GROUP BY d.developer_id ORDER BY d.name LIMIT ?""",
            (search.strip(), f"%{search.strip()}%", f"%{search.strip()}%", limit),
        ).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.post("/api/developers", status_code=201)
def create_developer(request: DeveloperInput):
    payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()
    payload = {key: value.strip() if isinstance(value, str) else value for key, value in payload.items()}
    if not payload["developer_id"] or not payload["name"]:
        raise HTTPException(status_code=422, detail="Developer ID and name must not be blank")
    try:
        with repository.connect() as connection:
            connection.execute(
                """INSERT INTO developers (developer_id,name,email,technical_expertise)
                   VALUES (?,?,?,?)""",
                (payload["developer_id"], payload["name"], payload["email"], payload["technical_expertise"]),
            )
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409, detail="Developer ID already exists") from error
    except Exception:
        logger.exception("Could not save developer profile")
        raise
    return payload


@app.get("/api/developers/{developer_id}")
def get_developer(developer_id: str):
    with repository.connect() as connection:
        developer = connection.execute(
            "SELECT * FROM developers WHERE developer_id=?", (developer_id,)
        ).fetchone()
        if developer is None:
            raise HTTPException(status_code=404, detail="Developer not found")
        expertise = connection.execute(
            """SELECT component,bugs_handled,resolved_bugs,last_activity_at
               FROM developer_expertise WHERE developer_id=? ORDER BY resolved_bugs DESC,component""",
            (developer_id,),
        ).fetchall()
        stats = connection.execute(
            """SELECT COUNT(*) AS bugs_handled,
                      SUM(CASE WHEN UPPER(status) IN ('RESOLVED','CLOSED') THEN 1 ELSE 0 END)
                          AS resolved_bugs
               FROM assignments WHERE developer_id=?""",
            (developer_id,),
        ).fetchone()
        assignments = connection.execute(
            """SELECT a.assignment_id,a.bug_id,a.assignment_date,a.status,b.title,b.severity,b.component
               FROM assignments a JOIN bugs b USING(bug_id) WHERE a.developer_id=?
               ORDER BY a.assignment_date DESC LIMIT 20""",
            (developer_id,),
        ).fetchall()
    return {
        "developer": dict(developer),
        "stats": {
            "bugs_handled": stats["bugs_handled"] or 0,
            "resolved_bugs": stats["resolved_bugs"] or 0,
        },
        "expertise": [dict(row) for row in expertise],
        "recent_assignments": [dict(row) for row in assignments],
    }


@app.post("/api/assignments", status_code=201)
def create_assignment(request: AssignmentInput):
    assignment_date = parse_timestamp(request.assignment_date)
    with repository.connect() as connection:
        bug = connection.execute("SELECT bug_id FROM bugs WHERE bug_id=?", (request.bug_id,)).fetchone()
        if bug is None:
            raise HTTPException(status_code=404, detail="Bug report not found")
        developer = connection.execute(
            "SELECT developer_id FROM developers WHERE developer_id=?", (request.developer_id,)
        ).fetchone()
        if developer is None:
            raise HTTPException(status_code=404, detail="Developer not found")
        cursor = connection.execute(
            """INSERT INTO assignments (bug_id,developer_id,assignment_date,status)
               VALUES (?,?,?,?)""",
            (request.bug_id, request.developer_id, assignment_date, request.status),
        )
        connection.execute(
            "UPDATE bugs SET status=?,assigned_developer_id=? WHERE bug_id=?",
            (request.status, request.developer_id, request.bug_id),
        )
        resolved_increment = int(request.status in {"RESOLVED", "CLOSED"})
        connection.execute(
            """INSERT INTO developer_expertise
                 (developer_id,component,bugs_handled,resolved_bugs,last_activity_at)
               SELECT ?,component,1,?,? FROM bugs WHERE bug_id=?
               ON CONFLICT(developer_id,component) DO UPDATE SET
                 bugs_handled=developer_expertise.bugs_handled+1,
                 resolved_bugs=developer_expertise.resolved_bugs+excluded.resolved_bugs,
                 last_activity_at=excluded.last_activity_at""",
            (request.developer_id, resolved_increment, assignment_date, request.bug_id),
        )
        row = connection.execute(
            """SELECT a.*,d.name AS developer_name,b.title AS bug_title,b.severity
               FROM assignments a JOIN developers d USING(developer_id)
               JOIN bugs b USING(bug_id) WHERE a.assignment_id=?""",
            (cursor.lastrowid,),
        ).fetchone()
    return dict(row)


@app.get("/api/assignments")
def list_assignments(
    search: str = "",
    status: str | None = None,
    sort: Literal["assignment_date", "status", "bug_title", "developer_name"] = "assignment_date",
    order: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=100, ge=1, le=500),
):
    where, params = [], []
    if search.strip():
        term = f"%{search.strip()}%"
        where.append("(b.title LIKE ? OR d.name LIKE ? OR a.developer_id LIKE ?)")
        params.extend([term, term, term])
    if status:
        where.append("UPPER(a.status)=UPPER(?)")
        params.append(status)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    with repository.connect() as connection:
        rows = connection.execute(
            f"""SELECT a.assignment_id,a.bug_id,b.title AS bug_title,a.developer_id,
                       d.name AS developer_name,a.assignment_date,b.severity,b.component,a.status
                FROM assignments a JOIN bugs b USING(bug_id)
                JOIN developers d USING(developer_id) {clause}
                ORDER BY {sort} {order.upper()} LIMIT ?""",
            (*params, limit),
        ).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.get("/api/dashboard/stats")
@app.get("/api/dashboard")
def dashboard_stats():
    with repository.connect() as connection:
        bugs = connection.execute(
            """SELECT COUNT(*) AS total,
                      SUM(CASE WHEN UPPER(status) NOT IN ('RESOLVED','CLOSED') THEN 1 ELSE 0 END) AS open,
                      SUM(CASE WHEN UPPER(status) IN ('RESOLVED','CLOSED') THEN 1 ELSE 0 END) AS resolved,
                      SUM(CASE WHEN assigned_developer_id IS NOT NULL THEN 1 ELSE 0 END) AS assigned
               FROM bugs"""
        ).fetchone()
        developers = connection.execute("SELECT COUNT(*) FROM developers").fetchone()[0]
        recent = connection.execute(
            """SELECT a.assignment_id,a.bug_id,b.title AS bug_title,a.developer_id,
                      d.name AS developer_name,a.assignment_date,a.status
               FROM assignments a JOIN bugs b USING(bug_id)
               JOIN developers d USING(developer_id)
               ORDER BY a.assignment_date DESC LIMIT 8"""
        ).fetchall()
    return {
        "total_bugs": bugs["total"] or 0,
        "open_bugs": bugs["open"] or 0,
        "resolved_bugs": bugs["resolved"] or 0,
        "assigned_bugs": bugs["assigned"] or 0,
        "total_developers": developers,
        "recent_assignments": [dict(row) for row in recent],
    }
