"""Unit tests for the generic upsert/dedup decision logic in
app.ingestion.persistence — no real database. A small fake client stands
in for just enough of the postgrest-py builder surface
(.table().select().eq().execute() and .table().upsert().execute()) to
exercise insert-vs-update counting and per-item failure isolation."""

from datetime import datetime, timezone

from app.ingestion.persistence import upsert_normalized_items
from app.ingestion.types import NormalizedContentItem


def _item(external_id: str) -> NormalizedContentItem:
    return NormalizedContentItem(
        external_id=external_id,
        source="arbeitnow",
        category="career",
        content_type="job",
        title=f"Job {external_id}",
        description=None,
        url=None,
        organization=None,
        location_city=None,
        location_region=None,
        location_country=None,
        is_remote=True,
        event_date=None,
        deadline=None,
        published_at=datetime.now(tz=timezone.utc),
    )


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    """Chainable stand-in supporting .select().eq().execute() and
    .upsert().execute() — the only two call shapes upsert_normalized_items
    actually uses."""

    def __init__(self, table: "FakeContentItemsTable"):
        self._table = table
        self._pending_upsert_row = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def upsert(self, row, on_conflict=None):
        assert on_conflict == "source,external_id"
        self._pending_upsert_row = row
        return self

    def execute(self):
        if self._pending_upsert_row is not None:
            row = self._pending_upsert_row
            if row["external_id"] in self._table.failing_external_ids:
                raise RuntimeError("simulated upsert failure")
            self._table.upserted_rows.append(row)
            return _FakeResult([row])
        return _FakeResult([{"external_id": eid} for eid in self._table.existing_external_ids])


class FakeContentItemsTable:
    def __init__(self, existing_external_ids=(), failing_external_ids=()):
        self.existing_external_ids = set(existing_external_ids)
        self.failing_external_ids = set(failing_external_ids)
        self.upserted_rows = []


class FakeClient:
    def __init__(self, existing_external_ids=(), failing_external_ids=()):
        self.content_items = FakeContentItemsTable(existing_external_ids, failing_external_ids)

    def table(self, name):
        assert name == "content_items"
        return _FakeQuery(self.content_items)


# ---- upsert_normalized_items ----------------------------------------------


def test_new_items_are_counted_as_inserted():
    client = FakeClient()
    result = upsert_normalized_items(client, "arbeitnow", [_item("job-a"), _item("job-b")])

    assert result.inserted == 2
    assert result.updated == 0
    assert result.failed == 0


def test_items_already_present_are_counted_as_updated():
    client = FakeClient(existing_external_ids={"job-a", "job-b"})
    result = upsert_normalized_items(client, "arbeitnow", [_item("job-a"), _item("job-b")])

    assert result.inserted == 0
    assert result.updated == 2


def test_rerunning_the_same_batch_is_idempotent_at_the_decision_level():
    # First run: both new.
    client = FakeClient()
    first = upsert_normalized_items(client, "arbeitnow", [_item("job-a"), _item("job-b")])
    assert first.inserted == 2

    # Second run against a client that now reflects those as existing:
    # both should be classified as updates, not duplicate inserts.
    client2 = FakeClient(existing_external_ids={"job-a", "job-b"})
    second = upsert_normalized_items(client2, "arbeitnow", [_item("job-a"), _item("job-b")])
    assert second.inserted == 0
    assert second.updated == 2


def test_mixed_new_and_existing_items_in_one_run():
    client = FakeClient(existing_external_ids={"job-a"})
    result = upsert_normalized_items(client, "arbeitnow", [_item("job-a"), _item("job-b")])

    assert result.updated == 1
    assert result.inserted == 1


def test_one_failing_item_does_not_abort_the_batch():
    client = FakeClient(failing_external_ids={"job-a"})
    result = upsert_normalized_items(client, "arbeitnow", [_item("job-a"), _item("job-b")])

    assert result.failed == 1
    assert result.failed_external_ids == ["job-a"]
    assert result.inserted == 1  # job-b still succeeded


def test_empty_items_list_is_a_no_op_and_skips_the_lookup_query():
    client = FakeClient()
    result = upsert_normalized_items(client, "arbeitnow", [])

    assert result.inserted == 0
    assert result.updated == 0
    assert result.failed == 0
    assert client.content_items.upserted_rows == []


def test_written_rows_always_carry_the_given_source():
    client = FakeClient()
    upsert_normalized_items(client, "arbeitnow", [_item("job-a")])

    assert client.content_items.upserted_rows[0]["source"] == "arbeitnow"
