"""Rank developers for one new bug and return evidence for the scoring engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ml_model.utils import load_bundle


def rank_developers(bug: dict, bundle: dict, top_k: int = 5) -> dict:
    model = bundle["model"]
    profiles = bundle["profiles"]
    row = {
        "title": bug.get("title", "") or "",
        "description": bug.get("description", "") or "",
        **{field: bug.get(field, "") or "" for field in
           ("product", "component", "severity", "priority")},
    }
    probabilities = model.predict_proba(pd.DataFrame([row]))[0]
    similar = bug.get("similar_bugs")
    if similar is None:
        similar = bundle["similarity_index"].retrieve(
            row["title"], row["description"], top_k=10
        )
    similar_counts: dict[str, int] = {}
    for item in similar:
        dev_id = item["developer_id"]
        similar_counts[dev_id] = similar_counts.get(dev_id, 0) + 1
    similar_total = sum(similar_counts.values())
    recommendations = []
    for developer_id, probability in zip(model.classes_, probabilities):
        developer_id = str(developer_id)
        profile = profiles.get(developer_id, {})
        similar_score = (similar_counts.get(developer_id, 0) / similar_total
                         if similar_total else 0.0)
        model_score = float(probability)
        relevance_score = (0.85 * model_score + 0.15 * similar_score
                           if similar_total else model_score)
        recommendations.append({
            "developer_id": developer_id,
            "relevance_score": relevance_score,
            "evidence": {
                "model_score": model_score,
                "similar_evidence_score": similar_score,
                "bugs_handled": int(profile.get("bugs_handled", 0)),
                "component_experience": int(
                    profile.get("component_experience", {}).get(row["component"], 0)
                ) if row["component"] else 0,
                "similar_bugs_resolved": similar_counts.get(developer_id, 0),
                "similar_bug_ids": [item["bug_id"] for item in similar
                                    if item["developer_id"] == developer_id],
                "product_experience": int(
                    profile.get("product_experience", {}).get(row["product"], 0)
                ) if row["product"] else 0,
                "last_assignment_at": profile.get("last_assignment_at"),
            },
        })
    recommendations.sort(key=lambda item: item["relevance_score"], reverse=True)
    return {
        "bug_id": str(bug.get("bug_id", "")),
        "recommendations": recommendations[:max(1, min(top_k, 5))],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", default="models/developer_recommender.joblib")
    parser.add_argument("--bug", required=True, help="JSON file containing a new bug report")
    parser.add_argument("--output", default="results/developer_rankings.csv")
    args = parser.parse_args()
    bug = json.loads(Path(args.bug).read_text(encoding="utf-8"))
    bundle = load_bundle(args.artifact)
    result = rank_developers(bug, bundle)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.json_normalize(result["recommendations"]).to_csv(output, index=False)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
