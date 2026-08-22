"""Unit tests for the Devpost source adapter: normalization, online-only
filtering, pagination, malformed-item handling, and mocked fetches. No
live network access — httpx.get is patched throughout."""

from unittest.mock import MagicMock, patch

import pytest

from app.ingestion.sources.devpost import (
    MalformedHackathonError,
    fetch_devpost_hackathons,
    is_online_hackathon,
    normalize_devpost_hackathon,
)

# A realistic raw item, based on a live-verified Devpost response.
_ONLINE_HACKATHON = {
    "id": 31101,
    "title": "3rd-Web-Hack",
    "displayed_location": {"icon": "globe", "location": "Online"},
    "open_state": "open",
    "url": "https://3rd-web-hack.devpost.com/",
    "submission_period_dates": "Aug 22 - Sep 27, 2026",
    "organization_name": "TechZap Club",
    "prize_amount": "$750",
    "themes": [{"name": "Blockchain"}, {"name": "Web"}],
}

_IN_PERSON_HACKATHON = {
    "id": 99999,
    "title": "Campus Hack Day",
    "displayed_location": {"icon": "map-marker-alt", "location": "San Francisco, CA"},
    "open_state": "open",
    "url": "https://campus-hack.devpost.com/",
    "submission_period_dates": "Sep 1 - Sep 2, 2026",
    "organization_name": "Some University",
}


def _response(payload):
    mock_response = MagicMock()
    mock_response.json.return_value = payload
    mock_response.raise_for_status.return_value = None
    return mock_response


# ---- normalize_devpost_hackathon ------------------------------------------


def test_normalize_maps_core_fields():
    item = normalize_devpost_hackathon(_ONLINE_HACKATHON)
    assert item.external_id == "31101"
    assert item.source == "devpost"
    assert item.title == "3rd-Web-Hack"
    assert item.url == _ONLINE_HACKATHON["url"]
    assert item.organization == "TechZap Club"


def test_normalize_fixes_category_and_content_type():
    item = normalize_devpost_hackathon(_ONLINE_HACKATHON)
    assert item.category == "career"
    assert item.content_type == "event"


def test_normalize_builds_description_from_dates_and_prize():
    item = normalize_devpost_hackathon(_ONLINE_HACKATHON)
    assert item.description == "Submission period: Aug 22 - Sep 27, 2026 · Prize: $750"


def test_normalize_description_omits_missing_prize():
    raw = {**_ONLINE_HACKATHON}
    del raw["prize_amount"]
    item = normalize_devpost_hackathon(raw)
    assert item.description == "Submission period: Aug 22 - Sep 27, 2026"


def test_normalize_description_handles_none_prize_amount():
    raw = {**_ONLINE_HACKATHON, "prize_amount": None}
    item = normalize_devpost_hackathon(raw)
    assert item.description == "Submission period: Aug 22 - Sep 27, 2026"


def test_normalize_description_is_none_when_no_source_fields_present():
    raw = {"id": 1, "title": "Bare Hackathon"}
    item = normalize_devpost_hackathon(raw)
    assert item.description is None


def test_normalize_strips_html_from_prize_amount():
    # The exact scenario reported: Devpost's currency markup was leaking
    # into the stored description.
    raw = {
        **_ONLINE_HACKATHON,
        "submission_period_dates": "Jul 15 - Oct 31, 2026",
        "prize_amount": "$<span data-currency-value>2,600</span>",
    }
    item = normalize_devpost_hackathon(raw)
    assert item.description == "Submission period: Jul 15 - Oct 31, 2026 · Prize: $2,600"


def test_normalize_plain_text_prize_amount_is_unchanged():
    # _ONLINE_HACKATHON's prize_amount ("$750") has no markup at all —
    # cleaning must not alter it.
    item = normalize_devpost_hackathon(_ONLINE_HACKATHON)
    assert "Prize: $750" in item.description


def test_normalize_strips_html_from_submission_period_dates():
    # Defensive: dates are built from the same source and could carry
    # markup too, even though today's samples don't.
    raw = {**_ONLINE_HACKATHON, "submission_period_dates": "<b>Aug 22</b> - Sep 27, 2026"}
    item = normalize_devpost_hackathon(raw)
    assert item.description.startswith("Submission period: Aug 22 - Sep 27, 2026")


def test_normalize_description_contains_no_html_tags():
    raw = {
        **_ONLINE_HACKATHON,
        "submission_period_dates": "<em>Jul 15</em> - Oct 31, 2026",
        "prize_amount": "$<span data-currency-value>2,600</span>",
    }
    item = normalize_devpost_hackathon(raw)
    assert "<" not in item.description
    assert ">" not in item.description


def test_normalize_leaves_location_fields_null():
    item = normalize_devpost_hackathon(_ONLINE_HACKATHON)
    assert item.location_city is None
    assert item.location_region is None
    assert item.location_country is None


def test_normalize_leaves_event_date_and_deadline_null():
    # submission_period_dates is a human-written range, never parsed.
    item = normalize_devpost_hackathon(_ONLINE_HACKATHON)
    assert item.event_date is None
    assert item.deadline is None


