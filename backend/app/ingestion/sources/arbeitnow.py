"""Arbeitnow source adapter: fetch + normalize only. No persistence
logic here — that lives in app.ingestion.persistence, which is shared by
every source. No API key required by Arbeitnow's public job board API.
"""

import html
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.ingestion.types import NormalizedContentItem

ARBEITNOW_SOURCE = "arbeitnow"
ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api"

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


class MalformedJobError(ValueError):
    """Raised when a raw Arbeitnow job record is missing a field required
    to build a valid NormalizedContentItem. Callers should skip the item
    and continue, not abort the run."""


def fetch_arbeitnow_jobs(*, timeout: float = 15.0) -> List[Dict[str, Any]]:
    """Fetch the current page of Arbeitnow job listings.

    Raises on network failure (httpx exceptions) or an unexpected response
    shape (ValueError) — either is treated as a hard failure of the whole
    run by the caller, since nothing has been written to the DB yet at
    this point.
    """
    response = httpx.get(ARBEITNOW_API_URL, timeout=timeout)
    response.raise_for_status()
    payload = response.json()

    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("Unexpected Arbeitnow response shape: missing 'data' list")

    return data


def is_remote_job(raw: Dict[str, Any]) -> bool:
    """Strict on purpose: only an explicit boolean True counts as remote,
    not any other truthy value."""
    return raw.get("remote") is True


def _strip_html(raw_html: Optional[str]) -> Optional[str]:
    if not raw_html:
        return None
    text = _TAG_RE.sub(" ", raw_html)
    text = html.unescape(text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text or None


def normalize_arbeitnow_job(raw: Dict[str, Any]) -> NormalizedContentItem:
    """Map one raw Arbeitnow job dict to the generic NormalizedContentItem
    shape. category/content_type are fixed ('career'/'job') — Arbeitnow is
    a single-purpose job board, not a multi-category source. Location is
    deliberately NOT split into city/region/country: Arbeitnow's `location`
    field isn't reliably "City, Country" (a real example seen was "Hamburg,
    Hamburg"), so guessing a split would fabricate structure the source
    doesn't provide. This is fine because ingestion is remote-only for
    now — the raw location string is kept in location_city for display,
    but it never participates in location-eligibility matching since
    is_remote is always true for anything this adapter produces.
    """
    slug = raw.get("slug")
    title = raw.get("title")

    if not slug or not str(slug).strip():
        raise MalformedJobError("Arbeitnow job is missing a usable 'slug' (external_id)")
    if not title or not str(title).strip():
        raise MalformedJobError(f"Arbeitnow job '{slug}' is missing a 'title'")

    published_at: Optional[datetime] = None
    created_at = raw.get("created_at")
    if isinstance(created_at, (int, float)):
        published_at = datetime.fromtimestamp(created_at, tz=timezone.utc)

    return NormalizedContentItem(
        external_id=str(slug).strip(),
        source=ARBEITNOW_SOURCE,
        category="career",
        content_type="job",
        title=str(title).strip(),
        description=_strip_html(raw.get("description")),
        url=raw.get("url") or None,
        organization=raw.get("company_name") or None,
        location_city=raw.get("location") or None,
        location_region=None,
        location_country=None,
        is_remote=bool(raw.get("remote", False)),
        event_date=None,
        deadline=None,
        published_at=published_at,
    )
