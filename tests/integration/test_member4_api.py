import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend.api import main
from backend.services import recommendations
from database import repository


def _member2_result():
    return {
        "bug_id": None,
        "recommendations": [
            {
                "developer_id": "dev-1",
                "rank": 1,
                "ml_score": 0.73,
                "ml_score_type": "uncalibrated Phase 4 LinearSVC decision margin",
                "expertise_score": 0.5,
                "recency_score": 0.8,
                "component_relevance": 0.4,
                "similar_bug_experience_score": 0.2,
                "cold_start": False,
                "main_explanation": "Prior verified work matches the requested component.",
                "supporting_evidence": ["2 verified assignments in parser"],
                "model_interpretation": "Text features contributed positively.",
                "model_contribution": {"method": "test fixture"},
                "evidence": {"historical_verified_bug_count": 2},
            }
        ],
    }


def _install_member2_adapter(monkeypatch, result=None):
    monkeypatch.setattr(
        recommendations,
        "_load_recommender",
        lambda: lambda bug, top_k, candidates: result or _member2_result(),
    )


def _bug_payload(**overrides):
    payload = {
        "title": "Editor loses cursor position",
        "description": "Cursor jumps after changing tabs.",
        "severity": "major",
        "priority": "P2",
        "component": "editor",
        "programming_language": "Java",
    }
    payload.update(overrides)
    return payload


def test_submission_persists_member2_evidence_and_dashboard(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DB_PATH", tmp_path / "test.db")
    repository.init_db()
    _install_member2_adapter(monkeypatch)
    with TestClient(main.app) as client:
        developer = client.post(
            "/api/developers",
            json={"developer_id": "dev-1", "name": "Developer One"},
        )
        assert developer.status_code == 201

        response = client.post("/api/bugs", json=_bug_payload())
        assert response.status_code == 201
        result = response.json()
        bug_id = result["bug"]["bug_id"]
        item = result["recommendations"][0]
        assert result["mode"] == "ml"
        assert item["ml_score"] == 0.73
        assert item["ml_score_type"].startswith("uncalibrated")
        assert item["assignment_score"] is None
        assert item["assignment_status"] == "awaiting_member3"
        assert item["model_contribution"] == {"method": "test fixture"}

        detail = client.get(f"/api/bugs/{bug_id}")
        assert detail.status_code == 200
        assert detail.json()["recommendations"][0]["evidence"]["historical_verified_bug_count"] == 2
        assert detail.json()["recommendations"][0]["supporting_evidence"] == [
            "2 verified assignments in parser"
        ]
        assert client.get("/api/dashboard/stats").json()["total_bugs"] == 1
        analytics = client.get("/api/dashboard/analytics").json()
        assert analytics["critical_high_bugs"] == 1
        assert analytics["priority_distribution"] == [{"label": "P2", "count": 1}]


def test_missing_candidates_and_model_assets_are_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DB_PATH", tmp_path / "missing.db")
    repository.init_db()
    with TestClient(main.app) as client:
        missing_candidates = client.post("/api/bugs", json=_bug_payload())
        assert missing_candidates.status_code == 422
        assert "No developer candidates" in missing_candidates.json()["detail"]

        client.post(
            "/api/developers",
            json={"developer_id": "dev-1", "name": "Developer One"},
        )
        monkeypatch.setattr(
            main,
            "recommend_for_bug",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                FileNotFoundError("Phase 4 model artifact is missing.")
            ),
        )
        unavailable = client.post("/api/bugs", json=_bug_payload())
        assert unavailable.status_code == 503
        assert unavailable.json()["detail"] == "Phase 4 model artifact is missing."
        assert client.get("/api/bugs").json()["total"] == 0
        health = client.get("/api/health").json()
        assert health["recommendation_mode"] == "unavailable"
        assert health["assignment_scoring_available"] is False


