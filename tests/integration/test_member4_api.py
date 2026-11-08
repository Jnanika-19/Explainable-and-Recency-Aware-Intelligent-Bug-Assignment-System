from fastapi.testclient import TestClient

from backend.api.main import app
from database import repository


def test_bug_submission_demo_recommendations_and_dashboard(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DB_PATH", tmp_path / "test.db")
    repository.init_db()
    with TestClient(app) as client:
        response = client.post(
            "/api/bugs",
            json={
                "title": "Editor loses cursor position",
                "description": "Cursor jumps after changing tabs.",
                "severity": "major",
                "priority": "P2",
                "component": "editor",
                "programming_language": "Java",
            },
        )
        assert response.status_code == 201
        result = response.json()
        bug_id = result["bug"]["bug_id"]
        assert result["mode"] == "demo"
        assert "DEMO ONLY" in result["disclaimer"]
        assert len(result["recommendations"]) == 3
        assert result["recommendations"][0]["mode"] == "demo"
        assert result["recommendations"][0]["score"] is None

        listing = client.get("/api/bugs", params={"search": "cursor"})
        assert listing.status_code == 200
        assert listing.json()["total"] == 1
        detail = client.get(f"/api/bugs/{bug_id}")
        assert detail.status_code == 200
        assert detail.json()["recommendations"][0]["mode"] == "demo"

        stats = client.get("/api/dashboard/stats").json()
        assert stats["total_bugs"] == 1
        assert stats["open_bugs"] == 1
        assert stats["assigned_bugs"] == 0
        assert client.get("/api/health").json()["recommendation_mode"] == "demo"
        standalone = client.post(
            "/api/recommendations",
            json={"title": "Compiler warning", "component": "compiler", "top_k": 2},
        )
        assert standalone.status_code == 200
        assert len(standalone.json()["recommendations"]) == 2


def test_input_validation_and_missing_resources(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DB_PATH", tmp_path / "validation.db")
    repository.init_db()
    with TestClient(app) as client:
        invalid = client.post("/api/bugs", json={"title": "x", "component": ""})
        assert invalid.status_code == 422
        assert client.get("/api/bugs/999").status_code == 404
        assert client.get("/api/developers/unknown").status_code == 404


def test_assignment_history_and_developer_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DB_PATH", tmp_path / "assignment.db")
    repository.init_db()
    with repository.connect() as connection:
        cursor = connection.execute(
            """INSERT INTO bugs
               (title,description,severity,priority,component,status,created_at)
               VALUES (?,?,?,?,?,?,?)""",
            ("Fix parser", "", "normal", "P2", "compiler", "OPEN", "2025-01-01T00:00:00Z"),
        )
        bug_id = cursor.lastrowid
    with TestClient(app) as client:
        developer = client.post(
            "/api/developers",
            json={"developer_id": "dev-1", "name": "Developer One"},
        )
        assert developer.status_code == 201
        assigned = client.post(
            "/api/assignments",
            json={"bug_id": bug_id, "developer_id": "dev-1", "status": "IN_PROGRESS"},
        )
        assert assigned.status_code == 201
        assert assigned.json()["developer_name"] == "Developer One"
        assert client.get("/api/assignments").json()["items"][0]["bug_id"] == bug_id
        assert client.get("/api/assignments", params={"status": "IN_PROGRESS"}).json()["items"]
        profile = client.get("/api/developers/dev-1")
        assert profile.status_code == 200
        assert profile.json()["developer"]["name"] == "Developer One"
        assert profile.json()["stats"]["bugs_handled"] == 1
        assert profile.json()["stats"]["resolved_bugs"] == 0
        assert profile.json()["expertise"][0]["component"] == "compiler"
        assert client.get("/api/dashboard").json()["assigned_bugs"] == 1
