import unittest
from datetime import datetime, timezone
from collections import Counter

from scripts.reconstruct_jdt_partial_workload import (
    add_state,
    assigned_verified_owner,
    event_is_before_cutoff,
)


UTC = timezone.utc


class PartialWorkloadTests(unittest.TestCase):
    def test_cutoff_is_strict(self):
        cutoff = datetime(2024, 1, 2, tzinfo=UTC)
        self.assertTrue(event_is_before_cutoff(datetime(2024, 1, 1, tzinfo=UTC), cutoff))
        self.assertFalse(event_is_before_cutoff(cutoff, cutoff))
        self.assertFalse(event_is_before_cutoff(datetime(2024, 1, 3, tzinfo=UTC), cutoff))

    def test_terminal_and_reopened_state_counts(self):
        developers = {"dev-a"}
        state = {"product": "JDT", "status": "NEW", "assignee": "dev-a"}
        by_developer = Counter()
        active = Counter()
        verified = Counter()
        add_state(state, 1, developers, by_developer, active, verified)
        self.assertEqual(by_developer["dev-a"], 1)

        add_state(state, -1, developers, by_developer, active, verified)
        state["status"] = "CLOSED"
        add_state(state, 1, developers, by_developer, active, verified)
        self.assertEqual(by_developer["dev-a"], 0)
        self.assertEqual(active["total"], 0)

        add_state(state, -1, developers, by_developer, active, verified)
        state["status"] = "REOPENED"
        add_state(state, 1, developers, by_developer, active, verified)
        self.assertEqual(by_developer["dev-a"], 1)

    def test_unverified_assignee_is_reported_as_unknown_not_attributed(self):
        state = {"product": "JDT", "status": "ASSIGNED", "assignee": "opaque-account"}
        by_developer = Counter()
        active = Counter()
        verified = Counter()
        add_state(state, 1, {"dev-a"}, by_developer, active, verified)
        self.assertEqual(by_developer["dev-a"], 0)
        self.assertEqual(active["total"], 1)
        self.assertEqual(active["unknown_or_unassigned"], 1)
        self.assertEqual(verified["total"], 0)

    def test_terminal_bug_owner_can_be_identified_for_reopen_attribution(self):
        state = {"product": "JDT", "status": "RESOLVED", "assignee": "dev-a"}
        self.assertEqual(assigned_verified_owner(state, {"dev-a"}), "dev-a")

    def test_non_jdt_bug_is_not_a_jdt_active_contribution(self):
        state = {"product": "Platform", "status": "ASSIGNED", "assignee": "dev-a"}
        by_developer = Counter()
        active = Counter()
        verified = Counter()
        add_state(state, 1, {"dev-a"}, by_developer, active, verified)
        self.assertEqual(by_developer["dev-a"], 0)
        self.assertEqual(active["total"], 0)


if __name__ == "__main__":
    unittest.main()