def test_service_maps_real_member2_schema_without_calibrating_margin(monkeypatch):
    captured = {}

    def fake_recommender(bug, top_k, candidates):
        captured.update(bug=bug, top_k=top_k, candidates=candidates)
        return _member2_result()

    monkeypatch.setattr(recommendations, "_load_recommender", lambda: fake_recommender)
    result = recommendations.recommend_for_bug(
        {"title": "Parser error", "component": "parser"},
        top_k=1,
        candidates=["dev-1"],
    )
    assert captured["top_k"] == 1
    assert captured["candidates"] == ["dev-1"]
    recommendation = result["recommendations"][0]
    assert recommendation["ml_score"] == 0.73
    assert recommendation["assignment_score"] is None
    assert recommendation["explanation"] == "Prior verified work matches the requested component."


def test_standalone_recommendation_is_not_persisted(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DB_PATH", tmp_path / "standalone.db")
    repository.init_db()
    _install_member2_adapter(monkeypatch)
    with TestClient(main.app) as client:
        client.post(
            "/api/developers",
            json={"developer_id": "dev-1", "name": "Developer One"},
        )
        response = client.post(
            "/api/recommendations",
            json={
                "title": "Compiler warning",
                "component": "compiler",
                "top_k": 1,
            },
        )
        assert response.status_code == 200
        assert response.json()["recommendations"][0]["developer_id"] == "dev-1"
        assert client.get("/api/bugs").json()["total"] == 0


def test_manual_assignment_updates_status_and_workload(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DB_PATH", tmp_path / "assignments.db")
    repository.init_db()
    with repository.connect() as connection:
        cursor = connection.execute(
            """INSERT INTO bugs
               (title,description,severity,priority,component,status,created_at)
               VALUES (?,?,?,?,?,?,?)""",
            ("Fix parser", "", "normal", "P2", "compiler", "OPEN", "2025-01-01T00:00:00Z"),
        )
        bug_id = cursor.lastrowid

    with TestClient(main.app) as client:
        developer = client.post(
            "/api/developers",
            json={"developer_id": "dev-1", "name": "Developer One"},
        )
        assert developer.status_code == 201
        assignment = client.post(
            "/api/assignments",
            json={"bug_id": bug_id, "developer_id": "dev-1", "status": "ASSIGNED"},
        )
        assert assignment.status_code == 201
        assert assignment.json()["developer_name"] == "Developer One"
        workload = client.get("/api/workloads").json()["items"][0]
        assert workload["active_assignments"] == 1
        assert workload["assigned"] == 1

        update = client.patch(f"/api/bugs/{bug_id}", json={"status": "IN_PROGRESS"})
        assert update.status_code == 200
        assert update.json()["bug"]["status"] == "IN_PROGRESS"
        assert client.get("/api/assignments").json()["items"][0]["status"] == "IN_PROGRESS"
        assert client.get("/api/dashboard").json()["assigned_bugs"] == 1


def test_invalid_input_and_database_failures_are_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DB_PATH", tmp_path / "validation.db")
    repository.init_db()
    with TestClient(main.app) as client:
        invalid = client.post("/api/bugs", json={"title": "x", "component": ""})
        assert invalid.status_code == 422
        assert client.get("/api/bugs/999").status_code == 404
        assert client.get("/api/developers/unknown").status_code == 404
        assert client.post(
            "/api/bugs",
            json=_bug_payload(submission_date="not-a-time"),
        ).status_code == 422

    with TestClient(main.app) as client:
        monkeypatch.setattr(
            repository,
            "connect",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                sqlite3.OperationalError("database unavailable")
            ),
        )
        failed = client.post("/api/bugs", json=_bug_payload())
        assert failed.status_code == 503
        assert failed.json()["detail"] == "Database is unavailable"


def test_service_requires_candidates_and_propagates_missing_assets(monkeypatch):
    with pytest.raises(ValueError, match="No developer candidates"):
        recommendations.recommend_for_bug(
            {"title": "Bug", "component": "compiler"},
            candidates=[],
        )

    def missing_assets():
        raise FileNotFoundError("Model bundle is missing.")

    monkeypatch.setattr(recommendations, "_load_recommender", missing_assets)
    with pytest.raises(FileNotFoundError, match="Model bundle is missing"):
        recommendations.recommend_for_bug(
            {"title": "Bug", "component": "compiler"},
            candidates=["dev-1"],
        )
