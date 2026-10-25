"""The invalidation log every cache records backend keeps, on memory and on SQL alike (ADR-0014)."""

import asyncio

import pytest

from harp_apps.http_cache.records import Ban, BanKind, BanMode, ban_prefixes
from harp_apps.http_cache.tests.test_records import make_record, put

KEY = "http://api/items/1?abc"


def test_a_key_is_covered_by_everything_its_endpoint_each_directory_of_its_path_and_its_path():
    assert ban_prefixes("http://api/items/1?abc") == [
        "",
        "http://api/",
        "http://api/items",
        "http://api/items/",
        "http://api/items/1",
    ]


def test_the_query_hash_of_a_key_is_not_part_of_its_directories():
    assert ban_prefixes("http://api/a/b?x/y") == [
        "",
        "http://api/",
        "http://api/a",
        "http://api/a/",
        "http://api/a/b",
    ]


def test_a_key_without_path_is_covered_by_everything_and_its_endpoint():
    assert ban_prefixes("http://api") == ["", "http://api/"]


def test_a_path_ending_with_a_slash_is_not_listed_twice():
    assert ban_prefixes("http://api/items/") == ["", "http://api/", "http://api/items", "http://api/items/"]


async def test_the_counter_starts_at_zero(records):
    assert await records.counter() == 0


async def test_a_ban_takes_the_next_number_of_the_counter(records):
    first = await records.ban(BanKind.EXACT, KEY, BanMode.HARD)
    second = await records.ban(BanKind.PREFIX, "http://api/", BanMode.SOFT)

    assert (first.seq, second.seq) == (1, 2)
    assert (second.kind, second.prefix, second.mode) == (BanKind.PREFIX, "http://api/", BanMode.SOFT)
    assert isinstance(second, Ban)
    assert await records.counter() == 2


async def test_concurrent_bans_take_distinct_consecutive_numbers(records):
    bans = await asyncio.gather(*(records.ban(BanKind.PREFIX, "", BanMode.HARD) for _ in range(10)))

    assert sorted(ban.seq for ban in bans) == list(range(1, 11))
    assert await records.counter() == 10


async def test_a_hard_ban_makes_the_variants_stored_before_it_unusable(records):
    await put(records, make_record(KEY, stamp=0))
    await records.ban(BanKind.EXACT, KEY, BanMode.HARD)

    assert await records.get_variants(KEY) == []


async def test_a_hard_ban_leaves_alone_the_variants_stamped_after_it(records):
    ban = await records.ban(BanKind.EXACT, KEY, BanMode.HARD)
    record = await put(records, make_record(KEY, stamp=ban.seq))

    assert [stored for stored, _ in await records.get_variants(KEY)] == [record]


async def test_a_soft_ban_keeps_the_variants_but_makes_them_stale(records):
    await put(records, make_record(KEY, stamp=0))
    await records.ban(BanKind.EXACT, KEY, BanMode.SOFT)

    ((stored, body),) = await records.get_variants(KEY)

    assert stored.stale is True
    assert body == b"payload"


async def test_a_variant_is_not_stale_without_a_ban(records):
    await put(records, make_record(KEY))

    ((stored, _),) = await records.get_variants(KEY)

    assert stored.stale is False


async def test_a_variant_stored_again_after_a_soft_ban_is_fresh(records):
    await put(records, make_record(KEY, stamp=0))
    ban = await records.ban(BanKind.EXACT, KEY, BanMode.SOFT)
    await put(records, make_record(KEY, stamp=ban.seq))

    ((stored, _),) = await records.get_variants(KEY)

    assert stored.stale is False


async def test_a_hard_ban_wins_over_a_soft_one(records):
    await put(records, make_record(KEY, stamp=0))
    await records.ban(BanKind.EXACT, KEY, BanMode.SOFT)
    await records.ban(BanKind.EXACT, KEY, BanMode.HARD)

    assert await records.get_variants(KEY) == []


async def test_an_exact_ban_covers_its_key_only(records):
    other_query = await put(records, make_record("http://api/items/1?def"))
    other_path = await put(records, make_record("http://api/items/2?abc"))
    await put(records, make_record(KEY))

    await records.ban(BanKind.EXACT, KEY, BanMode.HARD)

    assert await records.get_variants(KEY) == []
    assert [stored for stored, _ in await records.get_variants(other_query.key)] == [other_query]
    assert [stored for stored, _ in await records.get_variants(other_path.key)] == [other_path]


async def test_a_prefix_ban_covers_the_keys_under_the_prefix(records):
    await put(records, make_record("http://api/items/1"))
    await put(records, make_record("http://api/items/deep/2"))
    outside = await put(records, make_record("http://api/other"))
    sibling = await put(records, make_record("http://api/itemsx"))

    await records.ban(BanKind.PREFIX, "http://api/items/", BanMode.HARD)

    assert await records.get_variants("http://api/items/1") == []
    assert await records.get_variants("http://api/items/deep/2") == []
    assert [stored for stored, _ in await records.get_variants(outside.key)] == [outside]
    assert [stored for stored, _ in await records.get_variants(sibling.key)] == [sibling]


