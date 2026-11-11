"""FastAPI entry point for bug developer recommendations."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from database.repository import RecommendationStore
from ml_model.rank_developers import rank_developers
from ml_model.utils import load_bundle
from scoring_engine.confidence.estimate import add_confidence
from scoring_engine.final_scoring.rank import apply_intelligent_scoring


app = FastAPI(title="Explainable Bug Assignment API", version="0.1.0")
ARTIFACT_PATH = Path(os.getenv("BUG_ASSIGNMENT_MODEL", "models/developer_recommender.joblib"))
STORE_PATH = Path(os.getenv("BUG_ASSIGNMENT_DB", "database/recommendations.sqlite"))


class BugRequest(BaseModel):
    bug_id: str = "new-bug"
    title: str = Field(..., min_length=1)
    description: str = ""
    product: str = ""
    component: str = ""
    severity: str = ""
    priority: str = ""
    workload: dict[str, float] = Field(default_factory=dict)
    similar_bugs: list[dict] | None = None


@app.get("/health")
def health():
    return {"status": "ok", "model_available": ARTIFACT_PATH.is_file()}


@app.get("/")
def home():
    page = Path(__file__).parents[2] / "frontend" / "public" / "index.html"
    page = page.resolve()
    if page.is_file():
        return FileResponse(page)
    return {"message": "API is running. Open /docs to explore endpoints."}


@app.post("/api/recommend")
def recommend(bug: BugRequest):
    if not ARTIFACT_PATH.is_file():
        raise HTTPException(status_code=503, detail="Model artifact not found. Train the model first.")
    payload = bug.model_dump() if hasattr(bug, "model_dump") else bug.dict()
    workload = payload.pop("workload", {})
    try:
        bundle = load_bundle(ARTIFACT_PATH)
        result = rank_developers(payload, bundle, top_k=5)
        result = apply_intelligent_scoring(result, payload, workload=workload)
        result = add_confidence(result)
        store = RecommendationStore(STORE_PATH)
        result["run_id"] = store.save(payload["bug_id"], payload, result)
        return result
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
