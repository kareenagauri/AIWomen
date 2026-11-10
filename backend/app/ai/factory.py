"""Single entry point for obtaining an AIProvider. Callers (e.g.
run_enrich_content.py) should import get_ai_provider() from here rather
than importing ClaudeProvider or DevAIProvider directly, so the fake/real
switch stays centralized in one place instead of being duplicated at
every call site.

Controlled by Settings.ai_provider — "fake" (the default, for local
development) selects DevAIProvider; "claude" selects the real
ClaudeProvider and requires ANTHROPIC_API_KEY to be set.
"""

import logging

from app.ai.claude_provider import get_claude_provider
from app.ai.dev_provider import DevAIProvider
from app.ai.provider import AIProvider
from app.config import get_settings

logger = logging.getLogger("ai.factory")


def get_ai_provider() -> AIProvider:
    settings = get_settings()

    if settings.ai_provider == "fake":
        logger.warning(
            "Using DevAIProvider (Settings.ai_provider='fake') — responses are "
            "deterministic mock data, NOT real Claude output. Set AI_PROVIDER=claude "
            "in backend/.env to use the real Anthropic provider."
        )
        return DevAIProvider()

    if settings.ai_provider == "claude":
        return get_claude_provider()

    raise ValueError(
        f"Unknown ai_provider setting: {settings.ai_provider!r} (expected 'fake' or 'claude')"
    )
