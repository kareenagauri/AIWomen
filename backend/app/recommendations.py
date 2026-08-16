"""Deterministic recommendation scoring — pure, DB-free, independently
testable. Nothing in this module performs I/O; it operates entirely on
plain data passed in by the caller (the recommendations router)."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import FrozenSet, Iterable, List, Optional, Tuple

GOAL_WEIGHT = 2
INTEREST_WEIGHT = 1
RECENCY_BONUS = 1
RECENCY_WINDOW_DAYS = 30


@dataclass(frozen=True)
class ContentCandidate:
    id: str
    goal_ids: FrozenSet[str]
    interest_ids: FrozenSet[str]
    published_at: Optional[datetime]
    created_at: datetime


@dataclass(frozen=True)
class ScoredContent:
    content_id: str
    score: int
    matched_goal_ids: Tuple[str, ...]
    matched_interest_ids: Tuple[str, ...]
    is_recent: bool
    reference_date: datetime


def is_location_eligible(
    content_city: Optional[str],
    content_country: Optional[str],
    is_remote: bool,
    profile_city: Optional[str],
    profile_country: Optional[str],
) -> bool:
    """Whether a content item is eligible to be shown to a profile, based
    on location. Remote content and content with no location set (global)
    are always eligible; everything else must match city and country."""
    if is_remote:
        return True
    if not content_city:
        return True
    return content_city == profile_city and content_country == profile_country


def score_content(
    candidate: ContentCandidate,
    user_goal_ids: FrozenSet[str],
    user_interest_ids: FrozenSet[str],
    *,
    now: datetime,
) -> ScoredContent:
    """Score one candidate against one user's goals/interests.

    score = 2 x (# matching goals) + 1 x (# matching interests)
            + 1 if published within the last 30 days
    """
    matched_goals = tuple(sorted(candidate.goal_ids & user_goal_ids))
    matched_interests = tuple(sorted(candidate.interest_ids & user_interest_ids))

    reference_date = candidate.published_at or candidate.created_at
    is_recent = (now - reference_date) <= timedelta(days=RECENCY_WINDOW_DAYS)

    score = (
        GOAL_WEIGHT * len(matched_goals)
        + INTEREST_WEIGHT * len(matched_interests)
        + (RECENCY_BONUS if is_recent else 0)
    )

    return ScoredContent(
        content_id=candidate.id,
        score=score,
        matched_goal_ids=matched_goals,
        matched_interest_ids=matched_interests,
        is_recent=is_recent,
        reference_date=reference_date,
    )


def rank_content(
    candidates: Iterable[ContentCandidate],
    user_goal_ids: Iterable[str],
    user_interest_ids: Iterable[str],
    *,
    now: Optional[datetime] = None,
) -> List[ScoredContent]:
    """Score and rank a set of candidates. Deterministic ordering: score
    descending, then reference_date (published_at, falling back to
    created_at) descending as the tie-break."""
    now = now or datetime.now(timezone.utc)
    goal_ids = frozenset(user_goal_ids)
    interest_ids = frozenset(user_interest_ids)

    scored = [score_content(c, goal_ids, interest_ids, now=now) for c in candidates]
    scored.sort(key=lambda s: (-s.score, -s.reference_date.timestamp()))
    return scored
