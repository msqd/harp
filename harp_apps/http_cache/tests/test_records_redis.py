"""What is specific to the records in Redis: its layout, the expiry of bodies, the server it needs (ADR-0014, #1595)."""

import asyncio
import time

import pytest
from redis.asyncio import Redis

from harp.config import ConfigurationBuilder
from harp_apps.http_cache.records import BanKind, BanMode, digest_of
from harp_apps.http_cache.records import redis as redis_records
from harp_apps.http_cache.records.redis import RedisCacheRecords, UnsuitableRedis
from harp_apps.http_cache.tests.test_records import make_record, put


@pytest.fixture
def records(redis_client):
    return RedisCacheRecords(redis_client)


async def keys_of(client: Redis) -> set[str]:
    return {key.decode() async for key in client.scan_iter()}


async def test_a_variant_is_a_hash_and_its_resource_a_hash_of_variants(records, redis_client):
    record = await put(records, make_record("http://api/items", variant="v"))

    stored = await redis_client.hgetall(f"harp:cache:v:{record.entry_id}")
    assert stored[b"key"] == b"http://api/items"
    assert stored[b"body_digest"] == digest_of(b"payload").encode()
    assert await redis_client.hgetall("harp:cache:r:http://api/items") == {b"v": str(record.entry_id).encode()}


async def test_the_keys_of_an_endpoint_are_a_lex_sorted_set(records, redis_client):
    for key in ("http://api/b", "https://api/a", "http://api/a", "http://other/z"):
        await put(records, make_record(key))

    assert await redis_client.zrange("harp:cache:i:api", 0, -1, withscores=True) == [
        (b"http://api/a", 0.0),
        (b"http://api/b", 0.0),
        (b"https://api/a", 0.0),
    ]
    assert await redis_client.zrange("harp:cache:endpoints", 0, -1) == [b"api", b"other"]


async def test_keys_of_every_shape_are_listed(records):
    keys = ["http://api/a b", "http://api/*", "http://api/[x]?" + "0" * 64, "http://api/é", "http://api/"]
    for key in keys:
        await put(records, make_record(key))

    assert await records.list_keys() == sorted(keys, key=str.encode)


async def test_only_bodies_expire(records, redis_client):
    record = await put(records)
    await records.ban(BanKind.EXACT, record.key, BanMode.SOFT)

    ttls = {key: await redis_client.pttl(key) for key in await keys_of(redis_client)}

    expiring = {key for key, ttl in ttls.items() if ttl != -1}
    assert expiring == {f"harp:cache:b:{record.body_digest}", f"harp:cache:x:{record.body_digest}"}


async def test_a_body_is_kept_for_the_retention_after_a_variant_was_stored(redis_client):
    records = RedisCacheRecords(redis_client, retention=100)
    record = await put(records)

    assert 90_000 < await redis_client.pttl(f"harp:cache:b:{record.body_digest}") <= 100_000


async def test_a_variant_referring_to_a_body_extends_its_expiry_and_never_shortens_it(redis_client):
    long, short = RedisCacheRecords(redis_client, retention=1000), RedisCacheRecords(redis_client, retention=10)
    first = await put(short, make_record("http://api/1"))
    assert await redis_client.pttl(f"harp:cache:b:{first.body_digest}") <= 10_000

    await put(long, make_record("http://api/2"))
    assert await redis_client.pttl(f"harp:cache:b:{first.body_digest}") > 900_000

    await put(short, make_record("http://api/3"))
    assert await redis_client.pttl(f"harp:cache:b:{first.body_digest}") > 900_000


async def test_a_variant_whose_body_is_gone_is_not_served_and_is_deleted(records, redis_client):
    record = await put(records)
    await redis_client.delete(f"harp:cache:b:{record.body_digest}")  # evicted

    assert await records.get_variants(record.key) == []

    assert await records.list_keys() == []
    assert await records.stats() == []
    assert await records.get_by_id(record.entry_id) is None


async def test_a_body_nothing_refers_to_is_an_orphan(records, redis_client):
    await put(records, make_record("http://api/kept"))
    await redis_client.set(f"harp:cache:b:{digest_of(b'lost')}", b"lost")

    assert await records.reclaim_orphans(limit=100) == 1

    assert await records.body_digests() == {digest_of(b"payload")}


async def test_orphans_are_reclaimed_by_page(records, redis_client, monkeypatch):
    monkeypatch.setattr(redis_records, "ORPHAN_PAGE", 1)
    for n in range(3):
        await redis_client.set(f"harp:cache:b:orphan{n}", b"lost")

    reclaimed = sum([await records.reclaim_orphans(limit=100) for _ in range(30)])

    assert reclaimed == 3
    assert await records.body_digests() == set()


async def test_the_cache_leaves_the_keys_of_others_alone(records, redis_client):
    await redis_client.set("session:alice", "data")
    await redis_client.set("harp:blob:abc", "blob")
    await redis_client.set("b:abc", "body")
    await put(records)

    await records.reclaim_orphans(limit=100)
    await records.delete_stored_before(time.time(), limit=100)
    await records.ban(BanKind.PREFIX, "", BanMode.HARD)
    await records.reclaim(older_than=time.time() + 1, bans=10, entries=10)

    assert await redis_client.get("session:alice") == b"data"
    assert await redis_client.get("harp:blob:abc") == b"blob"
    assert await redis_client.get("b:abc") == b"body"


