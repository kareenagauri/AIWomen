"""DevAIProvider — a zero-setup, deterministic local substitute for
ClaudeProvider. FOR LOCAL DEVELOPMENT / TESTING ONLY — never use in
production, and never treat its output as a real model's judgment.

Why this exists and how it differs from FakeAIProvider: FakeAIProvider
(fake_provider.py) is the precise test double this project's ~65 unit
tests are already built on — the caller pre-programs every exact
response it should return. That's exactly right for unit tests, but
useless for "just run the CLI locally and see something plausible
happen" when ANTHROPIC_API_KEY is unavailable (e.g. exhausted account
credits). DevAIProvider needs no setup at all: given the same prompt, it
deterministically derives a plausible, schema-valid enrichment from
whatever content is actually in the prompt — using fixed string/keyword
rules, never randomness — so a given content item always produces the
same fake enrichment across runs, and the real enrichment pipeline
(validation, hashing, upsert) can be exercised end-to-end against a real
database without spending any real API credits.

Never imports or calls anthropic, openai, or any other external API —
this file has no network dependency of any kind.
"""

import json
import re
from typing import Any, Dict, Optional

from app.ai.provider import AIProvider, AIResponse

_CONTENT_TYPE_RE = re.compile(r"<content_type>(.*?)</content_type>", re.DOTALL)
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.DOTALL)
_DESCRIPTION_RE = re.compile(r"<description>(.*?)</description>", re.DOTALL)

# Maps a keyword that might explicitly appear in a job description to the
# experience_level it implies — mirrors (deliberately, for realism) the
# real system prompt's own instruction to only set a level on an
# explicit, stated signal, never a vague inference.
_LEVEL_KEYWORDS = {
    "senior": "senior",
    "lead": "senior",
    "staff": "senior",
    "principal": "senior",
    "junior": "entry",
    "entry-level": "entry",
    "entry level": "entry",
    "new grad": "entry",
    "graduate program": "entry",
    "mid-level": "mid",
    "mid level": "mid",
}

_SKILLS_BY_CONTENT_TYPE = {
    "job": ["Communication", "Problem Solving", "Time Management", "Python"],
    "event": ["Networking", "Public Speaking"],
    "article": ["Career Planning"],
    "program": ["Mentorship"],
    "scholarship": ["Academic Writing"],
    "video": ["Active Listening"],
    "local_resource": ["Community Engagement"],
}


def _first_match(pattern: "re.Pattern[str]", text: str) -> str:
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _detect_experience_level(*, content_type: str, description: str) -> Optional[str]:
    if content_type != "job":
        return None
    lowered = description.lower()
    for keyword, level in _LEVEL_KEYWORDS.items():
        if keyword in lowered:
            return level
    return None


def _truncate(text: str, max_length: int) -> str:
    return text if len(text) <= max_length else text[: max_length - 1].rstrip() + "…"


def build_mock_enrichment(*, content_type: str, title: str, description: str) -> Dict[str, Any]:
    """Deterministically derives a schema-valid enrichment dict from the
    given content — the same three examples below cover the range this
    project's real prompt is expected to see:

    - missing/incomplete input (no usable title)      -> minimal, empty tags
    - weak match (title but a very short description) -> short summary, no tags
    - partial match (a decent description, no explicit -> moderate summary,
      level signal, or a non-job content type)            a few tags, no level
    - strong match (a job with a substantial            -> full summary, several
      description and an explicit level keyword)          skills/topics, a level
    """
    title = title.strip()
    description = description.strip()

    if not title:
        return {
            "summary": "Not enough information was provided to summarize this content.",
            "skills": [],
            "topics": [],
            "experience_level": None,
        }

    if len(description) < 40:
        return {
            "summary": _truncate(f"{title}. Limited details are available for this item.", 500),
            "skills": [],
            "topics": [],
            "experience_level": None,
        }

    experience_level = _detect_experience_level(content_type=content_type, description=description)
    skills_pool = _SKILLS_BY_CONTENT_TYPE.get(content_type, ["General Skills"])

    if content_type == "job" and experience_level is not None and len(description) >= 100:
        # Strong match: rich input, explicit level signal.
        return {
            "summary": _truncate(
                f"{title} — a {experience_level}-level opportunity. {description}", 500
            ),
            "skills": skills_pool[:8],
            "topics": ["career-development", "job-search"],
            "experience_level": experience_level,
        }

    if content_type != "job":
        # Partial match: non-job content rarely states an experience
        # level, mirroring the real system prompt's own rule.
        return {
            "summary": _truncate(f"{title}. {description}", 500),
            "skills": [],
            "topics": skills_pool[:6] or ["general-interest"],
            "experience_level": None,
        }

    # Partial match: a job with a decent description but no explicit
    # level signal.
    return {
        "summary": _truncate(f"{title}. {description}", 500),
        "skills": skills_pool[:8],
        "topics": ["career-development"],
        "experience_level": experience_level,
    }


class DevAIProvider(AIProvider):
    """Deterministic, offline, always-succeeds AIProvider for local
    development when ANTHROPIC_API_KEY is unavailable. Every response it
    returns satisfies EnrichmentResult's own constraints (summary
    1-500 chars, <=8 skills, <=6 topics, each 1-60 chars, non-blank,
    experience_level one of entry/mid/senior/null) — the same schema the
    real ClaudeProvider is expected to produce.

    Selected only when Settings.ai_provider == "fake" (the default for
    local development — see app/ai/factory.get_ai_provider()). Never
    calls any external API; always returns immediately.
    """

    def generate(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> AIResponse:
        content_type = _first_match(_CONTENT_TYPE_RE, prompt) or "job"
        title = _first_match(_TITLE_RE, prompt)
        description = _first_match(_DESCRIPTION_RE, prompt)

        result = build_mock_enrichment(
            content_type=content_type, title=title, description=description
        )

        return AIResponse(
            text=json.dumps(result),
            model="dev-fake-model",
            stop_reason="end_turn",
        )
