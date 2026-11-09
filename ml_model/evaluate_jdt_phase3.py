"""Evaluate JDT recommendations on overall, seen, and cold-start test cohorts."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from sklearn.metrics import precision_recall_fscore_support


def evaluate_ranked_cohort(
    actual: Sequence[str],
    rankings: Sequence[Sequence[str]],
) -> dict[str, float | int]:
    """Evaluate rankings without dropping unseen labels from any denominator."""
    truth = np.asarray(actual, dtype=str)
    ranked = [list(map(str, row)) for row in rankings]
    if len(truth) != len(ranked):
        raise ValueError("Each actual test label must have one recommendation ranking.")
    if len(truth) == 0:
        raise ValueError("Cannot calculate metrics for an empty cohort.")
    if any(not row for row in ranked):
        raise ValueError("Every evaluated row must have at least one candidate.")

    top_one = np.asarray([row[0] for row in ranked], dtype=str)
    labels = sorted(set(truth.tolist()) | set(top_one.tolist()))
    metrics: dict[str, float | int] = {"n_records": len(truth)}
    for average in ("micro", "macro", "weighted"):
        precision, recall, f1, _ = precision_recall_fscore_support(
            truth,
            top_one,
            labels=labels,
            average=average,
            zero_division=0,
        )
        metrics[f"classification_precision_{average}"] = float(precision)
        metrics[f"classification_recall_{average}"] = float(recall)
        metrics[f"classification_f1_{average}"] = float(f1)

    metrics["top1_accuracy"] = float(np.mean(top_one == truth))
    for k in (1, 3, 5):
        hits = np.asarray([
            truth[index] in row[:k] for index, row in enumerate(ranked)
        ])
        metrics[f"top{k}_accuracy"] = float(hits.mean())
        metrics[f"precision_at_{k}"] = float(hits.mean() / min(k, len(ranked[0])))
        metrics[f"recall_at_{k}"] = float(hits.mean())
    reciprocal = []
    for expected, row in zip(truth, ranked, strict=True):
        rank = next((index + 1 for index, candidate in enumerate(row)
                     if candidate == expected), None)
        reciprocal.append(1.0 / rank if rank is not None else 0.0)
    metrics["mean_reciprocal_rank"] = float(np.mean(reciprocal))
    return metrics
