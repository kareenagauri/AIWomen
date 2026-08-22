"""Devpost source adapter: fetch + normalize only. No persistence logic
here — that lives in app.ingestion.persistence, shared unchanged by every
source.

Devpost has no official/documented public API. The endpoint used here
(devpost.com/api/hackathons) backs Devpost's own site, requires no
authentication, and returns clean structured JSON — verified live before
writing this adapter. It is not a versioned public contract, unlike
Arbeitnow's documented API: if its shape ever changes, fetch_devpost_
hackathons raises before anything is written to content_items, so
existing data is never at risk — the same safe-failure guarantee the
Arbeitnow adapter relies on.
"""

import html
import re
from typing import Any, Dict, List, Optional

import httpx

from app.ingestion.types import NormalizedContentItem

DEVPOST_SOURCE = "devpost"
DEVPOST_API_URL = "https://devpost.com/api/hackathons"
MAX_PAGES = 10

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


class MalformedHackathonError(ValueError):
    """Raised when a raw Devpost hackathon record is missing a field
    required to build a valid NormalizedContentItem. Callers should skip
    the item and continue, not abort the run."""


def fetch_devpost_hackathons(
    *, timeout: float = 15.0, max_pages: int = MAX_PAGES
) -> List[Dict[str, Any]]:
    """Fetch all currently-open hackathons, paginating up to max_pages as
    a fixed safety cap (avoids an unbounded loop if the source's paging
    metadata is ever wrong).

    Raises on network failure (httpx exceptions) or an unexpected
    response shape (ValueError) — either is a hard failure of the whole
    run, since nothing has been written to the DB yet at this point.
    """
    all_hackathons: List[Dict[str, Any]] = []

    for page in range(1, max_pages + 1):
        response = httpx.get(
            DEVPOST_API_URL,
            params={"status[]": "open", "order_by": "recently-added", "page": page},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()

        hackathons = payload.get("hackathons")
        if not isinstance(hackathons, list):
            raise ValueError("Unexpected Devpost response shape: missing 'hackathons' list")

        if not hackathons:
            break

        all_hackathons.extend(hackathons)

        meta = payload.get("meta") or {}
        total_count = meta.get("total_count")
        if isinstance(total_count, int) and len(all_hackathons) >= total_count:
            break

    return all_hackathons


def is_online_hackathon(raw: Dict[str, Any]) -> bool:
    """True only when Devpost's own displayed_location marks this as an
    online/global event (icon == "globe") — the same structured signal
    Devpost's own UI uses, not a string match on "Online" text that could
    vary."""
    location = raw.get("displayed_location")
    if not isinstance(location, dict):
        return False
    return location.get("icon") == "globe"


def _strip_html(text: Optional[str]) -> Optional[str]:
    """Removes HTML markup from a Devpost text field and returns clean
    plain text. Handles None/missing/empty input safely (returns None).

    Tags are replaced with an empty string, not a space — unlike
    Arbeitnow's equivalent helper (which handles multi-paragraph job
    descriptions, where a space avoids mashing words across block
    boundaries), Devpost's markup here wraps an inline value with no
    intended word break, e.g. prize_amount arrives as
    "$<span data-currency-value>2,600</span>" and must become "$2,600",
    not "$ 2,600". A local, minimal duplicate of the same pattern already
    used in arbeitnow.py — kept separate rather than shared, so this fix
    stays isolated to this file.
    """
    if not text:
        return None
    stripped = _TAG_RE.sub("", text)
    unescaped = html.unescape(stripped)
    collapsed = _WHITESPACE_RE.sub(" ", unescaped).strip()
    return collapsed or None


def _build_description(raw: Dict[str, Any]) -> Optional[str]:
    """Devpost's list endpoint has no long-form description field — build
    a short readable one from what it does provide. submission_period_dates
    is a human-written range ("Aug 22 - Sep 27, 2026"), preserved here as
    text rather than parsed into event_date/deadline (see normalize_
    devpost_hackathon). Both source fields can contain HTML markup (e.g.
    prize_amount's currency span) and are cleaned via _strip_html before
    being included."""
    parts = []

    dates = _strip_html(raw.get("submission_period_dates"))
    if dates:
        parts.append(f"Submission period: {dates}")

    prize = _strip_html(raw.get("prize_amount"))
    if prize:
        parts.append(f"Prize: {prize}")

    return " · ".join(parts) if parts else None


def normalize_devpost_hackathon(raw: Dict[str, Any]) -> NormalizedContentItem:
    """Map one raw Devpost hackathon dict to the generic
    NormalizedContentItem shape. category/content_type are fixed
    ('career'/'event') — this is the events source for this stage.

    event_date and deadline are deliberately left null: Devpost only
    provides submission_period_dates as a human-written range string, not
    a machine date, and guessing a parse risks reporting a wrong deadline
    — worse than reporting none. The raw range is preserved as readable
    text in the description instead.
    """
    hackathon_id = raw.get("id")
    title = raw.get("title")

    if hackathon_id is None:
        raise MalformedHackathonError("Devpost hackathon is missing an 'id' (external_id)")
    if not title or not str(title).strip():
        raise MalformedHackathonError(f"Devpost hackathon '{hackathon_id}' is missing a 'title'")

    return NormalizedContentItem(
        external_id=str(hackathon_id),
        source=DEVPOST_SOURCE,
        category="career",
        content_type="event",
        title=str(title).strip(),
        description=_build_description(raw),
        url=raw.get("url") or None,
        organization=raw.get("organization_name") or None,
        location_city=None,
        location_region=None,
        location_country=None,
        is_remote=is_online_hackathon(raw),
        event_date=None,
        deadline=None,
        published_at=None,
    )
