"""Reclaiming what bans cover, then the bans, on memory and on SQL alike (ADR-0014, #1597)."""

import time

from harp_apps.http_cache.records import BanKind, BanMode, EndpointStats, Reclaimed
from harp_apps.http_cache.tests.test_records import make_record, put

#: Reclaim every ban, whatever its age.
NOW = {"older_than": time.time() + 3600, "bans": 100, "entries": 100}


async def keys_of(records, *keys):
    return [key for key in keys if await records.get_variants(key)]


async def test_a_hard_ban_is_retired_once_the_entries_it_covers_are_deleted(records):
    await put(records, make_record("http://api/users/1", body=b"one"), b"one")
    await put(records, make_record("http://api/users/2", body=b"two"), b"two")
    await records.ban(BanKind.PREFIX, "http://api/users", BanMode.HARD)

    reclaimed = await records.reclaim(**NOW)

    assert reclaimed == Reclaimed(retired=1, deleted=2, pending=False)
    assert await records.bans() == []
    assert await records.list_keys() == []
    assert await records.body_digests() == set()
    assert await records.stats() == []


async def test_what_a_ban_does_not_cover_is_kept(records):
    outside = await put(records, make_record("http://api/other", body=b"other"), b"other")
    sibling = await put(records, make_record("http://api/usersx", body=b"x"), b"x")
    await put(records, make_record("http://api/users/1", body=b"one"), b"one")
    ban = await records.ban(BanKind.PREFIX, "http://api/users", BanMode.HARD)
    after = await put(records, make_record("http://api/users/2", body=b"two", stamp=ban.seq), b"two")

    await records.reclaim(**NOW)

    assert await records.list_keys() == [outside.key, after.key, sibling.key]
    assert await records.stats() == [EndpointStats("api", 3, len(b"other") + len(b"two") + len(b"x"))]


async def test_an_exact_ban_deletes_its_key_only(records):
    await put(records, make_record("http://api/a?1"))
    other = await put(records, make_record("http://api/a?2"))
    await records.ban(BanKind.EXACT, "http://api/a?1", BanMode.HARD)

    await records.reclaim(**NOW)

    assert await records.list_keys() == [other.key]


async def test_everything_and_endpoint_bans_delete_by_range(records):
    await put(records, make_record("http://api/a"))
    await put(records, make_record("https://api/b"))
    survivor = await put(records, make_record("http://other/c"))
    await records.ban(BanKind.PREFIX, "http://api/", BanMode.HARD)
    await records.ban(BanKind.PREFIX, "https://api/", BanMode.HARD)

    await records.reclaim(**NOW)

    assert await records.list_keys() == [survivor.key]

    await records.ban(BanKind.PREFIX, "", BanMode.HARD)
    await records.reclaim(**NOW)

    assert await records.list_keys() == []
    assert await records.bans() == []


async def test_a_ban_younger_than_the_age_asked_is_left_alone(records):
    await put(records)
    await records.ban(BanKind.PREFIX, "http://api/", BanMode.HARD)

    reclaimed = await records.reclaim(older_than=time.time() - 3600, bans=100, entries=100)

    assert reclaimed == Reclaimed()
    assert len(await records.bans()) == 1
    assert len(await records.list_keys()) == 1


async def test_reclamation_is_batched_and_resumes_where_it_stopped(records):
    for n in range(5):
        await put(records, make_record(f"http://api/users/{n}", body=bytes([n + 1])), bytes([n + 1]))
    await records.ban(BanKind.PREFIX, "http://api/users", BanMode.HARD)

    first = await records.reclaim(older_than=NOW["older_than"], bans=100, entries=2)

    assert first == Reclaimed(retired=0, deleted=2, pending=True)
    assert len(await records.bans()) == 1
    assert len(await records.list_keys()) == 3

    second = await records.reclaim(older_than=NOW["older_than"], bans=100, entries=2)
    third = await records.reclaim(older_than=NOW["older_than"], bans=100, entries=2)

    assert (second, third) == (Reclaimed(0, 2, True), Reclaimed(retired=1, deleted=1, pending=False))
    assert await records.bans() == []
    assert await records.stats() == []


async def test_a_run_retires_at_most_the_bans_asked(records):
    for n in range(3):
        await records.ban(BanKind.EXACT, f"http://api/{n}", BanMode.HARD)

    reclaimed = await records.reclaim(older_than=NOW["older_than"], bans=2, entries=100)

    assert reclaimed == Reclaimed(retired=2, deleted=0, pending=True)
    assert [ban.prefix for ban in await records.bans()] == ["http://api/2"]


