"""Unit tests for the Mindful.org source adapter: normalization, premium
exclusion, description cleaning, and mocked fetches. No live network
access — httpx.get is patched throughout.

Fixture XML mirrors the actual live feed structure, verified directly
against the raw RSS before this adapter was written (guid shape, CDATA
descriptions with an appended WordPress "appeared first on" boilerplate,
lowercase "premium" category, RFC 822 pubDate format)."""

from unittest.mock import MagicMock, patch
from xml.etree import ElementTree

import pytest

from app.ingestion.sources.mindful_org import (
    MalformedArticleError,
    fetch_mindful_org_items,
    is_premium_item,
    normalize_mindful_org_item,
)


def _item(xml: str) -> ElementTree.Element:
    return ElementTree.fromstring(xml)


# A realistic raw item, based on the live-verified Mindful.org feed.
_ARTICLE_XML = """
<item>
    <title>7 Simple Techniques for Releasing Tension</title>
    <link>https://www.mindful.org/7-simple-techniques/</link>
    <pubDate>Fri, 21 Aug 2026 03:53:07 +0000</pubDate>
    <category><![CDATA[Stress &amp; Anxiety]]></category>
    <category><![CDATA[Self-Care]]></category>
    <guid isPermaLink="false">https://www.mindful.org/?p=667998</guid>
    <description><![CDATA[<p>Our hands carry, fold, type, hold, grasp, and steady us all day long. Try these mindful techniques for releasing tension. </p>
<p>The post <a href="https://www.mindful.org/7-simple-techniques/">7 Simple Techniques for Releasing Tension</a> appeared first on <a href="https://www.mindful.org">Mindful</a>.</p>
]]></description>
</item>
"""

_PREMIUM_ARTICLE_XML = """
<item>
    <title>A 12-Minute Body Scan Meditation</title>
    <link>https://www.mindful.org/a-12-minute-body-scan/</link>
    <pubDate>Tue, 18 Aug 2026 18:45:05 +0000</pubDate>
    <category><![CDATA[Meditation]]></category>
    <category><![CDATA[premium]]></category>
    <guid isPermaLink="false">https://www.mindful.org/?p=636953</guid>
    <description><![CDATA[<p>Body scan meditation content.</p>]]></description>
</item>
"""


# ---- normalize_mindful_org_item --------------------------------------------


def test_normalize_maps_core_fields():
    item = normalize_mindful_org_item(_item(_ARTICLE_XML))
    assert item.title == "7 Simple Techniques for Releasing Tension"
    assert item.url == "https://www.mindful.org/7-simple-techniques/"
    assert item.organization == "Mindful.org"


def test_normalize_fixes_source_category_and_content_type():
    item = normalize_mindful_org_item(_item(_ARTICLE_XML))
    assert item.source == "mindful-org"
    assert item.category == "wellness"
    assert item.content_type == "article"


def test_normalize_uses_guid_as_external_id():
    item = normalize_mindful_org_item(_item(_ARTICLE_XML))
    assert item.external_id == "https://www.mindful.org/?p=667998"


def test_normalize_falls_back_to_link_when_guid_missing():
    xml = """
    <item>
        <title>No Guid Article</title>
        <link>https://www.mindful.org/no-guid/</link>
        <pubDate>Fri, 21 Aug 2026 03:53:07 +0000</pubDate>
        <description><![CDATA[<p>Content.</p>]]></description>
    </item>
    """
    item = normalize_mindful_org_item(_item(xml))
    assert item.external_id == "https://www.mindful.org/no-guid/"


def test_normalize_falls_back_to_link_when_guid_blank():
    xml = """
    <item>
        <title>Blank Guid Article</title>
        <link>https://www.mindful.org/blank-guid/</link>
        <guid isPermaLink="false">   </guid>
        <pubDate>Fri, 21 Aug 2026 03:53:07 +0000</pubDate>
        <description><![CDATA[<p>Content.</p>]]></description>
    </item>
    """
    item = normalize_mindful_org_item(_item(xml))
    assert item.external_id == "https://www.mindful.org/blank-guid/"


def test_normalize_strips_html_from_description():
    item = normalize_mindful_org_item(_item(_ARTICLE_XML))
    assert "<" not in item.description
    assert ">" not in item.description


def test_normalize_removes_wordpress_boilerplate_from_description():
    item = normalize_mindful_org_item(_item(_ARTICLE_XML))
    assert "appeared first on" not in item.description
    assert "The post" not in item.description
    assert item.description.startswith(
        "Our hands carry, fold, type, hold, grasp, and steady us all day long."
    )


def test_normalize_plain_text_description_unchanged():
    xml = """
    <item>
        <title>Plain Description Article</title>
        <link>https://www.mindful.org/plain/</link>
        <pubDate>Fri, 21 Aug 2026 03:53:07 +0000</pubDate>
        <description><![CDATA[Just plain text, no markup at all.]]></description>
    </item>
    """
    item = normalize_mindful_org_item(_item(xml))
    assert item.description == "Just plain text, no markup at all."


def test_normalize_description_none_when_missing():
    xml = """
    <item>
        <title>No Description Article</title>
        <link>https://www.mindful.org/no-desc/</link>
        <pubDate>Fri, 21 Aug 2026 03:53:07 +0000</pubDate>
    </item>
    """
    item = normalize_mindful_org_item(_item(xml))
    assert item.description is None


