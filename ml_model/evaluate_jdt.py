"""Classification and ranked-assignment metrics for JDT baseline experiments."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from sklearn.metrics import precision_recall_fscore_support


def evaluate_scores(
    y_true: Sequence[str],
    scores: np.ndarray,
    classes: Sequence[str],
    ks: tuple[int, ...] = (1, 3, 5),
) -> tuple[dict[str, float], list[list[str]]]:
    """Evaluate every test row; labels absent from training count as misses."""
    actual = np.asarray(y_true, dtype=str)
    class_names = np.asarray(classes, dtype=str)
    if scores.ndim != 2 or scores.shape != (len(actual), len(class_names)):
        raise ValueError(
            f"Scores have shape {scores.shape}; expected {(len(actual), len(class_names))}."
        )
    if len(actual) == 0 or len(class_names) == 0:
        raise ValueError("Evaluation requires test rows and trained developer classes.")
    if any(k <= 0 for k in ks):
        raise ValueError("Ranking cutoffs must be positive.")

    rankings: list[list[str]] = []
    ranking_indices = []
    for row in scores:
        indices = sorted(
            range(len(class_names)),
            key=lambda index: (-float(row[index]), str(class_names[index])),
        )
        ranking_indices.append(indices)
        rankings.append([str(class_names[index]) for index in indices])

    metrics: dict[str, float] = {}
    top_one = np.asarray([rank[0] for rank in rankings], dtype=str)
    labels = sorted(set(actual.tolist()) | set(top_one.tolist()))
    for average in ("micro", "macro", "weighted"):
        precision, recall, f1, _ = precision_recall_fscore_support(
            actual,
            top_one,
            labels=labels,
            average=average,
            zero_division=0,
        )
        metrics[f"classification_precision_{average}"] = float(precision)
        metrics[f"classification_recall_{average}"] = float(recall)
        metrics[f"classification_f1_{average}"] = float(f1)

    metrics["top1_accuracy"] = float(np.mean(top_one == actual))
    for k in ks:
        hits = np.asarray([
            actual[row_index] in rankings[row_index][:k]
            for row_index in range(len(actual))
        ])
        metrics[f"top{k}_accuracy"] = float(hits.mean())
        metrics[f"precision_at_{k}"] = float(hits.mean() / k)
        metrics[f"recall_at_{k}"] = float(hits.mean())
    reciprocal_ranks = []
    for row_index, ranked in enumerate(rankings):
        rank = next((index + 1 for index, candidate in enumerate(ranked)
                     if candidate == actual[row_index]), None)
        reciprocal_ranks.append(1.0 / rank if rank is not None else 0.0)
    metrics["mean_reciprocal_rank"] = float(np.mean(reciprocal_ranks))
    metrics["test_rows"] = float(len(actual))
    metrics["test_rows_with_developer_seen_in_training"] = float(
        np.isin(actual, class_names).sum()
    )
    metrics["test_rows_with_unseen_developer"] = float(
        (~np.isin(actual, class_names)).sum()
    )
    return metrics, rankings
