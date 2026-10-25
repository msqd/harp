"""What every cache records backend promises, on memory and on SQL alike (ADR-0014)."""

import asyncio
import uuid
from dataclasses import replace

import pytest

from harp_apps.http_cache.records import EndpointStats, VariantRecord, digest_of


def make_record(key="http://api/items", *, variant="", body=b"payload", stored_at=1000.0, **overrides) -> VariantRecord:
    fields = dict(
        key=key,
        variant=variant,
        entry_id=uuid.uuid4(),
        endpoint=key.split("/")[2],
        stamp=0,
        status=200,
        vary=None,
        body_digest=digest_of(body),
        body_size=len(body),
        created_at=stored_at,
        stored_at=stored_at,
        head=b"{}",
    )
    return VariantRecord(**{**fields, **overrides})


async def put(records, record=None, body=b"payload", *, keep=8, **kwargs):
    record = record or make_record(body=body)
    await records.put(record, body, keep=keep, **kwargs)
    return record


async def test_a_stored_variant_is_read_back_with_its_body(records):
    record = await put(records, make_record(body=b"hello"), b"hello")

    ((stored, body),) = await records.get_variants(record.key)

    assert stored == record
    assert body == b"hello"


async def test_an_unknown_key_holds_nothing(records):
    assert await records.get_variants("http://api/nothing") == []


async def test_a_variant_is_found_by_its_entry_id(records):
    record = await put(records)

    assert await records.get_by_id(record.entry_id) == record
    assert await records.get_by_id(uuid.uuid4()) is None


async def test_variants_of_a_key_come_oldest_stored_first(records):
    newest = await put(records, make_record(variant="b", stored_at=3.0))
    oldest = await put(records, make_record(variant="a", stored_at=1.0))
    middle = await put(records, make_record(variant="c", stored_at=2.0))

    stored = [record for record, _ in await records.get_variants(newest.key)]

    assert stored == [oldest, middle, newest]


async def test_a_variant_stored_again_replaces_the_one_it_supersedes(records):
    await put(records, make_record(variant="v", body=b"old"), b"old")
    replacement = await put(records, make_record(variant="v", body=b"new"), b"new")

    ((stored, body),) = await records.get_variants(replacement.key)

    assert stored == replacement
    assert body == b"new"


async def test_a_key_keeps_no_more_variants_than_asked_and_drops_the_oldest(records):
    for n in range(4):
        await put(records, make_record(variant=str(n), stored_at=float(n)), keep=3)

    variants = [record.variant for record, _ in await records.get_variants("http://api/items")]

    assert variants == ["1", "2", "3"]


async def test_a_variant_can_replace_another_by_entry_id(records):
    old = await put(records, make_record(variant="a", body=b"old"), b"old")
    renewed = replace(old, variant="b", stored_at=2.0)

    await records.put(renewed, b"new", keep=8, replaces=old.entry_id)

    assert [record for record, _ in await records.get_variants(old.key)] == [renewed]


async def test_a_variant_is_deleted_by_entry_id(records):
    kept = await put(records, make_record(variant="a"))
    dropped = await put(records, make_record(variant="b"))

    assert await records.delete_entry(dropped.entry_id) is True
    assert await records.delete_entry(dropped.entry_id) is False

    assert [record for record, _ in await records.get_variants(kept.key)] == [kept]


async def test_a_key_is_deleted_with_all_its_variants(records):
    await put(records, make_record(variant="a"))
    await put(records, make_record(variant="b"))
    other = await put(records, make_record("http://api/other"))

    assert await records.delete_key("http://api/items") == 2

    assert await records.get_variants("http://api/items") == []
    assert [record for record, _ in await records.get_variants(other.key)] == [other]


async def test_variants_stored_before_a_date_are_deleted(records):
    await put(records, make_record(variant="a", stored_at=1.0))
    fresh = await put(records, make_record(variant="b", stored_at=9.0))

    assert await records.delete_stored_before(5.0, limit=100) == 1

    assert [record for record, _ in await records.get_variants(fresh.key)] == [fresh]


