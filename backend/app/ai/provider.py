"""Provider-agnostic AI interface. Concrete providers (Claude, or any
future replacement) implement AIProvider; callers depend only on this
module, never on a concrete SDK import — no Anthropic (or any other
vendor) import belongs anywhere in this file."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AIResponse:
    text: str
    model: str
    stop_reason: str


class AIProviderError(Exception):
    """Base class for AI provider failures — configuration, timeout, rate
    limit, or any other call failure. Callers should catch this rather
    than a concrete SDK's exception types, so swapping providers never
    requires touching caller error handling."""


class AIProviderConfigError(AIProviderError):
    """Raised when a provider is constructed without the configuration it
    needs (e.g. a missing API key) — a hard failure at construction time,
    before any network call is attempted."""


class AIProvider(ABC):
    @abstractmethod
    def generate(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> AIResponse:
        """Send one request and return the model's response.

        response_format is a placeholder for structured-output requests
        (passed through to the provider's structured-output mechanism
        when supported) — no caller uses it yet.

        Raises AIProviderError (or a subclass) on failure — a caller
        never needs to catch a concrete SDK exception type.
        """
        raise NotImplementedError
