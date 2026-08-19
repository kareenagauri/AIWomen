from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from supabase import Client

from app.dependencies.auth import CurrentUser, get_current_user, get_user_supabase_client
from app.recommendations import ContentCandidate, score_content
from app.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/content", tags=["content"])


class ContentDetail(BaseModel):
    id: str
    category: str
    content_type: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    organization: Optional[str] = None
    location_city: Optional[str] = None
    location_region: Optional[str] = None
    location_country: Optional[str] = None
    is_remote: bool
    event_date: Optional[str] = None
    deadline: Optional[str] = None
    published_at: Optional[str] = None
    matched_goal_ids: List[str]
    matched_interest_ids: List[str]
    is_saved: bool


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@router.get("/{content_id}", response_model=ContentDetail)
def get_content_detail(
    content_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    user_client: Client = Depends(get_user_supabase_client),
) -> ContentDetail:
    public_client = get_supabase_client()
    content_id_str = str(content_id)

    content_result = (
        public_client.table("content_items")
        .select("*")
        .eq("id", content_id_str)
        .eq("is_active", True)
        .execute()
    )
    if not content_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    row: Dict[str, Any] = content_result.data[0]

    # Public tag data for this one item.
    goal_tags = (
        public_client.table("content_goals")
        .select("goal_id")
        .eq("content_id", content_id_str)
        .execute()
    )
    interest_tags = (
        public_client.table("content_interests")
        .select("interest_id")
        .eq("content_id", content_id_str)
        .execute()
    )

    # User-specific data: goals/interests/saved-state, via the RLS-scoped
    # client authenticated as this user — never the shared public client.
    goals_result = (
        user_client.table("user_goals").select("goal_id").eq("user_id", current_user.id).execute()
    )
    interests_result = (
        user_client.table("user_interests")
        .select("interest_id")
        .eq("user_id", current_user.id)
        .execute()
    )
    saved_result = (
        user_client.table("saved_content")
        .select("content_id")
        .eq("user_id", current_user.id)
        .eq("content_id", content_id_str)
        .execute()
    )

    # Reuses the exact same pure scoring function the recommendation feed
    # uses — not a reimplementation of "what counts as a match" — and simply
    # discards the score it also computes, since this endpoint never
    # exposes it.
    candidate = ContentCandidate(
        id=row["id"],
        goal_ids=frozenset(t["goal_id"] for t in goal_tags.data),
        interest_ids=frozenset(t["interest_id"] for t in interest_tags.data),
        published_at=_parse_datetime(row.get("published_at")),
        created_at=_parse_datetime(row["created_at"]),
    )
    user_goal_ids = frozenset(r["goal_id"] for r in goals_result.data)
    user_interest_ids = frozenset(r["interest_id"] for r in interests_result.data)
    scored = score_content(
        candidate, user_goal_ids, user_interest_ids, now=datetime.now(timezone.utc)
    )

    return ContentDetail(
        id=row["id"],
        category=row["category"],
        content_type=row["content_type"],
        title=row["title"],
        description=row.get("description"),
        url=row.get("url"),
        organization=row.get("organization"),
        location_city=row.get("location_city"),
        location_region=row.get("location_region"),
        location_country=row.get("location_country"),
        is_remote=row["is_remote"],
        event_date=row.get("event_date"),
        deadline=row.get("deadline"),
        published_at=row.get("published_at"),
        matched_goal_ids=list(scored.matched_goal_ids),
        matched_interest_ids=list(scored.matched_interest_ids),
        is_saved=bool(saved_result.data),
    )