async def test_expiry_deletes_by_batch(records):
    for n in range(5):
        await put(records, make_record(f"http://api/{n}", stored_at=1.0))

    assert await records.delete_stored_before(5.0, limit=2) == 2
    assert await records.delete_stored_before(5.0, limit=2) == 2
    assert await records.delete_stored_before(5.0, limit=2) == 1


async def test_keys_come_in_endpoint_then_path_order(records):
    for key in ("http://b/a", "http://a/z", "http://b/Z", "https://a/m", "http://a/a"):
        await put(records, make_record(key))

    # bytewise: "Z" sorts before "a"; and the endpoint comes before the scheme
    assert await records.list_keys() == ["http://a/a", "http://a/z", "https://a/m", "http://b/Z", "http://b/a"]


async def test_keys_are_listed_per_endpoint_and_by_page(records):
    for key in ("http://a/1", "http://a/2", "https://a/3", "http://b/1"):
        await put(records, make_record(key))

    first = await records.list_keys(endpoint="a", limit=2)
    second = await records.list_keys(endpoint="a", after=first[-1], limit=2)

    assert first == ["http://a/1", "http://a/2"]
    assert second == ["https://a/3"]


async def test_a_page_of_all_keys_continues_across_endpoints(records):
    for key in ("http://a/1", "http://a/2", "http://b/1"):
        await put(records, make_record(key))

    first = await records.list_keys(limit=2)
    second = await records.list_keys(after=first[-1], limit=2)

    assert (first, second) == (["http://a/1", "http://a/2"], ["http://b/1"])


async def test_a_key_listed_has_a_variant(records):
    first = await put(records, make_record("http://a/1"))
    await put(records, make_record("http://a/2"))
    await records.delete_key("http://a/2")

    assert await records.list_keys() == [first.key]


async def test_bodies_are_stored_once_whoever_carries_them(records):
    await put(records, make_record("http://a/1", body=b"same"), b"same")
    await put(records, make_record("http://a/2", body=b"same"), b"same")

    assert await records.body_digests() == {digest_of(b"same")}


async def test_a_shared_body_stays_while_a_record_references_it(records):
    first = await put(records, make_record("http://a/1", body=b"same"), b"same")
    second = await put(records, make_record("http://a/2", body=b"same"), b"same")

    await records.delete_entry(first.entry_id)

    ((_, body),) = await records.get_variants(second.key)
    assert body == b"same"
    assert await records.body_digests() == {digest_of(b"same")}


async def test_a_body_goes_with_its_last_record(records):
    first = await put(records, make_record("http://a/1", body=b"same"), b"same")
    second = await put(records, make_record("http://a/2", body=b"same"), b"same")

    await records.delete_entry(first.entry_id)
    await records.delete_key(second.key)

    assert await records.body_digests() == set()


async def test_a_body_goes_when_its_record_is_replaced_or_evicted_or_expired(records):
    await put(records, make_record(variant="v", body=b"replaced"), b"replaced")
    await put(records, make_record(variant="v", body=b"replacement"), b"replacement")
    assert await records.body_digests() == {digest_of(b"replacement")}

    await put(records, make_record(variant="w", body=b"newest", stored_at=2000.0), b"newest", keep=1)
    assert await records.body_digests() == {digest_of(b"newest")}

    await records.delete_stored_before(3000.0, limit=10)
    assert await records.body_digests() == set()


async def test_counters_follow_the_writes_per_endpoint(records):
    first = await put(records, make_record("http://a/1", body=b"12345"), b"12345")
    await put(records, make_record("http://a/2", body=b"123"), b"123")
    await put(records, make_record("http://b/1", body=b"1"), b"1")

    assert await records.stats() == [EndpointStats("a", 2, 8), EndpointStats("b", 1, 1)]

    await put(records, make_record("http://a/1", body=b"1234567890"), b"1234567890")
    assert await records.stats() == [EndpointStats("a", 2, 13), EndpointStats("b", 1, 1)]

    await records.delete_entry(first.entry_id)  # already replaced above: nothing more to count
    await records.delete_key("http://a/2")
    assert await records.stats() == [EndpointStats("a", 1, 10), EndpointStats("b", 1, 1)]


