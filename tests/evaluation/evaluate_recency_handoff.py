
"""
Member 3 - Recency evaluation using Member 2's validated handoff.

Objectives:
1. Recalculate Member 3 recency for all 331 test bugs x 79 candidates.
2. Compare the result with Member 2's existing recency features.
3. Evaluate Recency-only ranking against the ML-only baseline.
4. Check candidate coverage and chronological filtering.
5. Save evaluation outputs without modifying original datasets.
"""

import json
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------
# PROJECT CONFIGURATION
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data" / "processed"

HANDOFF_DIR = (
    PROJECT_ROOT
    / "ml_model"
    / "exports"
    / "member3_handoff"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "results"
    / "member3"
    / "recency"
)

TRAIN_FILE = DATA_DIR / "jdt_known_entry_train.csv"

FEATURE_FILE = HANDOFF_DIR / "member2_candidate_features_331x79.csv"
SCORE_FILE = HANDOFF_DIR / "member2_candidate_scores_331x79.csv"
GROUND_TRUTH_FILE = HANDOFF_DIR / "member2_ground_truth.csv"
ROSTER_FILE = HANDOFF_DIR / "member2_candidate_roster.csv"
VALIDATION_FILE = HANDOFF_DIR / "member2_candidate_export_validation.json"

sys.path.insert(0, str(PROJECT_ROOT))

from scoring_engine.recency.recency_calculator import (
    DEFAULT_HALF_LIFE_DAYS,
    get_all_developer_recency,
    parse_timestamp,
)


# ---------------------------------------------------------
# GENERAL HELPERS
# ---------------------------------------------------------

def check_files():

    required = [
        TRAIN_FILE,
        FEATURE_FILE,
        SCORE_FILE,
        GROUND_TRUTH_FILE,
        ROSTER_FILE,
        VALIDATION_FILE,
    ]

    missing = [str(path) for path in required if not path.is_file()]

    if missing:
        raise FileNotFoundError(
            "Required input files are missing:\n"
            + "\n".join(missing)
        )


def load_csv(path):

    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False
    )


def check_columns(frame, required, filename):

    missing = set(required) - set(frame.columns)

    if missing:
        raise ValueError(
            f"{filename} is missing columns: {sorted(missing)}"
        )


def ranking_metrics(name, rank_map, actual_map):

    total = len(actual_map)

    seen_ranks = [
        rank_map[bug_id]
        for bug_id in actual_map
        if rank_map.get(bug_id) is not None
    ]

    all_ranks = [
        rank_map.get(bug_id)
        for bug_id in actual_map
    ]

    def top_k(ranks, k):
        return sum(
            rank is not None and rank <= k
            for rank in ranks
        )

    reciprocal_sum = sum(
        1.0 / rank if rank is not None else 0.0
        for rank in all_ranks
    )

    seen_reciprocal_sum = sum(
        1.0 / rank for rank in seen_ranks
    )

    return {
        "method": name,
        "total_test_bugs": total,
        "targets_in_candidate_roster": len(seen_ranks),
        "targets_outside_candidate_roster": total - len(seen_ranks),

        "top1_all_pct": top_k(all_ranks, 1) / total * 100,
        "top3_all_pct": top_k(all_ranks, 3) / total * 100,
        "top5_all_pct": top_k(all_ranks, 5) / total * 100,
        "mrr_all": reciprocal_sum / total,

        "top1_seen_pct": (
            top_k(seen_ranks, 1) / len(seen_ranks) * 100
            if seen_ranks else 0
        ),
        "top3_seen_pct": (
            top_k(seen_ranks, 3) / len(seen_ranks) * 100
            if seen_ranks else 0
        ),
        "top5_seen_pct": (
            top_k(seen_ranks, 5) / len(seen_ranks) * 100
            if seen_ranks else 0
        ),
        "mrr_seen": (
            seen_reciprocal_sum / len(seen_ranks)
            if seen_ranks else 0
        ),
    }


# ---------------------------------------------------------
# LOAD AND VALIDATE INPUT DATA
# ---------------------------------------------------------

