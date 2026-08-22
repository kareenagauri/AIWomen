"""Manual entry point for ingesting open, online Devpost hackathons into
content_items.

Run with (from backend/, venv active):

    python -m app.ingestion.run_devpost

Not wired to any scheduler — deliberately manual for this stage. Requires
SUPABASE_SERVICE_ROLE_KEY to be set (see backend/.env.example); the API
server itself does not need it and boots fine without it.
"""

import logging
import sys

from app.ingestion.persistence import upsert_normalized_items
from app.ingestion.sources.devpost import (
    DEVPOST_SOURCE,
    MalformedHackathonError,
    fetch_devpost_hackathons,
    is_online_hackathon,
    normalize_devpost_hackathon,
)
from app.supabase_client import get_service_role_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("ingestion.devpost")


def run() -> int:
    try:
        raw_hackathons = fetch_devpost_hackathons()
    except Exception as exc:  # fetch/pagination failure — nothing written to the DB yet
        logger.error("Failed to fetch Devpost hackathons: %s", exc)
        return 1

    logger.info("Fetched %d open hackathons from Devpost", len(raw_hackathons))

    online_hackathons = [h for h in raw_hackathons if is_online_hackathon(h)]
    logger.info("%d of %d hackathons are online", len(online_hackathons), len(raw_hackathons))

    normalized = []
    skipped = 0
    for hackathon in online_hackathons:
        try:
            normalized.append(normalize_devpost_hackathon(hackathon))
        except MalformedHackathonError as exc:
            skipped += 1
            logger.warning("Skipping malformed hackathon: %s", exc)

    logger.info("%d hackathons normalized, %d skipped as malformed", len(normalized), skipped)

    client = get_service_role_client()
    result = upsert_normalized_items(client, DEVPOST_SOURCE, normalized)

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
