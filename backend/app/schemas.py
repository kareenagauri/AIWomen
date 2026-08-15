from typing import Optional

from pydantic import BaseModel


class TagOption(BaseModel):
    """A single curated goal or interest option — both tables share this shape."""

    id: str
    slug: str
    label: str
    description: Optional[str] = None
