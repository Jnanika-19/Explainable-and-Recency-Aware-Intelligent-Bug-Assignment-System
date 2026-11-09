"""Run a redacted integration demonstration on a real chronological holdout bug."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from ml_model.developer_recommender import recommend_developers

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST_PATH = PROJECT_ROOT / "data" / "processed" / "jdt_known_entry_test.csv"


def build_demo(
    bug_id: str | None = None,
    top_k: int = 3,
    test_path: str | Path = DEFAULT_TEST_PATH,
) -> dict[str, object]:
    """Run inference using one existing holdout record; do not score evaluation."""
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k must be a positive integer.")
    path = Path(test_path)
    if not path.is_file():
        raise FileNotFoundError(f"Chronological holdout file is missing: {path}")
    test = pd.read_csv(path, keep_default_na=False)
    required = {
        "bug_id",
        "title",
        "description",
        "component",
        "severity",
        "priority",
        "product",
        "created_at",
    }
    missing = required - set(test.columns)
    if missing:
        raise ValueError(f"Holdout input is missing required fields: {sorted(missing)}")
    if bug_id is not None:
        selected = test.loc[test["bug_id"].astype(str).eq(str(bug_id))]
        if selected.empty:
            raise ValueError(f"Bug ID {bug_id!r} is not present in the holdout file.")
        row = selected.iloc[0]
    else:
        if test.empty:
            raise ValueError("Chronological holdout file contains no bug records.")
        row = test.iloc[0]

    bug_report: dict[str, Any] = {
        "bug_id": int(row["bug_id"]),
        "title": str(row["title"]),
        "description": str(row["description"]),
        "component": str(row["component"]),
        "severity": str(row["severity"]),
        "priority": str(row["priority"]),
        "product": str(row["product"]),
        "prediction_timestamp": str(row["created_at"]),
    }
    response = recommend_developers(bug_report, top_k=top_k)

    aliases = {
        str(item["developer_id"]): f"developer_{index}"
        for index, item in enumerate(response["recommendations"], start=1)
    }
    redacted_recommendations = []
    for item in response["recommendations"]:
        original_id = str(item["developer_id"])
        redacted = dict(item)
        redacted["developer_id"] = aliases[original_id]
        for field in ("main_explanation",):
            redacted[field] = str(redacted[field]).replace(
                original_id,
                aliases[original_id],
            )
        redacted_recommendations.append(redacted)

    return {
        "demonstration_only": True,
        "source": "Existing real JDT chronological holdout row; inference demonstration, not a new evaluation.",
        "developer_identifiers_redacted": True,
        "request": bug_report,
        "response": {
            "bug_id": response["bug_id"],
            "recommendations": redacted_recommendations,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bug-id", help="Use a specific bug ID from the holdout CSV.")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--test-path", default=str(DEFAULT_TEST_PATH))
    args = parser.parse_args()
    result = build_demo(args.bug_id, args.top_k, args.test_path)
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