def test_normalize_parses_pubdate_into_published_at():
    item = normalize_mindful_org_item(_item(_ARTICLE_XML))
    assert item.published_at is not None
    assert item.published_at.year == 2026
    assert item.published_at.month == 8
    assert item.published_at.day == 21


def test_normalize_published_at_none_when_pubdate_missing():
    xml = """
    <item>
        <title>No Date Article</title>
        <link>https://www.mindful.org/no-date/</link>
    </item>
    """
    item = normalize_mindful_org_item(_item(xml))
    assert item.published_at is None


def test_normalize_published_at_none_when_pubdate_malformed():
    xml = """
    <item>
        <title>Bad Date Article</title>
        <link>https://www.mindful.org/bad-date/</link>
        <pubDate>not a real date</pubDate>
    </item>
    """
    item = normalize_mindful_org_item(_item(xml))
    assert item.published_at is None


def test_normalize_raises_when_title_missing():
    xml = """
    <item>
        <link>https://www.mindful.org/no-title/</link>
    </item>
    """
    with pytest.raises(MalformedArticleError):
        normalize_mindful_org_item(_item(xml))


def test_normalize_raises_when_link_missing():
    xml = """
    <item>
        <title>No Link Article</title>
    </item>
    """
    with pytest.raises(MalformedArticleError):
        normalize_mindful_org_item(_item(xml))


def test_normalize_location_fields_are_none():
    item = normalize_mindful_org_item(_item(_ARTICLE_XML))
    assert item.location_city is None
    assert item.location_region is None
    assert item.location_country is None


def test_normalize_is_remote_is_false():
    # Explicit per the project's requirement: an article has no physical
    # location and is not a "remote opportunity" — it's not a location
    # concept at all.
    item = normalize_mindful_org_item(_item(_ARTICLE_XML))
    assert item.is_remote is False


def test_normalize_event_date_and_deadline_are_none():
    item = normalize_mindful_org_item(_item(_ARTICLE_XML))
    assert item.event_date is None
    assert item.deadline is None


def test_normalize_is_deterministic_for_safe_reruns():
    first = normalize_mindful_org_item(_item(_ARTICLE_XML))
    second = normalize_mindful_org_item(_item(_ARTICLE_XML))
    assert first == second


# ---- is_premium_item --------------------------------------------------------


def test_is_premium_item_true_for_lowercase_premium():
    assert is_premium_item(_item(_PREMIUM_ARTICLE_XML))


def test_is_premium_item_true_for_uppercase_premium():
    xml = """
    <item>
        <title>Upper Premium</title>
        <category><![CDATA[PREMIUM]]></category>
    </item>
    """
    assert is_premium_item(_item(xml))


def test_is_premium_item_true_for_mixed_case_premium():
    xml = """
    <item>
        <title>Mixed Premium</title>
        <category><![CDATA[Premium]]></category>
    </item>
    """
    assert is_premium_item(_item(xml))


def test_is_premium_item_false_when_no_premium_category():
    assert not is_premium_item(_item(_ARTICLE_XML))


def test_is_premium_item_false_when_no_categories_at_all():
    xml = "<item><title>No Categories</title></item>"
    assert not is_premium_item(_item(xml))


# ---- fetch_mindful_org_items (mocked, no network) --------------------------


def _response(xml_bytes: bytes):
    mock_response = MagicMock()
    mock_response.content = xml_bytes
    mock_response.raise_for_status.return_value = None
    return mock_response


_VALID_FEED_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Mindful</title>
<item>
<title>Item One</title>
<link>https://www.mindful.org/item-one/</link>
<guid isPermaLink="false">https://www.mindful.org/?p=1</guid>
<pubDate>Fri, 21 Aug 2026 03:53:07 +0000</pubDate>
<description><![CDATA[<p>Content one.</p>]]></description>
</item>
<item>
<title>Item Two</title>
<link>https://www.mindful.org/item-two/</link>
<guid isPermaLink="false">https://www.mindful.org/?p=2</guid>
<pubDate>Tue, 18 Aug 2026 18:45:05 +0000</pubDate>
<description><![CDATA[<p>Content two.</p>]]></description>
</item>
</channel>
</rss>
"""


@patch("app.ingestion.sources.mindful_org.httpx.get")
def test_fetch_returns_items_from_valid_feed(mock_get):
    mock_get.return_value = _response(_VALID_FEED_XML)

    items = fetch_mindful_org_items()

    assert len(items) == 2
    assert items[0].find("title").text == "Item One"
    mock_get.assert_called_once()


@patch("app.ingestion.sources.mindful_org.httpx.get")
def test_fetch_raises_on_invalid_xml(mock_get):
    mock_get.return_value = _response(b"this is not xml <<<")

    with pytest.raises(ValueError):
        fetch_mindful_org_items()


@patch("app.ingestion.sources.mindful_org.httpx.get")
def test_fetch_raises_when_channel_missing(mock_get):
    mock_get.return_value = _response(b"<rss version=\"2.0\"></rss>")

    with pytest.raises(ValueError):
        fetch_mindful_org_items()


@patch("app.ingestion.sources.mindful_org.httpx.get")
def test_fetch_propagates_http_errors(mock_get):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("HTTP 503")
    mock_get.return_value = mock_response

    with pytest.raises(Exception):
        fetch_mindful_org_items()
