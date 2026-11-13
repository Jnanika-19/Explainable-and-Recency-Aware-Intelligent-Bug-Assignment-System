
import sys
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add the main project directory to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scoring_engine.workload.workload_calculator import (
    calculate_developer_workload,
    normalize_developer_workload
)


class TestWorkloadCalculator(unittest.TestCase):

    def setUp(self):

        self.reference_date = datetime(
            2024, 2, 1, 0, 0, 0,
            tzinfo=timezone.utc
        )

    def create_event(
        self,
        bug_id,
        developer,
        event_time,
        event_type="assignment_added"
    ):

        return {
            "bug_id": bug_id,
            "developer_label": developer,
            "label_event_time": event_time,
            "label_event_type": event_type
        }

    # ------------------------------------------
    # TEST 1: RECENT ASSIGNMENT COUNTING
    # ------------------------------------------

    def test_recent_assignments_are_counted(self):

        events = [
            self.create_event(
                "BUG-1", "A", "2024-01-31T00:00:00Z"
            ),
            self.create_event(
                "BUG-2", "A", "2024-01-20T00:00:00Z"
            ),
            self.create_event(
                "BUG-3", "A", "2023-12-20T00:00:00Z"
            )
        ]

        result = calculate_developer_workload(
            events,
            self.reference_date,
            candidate_developers=["A"],
            window_days=30
        )

        self.assertEqual(
            result["A"]["assignment_count"],
            2
        )

    # ------------------------------------------
    # TEST 2: WINDOW BOUNDARIES AND EXCLUSIONS
    # ------------------------------------------

    def test_window_boundaries_and_exclusions(self):

        events = [
            self.create_event(
                "BUG-1", "A", "2024-01-02T00:00:00Z"
            ),
            self.create_event(
                "BUG-2", "A", "2024-01-01T23:59:59Z"
            ),
            self.create_event(
                "BUG-3", "A", "2024-01-31T00:00:00Z"
            ),
            self.create_event(
                "BUG-4", "A", "2024-02-01T00:00:00Z"
            ),
            self.create_event(
                "TARGET", "A", "2024-01-30T00:00:00Z"
            ),
            self.create_event(
                "BUG-5", "A", "2024-02-02T00:00:00Z"
            ),
            self.create_event(
                "BUG-6",
                "A",
                "2024-01-29T00:00:00Z",
                "assignment_removed"
            )
        ]

        result = calculate_developer_workload(
            events,
            self.reference_date,
            candidate_developers=["A"],
            window_days=30,
            exclude_bug_id="TARGET"
        )

        self.assertEqual(
            result["A"]["assignment_count"],
            2
        )

    # ------------------------------------------
    # TEST 3: CANDIDATE LIST
    # ------------------------------------------

    def test_candidate_list_is_respected(self):

        events = [
            self.create_event(
                "BUG-1", "A", "2024-01-25T00:00:00Z"
            ),
            self.create_event(
                "BUG-2", "B", "2024-01-25T00:00:00Z"
            )
        ]

        result = calculate_developer_workload(
            events,
            self.reference_date,
            candidate_developers=["A", "C"],
            window_days=30
        )

        self.assertEqual(
            set(result.keys()),
            {"A", "C"}
        )

        self.assertEqual(
            result["A"]["assignment_count"],
            1
        )

        self.assertEqual(
            result["C"]["assignment_count"],
            0
        )

    # ------------------------------------------
    # TEST 4: DIFFERENT WORKLOAD WINDOWS
    # ------------------------------------------

    def test_different_workload_windows(self):

        events = [
            self.create_event(
                "BUG-1", "A", "2024-01-20T00:00:00Z"
            ),
            self.create_event(
                "BUG-2", "A", "2023-12-20T00:00:00Z"
            ),
            self.create_event(
                "BUG-3", "A", "2023-11-20T00:00:00Z"
            )
        ]

        result_30 = calculate_developer_workload(
            events,
            self.reference_date,
            candidate_developers=["A"],
            window_days=30
        )

        result_90 = calculate_developer_workload(
            events,
            self.reference_date,
            candidate_developers=["A"],
            window_days=90
        )

        count_30 = result_30["A"]["assignment_count"]
        count_90 = result_90["A"]["assignment_count"]

        self.assertEqual(count_30, 1)
        self.assertEqual(count_90, 3)

        self.assertGreater(count_90, count_30)

    # ------------------------------------------
    # TEST 5: WORKLOAD NORMALIZATION
    # ------------------------------------------

    def test_workload_normalization(self):

        events = []

        assignment_counts = {
            "A": 0,
            "B": 5,
            "C": 10,
            "D": 20
        }

        for developer, count in assignment_counts.items():

            for index in range(count):

                event_time = (
                    self.reference_date
                    - timedelta(days=index + 1)
                )

                events.append(
                    self.create_event(
                        f"{developer}-{index}",
                        developer,
                        event_time.isoformat()
                    )
                )

        raw_results = calculate_developer_workload(
            events,
            self.reference_date,
            candidate_developers=list(
                assignment_counts.keys()
            ),
            window_days=30
        )

        normalized = normalize_developer_workload(
            raw_results
        )

        # Developer A has no recorded workload evidence.
        self.assertIsNone(
            normalized["A"]["workload_suitability_score"]
        )

        self.assertFalse(
            normalized["A"]["workload_evidence_available"]
        )

        # Developers with recorded activity receive scores.
        self.assertIsNotNone(
            normalized["B"]["workload_suitability_score"]
        )

        self.assertIsNotNone(
            normalized["C"]["workload_suitability_score"]
        )

        self.assertIsNotNone(
            normalized["D"]["workload_suitability_score"]
        )

        # More assignment activity means lower suitability.
        self.assertGreater(
            normalized["B"]["workload_suitability_score"],
            normalized["C"]["workload_suitability_score"]
        )

        self.assertGreater(
            normalized["C"]["workload_suitability_score"],
            normalized["D"]["workload_suitability_score"]
        )

    # ------------------------------------------
    # TEST 6: NO WORKLOAD EVIDENCE
    # ------------------------------------------

    def test_no_workload_evidence(self):

        raw_results = calculate_developer_workload(
            [],
            self.reference_date,
            candidate_developers=["A", "B"],
            window_days=30
        )

        normalized = normalize_developer_workload(
            raw_results
        )

        for developer in ["A", "B"]:

            self.assertIsNone(
                normalized[developer]["workload_pressure"]
            )

            self.assertIsNone(
                normalized[developer]["workload_suitability_score"]
            )

            self.assertFalse(
                normalized[developer]["workload_evidence_available"]
            )

            self.assertEqual(
                normalized[developer]["workload_evidence_status"],
                "no_recent_assignment_evidence"
            )

    # ------------------------------------------
    # TEST 7: INVALID WORKLOAD WINDOWS
    # ------------------------------------------

    def test_invalid_window_is_rejected(self):

        for invalid_window in [0, -1]:

            with self.subTest(window_days=invalid_window):

                with self.assertRaises(ValueError):

                    calculate_developer_workload(
                        [],
                        self.reference_date,
                        window_days=invalid_window
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
