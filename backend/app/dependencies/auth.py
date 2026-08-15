from fastapi import HTTPException, Request, status
from pydantic import BaseModel
from supabase_auth.errors import AuthApiError, AuthInvalidJwtError

from app.supabase_client import get_supabase_client


class CurrentUser(BaseModel):
    id: str


def get_current_user(request: Request) -> CurrentUser:
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must use the Bearer scheme",
        )

    client = get_supabase_client()

    try:
        response = client.auth.get_claims(token)
    except (AuthInvalidJwtError, AuthApiError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    if response is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    claims = response.get("claims") if isinstance(response, dict) else None
    user_id = claims.get("sub") if isinstance(claims, dict) else None

    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing a subject claim",
        )

    return CurrentUser(id=user_id)
