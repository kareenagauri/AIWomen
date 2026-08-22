"""Generic normalized shape that any content source's adapter must
produce. Persistence code (persistence.py) only ever knows about this
shape — it has no awareness of Arbeitnow or any other specific source."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class NormalizedContentItem:
    external_id: str
    source: str
    category: str
    content_type: str
    title: str
    description: Optional[str]
    url: Optional[str]
    organization: Optional[str]
    location_city: Optional[str]
    location_region: Optional[str]
    location_country: Optional[str]
    is_remote: bool
    event_date: Optional[datetime]
    deadline: Optional[datetime]
    published_at: Optional[datetime]

    def to_row(self) -> Dict[str, Any]:
        """Dict shape ready for a content_items insert/update — datetimes
        serialized to ISO 8601 strings, as PostgREST expects."""
        return {
            "external_id": self.external_id,
            "source": self.source,
            "category": self.category,
            "content_type": self.content_type,
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "organization": self.organization,
            "location_city": self.location_city,
            "location_region": self.location_region,
            "location_country": self.location_country,
            "is_remote": self.is_remote,
            "event_date": self.event_date.isoformat() if self.event_date else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }
