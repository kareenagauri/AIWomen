"""Unit tests for the AI provider foundation: the provider-agnostic
interface, the fake test double, and the Claude implementation's
configuration/error-wrapping behavior. No real network access anywhere
in this file — the Claude SDK client is always mocked or never
constructed with a working key."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import anthropic
import httpx2
import pytest

from app.ai.claude_provider import ClaudeProvider, get_claude_provider
from app.ai.fake_provider import FakeAIProvider
from app.ai.provider import AIProvider, AIProviderConfigError, AIProviderError, AIResponse


# ---- FakeAIProvider ---------------------------------------------------


def test_fake_provider_returns_responses_in_order():
    responses = [
        AIResponse(text="first", model="fake-model", stop_reason="end_turn"),
        AIResponse(text="second", model="fake-model", stop_reason="end_turn"),
    ]
    provider = FakeAIProvider(responses)

    first = provider.generate(system="sys", prompt="a", max_tokens=100)
    second = provider.generate(system="sys", prompt="b", max_tokens=100)

    assert first.text == "first"
    assert second.text == "second"


def test_fake_provider_records_calls():
    provider = FakeAIProvider(
        [AIResponse(text="ok", model="fake-model", stop_reason="end_turn")]
    )

    provider.generate(system="be terse", prompt="hello", max_tokens=50, response_format={"type": "json"})

    assert provider.calls == [
        {
            "system": "be terse",
            "prompt": "hello",
            "max_tokens": 50,
            "response_format": {"type": "json"},
        }
    ]


def test_fake_provider_raises_when_exhausted():
    provider = FakeAIProvider([])
    with pytest.raises(AssertionError):
        provider.generate(system="sys", prompt="a", max_tokens=10)


def test_fake_provider_makes_no_network_calls():
    # No anthropic/httpx import anywhere in fake_provider.py — asserting
    # this module-level fact protects the "no real Claude calls in tests"
    # guarantee even if the implementation changes later. Parsed via ast
    # (not a substring search) so this only inspects actual import
    # statements, not prose in the module's own docstring.
    import ast

    import app.ai.fake_provider as fake_provider_module

    with open(fake_provider_module.__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert "anthropic" not in imported_roots
    assert "httpx" not in imported_roots


def test_ai_provider_is_abstract():
    with pytest.raises(TypeError):
        AIProvider()  # type: ignore[abstract]


# ---- ClaudeProvider construction / config errors -----------------------


def test_claude_provider_raises_config_error_when_api_key_missing():
    with pytest.raises(AIProviderConfigError):
        ClaudeProvider(api_key=None, model="claude-opus-5", timeout_seconds=30.0, max_retries=2)


def test_claude_provider_raises_config_error_when_api_key_blank():
    with pytest.raises(AIProviderConfigError):
        ClaudeProvider(api_key="", model="claude-opus-5", timeout_seconds=30.0, max_retries=2)


def test_claude_provider_config_error_never_contains_api_key_value():
    # Guards the "no API keys logged" requirement at the exception-message
    # level: even though no key was configured here, this proves the
    # error path never echoes back whatever key value it was given.
    secret = "sk-ant-super-secret-value"
    with pytest.raises(AIProviderConfigError) as exc_info:
        ClaudeProvider(api_key=None, model="claude-opus-5", timeout_seconds=30.0, max_retries=2)
    assert secret not in str(exc_info.value)


def test_get_claude_provider_raises_config_error_when_settings_key_missing():
    fake_settings = SimpleNamespace(
        anthropic_api_key=None,
        ai_model="claude-opus-5",
        ai_timeout_seconds=30.0,
        ai_max_retries=2,
    )
    with patch("app.ai.claude_provider.get_settings", return_value=fake_settings):
        with pytest.raises(AIProviderConfigError):
            get_claude_provider()


def test_get_claude_provider_constructs_with_settings_values():
    fake_settings = SimpleNamespace(
        anthropic_api_key="test-key",
        ai_model="claude-opus-5",
        ai_timeout_seconds=12.5,
        ai_max_retries=1,
    )
    with patch("app.ai.claude_provider.get_settings", return_value=fake_settings):
        provider = get_claude_provider()

    assert isinstance(provider, ClaudeProvider)
    assert provider._model == "claude-opus-5"


# ---- ClaudeProvider.generate() ------------------------------------------


def _make_provider() -> ClaudeProvider:
    # A syntactically-valid but fake key — anthropic.Anthropic(...)
    # never makes a network call at construction time, only when
    # .messages.create(...) is actually invoked.
    return ClaudeProvider(
        api_key="test-key-not-real", model="claude-opus-5", timeout_seconds=5.0, max_retries=2
    )


def test_generate_returns_text_from_response():
    provider = _make_provider()
    fake_response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="hello world")],
        model="claude-opus-5",
        stop_reason="end_turn",
    )
    provider._client.messages.create = MagicMock(return_value=fake_response)

    result = provider.generate(system="sys", prompt="hi", max_tokens=100)

    assert result == AIResponse(text="hello world", model="claude-opus-5", stop_reason="end_turn")


def test_generate_concatenates_only_text_blocks():
    provider = _make_provider()
    fake_response = SimpleNamespace(
        content=[
            SimpleNamespace(type="thinking", thinking="reasoning..."),
            SimpleNamespace(type="text", text="part one. "),
            SimpleNamespace(type="text", text="part two."),
        ],
        model="claude-opus-5",
        stop_reason="end_turn",
    )
    provider._client.messages.create = MagicMock(return_value=fake_response)

    result = provider.generate(system="sys", prompt="hi", max_tokens=100)

    assert result.text == "part one. part two."


def test_generate_passes_response_format_as_output_config():
    provider = _make_provider()
    fake_response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="ok")],
        model="claude-opus-5",
        stop_reason="end_turn",
    )
    mock_create = MagicMock(return_value=fake_response)
    provider._client.messages.create = mock_create

    schema = {"type": "json_schema", "schema": {"type": "object"}}
    provider.generate(system="sys", prompt="hi", max_tokens=100, response_format=schema)

    _, kwargs = mock_create.call_args
    assert kwargs["output_config"] == {"format": schema}


def test_generate_omits_output_config_when_no_response_format():
    provider = _make_provider()
    fake_response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="ok")],
        model="claude-opus-5",
        stop_reason="end_turn",
    )
    mock_create = MagicMock(return_value=fake_response)
    provider._client.messages.create = mock_create

    provider.generate(system="sys", prompt="hi", max_tokens=100)

    _, kwargs = mock_create.call_args
    assert "output_config" not in kwargs


def test_generate_wraps_api_connection_error():
    provider = _make_provider()
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    provider._client.messages.create = MagicMock(
        side_effect=anthropic.APIConnectionError(message="Connection error.", request=request)
    )

    with pytest.raises(AIProviderError):
        provider.generate(system="sys", prompt="hi", max_tokens=100)


def test_generate_error_never_contains_api_key_or_full_prompt():
    provider = _make_provider()
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    provider._client.messages.create = MagicMock(
        side_effect=anthropic.APIConnectionError(message="Connection error.", request=request)
    )

    secret_prompt = "PROMPT_MARKER_should_never_leak_into_error_text"
    with pytest.raises(AIProviderError) as exc_info:
        provider.generate(system="sys", prompt=secret_prompt, max_tokens=100)

    assert "test-key-not-real" not in str(exc_info.value)
    assert secret_prompt not in str(exc_info.value)
