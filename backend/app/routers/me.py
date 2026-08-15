from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies.auth import CurrentUser, get_current_user

router = APIRouter(prefix="/api", tags=["me"])


class MeResponse(BaseModel):
    user_id: str


@router.get("/me", response_model=MeResponse)
def read_me(current_user: CurrentUser = Depends(get_current_user)) -> MeResponse:
    return MeResponse(user_id=current_user.id)
