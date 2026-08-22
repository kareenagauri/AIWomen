"""Unit tests for the Arbeitnow source adapter: normalization, remote
filtering, malformed-item handling, and a mocked fetch. No live network
access — httpx.get is patched."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.ingestion.sources.arbeitnow import (
    MalformedJobError,
    fetch_arbeitnow_jobs,
    is_remote_job,
    normalize_arbeitnow_job,
)

# A realistic raw item, based on a live-verified Arbeitnow response.
_VALID_JOB = {
    "slug": "senior-it-administrator-hamburg-hamburg-431395",
    "company_name": "appinio",
    "title": "Senior IT Administrator (m/f/d)",
    "description": "<p>We are looking for a <b>Senior IT Administrator</b>.</p>",
    "remote": True,
    "url": "https://www.arbeitnow.com/jobs/companies/appinio/senior-it-administrator-hamburg-hamburg-431395",
    "tags": ["Engineering"],
    "job_types": [],
    "location": "Hamburg, Hamburg",
    "created_at": 1787388908,
}


# ---- normalize_arbeitnow_job ----------------------------------------------


def test_normalize_maps_core_fields():
    item = normalize_arbeitnow_job(_VALID_JOB)
    assert item.external_id == "senior-it-administrator-hamburg-hamburg-431395"
    assert item.source == "arbeitnow"
    assert item.category == "career"
    assert item.content_type == "job"
    assert item.title == "Senior IT Administrator (m/f/d)"
    assert item.organization == "appinio"
    assert item.url == _VALID_JOB["url"]
    assert item.is_remote is True


def test_normalize_strips_html_from_description():
    item = normalize_arbeitnow_job(_VALID_JOB)
    assert item.description == "We are looking for a Senior IT Administrator ."


def test_normalize_converts_unix_timestamp_to_utc_datetime():
    item = normalize_arbeitnow_job(_VALID_JOB)
    assert item.published_at == datetime.fromtimestamp(1787388908, tz=timezone.utc)


def test_normalize_does_not_split_location():
    # "Hamburg, Hamburg" is not reliably "City, Country" — kept as a raw
    # string in location_city, region/country left null rather than guessed.
    item = normalize_arbeitnow_job(_VALID_JOB)
    assert item.location_city == "Hamburg, Hamburg"
    assert item.location_region is None
    assert item.location_country is None


def test_normalize_handles_missing_optional_fields():
    raw = {"slug": "job-x", "title": "Some Job"}
    item = normalize_arbeitnow_job(raw)
    assert item.description is None
    assert item.url is None
    assert item.organization is None
    assert item.location_city is None
    assert item.is_remote is False
    assert item.published_at is None


def test_normalize_raises_when_slug_missing():
    raw = {**_VALID_JOB, "slug": None}
    with pytest.raises(MalformedJobError):
        normalize_arbeitnow_job(raw)


def test_normalize_raises_when_slug_blank():
    raw = {**_VALID_JOB, "slug": "   "}
    with pytest.raises(MalformedJobError):
        normalize_arbeitnow_job(raw)


def test_normalize_raises_when_title_missing():
    raw = {**_VALID_JOB, "title": None}
    with pytest.raises(MalformedJobError):
        normalize_arbeitnow_job(raw)


# ---- is_remote_job ---------------------------------------------------------


def test_is_remote_job_true():
    assert is_remote_job({"remote": True})


def test_is_remote_job_false():
    assert not is_remote_job({"remote": False})


def test_is_remote_job_missing_key():
    assert not is_remote_job({})


def test_is_remote_job_rejects_truthy_non_boolean():
    # Strict on purpose — a stray string/int should not count as remote.
    assert not is_remote_job({"remote": "true"})


# ---- fetch_arbeitnow_jobs (mocked, no network) -----------------------------


@patch("app.ingestion.sources.arbeitnow.httpx.get")
def test_fetch_returns_data_list(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [_VALID_JOB]}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    jobs = fetch_arbeitnow_jobs()

    assert jobs == [_VALID_JOB]
    mock_get.assert_called_once()


@patch("app.ingestion.sources.arbeitnow.httpx.get")
def test_fetch_raises_on_unexpected_shape(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"unexpected": "shape"}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    with pytest.raises(ValueError):
        fetch_arbeitnow_jobs()
