"""Dataset inspection and explicit mapping into the project's canonical schema."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import pandas as pd

from preprocessing.feature_preparation.text import clean_report_text


REQUIRED_FIELDS = ("bug_id", "developer_id", "title", "description")
OPTIONAL_FIELDS = (
    "product", "component", "severity", "priority", "created_at",
    "resolved_at", "status",
)


@dataclass(frozen=True)
class DatasetSchema:
    """Maps canonical field names to the exact column names in a source file."""

    columns: Mapping[str, str]
    resolved_values: tuple[str, ...] = field(default_factory=tuple)

    def validate(self, available_columns: list[str]) -> None:
        missing = [
            canonical for canonical in REQUIRED_FIELDS
            if canonical not in self.columns
        ]
        if missing:
            raise ValueError(f"Schema mapping is missing required fields: {missing}")
        bad = {
            canonical: source
            for canonical, source in self.columns.items()
            if source not in available_columns
        }
        if bad:
            raise ValueError(
                f"Mapped source columns were not found: {bad}. "
                f"Available columns: {available_columns}"
            )


def inspect_csv(path: str | Path, sample_rows: int = 5) -> dict:
    """Return the actual CSV headers and a small sample without guessing fields."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        sample = stream.read(8192)
        stream.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(stream, dialect=dialect)
        columns = reader.fieldnames or []
        rows = [row for _, row in zip(range(sample_rows), reader)]
    return {"path": str(path), "columns": columns, "delimiter": dialect.delimiter,
            "sample": rows}


def load_canonical_csv(path: str | Path, schema: DatasetSchema) -> pd.DataFrame:
    """Read a CSV and rename only explicitly mapped columns to canonical names."""
    inspected = inspect_csv(path, sample_rows=0)
    schema.validate(inspected["columns"])
    frame = pd.read_csv(path, sep=inspected["delimiter"])
    selected = {
        source: canonical
        for canonical, source in schema.columns.items()
    }
    frame = frame[list(selected)].rename(columns=selected).copy()
    for field_name in ("bug_id", "developer_id", "title", "description"):
        frame[field_name] = frame[field_name].fillna("").astype(str).str.strip()
    for field_name in ("title", "description"):
        frame[field_name] = frame[field_name].map(clean_report_text)
    for field_name in OPTIONAL_FIELDS:
        if field_name not in frame:
            frame[field_name] = ""
        else:
            frame[field_name] = frame[field_name].fillna("").astype(str).str.strip()
    frame = frame[
        frame["bug_id"].ne("")
        & frame["developer_id"].ne("")
        & (frame["title"].ne("") | frame["description"].ne(""))
    ]
    if frame["bug_id"].duplicated().any():
        duplicates = int(frame["bug_id"].duplicated(keep=False).sum())
        raise ValueError(
            f"Found {duplicates} rows belonging to repeated bug IDs. "
            "Prepare one final assigned/resolved record per bug in the "
            "Member 1 preprocessing output before training."
        )
    if schema.resolved_values and "status" in schema.columns:
        allowed = {value.casefold() for value in schema.resolved_values}
        frame = frame[frame["status"].str.casefold().isin(allowed)]
    if "created_at" in schema.columns:
        frame["created_at"] = pd.to_datetime(frame["created_at"], errors="coerce", utc=True)
    if "resolved_at" in schema.columns:
        frame["resolved_at"] = pd.to_datetime(frame["resolved_at"], errors="coerce", utc=True)
    if frame.empty:
        raise ValueError("No usable assigned bug records remain after validation.")
    return frame.reset_index(drop=True)
