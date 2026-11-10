"""Mindful.org (wellness) source adapter: fetch + normalize only. All
RSS/XML-specific logic is contained entirely in this file — the shared
ingestion architecture (NormalizedContentItem, persistence.py) has no
awareness of XML at all.

Mindful.org publishes an official RSS 2.0 feed (mindful.org/feed) — a
publication-owned syndication feed, not an undocumented endpoint, unlike
Devpost. Verified against the live, raw XML before writing this adapter:
standard WordPress RSS 2.0 with extra namespaces (content/wfw/dc/atom/sy/
slash), but every field used here — title, link, guid, pubDate, category,
description — is a core, unnamespaced RSS element, so no namespace
handling is needed for xml.etree.ElementTree lookups.
"""

import html
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Optional
from xml.etree import ElementTree

import httpx

from app.ingestion.types import NormalizedContentItem

MINDFUL_ORG_SOURCE = "mindful-org"
MINDFUL_ORG_FEED_URL = "https://www.mindful.org/feed/"
MINDFUL_ORG_ORGANIZATION = "Mindful.org"

_PREMIUM_CATEGORY = "premium"

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
# Mindful.org's WordPress feed appends this to every <description> —
# confirmed present on 100% of live items checked. Not real excerpt
# content, so it's stripped rather than stored.
_WORDPRESS_BOILERPLATE_MARKER = "The post "


class MalformedArticleError(ValueError):
    """Raised when a raw RSS <item> is missing a field required to build
    a valid NormalizedContentItem. Callers should skip the item and
    continue, not abort the run."""


def fetch_mindful_org_items(*, timeout: float = 15.0) -> List[ElementTree.Element]:
    """Fetch and parse the Mindful.org RSS feed, returning its <item>
    elements.

    Raises on network failure (httpx exceptions) or an invalid/unexpected
    response (ValueError, wrapping either an XML parse error or a missing
    <channel>) — either is a hard failure of the whole run, since nothing
    has been written to the DB yet at this point.
    """
    response = httpx.get(MINDFUL_ORG_FEED_URL, timeout=timeout, follow_redirects=True)
    response.raise_for_status()

    try:
        root = ElementTree.fromstring(response.content)
    except ElementTree.ParseError as exc:
        raise ValueError(f"Unexpected Mindful.org RSS response: invalid XML ({exc})") from exc

    channel = root.find("channel")
    if channel is None:
        raise ValueError("Unexpected Mindful.org RSS shape: missing <channel>")

    return channel.findall("item")


def _element_text(item: ElementTree.Element, tag: str) -> Optional[str]:
    element = item.find(tag)
    if element is None or element.text is None:
        return None
    text = element.text.strip()
    return text or None


def is_premium_item(item: ElementTree.Element) -> bool:
    """True if any <category> on this item is "premium", matched
    case-insensitively. The live feed uses lowercase "premium" — verified
    directly against the raw XML, not assumed from a paraphrased summary
    — but matching case-insensitively is a small, cheap safeguard against
    that casing ever varying."""
    for category in item.findall("category"):
        if category.text and category.text.strip().lower() == _PREMIUM_CATEGORY:
            return True
    return False


def _clean_description(raw_html: Optional[str]) -> Optional[str]:
    """Strips HTML markup and the WordPress "The post ... appeared first
    on Mindful." boilerplate from a raw RSS description, returning clean
    excerpt text. Handles None/missing/empty input safely.

    Tags are replaced with a space, not an empty string — unlike
    Devpost's equivalent helper (which cleans an inline currency span
    with no intended word break), this description is genuine
    multi-paragraph content, so a space avoids mashing words together
    across paragraph boundaries.
    """
    if not raw_html:
        return None

    stripped = _TAG_RE.sub(" ", raw_html)
    unescaped = html.unescape(stripped)
    collapsed = _WHITESPACE_RE.sub(" ", unescaped).strip()

    if _WORDPRESS_BOILERPLATE_MARKER in collapsed:
        collapsed = collapsed.split(_WORDPRESS_BOILERPLATE_MARKER, 1)[0].strip()

    return collapsed or None


def normalize_mindful_org_item(item: ElementTree.Element) -> NormalizedContentItem:
    """Map one raw RSS <item> element to the generic NormalizedContentItem
    shape. category/content_type/organization are fixed — every item
    comes from this one publication, unlike Arbeitnow/Devpost where those
    fields vary per listing.

    location fields are always null and is_remote is always False: an
    article has no physical location and is not a "remote opportunity" —
    it has no location concept at all, which is a different thing from
    being globally accessible.
    """
    title = _element_text(item, "title")
    link = _element_text(item, "link")
    guid = _element_text(item, "guid")

    if not title:
        raise MalformedArticleError("Mindful.org item is missing a 'title'")
    if not link:
        raise MalformedArticleError(f"Mindful.org item '{title}' is missing a 'link'")

    external_id = guid if guid else link

    published_at: Optional[datetime] = None
    pub_date_text = _element_text(item, "pubDate")
    if pub_date_text:
        try:
            published_at = parsedate_to_datetime(pub_date_text)
        except (TypeError, ValueError):
            published_at = None

    return NormalizedContentItem(
        external_id=external_id,
        source=MINDFUL_ORG_SOURCE,
        category="wellness",
        content_type="article",
        title=title,
        description=_clean_description(_element_text(item, "description")),
        url=link,
        organization=MINDFUL_ORG_ORGANIZATION,
        location_city=None,
        location_region=None,
        location_country=None,
        is_remote=False,
        event_date=None,
        deadline=None,
        published_at=published_at,
    )
