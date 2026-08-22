"""Generic persistence layer for the ingestion pipeline. Knows about
content_items and NormalizedContentItem — nothing about any specific
source. Reused unchanged by every future source adapter."""

from dataclasses import dataclass, field
from typing import List, Set

from supabase import Client

from app.ingestion.types import NormalizedContentItem


@dataclass
class IngestionResult:
    inserted: int = 0
    updated: int = 0
    failed: int = 0
    failed_external_ids: List[str] = field(default_factory=list)


def upsert_normalized_items(
    client: Client, source: str, items: List[NormalizedContentItem]
) -> IngestionResult:
    """Insert-or-update each item by (source, external_id).

    Each item is written independently (not one batch call) so a single
    failing row can't abort the whole run. Never touches rows belonging to
    a different source or to seed data — the conflict target is always
    (source, external_id), and every row this function writes carries the
    given source. Does not deactivate anything missing from this run —
    that's deliberately out of scope for this stage.
    """
    result = IngestionResult()

    if not items:
        return result

    existing = client.table("content_items").select("external_id").eq("source", source).execute()
    existing_ids: Set[str] = {row["external_id"] for row in existing.data if row.get("external_id")}

    for item in items:
        is_update = item.external_id in existing_ids

        try:
            client.table("content_items").upsert(
                item.to_row(),
                on_conflict="source,external_id",
            ).execute()
        except Exception:  # noqa: BLE001 - deliberately broad: any failure on
            # one item (network hiccup, constraint violation, etc.) must be
            # isolated and counted, never abort the rest of the batch.
            result.failed += 1
            result.failed_external_ids.append(item.external_id)
            continue

        if is_update:
            result.updated += 1
        else:
            result.inserted += 1

    return result