async def test_an_endpoint_with_nothing_left_has_no_counters(records):
    record = await put(records, make_record("http://a/1"))
    await records.delete_entry(record.entry_id)

    assert await records.stats() == []


async def test_counters_follow_eviction_and_expiry(records):
    await put(records, make_record(variant="a", body=b"aa", stored_at=1.0), b"aa", keep=1)
    await put(records, make_record(variant="b", body=b"bbb", stored_at=2.0), b"bbb", keep=1)
    assert await records.stats() == [EndpointStats("api", 1, 3)]

    await records.delete_stored_before(10.0, limit=10)
    assert await records.stats() == []


async def test_the_largest_entries_come_biggest_first(records):
    await put(records, make_record("http://a/small", body=b"1"), b"1")
    await put(records, make_record("http://a/large", body=b"1" * 30), b"1" * 30)
    await put(records, make_record("http://b/medium", body=b"1" * 10), b"1" * 10)

    assert [record.key for record in await records.largest(limit=2)] == ["http://a/large", "http://b/medium"]
    assert [record.key for record in await records.largest(endpoint="b")] == ["http://b/medium"]


async def test_the_stamp_is_kept_on_the_record(records):
    """Reserved: the invalidation counter read before the fetch (#1596)."""
    record = await put(records, make_record(stamp=42))

    assert (await records.get_by_id(record.entry_id)).stamp == 42


async def test_writers_of_one_variant_leave_one_variant_and_exact_counters(records):
    bodies = [bytes([65 + n]) * (n + 1) for n in range(10)]

    await asyncio.gather(*(put(records, make_record(variant="v", body=body), body) for body in bodies))

    ((record, body),) = await records.get_variants("http://api/items")
    assert body in bodies
    assert await records.stats() == [EndpointStats("api", 1, len(body))]
    assert await records.body_digests() == {record.body_digest}


@pytest.mark.parametrize("size", [0, 1])
async def test_an_empty_body_is_a_body(records, size):
    record = await put(records, make_record(body=b"x" * size), b"x" * size)

    ((_, body),) = await records.get_variants(record.key)
    assert body == b"x" * size


async def test_a_variant_purged_since_it_was_read_does_not_come_back(records):
    """The copy being written (a 304 freshening, say) predates the purge."""
    old = await put(records)
    await records.delete_key(old.key)

    await records.put(replace(old, stored_at=2000.0), b"fresher", keep=8, replaces=old.entry_id)

    assert await records.list_keys() == []
    assert await records.stats() == []
    assert await records.body_digests() == set()


async def test_a_variant_replaced_since_it_was_read_is_not_overwritten(records):
    old = await put(records, make_record(variant="v", body=b"old"), b"old")
    current = await put(records, make_record(variant="v", body=b"current"), b"current")

    await records.put(replace(old, stored_at=2000.0), b"stale", keep=8, replaces=old.entry_id)

    assert [(r, b) for r, b in await records.get_variants(old.key)] == [(current, b"current")]
    assert await records.stats() == [EndpointStats("api", 1, len(b"current"))]


async def test_responses_refused_are_counted_per_endpoint(records):
    await records.count_refused("api")
    await records.count_refused("api")
    await records.count_refused("web")
    await put(records, make_record("http://web/x", body=b"1"), b"1")

    assert await records.stats() == [EndpointStats("api", 0, 0, 2), EndpointStats("web", 1, 1, 1)]

    await records.delete_key("http://web/x")
    assert await records.stats() == [EndpointStats("api", 0, 0, 2), EndpointStats("web", 0, 0, 1)]


async def test_the_query_kept_for_display_is_read_back(records):
    record = await put(records, make_record(query="a=REDACTED&b=1"))

    assert (await records.get_by_id(record.entry_id)).query == "a=REDACTED&b=1"
