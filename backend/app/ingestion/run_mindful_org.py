"""Manual entry point for ingesting Mindful.org wellness articles into
content_items.

Run with (from backend/, venv active):

    python -m app.ingestion.run_mindful_org

Not wired to any scheduler — deliberately manual for this stage. Requires
SUPABASE_SERVICE_ROLE_KEY to be set (see backend/.env.example); the API
server itself does not need it and boots fine without it.
"""

import logging
import sys

from app.ingestion.persistence import upsert_normalized_items
from app.ingestion.sources.mindful_org import (
    MINDFUL_ORG_SOURCE,
    MalformedArticleError,
    fetch_mindful_org_items,
    is_premium_item,
    normalize_mindful_org_item,
)
from app.supabase_client import get_service_role_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("ingestion.mindful_org")


def run() -> int:
    try:
        raw_items = fetch_mindful_org_items()
    except Exception as exc:  # fetch/parse failure — nothing written to the DB yet
        logger.error("Failed to fetch Mindful.org RSS feed: %s", exc)
        return 1

    logger.info("Fetched %d items from Mindful.org", len(raw_items))

    eligible_items = [item for item in raw_items if not is_premium_item(item)]
    logger.info(
        "%d of %d items are eligible (non-premium)", len(eligible_items), len(raw_items)
    )

    normalized = []
    skipped = 0
    for item in eligible_items:
        try:
            normalized.append(normalize_mindful_org_item(item))
        except MalformedArticleError as exc:
            skipped += 1
            logger.warning("Skipping malformed item: %s", exc)

    logger.info("%d items normalized, %d skipped as malformed", len(normalized), skipped)

    client = get_service_role_client()
    result = upsert_normalized_items(client, MINDFUL_ORG_SOURCE, normalized)

    logger.info(
        "Ingestion complete: %d inserted, %d updated, %d failed",
        result.inserted,
        result.updated,
        result.failed,
    )
    if result.failed_external_ids:
        logger.warning("Failed external_ids: %s", result.failed_external_ids)

    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
