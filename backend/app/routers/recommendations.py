from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from supabase import Client

from app.dependencies.auth import CurrentUser, get_current_user, get_user_supabase_client
from app.recommendations import ContentCandidate, is_location_eligible, rank_content
from app.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

_VALID_CATEGORIES = ("career", "wellness")


class RecommendationItem(BaseModel):
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
    score: int
    matched_goal_ids: List[str]
    matched_interest_ids: List[str]


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@router.get("", response_model=List[RecommendationItem])
def get_recommendations(
    category: Optional[str] = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    user_client: Client = Depends(get_user_supabase_client),
) -> List[RecommendationItem]:
    if category is not None and category not in _VALID_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"category must be one of {_VALID_CATEGORIES}",
        )

    # User-specific data (profile location, goals, interests) goes through
    # the RLS-scoped, per-request client authenticated as this user —
    # never the shared public client, and never via an internal HTTP call
    # to our own /api/profile or /api/goals endpoints.
    profile_result = (
        user_client.table("profiles")
        .select("location_city, location_country")
        .eq("id", current_user.id)
        .execute()
    )
    profile_row = profile_result.data[0] if profile_result.data else {}
    profile_city = profile_row.get("location_city")
    profile_country = profile_row.get("location_country")

    goals_result = (
        user_client.table("user_goals").select("goal_id").eq("user_id", current_user.id).execute()
    )
    user_goal_ids: Set[str] = {row["goal_id"] for row in goals_result.data}

    interests_result = (
        user_client.table("user_interests")
        .select("interest_id")
        .eq("user_id", current_user.id)
        .execute()
    )
    user_interest_ids: Set[str] = {row["interest_id"] for row in interests_result.data}

    # Public content data: the shared cached anon-key client, same pattern
    # as /api/onboarding/options — content_items/content_goals/content_interests
    # have public SELECT policies, no user JWT required to read them.
    public_client = get_supabase_client()

    content_query = public_client.table("content_items").select("*").eq("is_active", True)
    if category:
        content_query = content_query.eq("category", category)
    content_rows: List[Dict[str, Any]] = content_query.execute().data

    eligible_rows = [
        row
        for row in content_rows
        if is_location_eligible(
            content_city=row.get("location_city"),
            content_country=row.get("location_country"),
            is_remote=row["is_remote"],
            profile_city=profile_city,
            profile_country=profile_country,
        )
    ]

    content_ids = [row["id"] for row in eligible_rows]

    goal_tags_by_content: Dict[str, Set[str]] = {}
    interest_tags_by_content: Dict[str, Set[str]] = {}

    if content_ids:
        goal_tags = (
            public_client.table("content_goals")
            .select("content_id, goal_id")
            .in_("content_id", content_ids)
            .execute()
            .data
        )
        for row in goal_tags:
            goal_tags_by_content.setdefault(row["content_id"], set()).add(row["goal_id"])

        interest_tags = (
            public_client.table("content_interests")
            .select("content_id, interest_id")
            .in_("content_id", content_ids)
            .execute()
            .data
        )
        for row in interest_tags:
            interest_tags_by_content.setdefault(row["content_id"], set()).add(row["interest_id"])

    row_by_id = {row["id"]: row for row in eligible_rows}

    candidates = [
        ContentCandidate(
            id=row["id"],
            goal_ids=frozenset(goal_tags_by_content.get(row["id"], set())),
            interest_ids=frozenset(interest_tags_by_content.get(row["id"], set())),
            published_at=_parse_datetime(row.get("published_at")),
            created_at=_parse_datetime(row["created_at"]),
        )
        for row in eligible_rows
    ]

    ranked = rank_content(candidates, user_goal_ids, user_interest_ids)

    items: List[RecommendationItem] = []
    for scored in ranked:
        row = row_by_id[scored.content_id]
        items.append(
            RecommendationItem(
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
                score=scored.score,
                matched_goal_ids=list(scored.matched_goal_ids),
                matched_interest_ids=list(scored.matched_interest_ids),
            )
        )

    return items
