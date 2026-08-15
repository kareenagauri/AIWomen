from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from app.schemas import TagOption
from app.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


class OnboardingOptionsResponse(BaseModel):
    goals: List[TagOption]
    interests: List[TagOption]


@router.get("/options", response_model=OnboardingOptionsResponse)
def get_onboarding_options() -> OnboardingOptionsResponse:
    # Public data (goals/interests have an open SELECT policy), so the
    # shared anon-key client is used directly — no user JWT involved,
    # and this endpoint requires no authentication.
    client = get_supabase_client()

    goals_result = (
        client.table("goals")
        .select("id, slug, label, description")
        .order("label")
        .execute()
    )
    interests_result = (
        client.table("interests")
        .select("id, slug, label, description")
        .order("label")
        .execute()
    )

    return OnboardingOptionsResponse(
        goals=[TagOption(**row) for row in goals_result.data],
        interests=[TagOption(**row) for row in interests_result.data],
    )