async def test_an_endpoint_prefix_does_not_cover_an_endpoint_that_starts_the_same(records):
    await put(records, make_record("http://api/items"))
    neighbour = await put(records, make_record("http://api2/items"))

    await records.ban(BanKind.PREFIX, "http://api/", BanMode.HARD)

    assert await records.get_variants("http://api/items") == []
    assert [stored for stored, _ in await records.get_variants(neighbour.key)] == [neighbour]


async def test_the_empty_prefix_covers_everything(records):
    await put(records, make_record("http://api/items"))
    await put(records, make_record("https://other/items"))

    await records.ban(BanKind.PREFIX, "", BanMode.HARD)

    assert await records.get_variants("http://api/items") == []
    assert await records.get_variants("https://other/items") == []


async def test_a_variant_stamped_before_a_ban_is_refused(records):
    stamp = await records.counter()
    await records.ban(BanKind.EXACT, KEY, BanMode.HARD)

    stored = await records.put(make_record(KEY, stamp=stamp), b"payload", keep=8)

    assert stored is False
    assert await records.get_variants(KEY) == []
    assert await records.list_keys() == []
    assert await records.stats() == []


async def test_a_variant_stamped_before_a_soft_ban_is_refused_too(records):
    stamp = await records.counter()
    await records.ban(BanKind.PREFIX, "http://api/", BanMode.SOFT)

    assert await records.put(make_record(KEY, stamp=stamp), b"payload", keep=8) is False


async def test_a_variant_stamped_after_a_ban_is_stored(records):
    await records.ban(BanKind.EXACT, KEY, BanMode.HARD)

    stored = await records.put(make_record(KEY, stamp=await records.counter()), b"payload", keep=8)

    assert stored is True


async def test_a_ban_on_another_key_refuses_nothing(records):
    stamp = await records.counter()
    await records.ban(BanKind.EXACT, "http://api/other", BanMode.HARD)

    assert await records.put(make_record(KEY, stamp=stamp), b"payload", keep=8) is True


async def test_a_replacement_stamped_before_a_ban_is_refused_and_the_variant_stays(records):
    old = await put(records, make_record(KEY, stamp=0))
    await records.ban(BanKind.EXACT, KEY, BanMode.SOFT)

    refreshed = await records.put(make_record(KEY, stamp=0, body=b"new"), b"new", keep=8, replaces=old.entry_id)

    assert refreshed is False
    ((stored, body),) = await records.get_variants(KEY)
    assert (stored.entry_id, body) == (old.entry_id, b"payload")


async def test_a_fetch_that_started_before_a_ban_cannot_store_after_it(records):
    """Two concurrent tasks: one reads the counter and fetches, the other bans while it fetches."""
    fetching = asyncio.Event()
    banned = asyncio.Event()

    async def fetch_then_store():
        stamp = await records.counter()
        fetching.set()
        await banned.wait()
        return await records.put(make_record(KEY, stamp=stamp), b"stale", keep=8)

    async def ban_meanwhile():
        await fetching.wait()
        await records.ban(BanKind.EXACT, KEY, BanMode.HARD)
        banned.set()

    stored, _ = await asyncio.gather(fetch_then_store(), ban_meanwhile())

    assert stored is False
    assert await records.get_variants(KEY) == []


async def test_a_ban_racing_a_store_always_hides_what_the_fetch_stored(records):
    """Whichever of the store and the ban commits first, the entry of the earlier fetch is never served fresh."""
    for _ in range(20):
        await records.delete_key(KEY)
        stamp = await records.counter()
        await asyncio.gather(
            records.put(make_record(KEY, stamp=stamp), b"stale", keep=8),
            records.ban(BanKind.EXACT, KEY, BanMode.HARD),
        )

        assert await records.get_variants(KEY) == []


@pytest.mark.parametrize("mode", list(BanMode))
async def test_bans_survive_the_deletion_of_the_variants_they_cover(records, mode):
    await put(records, make_record(KEY, stamp=0))
    ban = await records.ban(BanKind.EXACT, KEY, mode)

    await records.delete_key(KEY)

    assert await records.put(make_record(KEY, stamp=0), b"payload", keep=8) is False
    assert await records.counter() == ban.seq


async def test_a_path_ban_covers_the_path_and_everything_under_it_cut_at_segments(records):
    await put(records, make_record("http://api/users"))
    await put(records, make_record("http://api/users?abc"))
    await put(records, make_record("http://api/users/42"))
    await put(records, make_record("http://api/users/42/posts?abc"))
    outside = await put(records, make_record("http://api/usersx"))
    other_scheme = await put(records, make_record("https://api/users/42"))

    await records.ban(BanKind.PREFIX, "http://api/users", BanMode.HARD)

    for key in ("http://api/users", "http://api/users?abc", "http://api/users/42", "http://api/users/42/posts?abc"):
        assert await records.get_variants(key) == [], key
    assert [stored for stored, _ in await records.get_variants(outside.key)] == [outside]
    assert [stored for stored, _ in await records.get_variants(other_scheme.key)] == [other_scheme]
