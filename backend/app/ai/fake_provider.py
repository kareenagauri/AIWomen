"""Deterministic AIProvider test double — no network access, no API key,
no anthropic import. Lets any future caller of AIProvider be tested
without making a real Claude API call, the same way httpx.get() is
mocked in every existing ingestion test."""

from typing import Any, Dict, List, Optional

from app.ai.provider import AIProvider, AIResponse


class FakeAIProvider(AIProvider):
    """Returns pre-programmed responses in call order. Records every
    call it receives (system/prompt/max_tokens/response_format) so tests
    can assert on what was actually sent."""

    def __init__(self, responses: List[AIResponse]) -> None:
        self._responses = list(responses)
        self.calls: List[Dict[str, Any]] = []

    def generate(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> AIResponse:
        self.calls.append(
            {
                "system": system,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "response_format": response_format,
            }
        )
        if not self._responses:
            raise AssertionError("FakeAIProvider has no more programmed responses")
        return self._responses.pop(0)
