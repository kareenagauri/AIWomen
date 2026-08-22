"""Unit tests for the pure scoring/eligibility logic in app.recommendations.
No database, no HTTP, no fixtures beyond plain Python objects — this is
what "independently testable" means in practice for Stage 6A."""

from datetime import datetime, timedelta, timezone

from app.recommendations import (
    ContentCandidate,
    is_location_eligible,
    matches_location_preference,
    matches_search,
    rank_content,
    score_content,
)

NOW = datetime(2026, 8, 16, tzinfo=timezone.utc)


def _candidate(
    id_: str,
    goal_ids=frozenset(),
    interest_ids=frozenset(),
    published_at=None,
    created_at=NOW - timedelta(days=100),
) -> ContentCandidate:
    return ContentCandidate(
        id=id_,
        goal_ids=frozenset(goal_ids),
        interest_ids=frozenset(interest_ids),
        published_at=published_at,
        created_at=created_at,
    )


# ---- score_content -----------------------------------------------------


def test_no_matches_scores_zero_when_not_recent():
    candidate = _candidate("c1", created_at=NOW - timedelta(days=100))
    result = score_content(candidate, frozenset(), frozenset(), now=NOW)
    assert result.score == 0
    assert result.matched_goal_ids == ()
    assert result.matched_interest_ids == ()
    assert result.is_recent is False


def test_goal_match_worth_two_points_each():
    candidate = _candidate("c1", goal_ids={"g1", "g2"}, created_at=NOW - timedelta(days=100))
    result = score_content(candidate, frozenset({"g1", "g2", "g3"}), frozenset(), now=NOW)
    assert result.score == 4  # 2 matched goals x 2
    assert result.matched_goal_ids == ("g1", "g2")


def test_interest_match_worth_one_point_each():
    candidate = _candidate("c1", interest_ids={"i1"}, created_at=NOW - timedelta(days=100))
    result = score_content(candidate, frozenset(), frozenset({"i1"}), now=NOW)
    assert result.score == 1
    assert result.matched_interest_ids == ("i1",)


def test_recency_bonus_applied_within_30_days():
    candidate = _candidate("c1", published_at=NOW - timedelta(days=29))
    result = score_content(candidate, frozenset(), frozenset(), now=NOW)
    assert result.score == 1
    assert result.is_recent is True


def test_recency_bonus_not_applied_beyond_30_days():
    candidate = _candidate("c1", published_at=NOW - timedelta(days=31))
    result = score_content(candidate, frozenset(), frozenset(), now=NOW)
    assert result.score == 0
    assert result.is_recent is False


def test_recency_falls_back_to_created_at_when_published_at_missing():
    candidate = _candidate("c1", published_at=None, created_at=NOW - timedelta(days=5))
    result = score_content(candidate, frozenset(), frozenset(), now=NOW)
    assert result.is_recent is True
    assert result.reference_date == NOW - timedelta(days=5)


def test_combined_score_matches_the_documented_formula():
    # 2 goals matched (+4) + 1 interest matched (+1) + recent (+1) = 6
    candidate = _candidate(
        "c1",
        goal_ids={"g1", "g2"},
        interest_ids={"i1"},
        published_at=NOW - timedelta(days=1),
    )
    result = score_content(
        candidate, frozenset({"g1", "g2"}), frozenset({"i1"}), now=NOW
    )
    assert result.score == 6


# ---- rank_content --------------------------------------------------------


def test_rank_content_sorts_by_score_descending():
    high = _candidate("high", goal_ids={"g1"}, created_at=NOW - timedelta(days=100))
    low = _candidate("low", created_at=NOW - timedelta(days=100))
    ranked = rank_content([low, high], user_goal_ids={"g1"}, user_interest_ids=set(), now=NOW)
    assert [r.content_id for r in ranked] == ["high", "low"]


def test_rank_content_tie_breaks_by_reference_date_descending():
    older = _candidate("older", created_at=NOW - timedelta(days=50))
    newer = _candidate("newer", created_at=NOW - timedelta(days=10))
    # Neither matches anything and neither is within the recency window,
    # so both score 0 — order must come entirely from the tie-break.
    ranked = rank_content([older, newer], user_goal_ids=set(), user_interest_ids=set(), now=NOW)
    assert [r.content_id for r in ranked] == ["newer", "older"]


def test_rank_content_is_deterministic_across_repeated_calls():
    candidates = [
        _candidate("a", goal_ids={"g1"}, created_at=NOW - timedelta(days=20)),
        _candidate("b", interest_ids={"i1"}, created_at=NOW - timedelta(days=5)),
        _candidate("c", created_at=NOW - timedelta(days=200)),
    ]
    first = rank_content(candidates, {"g1"}, {"i1"}, now=NOW)
    second = rank_content(candidates, {"g1"}, {"i1"}, now=NOW)
    assert [r.content_id for r in first] == [r.content_id for r in second]


# ---- is_location_eligible -------------------------------------------------


def test_remote_content_is_always_eligible():
    assert is_location_eligible(
        content_city="Mumbai",
        content_country="India",
        is_remote=True,
        profile_city="Bengaluru",
        profile_country="India",
    )


def test_content_with_no_city_is_always_eligible():
    assert is_location_eligible(
        content_city=None,
        content_country=None,
        is_remote=False,
        profile_city="Bengaluru",
        profile_country="India",
    )


def test_matching_city_and_country_is_eligible():
    assert is_location_eligible(
        content_city="Bengaluru",
        content_country="India",
        is_remote=False,
        profile_city="Bengaluru",
        profile_country="India",
    )


def test_mismatched_city_is_not_eligible():
    assert not is_location_eligible(
        content_city="Mumbai",
        content_country="India",
        is_remote=False,
        profile_city="Bengaluru",
        profile_country="India",
    )


# ---- matches_search --------------------------------------------------


def test_search_exact_title_match():
    assert matches_search(
        "Women in Leadership Scholarship", "Women in Leadership Scholarship", None
    )


def test_search_partial_title_match():
    assert matches_search("leadership", "Women in Leadership Scholarship", None)


def test_search_description_match():
    assert matches_search(
        "mentorship", "Some Title", "A mentorship program for career returners."
    )


def test_search_case_insensitive():
    assert matches_search("LEADERSHIP", "Women in Leadership Scholarship", None)


def test_search_strips_leading_and_trailing_whitespace():
    assert matches_search("  leadership  ", "Women in Leadership Scholarship", None)


def test_search_empty_string_matches_everything():
    assert matches_search("", "Anything at all", None)


def test_search_whitespace_only_matches_everything():
    assert matches_search("   ", "Anything at all", None)


def test_search_non_matching_term_does_not_match():
    assert not matches_search(
        "astrophysics", "Women in Leadership Scholarship", "A mentorship program."
    )


# ---- matches_location_preference -----------------------------------------


def test_no_preference_accepts_remote():
    assert matches_location_preference(None, is_remote=True)


def test_no_preference_accepts_local():
    assert matches_location_preference(None, is_remote=False)


def test_remote_preference_accepts_remote():
    assert matches_location_preference("remote", is_remote=True)


def test_remote_preference_rejects_local():
    assert not matches_location_preference("remote", is_remote=False)


def test_local_preference_accepts_local():
    assert matches_location_preference("local", is_remote=False)


def test_local_preference_rejects_remote():
    assert not matches_location_preference("local", is_remote=True)
