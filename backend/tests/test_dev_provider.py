"""Unit tests for DevAIProvider (the local-dev mock provider) and
get_ai_provider() (the fake/claude switch). No real network access
anywhere in this file — DevAIProvider makes none by construction, and
the "claude" branch is tested only via construction-time config errors,
never a real call."""

import ast
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.ai.dev_provider import DevAIProvider, build_mock_enrichment
from app.ai.enrichment import EnrichmentResult, build_user_prompt
from app.ai.provider import AIProviderConfigError, AIResponse


# ---- build_mock_enrichment: the four required example categories --------


def test_missing_input_produces_minimal_valid_result():
    result = build_mock_enrichment(content_type="job", title="", description="")
    validated = EnrichmentResult.model_validate(result)
    assert validated.skills == []
    assert validated.topics == []
    assert validated.experience_level is None


def test_weak_match_short_description_produces_valid_result_with_no_tags():
    result = build_mock_enrichment(
        content_type="job", title="Engineer", description="Short role."
    )
    validated = EnrichmentResult.model_validate(result)
    assert validated.skills == []
    assert validated.topics == []
    assert validated.experience_level is None


def test_partial_match_non_job_content_never_sets_experience_level():
    result = build_mock_enrichment(
        content_type="article",
        title="Negotiating Salary with Confidence",
        description="A detailed article covering strategies for negotiating "
        "compensation, including research, timing, and communication tips.",
    )
    validated = EnrichmentResult.model_validate(result)
    assert validated.experience_level is None
    assert len(validated.summary) > 0


def test_partial_match_job_with_no_explicit_level_stays_null():
    result = build_mock_enrichment(
        content_type="job",
        title="Software Engineer",
        description="Join our team to build delightful products used by "
        "thousands of customers every single day of the week.",
    )
    validated = EnrichmentResult.model_validate(result)
    assert validated.experience_level is None


def test_strong_match_job_with_explicit_level_sets_experience_level():
    result = build_mock_enrichment(
        content_type="job",
        title="Senior Backend Engineer",
        description="We are looking for a Senior Backend Engineer to lead our "
        "platform team, mentor junior staff, and own architectural decisions "
        "across our distributed systems and data infrastructure.",
    )
    validated = EnrichmentResult.model_validate(result)
    assert validated.experience_level == "senior"
    assert len(validated.skills) > 0


def test_strong_match_entry_level_keyword_detected():
    result = build_mock_enrichment(
        content_type="job",
        title="Software Engineer",
        description="This is an entry-level position for new graduates looking "
        "to start their career in software engineering with full mentorship "
        "and structured onboarding support provided.",
    )
    validated = EnrichmentResult.model_validate(result)
    assert validated.experience_level == "entry"


# ---- Determinism -----------------------------------------------------------


def test_same_input_produces_identical_output():
    kwargs = dict(
        content_type="job",
        title="Senior Data Scientist",
        description="A senior role requiring 8+ years of experience in "
        "machine learning, statistics, and large-scale data pipelines.",
    )
    first = build_mock_enrichment(**kwargs)
    second = build_mock_enrichment(**kwargs)
    assert first == second


# ---- Always schema-valid, for every category -------------------------------


@pytest.mark.parametrize(
    "content_type,title,description",
    [
        ("job", "", ""),
        ("job", "Engineer", "short"),
        ("article", "Some Article", "A reasonably detailed article body here."),
        ("job", "Senior Engineer", "Senior role, 10+ years experience required."),
        ("event", "Community Meetup", "A casual networking event for professionals."),
        ("wellness-ish-unused", "Meditation Guide", "A gentle guide to daily mindfulness practice."),
    ],
)
def test_build_mock_enrichment_always_validates(content_type, title, description):
    result = build_mock_enrichment(content_type=content_type, title=title, description=description)
    EnrichmentResult.model_validate(result)  # must not raise


# ---- DevAIProvider.generate() ----------------------------------------------


