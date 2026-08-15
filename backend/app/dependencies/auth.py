from typing import Tuple

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel
from supabase import Client
from supabase_auth.errors import AuthApiError, AuthInvalidJwtError

from app.supabase_client import get_supabase_client, get_user_scoped_client


class CurrentUser(BaseModel):
    id: str


def _verify_bearer_token(request: Request) -> Tuple[str, str]:
    """Parse and verify the request's bearer token. Returns (user_id, token).

    Shared by get_current_user and get_user_supabase_client so a request
    using both only verifies the token once (FastAPI caches this
    dependency's result per-request, since both depend on this same
    function object).
    """
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

    return user_id, token


def get_current_user(
    verified: Tuple[str, str] = Depends(_verify_bearer_token),
) -> CurrentUser:
    user_id, _ = verified
    return CurrentUser(id=user_id)


def get_user_supabase_client(
    verified: Tuple[str, str] = Depends(_verify_bearer_token),
) -> Client:
    """A Supabase client authenticated as the requesting user, for routes
    that need to query/update user-owned tables under RLS."""
    _, token = verified
    return get_user_scoped_client(token)
