"""Preprocess verified JDT assignment history for Member 2 experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ml_model.jdt_dataset import prepare_member2_data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--processed-dir", default="data/processed")
    args = parser.parse_args()
    report = prepare_member2_data(args.raw_dir, args.processed_dir)
    report_path = Path(args.processed_dir) / "jdt_preprocessing_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"Saved preprocessing report to {report_path}")


if __name__ == "__main__":
    main()
