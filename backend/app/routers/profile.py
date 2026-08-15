from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from supabase import Client

from app.dependencies.auth import CurrentUser, get_current_user, get_user_supabase_client

router = APIRouter(prefix="/api/profile", tags=["profile"])

_PROFILE_MISSING_DETAIL = (
    "Profile record not found for authenticated user. This indicates a data "
    "integrity issue — the signup trigger should have created it automatically."
)


class ProfileResponse(BaseModel):
    id: str
    display_name: Optional[str] = None
    career_field: Optional[str] = None
    location_city: Optional[str] = None
    location_region: Optional[str] = None
    location_country: Optional[str] = None
    bio: Optional[str] = None
    onboarding_completed: bool
    created_at: str
    updated_at: str


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: Optional[str] = Field(default=None, max_length=200)
    career_field: Optional[str] = Field(default=None, max_length=200)
    location_city: Optional[str] = Field(default=None, max_length=200)
    location_region: Optional[str] = Field(default=None, max_length=200)
    location_country: Optional[str] = Field(default=None, max_length=200)
    bio: Optional[str] = Field(default=None, max_length=2000)


def _fetch_profile_row(client: Client, user_id: str) -> Dict[str, Any]:
    result = client.table("profiles").select("*").eq("id", user_id).execute()
    rows = result.data
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_PROFILE_MISSING_DETAIL,
        )
    return rows[0]


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(
    current_user: CurrentUser = Depends(get_current_user),
    client: Client = Depends(get_user_supabase_client),
) -> ProfileResponse:
    row = _fetch_profile_row(client, current_user.id)
    return ProfileResponse(**row)


@router.put("/me", response_model=ProfileResponse)
def update_my_profile(
    payload: ProfileUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    client: Client = Depends(get_user_supabase_client),
) -> ProfileResponse:
    # Only fields the client actually included in the request body are
    # touched — omitted fields are left unchanged, matching partial-update
    # (PATCH-like) semantics even though this is a PUT.
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        row = _fetch_profile_row(client, current_user.id)
        return ProfileResponse(**row)

    result = (
        client.table("profiles")
        .update(updates)
        .eq("id", current_user.id)
        .execute()
    )
    rows = result.data
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_PROFILE_MISSING_DETAIL,
        )
    return ProfileResponse(**rows[0])