def run_evaluation():

    print("\n========== MEMBER 3 RECENCY EVALUATION ==========")

    check_files()

    train = load_csv(TRAIN_FILE)
    features = load_csv(FEATURE_FILE)
    ground_truth = load_csv(GROUND_TRUTH_FILE)
    roster = load_csv(ROSTER_FILE)
    scores = pd.read_csv(SCORE_FILE, dtype={"bug_id": str})

    with VALIDATION_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        member2_validation = json.load(file)

    check_columns(
        train,
        ["bug_id", "developer_id", "assignment_time"],
        "Training dataset"
    )

    check_columns(
        features,
        [
            "bug_id",
            "prediction_timestamp_utc",
            "candidate_developer_id",
            "days_since_last_activity",
            "days_since_last_component",
            "component_recency_score",
        ],
        "Member 2 feature dataset"
    )

    check_columns(
        ground_truth,
        [
            "bug_id",
            "prediction_timestamp_utc",
            "actual_developer_id",
        ],
        "Ground truth"
    )

    check_columns(
        roster,
        ["developer_id"],
        "Candidate roster"
    )

    # -----------------------------------------------------
    # PREPARE CANDIDATE ROSTER
    # -----------------------------------------------------

    candidates = sorted(
        set(roster["developer_id"].str.strip())
    )

    if len(candidates) != 79:
        raise ValueError(
            f"Expected 79 developers, found {len(candidates)}."
        )

    candidate_set = set(candidates)

    # -----------------------------------------------------
    # VALIDATE TRAINING DATA
    # -----------------------------------------------------

    train["bug_id"] = train["bug_id"].str.strip()
    train["developer_id"] = train["developer_id"].str.strip()

    train["assignment_time"] = train[
        "assignment_time"
    ].map(parse_timestamp)

    if "label_type" in train.columns:

        label_types = set(train["label_type"])

        if label_types != {"known_entry"}:
            raise ValueError(
                "Training history contains non-verified records."
            )

    if not set(candidates).issubset(
        set(train["developer_id"])
    ):
        raise ValueError(
            "Some candidate developers are missing from training history."
        )

    events = []

    for row in train.to_dict(orient="records"):

        events.append({
            "bug_id": row["bug_id"],
            "developer_label": row["developer_id"],
            "label_event_time": row["assignment_time"].isoformat(),
            "label_event_type": "assignment_added",
        })

    print("\nTRAINING HISTORY")
    print("Verified training assignments:", len(events))
    print("Candidate developers:", len(candidates))

    # -----------------------------------------------------
    # VALIDATE TEST BUGS AND FEATURE PAIRS
    # -----------------------------------------------------

    ground_truth["bug_id"] = (
        ground_truth["bug_id"].str.strip()
    )

    if ground_truth["bug_id"].duplicated().any():
        raise ValueError("Duplicate ground-truth bug IDs found.")

    if len(ground_truth) != 331:
        raise ValueError(
            f"Expected 331 test bugs, got {len(ground_truth)}."
        )

    features["bug_id"] = features["bug_id"].astype(str)
    features["candidate_developer_id"] = (
        features["candidate_developer_id"].str.strip()
    )

    ground_truth["prediction_timestamp_utc"] = (
        ground_truth["prediction_timestamp_utc"].map(
            parse_timestamp
        )
    )

    if len(features) != 331 * 79:
        raise ValueError(
            f"Expected 26149 feature rows, got {len(features)}."
        )

    if features.duplicated(
        ["bug_id", "candidate_developer_id"]
    ).any():
        raise ValueError("Duplicate bug-candidate feature pairs.")

    if len(scores) != 331:
        raise ValueError("Incorrect ML score row count.")

    candidate_score_columns = [
        column for column in scores.columns
        if column not in {
            "bug_id",
            "prediction_timestamp_utc",
        }
    ]

    if set(candidate_score_columns) != candidate_set:
        raise ValueError(
            "ML score columns do not match the candidate roster."
        )

    # Confirm every bug has all 79 candidates.
    expected_pairs = {
        (bug_id, developer)
        for bug_id in ground_truth["bug_id"]
        for developer in candidates
    }

    actual_pairs = set(
        zip(
            features["bug_id"],
            features["candidate_developer_id"],
            strict=True
        )
    )

    if expected_pairs != actual_pairs:
        raise ValueError(
            "Candidate feature coverage is incomplete."
        )

    feature_time_map = (
        features.groupby("bug_id")["prediction_timestamp_utc"]
        .nunique()
    )

    if not feature_time_map.eq(1).all():
        raise ValueError(
            "Inconsistent prediction timestamps in feature data."
        )

    print("\nTEST DATA")
    print("Test bugs:", len(ground_truth))
    print("Candidate pairs:", len(features))
    print("Score matrix:", scores.shape)

    # -----------------------------------------------------
    # RECENCY CALCULATION
    # -----------------------------------------------------

    recency_rows = []

    print("\nCalculating Member 3 Recency scores...")

    for target in ground_truth.to_dict(orient="records"):

        bug_id = target["bug_id"]
        prediction_time = target["prediction_timestamp_utc"]

        result = get_all_developer_recency(
            assignment_events=events,
            reference_date=prediction_time,
            candidate_developers=candidates,
            exclude_bug_id=bug_id,
            half_life_days=DEFAULT_HALF_LIFE_DAYS,
        )

        for developer in candidates:

            evidence = result.get(developer)

            if evidence is None:

                last_activity = ""
                days_since = ""
                recency_score = ""

            else:

                last_activity = evidence["last_activity"]
                days_since = evidence["days_since_activity"]
                recency_score = evidence["recency_score"]

                if parse_timestamp(last_activity) >= prediction_time:
                    raise AssertionError(
                        "Future assignment detected."
                    )

            recency_rows.append({
                "bug_id": bug_id,
                "prediction_timestamp_utc": prediction_time.isoformat(),
                "candidate_developer_id": developer,
                "last_historical_activity": last_activity,
                "days_since_activity": days_since,
                "member3_recency_score": recency_score,
            })

    recency = pd.DataFrame(recency_rows)

    # -----------------------------------------------------
    # COMPARE MEMBER 3 WITH MEMBER 2
    # -----------------------------------------------------

    comparison = recency.merge(
        features[
            [
                "bug_id",
                "candidate_developer_id",
                "days_since_last_activity",
                "days_since_last_component",
                "component_recency_score",
                "recent_activity_count_30d",
                "recent_activity_count_90d",
                "recent_activity_count_365d",
            ]
        ],
        on=["bug_id", "candidate_developer_id"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )

    if not comparison["_merge"].eq("both").all():
        raise AssertionError(
            "Recency output does not match Member 2 feature coverage."
        )

    comparison.drop(columns=["_merge"], inplace=True)

    comparison["m3_days_numeric"] = pd.to_numeric(
        comparison["days_since_activity"],
        errors="coerce"
    )

    comparison["m2_days_numeric"] = pd.to_numeric(
        comparison["days_since_last_activity"],
        errors="coerce"
    )

    comparison["absolute_days_difference"] = (
        comparison["m3_days_numeric"]
        - comparison["m2_days_numeric"]
    ).abs()

    missingness_match = (
        comparison["m3_days_numeric"].isna()
        == comparison["m2_days_numeric"].isna()
    ).all()

    valid_differences = comparison[
        comparison["absolute_days_difference"].notna()
    ]["absolute_days_difference"]

    max_difference = (
        float(valid_differences.max())
        if len(valid_differences)
        else None
    )

    mean_difference = (
        float(valid_differences.mean())
        if len(valid_differences)
        else None
    )

    tolerance = 1e-6

    comparison_match = (
        missingness_match
        and max_difference is not None
        and max_difference <= tolerance
    )

    # -----------------------------------------------------
    # RECENCY-ONLY RANKING
    # -----------------------------------------------------

    comparison["has_recency_history"] = (
        comparison["member3_recency_score"].ne("")
    )

    comparison["member3_recency_score_numeric"] = pd.to_numeric(
        comparison["member3_recency_score"],
        errors="coerce"
    )

    recency_ranked = comparison.sort_values(
        [
            "bug_id",
            "has_recency_history",
            "member3_recency_score_numeric",
            "candidate_developer_id",
        ],
        ascending=[True, False, False, True],
        na_position="last",
        kind="stable",
    ).copy()

    recency_ranked["recency_only_rank"] = (
        recency_ranked.groupby("bug_id").cumcount() + 1
    )

    recency_rank_map = {}

    for bug_id, group in recency_ranked.groupby("bug_id"):
        recency_rank_map[bug_id] = {
            developer: int(rank)
            for developer, rank in zip(
                group["candidate_developer_id"],
                group["recency_only_rank"],
                strict=True
            )
        }

    # -----------------------------------------------------
    # MEMBER 2 ML-ONLY RANKING
    # -----------------------------------------------------

    scores["bug_id"] = scores["bug_id"].astype(str)
    scores = scores.set_index("bug_id")

    for developer in candidates:
        scores[developer] = pd.to_numeric(
            scores[developer],
            errors="raise"
        )

    if not scores[candidates].map(
        lambda value: pd.notna(value) and abs(value) != float("inf")
    ).all().all():
        raise ValueError("Invalid ML score values detected.")

    ml_rank_map = {}

    for bug_id in ground_truth["bug_id"]:

        score_row = scores.loc[bug_id]

        ordered = sorted(
            candidates,
            key=lambda developer: (
                -float(score_row[developer]),
                developer,
            )
        )

        ml_rank_map[bug_id] = {
            developer: rank
            for rank, developer in enumerate(ordered, start=1)
        }

    # -----------------------------------------------------
    # EVALUATE AGAINST GROUND TRUTH
    # -----------------------------------------------------

    actual_map = {
        row["bug_id"]: row["actual_developer_id"].strip()
        for row in ground_truth.to_dict(orient="records")
    }

    recency_actual_ranks = {}
    ml_actual_ranks = {}

    for bug_id, actual_developer in actual_map.items():

        recency_actual_ranks[bug_id] = (
            recency_rank_map[bug_id].get(actual_developer)
        )

        ml_actual_ranks[bug_id] = (
            ml_rank_map[bug_id].get(actual_developer)
        )

    recency_metrics = ranking_metrics(
        "Member 3 Recency-only",
        recency_actual_ranks,
        actual_map,
    )

    ml_metrics = ranking_metrics(
        "Member 2 ML-only",
        ml_actual_ranks,
        actual_map,
    )

    metrics = pd.DataFrame([
        recency_metrics,
        ml_metrics,
    ])

    # -----------------------------------------------------
    # SAVE RESULTS
    # -----------------------------------------------------

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    details_path = (
        OUTPUT_DIR
        / "member3_recency_candidate_evaluation.csv"
    )

    metrics_path = (
        OUTPUT_DIR
        / "member3_recency_ranking_metrics.csv"
    )

    report_path = (
        OUTPUT_DIR
        / "member3_recency_validation.json"
    )

    comparison.to_csv(
        details_path,
        index=False,
        encoding="utf-8"
    )

    metrics.to_csv(
        metrics_path,
        index=False,
        encoding="utf-8"
    )

    seen_targets = sum(
        actual in candidate_set
        for actual in actual_map.values()
    )

    report = {
        "component": "Member 3 Recency",
        "half_life_days": DEFAULT_HALF_LIFE_DAYS,

        "input_counts": {
            "verified_training_assignments": len(train),
            "test_bugs": len(ground_truth),
            "candidate_developers": len(candidates),
            "candidate_pairs": len(comparison),
        },

        "temporal_policy": (
            "Verified known-entry training assignments strictly "
            "before each test bug prediction timestamp."
        ),

        "target_bug_excluded": True,
        "future_data_leakage_check": "passed",

        "candidate_pair_coverage": (
            len(comparison) == 331 * 79
        ),

        "member2_recency_comparison": {
            "feature_compared": "days_since_last_activity",
            "missingness_matches": bool(missingness_match),
            "maximum_absolute_difference_days": max_difference,
            "mean_absolute_difference_days": mean_difference,
            "tolerance_days": tolerance,
            "values_match_within_tolerance": bool(comparison_match),
        },

        "ground_truth_coverage": {
            "targets_in_roster": seen_targets,
            "targets_outside_roster": len(actual_map) - seen_targets,
        },

        "ranking_metrics": [
            recency_metrics,
            ml_metrics,
        ],

        "double_counting_warning": (
            "Member 2 already uses days_since_last_activity. "
            "Member 3 Recency score is a deterministic transformation "
            "of the same global elapsed-time signal. Do not simply add "
            "the Recency score to the raw ML margin."
        ),

        "component_recency_note": (
            "component_recency_score is a separate component-specific "
            "feature and must not be confused with global Recency."
        ),

        "member2_validation_report": member2_validation,

        "outputs": [
            str(details_path.relative_to(PROJECT_ROOT)),
            str(metrics_path.relative_to(PROJECT_ROOT)),
            str(report_path.relative_to(PROJECT_ROOT)),
        ],
    }

    with report_path.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(report, file, indent=4)

    # -----------------------------------------------------
    # DISPLAY RESULTS
    # -----------------------------------------------------

    print("\n========== RECENCY FEATURE COMPARISON ==========")

    print("Member 3 vs Member 2 days-since-activity comparison")
    print("Missingness matches:", missingness_match)
    print("Maximum difference:", max_difference)
    print("Mean difference:", mean_difference)
    print("Match within tolerance:", comparison_match)

    print("\n========== RANKING COMPARISON ==========")

    print(metrics.to_string(index=False))

    print("\n========== OUTPUT FILES ==========")
    print(details_path)
    print(metrics_path)
    print(report_path)

    print("\nRECENCY EVALUATION COMPLETED.")


if __name__ == "__main__":
    run_evaluation()