async def test_a_retired_ban_never_lets_a_covered_entry_come_back(records):
    """A fetch that started before the ban stores after the ban was reclaimed: it is refused."""
    stamp = await records.counter()
    await records.ban(BanKind.PREFIX, "http://api/users", BanMode.HARD)
    await records.reclaim(**NOW)
    assert await records.bans() == []

    stored = await records.put(make_record("http://api/users/1", stamp=stamp), b"payload", keep=8)

    assert stored is False
    assert await records.list_keys() == []
    assert await records.stats() == []


async def test_a_fetch_that_started_after_a_retired_ban_is_stored(records):
    await records.ban(BanKind.PREFIX, "http://api/users", BanMode.HARD)
    await records.reclaim(**NOW)

    stored = await records.put(make_record("http://api/users/1", stamp=await records.counter()), b"payload", keep=8)

    assert stored is True
    assert len(await records.get_variants("http://api/users/1")) == 1


async def test_a_soft_ban_keeps_its_entries_and_stays_while_one_is_stale(records):
    await put(records, make_record("http://api/users/1"))
    await records.ban(BanKind.PREFIX, "http://api/users", BanMode.SOFT)

    reclaimed = await records.reclaim(**NOW)

    assert reclaimed == Reclaimed()
    assert len(await records.bans()) == 1
    ((stored, _),) = await records.get_variants("http://api/users/1")
    assert stored.stale is True


async def test_a_soft_ban_is_retired_once_its_entries_are_revalidated(records):
    first = await put(records, make_record("http://api/users/1"))
    ban = await records.ban(BanKind.PREFIX, "http://api/users", BanMode.SOFT)
    # the revalidation: same entry, stamped with the fetch that asked the origin
    await put(records, make_record("http://api/users/1", stamp=ban.seq), replaces=first.entry_id)

    reclaimed = await records.reclaim(**NOW)

    assert reclaimed == Reclaimed(retired=1)
    assert await records.bans() == []
    ((stored, _),) = await records.get_variants("http://api/users/1")
    assert stored.stale is False


async def test_a_soft_ban_is_retired_once_its_entries_are_gone(records):
    first = await put(records, make_record("http://api/users/1"))
    await records.ban(BanKind.PREFIX, "http://api/users", BanMode.SOFT)
    await records.delete_entry(first.entry_id)

    assert (await records.reclaim(**NOW)).retired == 1


async def test_a_soft_ban_retired_does_not_let_a_fetch_that_started_before_it_store_a_fresh_entry(records):
    stamp = await records.counter()
    await records.ban(BanKind.PREFIX, "http://api/users", BanMode.SOFT)
    await records.reclaim(**NOW)

    assert await records.put(make_record("http://api/users/1", stamp=stamp), b"payload", keep=8) is False


async def test_an_entry_the_retired_bans_did_not_cover_is_still_freshened(records):
    old = await put(records, make_record("http://api/other", stamp=0))
    await records.ban(BanKind.PREFIX, "http://api/users", BanMode.HARD)
    await records.reclaim(**NOW)

    freshened = make_record("http://api/other", stamp=0, stored_at=2000.0)

    assert await records.put(freshened, b"payload", keep=8, replaces=old.entry_id) is True


async def test_an_older_ban_of_the_same_kind_prefix_and_mode_is_dropped_for_the_newer(records):
    await records.ban(BanKind.PREFIX, "http://api/users", BanMode.SOFT)
    await records.ban(BanKind.PREFIX, "http://api/users", BanMode.SOFT)
    await records.ban(BanKind.PREFIX, "http://api/users", BanMode.HARD)

    await records.reclaim(older_than=0, bans=100, entries=100)

    assert [(ban.seq, ban.mode) for ban in await records.bans()] == [(2, BanMode.SOFT), (3, BanMode.HARD)]


async def test_a_dropped_ban_still_covers_what_its_successor_covers(records):
    await put(records, make_record("http://api/users/1"))
    await records.ban(BanKind.PREFIX, "http://api/users", BanMode.SOFT)
    await records.ban(BanKind.PREFIX, "http://api/users", BanMode.SOFT)

    await records.reclaim(older_than=0, bans=100, entries=100)

    ((stored, _),) = await records.get_variants("http://api/users/1")
    assert stored.stale is True


async def test_nothing_to_reclaim(records):
    assert await records.reclaim(**NOW) == Reclaimed()
    assert await records.reclaim_orphans(limit=100) == 0
