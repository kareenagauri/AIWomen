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


def get_service_role_client() -> Client:
    """A client authenticated with the service-role key, bypassing RLS
    entirely.

    ONLY for offline scripts with no live user request (e.g. content
    ingestion) — never import this from a router or any request-handling
    code path. Every table this app exposes to end users enforces access
    through RLS or through get_user_scoped_client's per-user filtering;
    this client sidesteps both, so its use is deliberately confined to
    app/ingestion/.
    """
    settings = get_settings()
    if not settings.supabase_service_role_key:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY is not set — required to run offline "
            "ingestion scripts. Add it to backend/.env."
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
