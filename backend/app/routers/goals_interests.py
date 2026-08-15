from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from supabase import Client

from app.dependencies.auth import CurrentUser, get_current_user, get_user_supabase_client
from app.schemas import TagOption

router = APIRouter(prefix="/api/profile/me", tags=["goals", "interests"])


class GoalSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal_ids: List[UUID] = Field(default_factory=list)


class InterestSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interest_ids: List[UUID] = Field(default_factory=list)


def _replace_relations(
    client: Client,
    *,
    junction_table: str,
    lookup_table: str,
    target_column: str,
    user_id: str,
    target_ids: List[UUID],
) -> None:
    """Replace all of a user's rows in a junction table with the submitted
    set. Delete-then-insert (not diffed) — see Stage 4 design notes for why
    that's safe and sufficient here."""
    unique_ids = sorted({str(tid) for tid in target_ids})

    if unique_ids:
        existing = client.table(lookup_table).select("id").in_("id", unique_ids).execute()
        found_ids = {row["id"] for row in existing.data}
        missing_ids = [gid for gid in unique_ids if gid not in found_ids]
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown {lookup_table} id(s): {missing_ids}",
            )

    client.table(junction_table).delete().eq("user_id", user_id).execute()

    if unique_ids:
        client.table(junction_table).insert(
            [{"user_id": user_id, target_column: gid} for gid in unique_ids]
        ).execute()


def _fetch_related(
    client: Client, *, junction_table: str, embed_table: str, user_id: str
) -> List[TagOption]:
    result = (
        client.table(junction_table)
        .select(f"{embed_table}(id, slug, label, description)")
        .eq("user_id", user_id)
        .execute()
    )
    rows: List[Dict[str, Any]] = result.data
    return [TagOption(**row[embed_table]) for row in rows if row.get(embed_table)]


@router.get("/goals", response_model=List[TagOption])
def get_my_goals(
    current_user: CurrentUser = Depends(get_current_user),
    client: Client = Depends(get_user_supabase_client),
) -> List[TagOption]:
    return _fetch_related(
        client, junction_table="user_goals", embed_table="goals", user_id=current_user.id
    )


@router.put("/goals", response_model=List[TagOption])
def replace_my_goals(
    payload: GoalSelectionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    client: Client = Depends(get_user_supabase_client),
) -> List[TagOption]:
    _replace_relations(
        client,
        junction_table="user_goals",
        lookup_table="goals",
        target_column="goal_id",
        user_id=current_user.id,
        target_ids=payload.goal_ids,
    )
    return _fetch_related(
        client, junction_table="user_goals", embed_table="goals", user_id=current_user.id
    )


@router.get("/interests", response_model=List[TagOption])
def get_my_interests(
    current_user: CurrentUser = Depends(get_current_user),
    client: Client = Depends(get_user_supabase_client),
) -> List[TagOption]:
    return _fetch_related(
        client, junction_table="user_interests", embed_table="interests", user_id=current_user.id
    )


@router.put("/interests", response_model=List[TagOption])
def replace_my_interests(
    payload: InterestSelectionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    client: Client = Depends(get_user_supabase_client),
) -> List[TagOption]:
    _replace_relations(
        client,
        junction_table="user_interests",
        lookup_table="interests",
        target_column="interest_id",
        user_id=current_user.id,
        target_ids=payload.interest_ids,
    )
    return _fetch_related(
        client, junction_table="user_interests", embed_table="interests", user_id=current_user.id
    )
