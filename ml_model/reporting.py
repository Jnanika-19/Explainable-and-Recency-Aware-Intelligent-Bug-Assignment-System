"""Create feature-importance output for a fitted recommendation pipeline."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def save_feature_importance(model, output_path: str | Path, top_n: int = 30) -> pd.DataFrame:
    """Save a bar chart and CSV of model impurity importances when supported."""
    preprocessor = model.named_steps["features"]
    classifier = model.named_steps["classifier"]
    feature_names = preprocessor.get_feature_names_out()
    importances = classifier.feature_importances_
    if "select" in model.named_steps:
        mask = model.named_steps["select"].get_support()
        feature_names = feature_names[mask]
    if len(feature_names) != len(importances):
        raise ValueError("Feature names do not align with classifier importances.")
    ranked = pd.DataFrame({"feature": feature_names, "importance": importances})
    ranked = ranked.sort_values("importance", ascending=False).head(top_n)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(output_path.with_suffix(".csv"), index=False)
    plot_data = ranked.sort_values("importance")
    figure, axis = plt.subplots(figsize=(10, max(4, len(plot_data) * 0.28)))
    axis.barh(plot_data["feature"], plot_data["importance"], color="#3465a4")
    axis.set_title("Random Forest Feature Importance (impurity based)")
    axis.set_xlabel("Importance")
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)
    return ranked