def test_dev_provider_extracts_content_from_real_prompt_format():
    provider = DevAIProvider()
    prompt = build_user_prompt(
        "job",
        "Senior Platform Engineer",
        "We need a senior engineer to lead this team with deep infrastructure expertise.",
    )

    response = provider.generate(system="irrelevant", prompt=prompt, max_tokens=1024)

    assert isinstance(response, AIResponse)
    assert response.model == "dev-fake-model"
    assert response.stop_reason == "end_turn"
    parsed = json.loads(response.text)
    EnrichmentResult.model_validate(parsed)
    assert parsed["experience_level"] == "senior"


def test_dev_provider_handles_missing_description_tag_gracefully():
    provider = DevAIProvider()
    prompt = "<content_type>job</content_type>\n<title>Engineer</title>"  # no description tag

    response = provider.generate(system="sys", prompt=prompt, max_tokens=1024)

    parsed = json.loads(response.text)
    EnrichmentResult.model_validate(parsed)  # must not raise


def test_dev_provider_never_imports_network_libraries():
    import app.ai.dev_provider as dev_provider_module

    with open(dev_provider_module.__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert "anthropic" not in imported_roots
    assert "openai" not in imported_roots
    assert "httpx" not in imported_roots
    assert "requests" not in imported_roots


def test_dev_provider_makes_no_real_call_and_returns_immediately():
    # DevAIProvider.generate() is pure computation — no I/O of any kind.
    # Calling it many times in a tight loop with no mocking/patching is
    # itself proof there's no network dependency to fail or hang on.
    provider = DevAIProvider()
    for _ in range(50):
        response = provider.generate(
            system="sys", prompt="<content_type>job</content_type><title>X</title>",
            max_tokens=100,
        )
        assert response.text


# ---- get_ai_provider() factory ---------------------------------------------


def test_factory_returns_dev_provider_when_configured_fake():
    from app.ai.factory import get_ai_provider

    fake_settings = SimpleNamespace(ai_provider="fake")
    with patch("app.ai.factory.get_settings", return_value=fake_settings):
        provider = get_ai_provider()

    assert isinstance(provider, DevAIProvider)


def test_factory_returns_claude_provider_when_configured_claude():
    # get_claude_provider() reads settings via its own imported
    # get_settings reference in app.ai.claude_provider, a separate name
    # binding from app.ai.factory's — both must be patched, or this test's
    # result would depend on whatever ANTHROPIC_API_KEY happens to be set
    # in the real environment's .env, rather than the fake_settings given
    # here. (Caught during implementation: the real .env in this
    # environment does have a key set, which silently masked an
    # under-patched version of this test.)
    from app.ai.factory import get_ai_provider
    from app.ai.claude_provider import ClaudeProvider

    fake_settings = SimpleNamespace(
        ai_provider="claude",
        anthropic_api_key="test-key",
        ai_model="claude-opus-5",
        ai_timeout_seconds=30.0,
        ai_max_retries=2,
    )
    with patch("app.ai.factory.get_settings", return_value=fake_settings), patch(
        "app.ai.claude_provider.get_settings", return_value=fake_settings
    ):
        provider = get_ai_provider()

    assert isinstance(provider, ClaudeProvider)


def test_factory_claude_without_key_raises_config_error():
    # Same dual-patch requirement as above — must not depend on whether
    # the real environment happens to have ANTHROPIC_API_KEY set.
    from app.ai.factory import get_ai_provider

    fake_settings = SimpleNamespace(
        ai_provider="claude",
        anthropic_api_key=None,
        ai_model="claude-opus-5",
        ai_timeout_seconds=30.0,
        ai_max_retries=2,
    )
    with patch("app.ai.factory.get_settings", return_value=fake_settings), patch(
        "app.ai.claude_provider.get_settings", return_value=fake_settings
    ):
        with pytest.raises(AIProviderConfigError):
            get_ai_provider()


def test_settings_ai_provider_field_defaults_to_fake():
    # Checks the field's own declared default directly, rather than
    # constructing a real Settings() — which would read backend/.env and
    # could silently pass or fail depending on that file's unrelated,
    # environment-specific contents rather than the code's actual default.
    from app.config import Settings

    assert Settings.model_fields["ai_provider"].default == "fake"
