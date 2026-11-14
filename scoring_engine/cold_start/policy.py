"""Evidence-aware cold-start decisions for bug-assignment candidates."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ColdStartStatus(str, Enum):
    ELIGIBLE_WITH_HISTORY = "eligible_with_assignment_history"
    CONFIRMED_NEW = "confirmed_new_developer"
    UNMATCHED_GIT_CONTRIBUTOR = "git_contributor_without_verified_bugzilla_identity"
    INSUFFICIENT_ASSIGNMENT_HISTORY = "insufficient_assignment_history"
    MANUAL_REVIEW = "manual_review_insufficient_or_conflicting_evidence"


@dataclass(frozen=True)
class ColdStartAssessment:
    status: ColdStartStatus
    eligible_for_history_model: bool
    fallback: str
    reasons: tuple[str, ...]


def assess_cold_start(
    *,
    assignment_count: int | None,
    git_commit_count: int = 0,
    identity_verified: bool = False,
    identity_conflict: bool = False,
    explicitly_confirmed_new: bool = False,
    assignment_history_complete: bool = True,
    minimum_assignments: int = 1,
) -> ColdStartAssessment:
    """Assess candidate evidence without treating Git commits as assignments."""
    for name, value in (
        ("git_commit_count", git_commit_count),
        ("minimum_assignments", minimum_assignments),
    ):
        if value < 0:
            raise ValueError(f"{name} must be non-negative")
    if assignment_count is not None and assignment_count < 0:
        raise ValueError("assignment_count must be non-negative or None")
    if minimum_assignments == 0:
        raise ValueError("minimum_assignments must be at least one")

    reasons: list[str] = []
    if identity_conflict:
        reasons.append("identity evidence is conflicting")
    if not assignment_history_complete:
        reasons.append("assignment history is incomplete")

    if identity_conflict or not assignment_history_complete:
        return ColdStartAssessment(
            ColdStartStatus.MANUAL_REVIEW,
            False,
            "manual_review_no_automatic_assignment_recommendation",
            tuple(reasons),
        )

    if explicitly_confirmed_new:
        if assignment_count not in (None, 0):
            return ColdStartAssessment(
                ColdStartStatus.MANUAL_REVIEW,
                False,
                "review_conflicting_new_developer_and_assignment_evidence",
                ("new-developer evidence conflicts with observed assignments",),
            )
        if not identity_verified:
            return ColdStartAssessment(
                ColdStartStatus.MANUAL_REVIEW,
                False,
                "verify_identity_before_classifying_new_developer",
                ("new-developer evidence requires a verified identity",),
            )
        return ColdStartAssessment(
            ColdStartStatus.CONFIRMED_NEW,
            False,
            "use_non_assignment_evidence_only_with_human_review",
            ("explicitly confirmed new developer",),
        )

    if not identity_verified:
        if git_commit_count:
            return ColdStartAssessment(
                ColdStartStatus.UNMATCHED_GIT_CONTRIBUTOR,
                False,
                "repository_scoped_git_evidence_only_manual_review_required",
                (
                    "Git contribution history exists",
                    "no verified Bugzilla identity link",
                ),
            )
        return ColdStartAssessment(
            ColdStartStatus.MANUAL_REVIEW,
            False,
            "manual_review_identity_and_assignment_evidence",
            ("no verified identity or Git contribution evidence",),
        )

    if assignment_count is None:
        return ColdStartAssessment(
            ColdStartStatus.MANUAL_REVIEW,
            False,
            "manual_review_assignment_history_unavailable",
            ("assignment count is unavailable",),
        )

    if assignment_count >= minimum_assignments:
        return ColdStartAssessment(
            ColdStartStatus.ELIGIBLE_WITH_HISTORY,
            True,
            "rank_using_available_assignment_history_features",
            (f"{assignment_count} observed assignments",),
        )

    if assignment_count == 0:
        reasons.append("no observed assignment events")
    else:
        reasons.append(f"only {assignment_count} observed assignments")
    return ColdStartAssessment(
        ColdStartStatus.INSUFFICIENT_ASSIGNMENT_HISTORY,
        False,
        "manual_review_or_non_assignment_fallback",
        tuple(reasons),
    )
