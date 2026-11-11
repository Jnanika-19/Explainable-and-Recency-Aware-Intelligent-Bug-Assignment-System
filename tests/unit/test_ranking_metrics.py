import numpy as np

from ml_model.evaluate_model import ranking_metrics


def test_ranking_metrics_for_single_relevant_developer():
    metrics = ranking_metrics(
        y_true=["dev-b"],
        score_matrix=np.array([[0.2, 0.8, 0.1]]),
        classes=["dev-a", "dev-b", "dev-c"],
        k=2,
    )
    assert metrics["precision_at_2"] == 0.5
    assert metrics["recall_at_2"] == 1.0
    assert metrics["mrr"] == 1.0
    assert metrics["map"] == 1.0


def test_ranking_metrics_empty_retrieval_hit_is_zero():
    metrics = ranking_metrics(
        y_true=["dev-c"],
        score_matrix=np.array([[0.1, 0.9]]),
        classes=["dev-a", "dev-b"],
        k=5,
    )
    assert metrics["recall_at_5"] == 0.0
    assert metrics["mrr"] == 0.0
