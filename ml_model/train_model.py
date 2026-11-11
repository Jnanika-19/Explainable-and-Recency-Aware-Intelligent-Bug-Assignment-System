"""Train, compare, and save the developer recommender from a mapped bug CSV."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bug_similarity.retrieval.similar_bugs import SimilarBugIndex
from ml_model.developer_profiles import build_developer_profiles
from ml_model.evaluate_model import chronological_split, compare_models
from ml_model.reporting import save_feature_importance
from ml_model.utils import save_bundle
from preprocessing.data_cleaning.schema import DatasetSchema, inspect_csv, load_canonical_csv


def train(data_path: str, schema_path: str, artifact_path: str, results_dir: str):
    Path(results_dir).mkdir(parents=True, exist_ok=True)
    schema_json = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    schema = DatasetSchema(
        columns=schema_json["columns"],
        resolved_values=tuple(schema_json.get("resolved_values", [])),
    )
    frame = load_canonical_csv(data_path, schema)
    train_rows, validation_rows = chronological_split(frame)
    metrics, chosen = compare_models(train_rows, validation_rows)
    metrics = metrics.sort_values("mrr", ascending=False).reset_index(drop=True)
    metrics.to_csv(Path(results_dir) / "model_metrics.csv", index=False)
    # Refit the selected pipeline on all available history for later inference.
    final_model = chosen["model"]
    final_model.fit(frame, frame["developer_id"].astype(str))
    save_feature_importance(final_model, Path(results_dir) / "feature_importance.png")
    profiles = build_developer_profiles(frame)
    bundle = {
        "model": final_model,
        "model_name": chosen["name"],
        "profiles": profiles,
        "history": frame,
        "similarity_index": SimilarBugIndex().fit(frame),
        "schema": schema_json,
        "validation_metrics": metrics.to_dict(orient="records"),
    }
    save_bundle(bundle, artifact_path)
    return metrics, bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--artifact", default="models/developer_recommender.joblib")
    parser.add_argument("--results", default="results")
    args = parser.parse_args()
    Path(args.results).mkdir(parents=True, exist_ok=True)
    print("Detected columns:", inspect_csv(args.data)["columns"])
    metrics, bundle = train(args.data, args.schema, args.artifact, args.results)
    print(metrics.to_string(index=False))
    print(f"Saved {bundle['model_name']} bundle to {args.artifact}")


if __name__ == "__main__":
    main()
