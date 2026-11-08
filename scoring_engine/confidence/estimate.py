"""Simple confidence indicator based on concentration in the top recommendation."""


def add_confidence(result: dict) -> dict:
    items = result.get("recommendations", [])
    if not items:
        result["confidence"] = {"level": "low", "top_score_margin": 0.0}
        return result
    scores = [float(item["relevance_score"]) for item in items]
    margin = scores[0] - scores[1] if len(scores) > 1 else scores[0]
    result["confidence"] = {
        "level": "high" if margin >= 0.20 else "medium" if margin >= 0.08 else "low",
        "top_score_margin": float(margin),
        "note": "Heuristic ranking margin; not a calibrated probability.",
    }
    return result
