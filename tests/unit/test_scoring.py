from scoring_engine.confidence.estimate import add_confidence
from scoring_engine.final_scoring.rank import apply_intelligent_scoring


def test_scoring_retains_evidence_and_orders_candidates():
    result = {"bug_id": "b1", "recommendations": [
        {"developer_id": "d1", "relevance_score": 0.9, "evidence": {
            "component_experience": 8, "product_experience": 4,
            "last_assignment_at": None,
        }},
        {"developer_id": "d2", "relevance_score": 0.4, "evidence": {
            "component_experience": 0, "product_experience": 0,
            "last_assignment_at": None,
        }},
    ]}
    scored = apply_intelligent_scoring(result, {"component": "network"})
    scored = add_confidence(scored)
    assert scored["recommendations"][0]["developer_id"] == "d1"
    assert scored["recommendations"][0]["evidence"]["workload_score"] == 0.5
    assert scored["confidence"]["level"] == "high"
