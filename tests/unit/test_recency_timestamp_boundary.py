import sys
import unittest

from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scoring_engine.recency.recency_calculator import (
    get_developer_recency,
    get_all_developer_recency,
)


class TestRecencyTimestampBoundary(unittest.TestCase):

    def setUp(self):
        self.reference_date = datetime(
            2024, 2, 1, 0, 0, 0,
            tzinfo=timezone.utc
        )

    def test_equal_timestamp_is_excluded_from_developer_history(self):

        activities = [
            "2024-01-31T00:00:00Z",
            "2024-02-01T00:00:00Z",
        ]

        result = get_developer_recency(
            activities,
            self.reference_date
        )

        self.assertEqual(
            result["last_activity"],
            "2024-01-31T00:00:00+00:00"
        )

    def test_only_equal_timestamp_returns_no_history(self):

        result = get_developer_recency(
            ["2024-02-01T00:00:00Z"],
            self.reference_date
        )

        self.assertIsNone(result)

    def test_equal_timestamp_is_excluded_for_all_developers(self):

        events = [
            {
                "bug_id": "BUG-1",
                "developer_label": "developer_A",
                "label_event_time": "2024-02-01T00:00:00Z",
                "label_event_type": "assignment_added",
            }
        ]

        result = get_all_developer_recency(
            assignment_events=events,
            reference_date=self.reference_date,
            candidate_developers=["developer_A"],
        )

        self.assertIsNone(result["developer_A"])

    def test_earlier_event_is_selected_over_equal_timestamp(self):

        events = [
            {
                "bug_id": "BUG-1",
                "developer_label": "developer_A",
                "label_event_time": "2024-01-31T00:00:00Z",
                "label_event_type": "assignment_added",
            },
            {
                "bug_id": "BUG-2",
                "developer_label": "developer_A",
                "label_event_time": "2024-02-01T00:00:00Z",
                "label_event_type": "assignment_added",
            },
        ]

        result = get_all_developer_recency(
            assignment_events=events,
            reference_date=self.reference_date,
            candidate_developers=["developer_A"],
        )

        self.assertEqual(
            result["developer_A"]["last_activity"],
            "2024-01-31T00:00:00+00:00"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)