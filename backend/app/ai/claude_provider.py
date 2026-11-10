"""Claude (Anthropic) implementation of AIProvider. This is the only
file in app/ai/ (and the only file in the whole backend) that imports
the anthropic SDK — callers depend on AIProvider, never on this module
directly, so swapping providers later never touches caller code.
"""

from typing import Any, Dict, Optional

import anthropic

from app.ai.provider import AIProvider, AIProviderConfigError, AIProviderError, AIResponse
from app.config import get_settings


class ClaudeProvider(AIProvider):
    def __init__(
        self,
        *,
        api_key: Optional[str],
        model: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> None:
        if not api_key:
            raise AIProviderConfigError(
                "ANTHROPIC_API_KEY is not set — required to construct ClaudeProvider. "
                "Add it to backend/.env."
            )
        self._model = model
        # Explicit timeout + max_retries, not the SDK's own defaults: the
        # SDK already retries connection errors, 429, and 5xx with
        # exponential backoff up to max_retries — no hand-rolled retry
        # loop needed here.
        self._client = anthropic.Anthropic(
            api_key=api_key, timeout=timeout_seconds, max_retries=max_retries
        )

    def generate(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> AIResponse:
        create_kwargs: Dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        if response_format is not None:
            create_kwargs["output_config"] = {"format": response_format}

        try:
            response = self._client.messages.create(**create_kwargs)
        except anthropic.APIError as exc:
            # Deliberately broad within the SDK's own exception hierarchy
            # (anthropic.APIError is the common base of APIStatusError and
            # APIConnectionError): any Claude API failure — auth, rate
            # limit, timeout, server error, connection — surfaces to
            # callers as one AIProviderError, never a concrete anthropic.*
            # type. Only str(exc) is included, never the API key or the
            # request payload (system/prompt), so this message is safe to
            # log or display.
            raise AIProviderError(f"Claude API call failed: {exc}") from exc

        text = "".join(block.text for block in response.content if block.type == "text")
        return AIResponse(text=text, model=response.model, stop_reason=response.stop_reason)


def get_claude_provider() -> AIProvider:
    """Construct a ClaudeProvider from application settings. Raises
    AIProviderConfigError immediately (before any network call) if
    ANTHROPIC_API_KEY is not configured — mirrors
    app.supabase_client.get_service_role_client()'s shape exactly."""
    settings = get_settings()
    return ClaudeProvider(
        api_key=settings.anthropic_api_key,
        model=settings.ai_model,
        timeout_seconds=settings.ai_timeout_seconds,
        max_retries=settings.ai_max_retries,
    )