async def test_two_caches_in_one_redis_do_not_meet_when_their_prefix_differs(redis_client):
    one, other = RedisCacheRecords(redis_client, prefix="one:"), RedisCacheRecords(redis_client, prefix="o*:")
    await put(one)
    await other.ban(BanKind.PREFIX, "", BanMode.HARD)

    assert len(await one.get_variants("http://api/items")) == 1
    assert await other.get_variants("http://api/items") == []
    assert await other.body_digests() == set()


async def test_instances_share_the_log_and_the_records(redis_client):
    one, other = RedisCacheRecords(redis_client), RedisCacheRecords(redis_client)
    record = await put(one)

    ban = await other.ban(BanKind.EXACT, record.key, BanMode.HARD)

    assert await one.get_variants(record.key) == []
    assert await one.counter() == ban.seq == 1
    assert await one.bans() == [ban]


async def test_a_ban_is_numbered_in_the_order_it_commits(records):
    bans = await asyncio.gather(*(records.ban(BanKind.EXACT, f"http://api/{n}", BanMode.SOFT) for n in range(20)))

    assert sorted(ban.seq for ban in bans) == list(range(1, 21))
    assert [ban.seq for ban in await records.bans()] == list(range(1, 21))


async def test_a_ban_covering_many_keys_is_reclaimed_page_by_page(records, monkeypatch):
    monkeypatch.setattr(redis_records, "SCAN_PAGE", 3)
    for n in range(10):
        await put(records, make_record(f"http://api/users/{n}"))
    await put(records, make_record("http://api/other"))
    await records.ban(BanKind.PREFIX, "http://api/users", BanMode.HARD)

    reclaimed = await records.reclaim(older_than=time.time() + 1, bans=10, entries=100)

    assert (reclaimed.retired, reclaimed.deleted, reclaimed.pending) == (1, 10, False)
    assert await records.list_keys() == ["http://api/other"]


async def test_a_soft_ban_is_found_stuck_beyond_the_first_page(records, monkeypatch):
    monkeypatch.setattr(redis_records, "SCAN_PAGE", 2)
    for n in range(6):
        await put(records, make_record(f"http://api/users/{n}"))
    ban = await records.ban(BanKind.PREFIX, "http://api/users", BanMode.SOFT)
    for n in range(5):  # all but the last are freshened
        await put(records, make_record(f"http://api/users/{n}", stamp=ban.seq, variant="x"), keep=1)

    assert (await records.reclaim(older_than=time.time() + 1, bans=10, entries=100)).retired == 0


async def test_the_stats_survive_a_variant_lost_with_its_body(records, redis_client):
    first = await put(records, make_record("http://api/1", body=b"one"), b"one")
    await put(records, make_record("http://api/2", body=b"two"), b"two")
    await redis_client.delete(f"harp:cache:b:{first.body_digest}")

    await records.get_variants("http://api/1")

    assert [(s.entries, s.bytes) for s in await records.stats()] == [(1, 3)]


def test_a_client_that_decodes_responses_cannot_hold_bodies():
    with pytest.raises(ValueError, match="decode"):
        RedisCacheRecords(Redis(decode_responses=True))


class TestReady:
    """The server must not evict the invalidation log (ADR-0014)."""

    @pytest.fixture
    async def policy(self, redis_client):
        async def set_policy(name: str) -> None:
            await redis_client.config_set("maxmemory-policy", name)

        yield set_policy
        await set_policy("noeviction")

    async def build(self, redis_url):
        config = ConfigurationBuilder(
            {
                "applications": ["http_client", "http_cache", "storage"],
                "storage": {"blobs": {"type": "redis"}, "redis": {"url": redis_url}},
            },
            use_default_applications=False,
        )
        return await config.abuild_system(validate_dependencies=False)

    async def test_the_system_does_not_start_on_a_redis_that_evicts_any_key(self, policy, redis_url):
        await policy("allkeys-lru")

        with pytest.raises(UnsuitableRedis, match="allkeys-lru"):
            await self.build(redis_url)

    async def test_the_system_starts_on_a_redis_that_keeps_what_has_no_expiry(self, policy, redis_url):
        await policy("volatile-lru")

        system = await self.build(redis_url)

        await system.dispose()

    @pytest.mark.parametrize("name", ["noeviction", "volatile-lru", "volatile-lfu", "volatile-ttl", "volatile-random"])
    async def test_accepts_a_policy_that_keeps_what_has_no_expiry(self, records, policy, name):
        await policy(name)

        await records.ready()

    @pytest.mark.parametrize("name", ["allkeys-lru", "allkeys-lfu", "allkeys-random"])
    async def test_refuses_a_policy_that_evicts_any_key(self, records, policy, name):
        await policy(name)

        with pytest.raises(UnsuitableRedis, match=rf"maxmemory-policy '{name}'.*volatile-\*.*noeviction"):
            await records.ready()

    async def test_refuses_a_redis_without_the_script_expiry_options(self, records, monkeypatch):
        async def info(section):
            return {"redis_version": "6.2.14"}

        monkeypatch.setattr(records.client, "info", info)

        with pytest.raises(UnsuitableRedis, match="Redis 7.0 or later"):
            await records.ready()

    async def test_goes_on_when_the_server_does_not_tell_its_policy(self, records, monkeypatch, caplog):
        from redis.exceptions import ResponseError

        async def config_get(*args):
            raise ResponseError("unknown command 'CONFIG'")

        monkeypatch.setattr(records.client, "config_get", config_get)

        await records.ready()
