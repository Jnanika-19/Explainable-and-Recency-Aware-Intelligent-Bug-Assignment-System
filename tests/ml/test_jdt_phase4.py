import numpy as np
import pandas as pd
import pytest

from ml_model.jdt_recommendation import FEATURE_COLUMNS
from ml_model.train_jdt_phase4 import (
    _make_matrix,
    _ranking_outputs,
    _read_candidate_features,
)


def _candidate_frame():
    rows = []
    for bug_id, target in ((1, "Dev-A"), (2, "Dev-B")):
        for candidate in ("Dev-A", "Dev-B"):
            row = {
                "bug_id": bug_id,
                "candidate_developer_id": candidate,
                "target_developer_id": target,
                "is_ground_truth_candidate": candidate == target,
            }
            row.update({column: 0.0 for column in FEATURE_COLUMNS})
            row["historical_bug_count"] = 1.0 if candidate == "Dev-A" else 0.0
            row["days_since_last_activity"] = (
                np.nan if candidate == "Dev-B" else 3.0
            )
            rows.append(row)
    return pd.DataFrame(rows)


def _bug_records():
    return pd.DataFrame([
        {
            "bug_id": 1,
            "title": "alpha title",
            "description": "training description",
            "product": "JDT",
            "component": "Core",
            "severity": "major",
            "priority": "P1",
        },
        {
            "bug_id": 2,
            "title": "beta title",
            "description": "validationonly description",
            "product": "JDT",
            "component": "UI",
            "severity": "minor",
            "priority": "P2",
        },
    ])


def test_combined_matrix_uses_text_metadata_and_expertise_without_ids():
    candidates = _candidate_frame()
    bugs = _bug_records()
    training = candidates.loc[candidates["bug_id"].eq(1)].copy()
    train_matrix, transformers = _make_matrix(
        bugs.loc[bugs["bug_id"].eq(1)],
        training,
        {},
        fit=True,
    )
    validation = candidates.loc[candidates["bug_id"].eq(2)].copy()
    validation_matrix, _ = _make_matrix(
        bugs.loc[bugs["bug_id"].eq(2)],
        validation,
        transformers,
        fit=False,
    )

    assert train_matrix.shape[0] == 2
    assert validation_matrix.shape[0] == 2
    assert train_matrix.shape[1] == validation_matrix.shape[1]
    assert "training" in transformers["description_vectorizer"].vocabulary_
    assert "validationonly" not in transformers["description_vectorizer"].vocabulary_
    assert len(transformers["numeric_input_columns"]) == len(FEATURE_COLUMNS) + 2


def test_candidate_and_target_ids_do_not_change_predictive_matrix():
    candidates = _candidate_frame()
    bugs = _bug_records().loc[lambda frame: frame["bug_id"].eq(1)]
    pair_rows = candidates.loc[candidates["bug_id"].eq(1)].copy()
    matrix, transformers = _make_matrix(bugs, pair_rows, {}, fit=True)
    changed_ids = pair_rows.copy()
    changed_ids["candidate_developer_id"] = ["Other-1", "Other-2"]
    changed_ids["target_developer_id"] = ["Other-2", "Other-1"]
    changed_ids["is_ground_truth_candidate"] = [False, True]
    changed_matrix, _ = _make_matrix(bugs, changed_ids, transformers, fit=False)
    assert (matrix != changed_matrix).nnz == 0


def test_rankings_are_candidate_specific_and_ties_use_id_order():
    rows = pd.DataFrame({
        "bug_id": [1, 1, 2, 2],
        "candidate_developer_id": ["Dev-B", "Dev-A", "Dev-B", "Dev-A"],
        "target_developer_id": ["Dev-A", "Dev-A", "Unseen", "Unseen"],
    })
    rankings, actual = _ranking_outputs(rows, np.asarray([0.5, 0.5, 1.0, 0.0]))
    assert rankings[1] == ["Dev-A", "Dev-B"]
    assert rankings[2] == ["Dev-B", "Dev-A"]
    assert actual == {1: "Dev-A", 2: "Unseen"}


def test_candidate_label_mismatch_is_rejected(tmp_path):
    rows = _candidate_frame().iloc[:1].copy()
    rows["is_ground_truth_candidate"] = False
    path = tmp_path / "candidates.csv"
    rows.to_csv(path, index=False)
    with pytest.raises(ValueError, match="Candidate labels do not match"):
        _read_candidate_features(path)
