
import sys
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add the main project folder to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scoring_engine.recency.recency_calculator import (
    DEFAULT_HALF_LIFE_DAYS,
    parse_timestamp,
    calculate_recency_score,
    get_developer_recency,
    get_all_developer_recency
)


class TestRecencyCalculator(unittest.TestCase):

    def setUp(self):
        self.reference_date = datetime(
            2024, 2, 1, 0, 0, 0,
            tzinfo=timezone.utc
        )

    def test_default_half_life(self):
        last_activity = (
            self.reference_date - timedelta(
                days=DEFAULT_HALF_LIFE_DAYS
            )
        )

        score = calculate_recency_score(
            last_activity,
            self.reference_date
        )

        self.assertAlmostEqual(score, 0.5, places=12)

    def test_custom_half_life(self):
        last_activity = (
            self.reference_date - timedelta(days=365)
        )

        score = calculate_recency_score(
            last_activity,
            self.reference_date,
            half_life_days=365
        )

        self.assertAlmostEqual(score, 0.5, places=12)

    def test_exact_precision(self):
        last_activity = (
            self.reference_date - timedelta(hours=1)
        )

        result = get_developer_recency(
            [last_activity],
            self.reference_date
        )

        expected_days = 1 / 24

        self.assertAlmostEqual(
            result["days_since_activity"],
            expected_days,
            places=12
        )

        self.assertNotEqual(
            result["days_since_activity"],
            round(expected_days, 4)
        )

        self.assertNotEqual(
            result["recency_score"],
            round(result["recency_score"], 4)
        )

    def test_timezone_conversion(self):
        timestamp_utc = parse_timestamp(
            "2024-01-01T00:00:00Z"
        )

        timestamp_offset = parse_timestamp(
            "2024-01-01T05:30:00+05:30"
        )

        self.assertEqual(timestamp_utc, timestamp_offset)

    def test_future_activity_is_rejected(self):
        future_activity = (
            self.reference_date + timedelta(days=1)
        )

        with self.assertRaises(ValueError):
            calculate_recency_score(
                future_activity,
                self.reference_date
            )

    def test_future_activity_is_filtered(self):
        activities = [
            "2024-01-01T00:00:00Z",
            "2024-01-31T00:00:00Z",
            "2024-02-02T00:00:00Z"
        ]

        result = get_developer_recency(
            activities,
            self.reference_date
        )

        actual_last_activity = parse_timestamp(
            result["last_activity"]
        )

        expected_last_activity = parse_timestamp(
            "2024-01-31T00:00:00Z"
        )

        self.assertEqual(
            actual_last_activity,
            expected_last_activity
        )

    def test_all_developer_recency_filters_events(self):
        assignment_events = [
            {
                "bug_id": "BUG-1",
                "developer_label": "A",
                "label_event_time": "2024-01-01T00:00:00Z",
                "label_event_type": "assignment_added"
            },
            {
                "bug_id": "TARGET",
                "developer_label": "A",
                "label_event_time": "2024-01-31T00:00:00Z",
                "label_event_type": "assignment_added"
            },
            {
                "bug_id": "BUG-2",
                "developer_label": "B",
                "label_event_time": "2024-01-31T00:00:00Z",
                "label_event_type": "assignment_added"
            },
            {
                "bug_id": "BUG-3",
                "developer_label": "B",
                "label_event_time": "2024-02-02T00:00:00Z",
                "label_event_type": "assignment_added"
            },
            {
                "bug_id": "BUG-4",
                "developer_label": "C",
                "label_event_time": "2024-01-31T00:00:00Z",
                "label_event_type": "comment_added"
            }
        ]

        result = get_all_developer_recency(
            assignment_events=assignment_events,
            reference_date=self.reference_date,
            candidate_developers=["A", "B", "C", "D"],
            exclude_bug_id="TARGET"
        )

        self.assertEqual(
            set(result.keys()),
            {"A", "B", "C", "D"}
        )

        self.assertEqual(
            parse_timestamp(result["A"]["last_activity"]),
            parse_timestamp("2024-01-01T00:00:00Z")
        )

        self.assertEqual(
            parse_timestamp(result["B"]["last_activity"]),
            parse_timestamp("2024-01-31T00:00:00Z")
        )

        self.assertIsNone(result["C"])
        self.assertIsNone(result["D"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
