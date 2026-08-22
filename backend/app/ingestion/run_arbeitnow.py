"""Manual entry point for ingesting Arbeitnow remote jobs into
content_items.

Run with (from backend/, venv active):

    python -m app.ingestion.run_arbeitnow

Not wired to any scheduler — deliberately manual for this stage. Requires
SUPABASE_SERVICE_ROLE_KEY to be set (see backend/.env.example); the API
server itself does not need it and boots fine without it.
"""

import logging
import sys

from app.ingestion.persistence import upsert_normalized_items
from app.ingestion.sources.arbeitnow import (
    ARBEITNOW_SOURCE,
    MalformedJobError,
    fetch_arbeitnow_jobs,
    is_remote_job,
    normalize_arbeitnow_job,
)
from app.supabase_client import get_service_role_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("ingestion.arbeitnow")


def run() -> int:
    try:
        raw_jobs = fetch_arbeitnow_jobs()
    except Exception as exc:  # fetch failure — nothing written to the DB yet
        logger.error("Failed to fetch Arbeitnow jobs: %s", exc)
        return 1

    logger.info("Fetched %d jobs from Arbeitnow", len(raw_jobs))

    remote_jobs = [job for job in raw_jobs if is_remote_job(job)]
    logger.info("%d of %d jobs are remote", len(remote_jobs), len(raw_jobs))

    normalized = []
    skipped = 0
    for job in remote_jobs:
        try:
            normalized.append(normalize_arbeitnow_job(job))
        except MalformedJobError as exc:
            skipped += 1
            logger.warning("Skipping malformed job: %s", exc)

    logger.info("%d jobs normalized, %d skipped as malformed", len(normalized), skipped)

    client = get_service_role_client()
    result = upsert_normalized_items(client, ARBEITNOW_SOURCE, normalized)

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
