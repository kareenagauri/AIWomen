from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """Shared, cached anon-key client. Safe to reuse across concurrent
    requests only because it is never given a user's JWT — it is used for
    token verification (auth.get_claims) and for reading tables that have
    a public RLS policy (e.g. goals/interests), never for per-user queries."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def get_user_scoped_client(access_token: str) -> Client:
    """A fresh, uncached client authenticated as one user's JWT, for
    RLS-scoped table queries.

    Deliberately NOT cached/shared: postgrest-py's .auth() mutates the
    client's headers in place rather than returning a new object. Reusing
    one client across concurrent requests for different users would risk
    one user's token being attached to another user's in-flight query.
    """
    settings = get_settings()
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(access_token)
    return client
