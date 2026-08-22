-- Migration: add_content_items_external_id
-- Ingestion foundation: lets externally-sourced content_items rows be
-- safely upserted by (source, external_id) instead of duplicated on every
-- ingestion run. Seed rows are unaffected — they keep external_id = null,
-- and Postgres treats multiple NULLs in a unique constraint as
-- non-conflicting with each other, so no backfill is needed.

alter table public.content_items
  add column external_id text;

alter table public.content_items
  add constraint content_items_source_external_id_key
  unique (source, external_id);
