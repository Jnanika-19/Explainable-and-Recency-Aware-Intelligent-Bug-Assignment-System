
import sys
import unittest

from datetime import date, datetime, timezone
from pathlib import Path

# Add project root to Python import path.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scoring_engine.recency.recency_calculator import (
    parse_timestamp,
    calculate_recency_score,
    get_developer_recency,
    get_all_developer_recency,
)


class TestRecencyEdgeCases(unittest.TestCase):

    def setUp(self):
        self.reference_date = datetime(
            2024, 2, 1,
            tzinfo=timezone.utc
        )

    # -------------------------------------------------
    # TIMESTAMP VALIDATION
    # -------------------------------------------------

    def test_empty_timestamp(self):
        with self.assertRaises(ValueError):
            parse_timestamp("")

    def test_whitespace_timestamp(self):
        with self.assertRaises(ValueError):
            parse_timestamp("   ")

    def test_invalid_timestamp_format(self):
        with self.assertRaises(ValueError):
            parse_timestamp("not-a-valid-date")

    def test_none_timestamp(self):
        with self.assertRaises(TypeError):
            parse_timestamp(None)

    def test_unsupported_timestamp_type(self):
        with self.assertRaises(TypeError):
            parse_timestamp(12345)

    def test_naive_datetime_assumed_utc(self):
        timestamp = parse_timestamp(
            datetime(2024, 1, 1, 12, 0, 0)
        )

        self.assertEqual(timestamp.tzinfo, timezone.utc)

    def test_date_object_conversion(self):
        timestamp = parse_timestamp(date(2024, 1, 1))

        self.assertEqual(
            timestamp,
            datetime(2024, 1, 1, tzinfo=timezone.utc)
        )

    # -------------------------------------------------
    # HALF-LIFE VALIDATION
    # -------------------------------------------------

    def test_invalid_half_life_values(self):

        invalid_values = [
            0,
            -1,
            True,
            False,
            float("inf"),
            float("-inf"),
            float("nan"),
            None,
            "invalid",
        ]

        last_activity = datetime(
            2024, 1, 1,
            tzinfo=timezone.utc
        )

        for value in invalid_values:

            with self.subTest(half_life=value):

                with self.assertRaises(ValueError):
                    calculate_recency_score(
                        last_activity,
                        self.reference_date,
                        half_life_days=value
                    )

    # -------------------------------------------------
    # SCORE BOUNDARY VALIDATION
    # -------------------------------------------------

    def test_activity_at_reference_time_has_score_one(self):

        score = calculate_recency_score(
            self.reference_date,
            self.reference_date,
        )

        self.assertEqual(score, 1.0)

    # -------------------------------------------------
    # EMPTY HISTORICAL ACTIVITY
    # -------------------------------------------------

    def test_empty_activity_list_returns_none(self):

        result = get_developer_recency(
            [],
            self.reference_date
        )

        self.assertIsNone(result)

    def test_none_activity_list_returns_none(self):

        result = get_developer_recency(
            None,
            self.reference_date
        )

        self.assertIsNone(result)

    def test_candidate_without_history_returns_none(self):

        result = get_all_developer_recency(
            assignment_events=[],
            reference_date=self.reference_date,
            candidate_developers=["developer_A"]
        )

        self.assertIsNone(result["developer_A"])

    # -------------------------------------------------
    # EVENT TIMESTAMP VALIDATION
    # -------------------------------------------------

    def test_invalid_assignment_timestamp_is_rejected(self):

        events = [
            {
                "bug_id": "BUG-1",
                "developer_label": "developer_A",
                "label_event_time": "invalid-date",
                "label_event_type": "assignment_added",
            }
        ]

        with self.assertRaises(ValueError):
            get_all_developer_recency(
                assignment_events=events,
                reference_date=self.reference_date,
                candidate_developers=["developer_A"]
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