def test_normalize_sets_is_remote_true_for_globe_icon():
    item = normalize_devpost_hackathon(_ONLINE_HACKATHON)
    assert item.is_remote is True


def test_normalize_sets_is_remote_false_for_in_person_icon():
    item = normalize_devpost_hackathon(_IN_PERSON_HACKATHON)
    assert item.is_remote is False


def test_normalize_raises_when_id_missing():
    raw = {**_ONLINE_HACKATHON}
    del raw["id"]
    with pytest.raises(MalformedHackathonError):
        normalize_devpost_hackathon(raw)


def test_normalize_raises_when_title_missing():
    raw = {**_ONLINE_HACKATHON}
    del raw["title"]
    with pytest.raises(MalformedHackathonError):
        normalize_devpost_hackathon(raw)


def test_normalize_raises_when_title_blank():
    raw = {**_ONLINE_HACKATHON, "title": "   "}
    with pytest.raises(MalformedHackathonError):
        normalize_devpost_hackathon(raw)


def test_normalize_is_deterministic_for_safe_reruns():
    # Same raw input must always produce an equal NormalizedContentItem —
    # this is what makes rerunning ingestion safe at the mapping level,
    # complementing persistence.py's already-tested upsert idempotency.
    first = normalize_devpost_hackathon(_ONLINE_HACKATHON)
    second = normalize_devpost_hackathon(_ONLINE_HACKATHON)
    assert first == second


# ---- is_online_hackathon ---------------------------------------------------


def test_is_online_hackathon_true_for_globe_icon():
    assert is_online_hackathon(_ONLINE_HACKATHON)


def test_is_online_hackathon_false_for_map_marker_icon():
    assert not is_online_hackathon(_IN_PERSON_HACKATHON)


def test_is_online_hackathon_false_when_location_missing():
    assert not is_online_hackathon({"id": 1, "title": "No location field"})


def test_is_online_hackathon_false_when_location_not_a_dict():
    assert not is_online_hackathon({"displayed_location": "Online"})


# ---- fetch_devpost_hackathons (mocked, no network) -------------------------


@patch("app.ingestion.sources.devpost.httpx.get")
def test_fetch_single_page_when_total_count_fits(mock_get):
    mock_get.return_value = _response(
        {"hackathons": [_ONLINE_HACKATHON], "meta": {"total_count": 1, "per_page": 9}}
    )

    hackathons = fetch_devpost_hackathons()

    assert hackathons == [_ONLINE_HACKATHON]
    mock_get.assert_called_once()


@patch("app.ingestion.sources.devpost.httpx.get")
def test_fetch_paginates_across_multiple_pages(mock_get):
    page1 = _response(
        {"hackathons": [{"id": 1, "title": "A"}], "meta": {"total_count": 2, "per_page": 1}}
    )
    page2 = _response(
        {"hackathons": [{"id": 2, "title": "B"}], "meta": {"total_count": 2, "per_page": 1}}
    )
    mock_get.side_effect = [page1, page2]

    hackathons = fetch_devpost_hackathons()

    assert [h["id"] for h in hackathons] == [1, 2]
    assert mock_get.call_count == 2


@patch("app.ingestion.sources.devpost.httpx.get")
def test_fetch_stops_when_total_count_reached_without_over_fetching(mock_get):
    page1 = _response(
        {"hackathons": [{"id": 1, "title": "A"}], "meta": {"total_count": 1, "per_page": 1}}
    )
    mock_get.return_value = page1

    fetch_devpost_hackathons()

    # Must not request a second page once total_count is already satisfied.
    assert mock_get.call_count == 1


@patch("app.ingestion.sources.devpost.httpx.get")
def test_fetch_stops_on_empty_page_even_if_total_count_implies_more(mock_get):
    empty_page = _response({"hackathons": [], "meta": {"total_count": 50, "per_page": 9}})
    mock_get.return_value = empty_page

    hackathons = fetch_devpost_hackathons()

    assert hackathons == []
    assert mock_get.call_count == 1


@patch("app.ingestion.sources.devpost.httpx.get")
def test_fetch_respects_max_pages_safety_cap(mock_get):
    # Always returns one item and never signals completion via total_count
    # or an empty page — without the cap this would loop forever.
    mock_get.return_value = _response(
        {"hackathons": [{"id": 1, "title": "A"}], "meta": {"total_count": 999999, "per_page": 1}}
    )

    hackathons = fetch_devpost_hackathons(max_pages=3)

    assert mock_get.call_count == 3
    assert len(hackathons) == 3


@patch("app.ingestion.sources.devpost.httpx.get")
def test_fetch_sends_open_status_filter(mock_get):
    mock_get.return_value = _response({"hackathons": [], "meta": {"total_count": 0}})

    fetch_devpost_hackathons()

    _, kwargs = mock_get.call_args
    assert kwargs["params"]["status[]"] == "open"


@patch("app.ingestion.sources.devpost.httpx.get")
def test_fetch_raises_on_unexpected_shape(mock_get):
    mock_get.return_value = _response({"unexpected": "shape"})

    with pytest.raises(ValueError):
        fetch_devpost_hackathons()
