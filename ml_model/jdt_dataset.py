
"""Leakage-aware preprocessing helpers for Member 2's JDT assignment data."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from preprocessing.feature_preparation.text import clean_report_text


PRIMARY_COLUMNS = {
    "bug_id",
    "summary",
    "description",
    "product",
    "component",
    "severity",
    "priority",
    "creation_time",
    "developer_label",
    "label_event_time",
    "label_event_type",
    "label_type",
    "candidate_evidence_type",
    "jdt_entry_time",
    "history_status",
}

PROFILE_COLUMNS = {
    "first_observed_developer",
    "total_assigned_bugs",
    "components_worked_on",
    "known_entry_bugs",
    "provisional_bugs",
    "first_recorded_assignment",
    "latest_recorded_assignment",
}

EXPERTISE_COLUMNS = {
    "first_observed_developer",
    "component",
    "bug_count",
    "share_within_developer",
}

TIMESTAMP_COLUMNS = ("creation_time", "label_event_time", "jdt_entry_time")


def normalize_developer_id(value: object) -> str:
    """Trim and Unicode-normalize IDs without case-folding distinct identities."""
    if not isinstance(value, str):
        raise ValueError(
            f"Developer ID must be text, got {type(value).__name__}."
        )

    normalized = unicodedata.normalize("NFC", value).strip()

    if not normalized:
        raise ValueError("Developer ID cannot be blank.")

    return normalized


# Java stack-trace frame detection
_STACK_TRACE_FRAME = re.compile(
    r"^\s*at\s+.+\([^)]+:\d+\)\s*$"
)

_STACK_TRACE_LINE_MIN_LENGTH = 300


def clean_bug_text(value: object) -> str:
    """
    Restore escaped newlines, remove long stack-trace frames,
    and normalize text.
    """

    text = str(value or "")

    # Restore escaped line breaks.
    # Double-escaped sequences are replaced without modifying
    # normal Windows paths.
    text = (
        text.replace("\\\\r\\\\n", "\n")
        .replace("\\\\n", "\n")
    )

    # Remove unusually long Java stack-trace lines.
    # Preserve ordinary report text and Windows paths.
    lines = text.splitlines()

    filtered_lines = [
        line
        for line in lines
        if not (
            len(line.strip()) > _STACK_TRACE_LINE_MIN_LENGTH
            and _STACK_TRACE_FRAME.match(line)
        )
    ]

    # Apply the shared project text cleaner.
    cleaned = clean_report_text("\n".join(filtered_lines))

    # Normalize text to lowercase.
    return cleaned.lower()


def _read_csv(
    path: Path,
    expected_columns: set[str],
    label: str
) -> pd.DataFrame:

    if not path.is_file():
        raise FileNotFoundError(
            f"Required {label} dataset not found: {path}"
        )

    frame = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False
    )

    if len(frame.columns) != len(set(frame.columns)):
        raise ValueError(
            f"{label} dataset contains duplicate column names."
        )

    missing = expected_columns - set(frame.columns)

    if missing:
        raise ValueError(
            f"{label} dataset is missing columns: {sorted(missing)}"
        )

    return frame


def _normalise_ids(
    values: pd.Series,
    label: str
) -> pd.Series:

    normalized = values.map(normalize_developer_id)

    raw_to_normalized: dict[str, set[str]] = defaultdict(set)

    for raw, canonical in zip(values, normalized, strict=True):
        raw_to_normalized[canonical].add(raw)

    collisions = {
        key: sorted(raw_ids)
        for key, raw_ids in raw_to_normalized.items()
        if len(raw_ids) > 1
    }

    if collisions:
        raise ValueError(
            f"{label} ID normalization would merge distinct values: {collisions}"
        )

    return normalized


def _parse_utc_column(
    frame: pd.DataFrame,
    column: str,
    *,
    required: bool
) -> None:

    raw = frame[column].astype("string").str.strip()

    parsed = pd.to_datetime(
        raw.replace("", pd.NA),
        utc=True,
        errors="coerce"
    )

    invalid = raw.ne("").fillna(False) & parsed.isna()

    if invalid.any():
        examples = raw[invalid].head(5).tolist()

        raise ValueError(
            f"Invalid timestamps in {column}: {examples}"
        )

    if required and parsed.isna().any():
        raise ValueError(
            f"Required timestamp column {column} contains missing values."
        )

    frame[column] = parsed


def _parse_integer_column(
    frame: pd.DataFrame,
    column: str,
    label: str
) -> None:

    raw = frame[column].astype("string").str.strip()

    parsed = pd.to_numeric(
        raw.replace("", pd.NA),
        errors="coerce"
    )

    invalid = parsed.isna() | (parsed % 1 != 0)

    if invalid.any():
        examples = raw[invalid].head(5).tolist()

        raise ValueError(
            f"Invalid integer values in {label}.{column}: {examples}"
        )

    frame[column] = parsed.astype("int64")


def _format_utc(value: object) -> str:
    timestamp = pd.Timestamp(value)

    if timestamp.tzinfo is None:
        raise ValueError(
            "Cannot serialize a timezone-naive timestamp as UTC."
        )

    return timestamp.tz_convert("UTC").strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _validate_unique_normalization(
    original: pd.Series,
    normalized: pd.Series
) -> None:

    pairs = pd.DataFrame({
        "original": original,
        "normalized": normalized
    }).drop_duplicates()

    collisions = (
        pairs.groupby("normalized", sort=False)["original"].nunique()
    )

    if (collisions > 1).any():
        raise ValueError(
            "Developer ID normalization merges distinct source IDs: "
            f"{collisions[collisions > 1].index.tolist()}"
        )


def _check_profile_aggregates(
    primary: pd.DataFrame,
    profiles: pd.DataFrame,
    expertise: pd.DataFrame
) -> dict[str, int]:

    primary_ids = set(primary["developer_id"])
    profile_ids = set(profiles["developer_id"])
    expertise_ids = set(expertise["developer_id"])

    if primary_ids != profile_ids or primary_ids != expertise_ids:
        raise ValueError(
            "Developer IDs do not match across datasets: "
            f"primary-only={sorted(primary_ids - profile_ids - expertise_ids)[:10]}, "
            f"profile-only={sorted(profile_ids - primary_ids)[:10]}, "
            f"expertise-only={sorted(expertise_ids - primary_ids)[:10]}"
        )

    counts = (
        primary.groupby(
            ["developer_id", "label_type"],
            sort=False
        )
        .size()
        .unstack(fill_value=0)
    )

    totals = primary.groupby(
        "developer_id",
        sort=False
    ).size()

    component_counts = expertise.groupby(
        "developer_id",
        sort=False
    ).size()

    expertise_totals = (
        expertise.groupby("developer_id", sort=False)["bug_count"].sum()
    )

    profile_indexed = profiles.set_index("developer_id")

    mismatches = []

    for developer_id in sorted(primary_ids):

        profile = profile_indexed.loc[developer_id]

        known_count = int(
            counts.loc[developer_id].get("known_entry", 0)
        )

        provisional_count = int(
            counts.loc[developer_id].get("provisional", 0)
        )

        if (
            int(profile["total_assigned_bugs"])
            != int(totals.loc[developer_id])
            or int(profile["known_entry_bugs"]) != known_count
            or int(profile["provisional_bugs"]) != provisional_count
            or int(profile["components_worked_on"])
            != int(component_counts.loc[developer_id])
            or int(expertise_totals.loc[developer_id])
            != int(totals.loc[developer_id])
        ):
            mismatches.append(developer_id)

    share_sums = (
        expertise.groupby(
            "developer_id",
            sort=False
        )["share_within_developer"].sum()
    )

    bad_shares = share_sums[
        (share_sums - 1.0).abs() > 1e-6
    ]

    if mismatches or not bad_shares.empty:
        raise ValueError(
            "Developer aggregates do not reconcile: "
            f"count_mismatches={mismatches[:10]}, "
            f"share_mismatches={bad_shares.index.tolist()[:10]}"
        )

    return {
        "distinct_developers": len(primary_ids),
        "profile_rows": len(profiles),
        "expertise_rows": len(expertise),
        "profile_count_mismatches": 0,
        "expertise_share_mismatches": 0,
    }


def chronological_split(
    known: pd.DataFrame,
    test_fraction: float = 0.2
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp, pd.DataFrame]:
    """Split by issue creation while requiring training labels known by cutoff."""

    if not 0 < test_fraction < 1:
        raise ValueError(
            "test_fraction must be between 0 and 1."
        )

    if known.empty:
        raise ValueError(
            "Cannot split an empty known-entry dataset."
        )

    ordered = (
        known.sort_values(
            ["created_at", "bug_id"],
            kind="stable"
        ).reset_index(drop=True)
    )

    cut_index = math.floor(
        len(ordered) * (1 - test_fraction)
    )

    if cut_index <= 0 or cut_index >= len(ordered):
        raise ValueError(
            "Not enough records for the requested chronological split."
        )

    cutoff = pd.Timestamp(
        ordered.loc[cut_index, "created_at"]
    )

    train_mask = (
        (ordered["created_at"] < cutoff)
        & (ordered["assignment_time"] < cutoff)
    )

    test_mask = ordered["created_at"] >= cutoff

    excluded_mask = (
        (ordered["created_at"] < cutoff)
        & (ordered["assignment_time"] >= cutoff)
    )

    train = (
        ordered.loc[train_mask].copy().reset_index(drop=True)
    )

    test = (
        ordered.loc[test_mask].copy().reset_index(drop=True)
    )

    excluded = (
        ordered.loc[excluded_mask].copy().reset_index(drop=True)
    )

    if train.empty or test.empty:
        raise ValueError(
            "The leakage-safe chronological split produced an empty partition."
        )

    if not (train["assignment_time"] < cutoff).all():
        raise AssertionError(
            "Training contains an assignment label not known by cutoff."
        )

    if not (test["created_at"] >= cutoff).all():
        raise AssertionError(
            "Test contains a bug created before the cutoff."
        )

    if set(train["bug_id"]) & set(test["bug_id"]):
        raise AssertionError(
            "Train and test bug IDs overlap."
        )

    return train, test, cutoff, excluded


def build_temporal_expertise(
    known: pd.DataFrame,
    test: pd.DataFrame,
    candidates: list[str],
) -> pd.DataFrame:
    """Build per-candidate evidence snapshots using only prior assignment events."""

    history = known.sort_values(
        ["assignment_time", "bug_id"],
        kind="stable"
    )

    predictions = test.sort_values(
        ["created_at", "bug_id"],
        kind="stable"
    )

    events = history.to_dict(orient="records")

    total_by_developer: Counter[str] = Counter()

    component_by_pair: Counter[tuple[str, str]] = Counter()

    last_by_developer: dict[str, pd.Timestamp] = {}

    cursor = 0
    snapshots = []

    for prediction in predictions.to_dict(orient="records"):

        prediction_time = pd.Timestamp(
            prediction["created_at"]
        )

        while (
            cursor < len(events)
            and pd.Timestamp(events[cursor]["assignment_time"])
            < prediction_time
        ):

            event = events[cursor]

            developer_id = str(event["developer_id"])
            component = str(event["component"])

            total_by_developer[developer_id] += 1

            component_by_pair[
                (developer_id, component)
            ] += 1

            last_by_developer[developer_id] = pd.Timestamp(
                event["assignment_time"]
            )

            cursor += 1

        for developer_id in candidates:

            prior_total = total_by_developer[developer_id]

            prior_component = component_by_pair[
                (developer_id, str(prediction["component"]))
            ]

            last_assignment = last_by_developer.get(developer_id)

            snapshots.append({
                "prediction_bug_id": int(prediction["bug_id"]),
                "prediction_time_utc": _format_utc(prediction_time),
                "candidate_developer_id": developer_id,
                "prior_known_assignment_count": prior_total,
                "prior_component_assignment_count": prior_component,
                "prior_component_share": (
                    prior_component / prior_total if prior_total else 0.0
                ),
                "last_prior_assignment_utc": (
                    _format_utc(last_assignment)
                    if last_assignment is not None
                    else ""
                ),
                "days_since_last_prior_assignment": (
                    (prediction_time - last_assignment).total_seconds() / 86400
                    if last_assignment is not None
                    else ""
                ),
            })

        if pd.Timestamp(prediction["assignment_time"]) < prediction_time:
            raise ValueError(
                "A test assignment event predates its prediction time."
            )

    snapshot_frame = pd.DataFrame(snapshots)

    if not snapshot_frame.empty and (
        snapshot_frame["last_prior_assignment_utc"].ne("").any()
        and not (
            pd.to_datetime(
                snapshot_frame.loc[
                    snapshot_frame["last_prior_assignment_utc"].ne(""),
                    "last_prior_assignment_utc",
                ],
                utc=True,
            )
            < pd.to_datetime(
                snapshot_frame.loc[
                    snapshot_frame["last_prior_assignment_utc"].ne(""),
                    "prediction_time_utc",
                ],
                utc=True,
            )
        ).all()
    ):
        raise AssertionError(
            "Temporal expertise contains an assignment from the future."
        )

    return snapshot_frame


def prepare_member2_data(
    raw_dir: str | Path,
    processed_dir: str | Path
) -> dict:
    """Validate all source tables and write supervised/exploratory datasets."""

    raw_dir = Path(raw_dir)
    processed_dir = Path(processed_dir)

    primary = _read_csv(
        raw_dir / "jdt_training_primary.csv",
        PRIMARY_COLUMNS,
        "primary"
    )

    profiles = _read_csv(
        raw_dir / "developer_profile_summary.csv",
        PROFILE_COLUMNS,
        "profile"
    )

    expertise = _read_csv(
        raw_dir / "developer_component_expertise.csv",
        EXPERTISE_COLUMNS,
        "expertise"
    )

    source_counts = {
        "primary_rows": len(primary),
        "profile_rows": len(profiles),
        "expertise_rows": len(expertise),
    }

    if primary["bug_id"].duplicated().any():
        raise ValueError(
            "Primary dataset contains duplicate bug IDs."
        )

    if primary.duplicated().any():
        raise ValueError(
            "Primary dataset contains exact duplicate rows."
        )

    if profiles["first_observed_developer"].duplicated().any():
        raise ValueError(
            "Developer profile dataset contains duplicate developer IDs."
        )

    _parse_integer_column(primary, "bug_id", "primary")

    for column in TIMESTAMP_COLUMNS:
        _parse_utc_column(
            primary,
            column,
            required=column != "jdt_entry_time"
        )

    for column in (
        "total_assigned_bugs",
        "components_worked_on",
        "known_entry_bugs",
        "provisional_bugs"
    ):
        _parse_integer_column(
            profiles,
            column,
            "profile"
        )

    for column in (
        "first_recorded_assignment",
        "latest_recorded_assignment"
    ):
        _parse_utc_column(
            profiles,
            column,
            required=True
        )

    _parse_integer_column(
        expertise,
        "bug_count",
        "expertise"
    )

    expertise["share_within_developer"] = pd.to_numeric(
        expertise["share_within_developer"],
        errors="coerce"
    )

    if expertise["share_within_developer"].isna().any():
        raise ValueError(
            "Expertise dataset contains invalid component shares."
        )

    if (
        (expertise["bug_count"] < 0).any()
        or (expertise["share_within_developer"] < 0).any()
    ):
        raise ValueError(
            "Expertise counts and shares must be non-negative."
        )

    if expertise.duplicated(
        ["first_observed_developer", "component"]
    ).any():
        raise ValueError(
            "Expertise dataset contains duplicate developer-component rows."
        )

    primary_original = primary["developer_label"].copy()

    primary["developer_id"] = _normalise_ids(
        primary_original,
        "primary"
    )

    profiles_original = profiles["first_observed_developer"].copy()

    profiles["developer_id"] = _normalise_ids(
        profiles_original,
        "profile"
    )

    expertise_original = expertise["first_observed_developer"].copy()

    expertise["developer_id"] = _normalise_ids(
        expertise_original,
        "expertise"
    )

    for originals, normalized in (
        (primary_original, primary["developer_id"]),
        (profiles_original, profiles["developer_id"]),
        (expertise_original, expertise["developer_id"]),
    ):
        _validate_unique_normalization(
            originals,
            normalized
        )

    label_types = set(primary["label_type"])

    if label_types != {"known_entry", "provisional"}:
        raise ValueError(
            f"Unexpected primary label types: {sorted(label_types)}"
        )

    if primary["developer_id"].eq("").any():
        raise ValueError(
            "Primary dataset contains blank developer assignments."
        )

    for column, expected in (
        ("label_event_type", "assignment_added"),
        ("candidate_evidence_type", "direct_assignment"),
        ("history_status", "readable"),
        ("product", "JDT"),
    ):
        if not primary[column].eq(expected).all():
            raise ValueError(
                f"Primary dataset contains unsupported {column} values."
            )

    for column in ("component", "severity", "priority"):
        if primary[column].str.strip().eq("").any():
            raise ValueError(
                f"Primary dataset contains missing {column} values."
            )

    known_mask = primary["label_type"].eq("known_entry")
    provisional_mask = primary["label_type"].eq("provisional")

    known = primary.loc[known_mask].copy()
    provisional = primary.loc[provisional_mask].copy()

    if known["jdt_entry_time"].isna().any():
        raise ValueError(
            "Known-entry records must have a valid JDT entry timestamp."
        )

    if provisional["jdt_entry_time"].notna().any():
        raise ValueError(
            "Provisional records unexpectedly contain JDT entry timestamps."
        )

    if not (
        primary["creation_time"] < primary["label_event_time"]
    ).all():
        raise ValueError(
            "Primary assignment events must follow bug creation."
        )

    if not (
        (known["jdt_entry_time"] >= known["creation_time"])
        & (known["jdt_entry_time"] <= known["label_event_time"])
    ).all():
        raise ValueError(
            "Known-entry timestamps are not in chronological order."
        )

    profile_ranges_valid = (
        profiles["first_recorded_assignment"]
        <= profiles["latest_recorded_assignment"]
    )

    if not profile_ranges_valid.all():
        raise ValueError(
            "Developer profile has an inverted assignment time range."
        )

    if expertise.duplicated(
        ["developer_id", "component"]
    ).any():
        raise ValueError(
            "ID normalization creates duplicate expertise component rows."
        )

    aggregate_check = _check_profile_aggregates(
        primary,
        profiles,
        expertise
    )

    if (
        primary["developer_id"].nunique()
        != profiles["developer_id"].nunique()
    ):
        raise ValueError(
            "Developer identity normalization reduced the identity count."
        )

    # Text cleaning is shared with the existing BugWise preprocessing contract.
    primary["title"] = primary["summary"].map(clean_bug_text)
    primary["description"] = primary["description"].map(clean_bug_text)

    primary["created_at"] = primary["creation_time"]
    primary["assignment_time"] = primary["label_event_time"]

    primary["jdt_entry_time_utc"] = primary["jdt_entry_time"].map(
        lambda value: (
            _format_utc(value)
            if not pd.isna(value)
            else ""
        )
    )

    common_columns = [
        "bug_id",
        "title",
        "description",
        "product",
        "component",
        "severity",
        "priority",
        "created_at",
        "assignment_time",
        "developer_id",
        "developer_label",
        "label_type",
        "jdt_entry_time_utc",
    ]

    supervised = (
        primary.loc[known_mask, common_columns]
        .rename(columns={"developer_label": "developer_id_original"})
        .reset_index(drop=True)
    )

    exploratory = (
        primary.loc[provisional_mask, common_columns]
        .rename(
            columns={
                "developer_id": "assigned_developer_exploratory",
                "developer_label": "assigned_developer_original",
            }
        )
        .reset_index(drop=True)
    )

    train, test, cutoff, excluded = chronological_split(supervised)

    train_developers = sorted(
        train["developer_id"].unique().tolist()
    )

    temporal_expertise = build_temporal_expertise(
        supervised,
        test,
        train_developers
    )

    processed_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    outputs = {
        "jdt_known_entry_preprocessed.csv": supervised,
        "jdt_provisional_exploratory.csv": exploratory,
        "jdt_known_entry_train.csv": train,
        "jdt_known_entry_test.csv": test,
        "jdt_test_temporal_expertise.csv": temporal_expertise,
    }

    for filename, frame in outputs.items():
        frame.to_csv(
            processed_dir / filename,
            index=False,
            encoding="utf-8"
        )

    class_counts = supervised["developer_id"].value_counts()

    train_class_counts = train["developer_id"].value_counts()

    test_seen = test["developer_id"].isin(train_developers)

    report = {
        "source_counts": source_counts,

        "source_reconciliation": aggregate_check,

        "source_integrity": {
            "primary_duplicate_bug_ids": 0,
            "primary_exact_duplicate_rows": 0,
            "profile_duplicate_developer_ids": 0,
            "expertise_duplicate_developer_component_rows": 0,
            "developer_id_normalization": "trim and Unicode NFC; case preserved",
            "distinct_developer_ids": int(
                primary["developer_id"].nunique()
            ),
            "developer_id_casefold_collision": [
                value
                for value in sorted(primary["developer_id"].unique())
                if value.casefold() == "lars.vogel@vogella.com"
            ],
        },

        "label_counts": {
            "known_entry": len(supervised),
            "provisional_exploratory_only": len(exploratory),
        },

        "missing_text_values": {
            "known_entry_empty_titles": int(
                supervised["title"].eq("").sum()
            ),
            "known_entry_empty_descriptions": int(
                supervised["description"].eq("").sum()
            ),
            "provisional_empty_titles": int(
                exploratory["title"].eq("").sum()
            ),
            "provisional_empty_descriptions": int(
                exploratory["description"].eq("").sum()
            ),
        },

        "chronological_split": {
            "cutoff_utc": _format_utc(cutoff),
            "requested_test_fraction": 0.2,
            "training_rows": len(train),
            "training_developer_classes": len(train_developers),
            "test_rows": len(test),
            "test_rows_with_developer_seen_in_training": int(
                test_seen.sum()
            ),
            "test_rows_with_unseen_developer": int(
                (~test_seen).sum()
            ),
            "test_developer_classes_seen_in_training": int(
                test.loc[
                    test_seen,
                    "developer_id"
                ].nunique()
            ),
            "test_developer_classes_unseen_in_training": int(
                test.loc[
                    ~test_seen,
                    "developer_id"
                ].nunique()
            ),
            "excluded_pre_cutoff_rows_with_future_assignment_events": len(
                excluded
            ),
            "training_label_events_before_cutoff": bool(
                (train["assignment_time"] < cutoff).all()
            ),
            "test_bug_creation_at_or_after_cutoff": bool(
                (
                    test["created_at"].map(pd.Timestamp) >= cutoff
                ).all()
            ),
        },

        "class_imbalance": {
            "known_entry_classes": int(len(class_counts)),
            "known_entry_min_rows_per_developer": int(
                class_counts.min()
            ),
            "known_entry_median_rows_per_developer": float(
                class_counts.median()
            ),
            "known_entry_max_rows_per_developer": int(
                class_counts.max()
            ),
            "known_entry_singleton_developers": int(
                (class_counts == 1).sum()
            ),
            "training_min_rows_per_developer": int(
                train_class_counts.min()
            ),
            "training_median_rows_per_developer": float(
                train_class_counts.median()
            ),
            "training_max_rows_per_developer": int(
                train_class_counts.max()
            ),
            "training_singleton_developers": int(
                (train_class_counts == 1).sum()
            ),
            "known_entry_top_10_developers": [
                {
                    "developer_id": str(developer_id),
                    "rows": int(count)
                }
                for developer_id, count in class_counts.head(10).items()
            ],
        },

        "temporal_expertise": {
            "rows": len(temporal_expertise),
            "candidate_developers": len(train_developers),
            "timestamp_rule": "assignment_time < prediction created_at",
            "used_as_baseline_model_input": False,
        },

        "model_input_columns": ["title", "description"],
        "original_csv_files_modified": False,
        "provisional_rows_used_as_supervised_targets": 0,
    }

    return report
