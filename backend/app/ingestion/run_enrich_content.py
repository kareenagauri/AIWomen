"""Manual entry point for AI-enriching content_items (summary, skills,
topics, optional experience level) into content_enrichments.

Run with (from backend/, venv active):

    python -m app.ingestion.run_enrich_content
    python -m app.ingestion.run_enrich_content --limit 5
    python -m app.ingestion.run_enrich_content --limit 1 --dry-run
    python -m app.ingestion.run_enrich_content --limit 0   # unlimited

Not wired to any scheduler — deliberately manual for this stage. Requires
SUPABASE_SERVICE_ROLE_KEY to be set in every mode (selection always reads
content_items/content_enrichments).

AI provider is controlled by Settings.ai_provider (AI_PROVIDER in .env):
"fake" (the default) uses DevAIProvider — deterministic mock data, no
ANTHROPIC_API_KEY needed, no external call, safe for local development
even with --dry-run off. "claude" uses the real Anthropic provider and
requires ANTHROPIC_API_KEY. `--dry-run` itself is always fully offline
regardless of ai_provider — it never constructs any provider at all. See
backend/.env.example; the API server itself needs neither and boots fine
without them.
"""

import argparse
import json
import logging
import sys

from app.ai.enrichment import (
    DEFAULT_ENRICHMENT_LIMIT,
    ENRICHMENT_PROMPT_VERSION,
    MalformedEnrichmentError,
    apply_limit,
    enrich_content_item,
    ensure_model_supports_structured_output,
    select_items_needing_enrichment,
)
from app.ai.factory import get_ai_provider
from app.ai.provider import AIProviderConfigError, AIProviderError
from app.config import get_settings
from app.supabase_client import get_service_role_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("ingestion.enrich_content")

_CONTENT_ITEMS_COLUMNS = "id, content_type, title, description, updated_at"
_ENRICHMENTS_COLUMNS = "content_id, model, prompt_version, source_content_hash"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI-enrich content_items with a summary, skills, topics, "
        "and an optional experience level."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_ENRICHMENT_LIMIT,
        help=f"Max items to process this run (default {DEFAULT_ENRICHMENT_LIMIT}). "
        "0 means unlimited.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fully offline: select and print which items would be enriched, "
        "without constructing an AI provider, requiring ANTHROPIC_API_KEY, "
        "or making any network call to Claude. Writes nothing to the database.",
    )
    return parser.parse_args()


def run(*, limit: int, dry_run: bool) -> int:
    settings = get_settings()

    # Only meaningful for the real Claude provider — DevAIProvider (the
    # "fake" default) ignores Settings.ai_model entirely, so this check
    # would needlessly block local development with an unusual ai_model
    # value that was never going to reach a real API call anyway.
    if settings.ai_provider == "claude":
        try:
            ensure_model_supports_structured_output(settings.ai_model)
        except AIProviderConfigError as exc:
            logger.error("AI model configuration is invalid: %s", exc)
            return 1

    client = get_service_role_client()

    content_items = (
        client.table("content_items")
        .select(_CONTENT_ITEMS_COLUMNS)
        .eq("is_active", True)
        .execute()
        .data
    )
    existing_enrichments = (
        client.table("content_enrichments").select(_ENRICHMENTS_COLUMNS).execute().data
    )

    candidates = select_items_needing_enrichment(
        content_items,
        existing_enrichments,
        current_model=settings.ai_model,
        current_prompt_version=ENRICHMENT_PROMPT_VERSION,
    )
    candidates = apply_limit(candidates, limit)

    logger.info(
        "%d item(s) selected for enrichment (limit=%s)",
        len(candidates),
        limit if limit > 0 else "unlimited",
    )

    if not candidates:
        logger.info("Nothing to do.")
        return 0

    if dry_run:
        # Fully offline from here: no AIProvider is constructed, no
        # anthropic SDK client is initialized, ANTHROPIC_API_KEY is never
        # read, and no network call to Claude is made. Only confirms
        # which items are selected and would be sent for real enrichment.
        # summary/skills/topics/experience_level are genuinely unknown
        # without a real AI call, so they are printed as null rather than
        # fabricated — would_write reflects selection eligibility, not a
        # validated/guaranteed outcome.
        for item in candidates:
            print(
                json.dumps(
                    {
                        "content_id": item["id"],
                        "title": item["title"],
                        "summary": None,
                        "skills": None,
                        "topics": None,
                        "experience_level": None,
                        "would_write": True,
                    }
                )
            )
        logger.info(
            "Dry run complete: %d item(s) selected, no AI calls made, no database writes.",
            len(candidates),
        )
        return 0

    # Real run only from here — constructed only once real work exists.
    # get_ai_provider() returns DevAIProvider (fake, no key needed) or
    # ClaudeProvider (real) depending on Settings.ai_provider; the real
    # provider raises AIProviderConfigError immediately (before any
    # network call) if ANTHROPIC_API_KEY is unset.
    logger.info("Using AI provider: %s", settings.ai_provider)
    try:
        provider = get_ai_provider()
    except AIProviderConfigError as exc:
        logger.error("Failed to construct AI provider: %s", exc)
        return 1

    succeeded = 0
    failed = 0

    for item in candidates:
        content_id = item["id"]

        try:
            row = enrich_content_item(
                provider,
                content_id=content_id,
                content_type=item["content_type"],
                title=item["title"],
                description=item.get("description"),
            )
        except (AIProviderError, MalformedEnrichmentError) as exc:
            failed += 1
            logger.warning("Skipping content_id=%s: %s", content_id, exc)
            continue

        try:
            client.table("content_enrichments").upsert(row, on_conflict="content_id").execute()
        except Exception as exc:  # noqa: BLE001 - isolate this item's DB write
            # failure, same deliberately-broad reasoning as
            # persistence.py's upsert_normalized_items: a network hiccup
            # or constraint violation on one item must never abort the
            # rest of the batch.
            failed += 1
            logger.warning("Failed to write enrichment for content_id=%s: %s", content_id, exc)
            continue

        succeeded += 1

    logger.info("Enrichment complete: %d succeeded, %d failed", succeeded, failed)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    args = _parse_args()
    sys.exit(run(limit=args.limit, dry_run=args.dry_run))
