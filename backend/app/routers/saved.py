from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from supabase import Client

from app.dependencies.auth import CurrentUser, get_current_user, get_user_supabase_client
from app.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/saved", tags=["saved"])

_CONTENT_COLUMNS = (
    "id, category, content_type, title, description, url, organization, "
    "location_city, location_region, location_country, is_remote, "
    "event_date, deadline, published_at, is_active"
)


class SavedContentItem(BaseModel):
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
    saved_at: str


@router.get("", response_model=List[SavedContentItem])
def get_saved_content(
    current_user: CurrentUser = Depends(get_current_user),
    user_client: Client = Depends(get_user_supabase_client),
) -> List[SavedContentItem]:
    result = (
        user_client.table("saved_content")
        .select(f"created_at, content_items({_CONTENT_COLUMNS})")
        .eq("user_id", current_user.id)
        .order("created_at", desc=True)
        .execute()
    )

    items: List[SavedContentItem] = []
    for row in result.data:
        content: Optional[Dict[str, Any]] = row.get("content_items")
        if not content or not content.get("is_active", True):
            # Content was deactivated after being saved — skip rather than
            # show broken/removed content.
            continue
        items.append(
            SavedContentItem(
                id=content["id"],
                category=content["category"],
                content_type=content["content_type"],
                title=content["title"],
                description=content.get("description"),
                url=content.get("url"),
                organization=content.get("organization"),
                location_city=content.get("location_city"),
                location_region=content.get("location_region"),
                location_country=content.get("location_country"),
                is_remote=content["is_remote"],
                event_date=content.get("event_date"),
                deadline=content.get("deadline"),
                published_at=content.get("published_at"),
                saved_at=row["created_at"],
            )
        )
    return items


@router.post("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def save_content(
    content_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    user_client: Client = Depends(get_user_supabase_client),
) -> None:
    content_id_str = str(content_id)

    public_client = get_supabase_client()
    exists = (
        public_client.table("content_items")
        .select("id")
        .eq("id", content_id_str)
        .eq("is_active", True)
        .execute()
    )
    if not exists.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    # ignore_duplicates=True makes a repeated save a true no-op at the
    # database level (ON CONFLICT DO NOTHING) — no error, no duplicate row,
    # and the original created_at is preserved rather than bumped.
    user_client.table("saved_content").upsert(
        {"user_id": current_user.id, "content_id": content_id_str},
        on_conflict="user_id,content_id",
        ignore_duplicates=True,
    ).execute()


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_saved_content(
    content_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    user_client: Client = Depends(get_user_supabase_client),
) -> None:
    user_client.table("saved_content").delete().eq("user_id", current_user.id).eq(
        "content_id", str(content_id)
    ).execute()
