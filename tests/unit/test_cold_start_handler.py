import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scoring_engine.cold_start.cold_start_handler import (
    classify_developer_history,
    evaluate_limited_history_component_evidence,
    build_cold_start_assessment,
)


class TestColdStartHandler(unittest.TestCase):

    def setUp(self):
        self.reference_date = "2024-02-01T00:00:00Z"

    def create_event(
        self, bug_id, developer, event_time,
        component="UI", event_type="assignment_added"
    ):
        return {
            "bug_id": bug_id,
            "developer_label": developer,
            "label_event_time": event_time,
            "label_event_type": event_type,
            "component": component,
        }

    def test_history_classification(self):
        events = [
            self.create_event("B1", "A", "2024-01-01T00:00:00Z"),
            self.create_event("B2", "A", "2024-01-10T00:00:00Z"),
            self.create_event("B3", "A", "2024-01-20T00:00:00Z"),
            self.create_event("B4", "B", "2024-01-15T00:00:00Z"),
        ]

        result = classify_developer_history(
            events,
            self.reference_date,
            ["A", "B", "C"],
            minimum_history=3
        )

        self.assertEqual(result["A"]["history_status"], "sufficient_history")
        self.assertEqual(result["B"]["history_status"], "limited_history")
        self.assertEqual(result["C"]["history_status"], "no_assignment_history")

        self.assertEqual(result["A"]["history_count"], 3)
        self.assertEqual(result["B"]["history_count"], 1)
        self.assertEqual(result["C"]["history_count"], 0)

    def test_candidate_pool_and_event_exclusions(self):
        events = [
            self.create_event("B1", "A", "2024-01-31T00:00:00Z"),
            self.create_event("TARGET", "A", "2024-01-25T00:00:00Z"),
            self.create_event("B2", "A", "2024-02-01T00:00:00Z"),
            self.create_event("B3", "A", "2024-02-02T00:00:00Z"),
            self.create_event("B4", "A", "2024-01-20T00:00:00Z",
                              event_type="assignment_removed"),
            self.create_event("B5", "OUTSIDE", "2024-01-15T00:00:00Z"),
        ]

        result = classify_developer_history(
            events,
            self.reference_date,
            ["A"],
            minimum_history=2,
            exclude_bug_id="TARGET"
        )

        self.assertEqual(result["A"]["history_count"], 1)
        self.assertEqual(result["A"]["history_status"], "limited_history")
        self.assertEqual(set(result.keys()), {"A"})

    def test_invalid_history_thresholds(self):
        events = []

        for threshold in [0, -1, True, 1.5]:
            with self.subTest(threshold=threshold):
                with self.assertRaises(ValueError):
                    classify_developer_history(
                        events,
                        self.reference_date,
                        ["A"],
                        minimum_history=threshold
                    )

    def test_component_evidence_for_limited_history(self):
        history = {
            "B": {"history_status": "limited_history"},
            "D": {"history_status": "limited_history"},
            "E": {"history_status": "limited_history"},
            "A": {"history_status": "sufficient_history"},
        }

        events = [
            self.create_event("B1", "B", "2024-01-01T00:00:00Z", "UI"),
            self.create_event("B2", "B", "2024-01-02T00:00:00Z", "Core"),
            self.create_event("D1", "D", "2024-01-03T00:00:00Z", "Core"),
            self.create_event("E1", "E", "2024-01-04T00:00:00Z", ""),
            self.create_event("A1", "A", "2024-01-05T00:00:00Z", "UI"),
            self.create_event("B3", "B", "2024-02-01T00:00:00Z", "UI"),
        ]

        result = evaluate_limited_history_component_evidence(
            events,
            self.reference_date,
            history,
            target_component="UI"
        )

        self.assertEqual(result["B"]["component_match_count"], 1)
        self.assertEqual(result["B"]["component_observation_count"], 2)
        self.assertEqual(result["B"]["component_experience_share"], 0.5)
        self.assertEqual(result["B"]["component_evidence_status"], "component_match_found")

        self.assertEqual(result["D"]["component_evidence_status"], "no_component_match")
        self.assertEqual(result["D"]["component_experience_share"], 0.0)

        self.assertEqual(result["E"]["component_evidence_status"], "component_data_unavailable")
        self.assertIsNone(result["E"]["component_experience_share"])

        self.assertNotIn("A", result)

    def test_invalid_target_component(self):
        with self.assertRaises(ValueError):
            evaluate_limited_history_component_evidence(
                [],
                self.reference_date,
                {},
                target_component=" "
            )

    def test_cold_start_assessment_paths(self):
        history = {
            "A": {
                "history_count": 8,
                "history_status": "sufficient_history",
                "historical_components": ["UI"],
            },
            "B": {
                "history_count": 2,
                "history_status": "limited_history",
                "historical_components": ["UI"],
            },
            "C": {
                "history_count": 1,
                "history_status": "limited_history",
                "historical_components": ["Core"],
            },
            "D": {
                "history_count": 0,
                "history_status": "no_assignment_history",
                "historical_components": [],
            },
        }

        component_results = {
            "B": {"component_match_count": 1},
            "C": {"component_match_count": 0},
        }

        result = build_cold_start_assessment(
            history,
            component_results
        )

        self.assertEqual(result["A"]["recommendation_path"], "standard_history_based")
        self.assertEqual(result["B"]["recommendation_path"], "limited_history_component_supported")
        self.assertEqual(result["C"]["recommendation_path"], "additional_evidence_required")
        self.assertEqual(result["D"]["recommendation_path"], "external_evidence_required")

        self.assertFalse(result["A"]["additional_evidence_required"])
        self.assertFalse(result["B"]["additional_evidence_required"])
        self.assertTrue(result["C"]["additional_evidence_required"])
        self.assertTrue(result["D"]["additional_evidence_required"])


if __name__ == "__main__":
    unittest.main()
