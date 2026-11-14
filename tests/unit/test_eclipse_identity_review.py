import unittest

from scripts.prepare_eclipse_identity_review import (
    prepare_cohort_rows,
    prepare_review_rows,
)


class EclipseIdentityReviewTests(unittest.TestCase):
    def test_exact_email_and_name_candidate_rows_combine_without_merge(self):
        candidates = [
            {
                "repository": "repo-a",
                "git_author_key": "a1",
                "author_names": "Alice",
                "author_emails": "alice@example.test",
                "candidate_repository": "repo-b",
                "candidate_git_author_key": "b1",
                "candidate_names": "Alice",
                "candidate_emails": "alice@example.test",
                "match_reason": "exact_email_candidate",
                "bot_status": "not_flagged_unverified",
            },
            {
                "repository": "repo-a",
                "git_author_key": "a1",
                "author_names": "Alice",
                "author_emails": "alice@example.test",
                "candidate_repository": "repo-b",
                "candidate_git_author_key": "b1",
                "candidate_names": "Alice",
                "candidate_emails": "alice@example.test",
                "match_reason": "exact_normalized_name_candidate",
                "bot_status": "not_flagged_unverified",
            },
        ]
        rows = prepare_review_rows(candidates)
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["candidate_evidence"],
            "exact_email_candidate;exact_normalized_name_candidate",
        )
        self.assertEqual(rows[0]["review_decision"], "")
        self.assertEqual(
            rows[0]["manual_review_status"], "unresolved_manual_review_required"
        )

    def test_email_name_conflict_and_multiple_links_are_flagged(self):
        candidates = [
            {
                "repository": "repo-a",
                "git_author_key": "a1",
                "author_names": "Alice Smith",
                "author_emails": "shared@example.test",
                "candidate_repository": "repo-b",
                "candidate_git_author_key": "b1",
                "candidate_names": "Bob Jones",
                "candidate_emails": "shared@example.test",
                "match_reason": "exact_email_candidate",
                "bot_status": "not_flagged_unverified",
            },
            {
                "repository": "repo-a",
                "git_author_key": "a1",
                "author_names": "Alice Smith",
                "author_emails": "shared@example.test",
                "candidate_repository": "repo-c",
                "candidate_git_author_key": "c1",
                "candidate_names": "Alice Smith",
                "candidate_emails": "alice@example.test",
                "match_reason": "exact_normalized_name_candidate",
                "bot_status": "possible_bot_in_pair_needs_review",
            },
        ]
        rows = prepare_review_rows(candidates)
        self.assertEqual(rows[0]["email_name_conflict"], "true")
        self.assertEqual(rows[0]["multiple_candidate_links"], "true")
        self.assertEqual(rows[1]["multiple_candidate_links"], "true")
        self.assertEqual(rows[1]["possible_bot_in_pair"], "true")

    def test_cohorts_mark_missing_email_and_keep_identities_unverified(self):
        roster = [
            {
                "repository": "eclipse.jdt.core",
                "git_author_key": "key",
                "author_names": "Example Developer",
                "author_emails": "",
                "commit_count": "2",
                "changed_file_count": "4",
                "bot_status": "not_flagged_unverified",
                "identity_status": "ambiguous_missing_email",
            }
        ]
        cohorts = prepare_cohort_rows(roster, [], [])
        self.assertIn("missing_email_ambiguous", cohorts[0]["review_cohorts"])
        self.assertIn(
            "git_identity_not_automatically_verified", cohorts[0]["review_cohorts"]
        )
        self.assertEqual(cohorts[0]["candidate_link_count"], "0")


if __name__ == "__main__":
    unittest.main()
