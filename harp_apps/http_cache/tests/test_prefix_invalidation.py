"""Invalidating a path prefix, and reclaiming the bans, through the storage on every records backend (ADR-0014)."""

import asyncio

import pytest

from harp_apps.http_cache.records import BanKind, BanMode
from harp_apps.http_cache.storages import AsyncStorage, InvalidationError
from harp_apps.http_cache.tests.test_invalidation import HOST, SlowOrigin, _until, make_client
from harp_apps.http_cache.tests.test_invalidation_log import ENDPOINT, ValidatedOrigin


@pytest.fixture
def storage(records):
    return AsyncStorage(records)


async def fetch_all(client, *paths):
    for path in paths:
        await client.get(f"{HOST}{path}")


@pytest.mark.asyncio
class TestPrefixInvalidation:
    async def test_the_path_and_what_is_under_it_are_fetched_again_and_nothing_else(self, storage):
        origin = ValidatedOrigin()
        paths = ["/api/users", "/api/users/42", "/api/users/42/posts", "/api/usersx", "/api/other", "/api"]
        async with make_client(origin, storage) as client:
            await fetch_all(client, *paths)
            origin.version = 2
            await storage.invalidate_prefix(ENDPOINT, "/api/users", mode=BanMode.HARD)

            texts = {path: (await client.get(f"{HOST}{path}")).text for path in paths}

        assert {path: text[:2] for path, text in texts.items()} == {
            "/api/users": "v2",
            "/api/users/42": "v2",
            "/api/users/42/posts": "v2",
            "/api/usersx": "v1",
            "/api/other": "v1",
            "/api": "v1",
        }

    async def test_a_trailing_slash_does_not_change_what_is_covered(self, storage):
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await fetch_all(client, "/api/users", "/api/users/42")
            await storage.invalidate_prefix(ENDPOINT, "/api/users/", mode=BanMode.HARD)
            await fetch_all(client, "/api/users", "/api/users/42")

        assert len(origin.requests) == 4

    async def test_a_query_is_covered_whatever_its_value(self, storage):
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await fetch_all(client, "/api/users?page=1", "/api/users?page=2")
            await storage.invalidate_prefix(ENDPOINT, "/api/users", mode=BanMode.HARD)
            await fetch_all(client, "/api/users?page=1", "/api/users?page=2")

        assert len(origin.requests) == 4

    async def test_both_schemes_are_covered(self, records, storage):
        await storage.invalidate_prefix(ENDPOINT, "/api/users", mode=BanMode.HARD)

        assert [(ban.kind, ban.prefix) for ban in await records.bans()] == [
            (BanKind.PREFIX, f"http://{ENDPOINT}/api/users"),
            (BanKind.PREFIX, f"https://{ENDPOINT}/api/users"),
        ]

    async def test_a_soft_prefix_ban_revalidates(self, storage):
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await fetch_all(client, "/api/users/42", "/api/other")
            await storage.invalidate_prefix(ENDPOINT, "/api/users", mode=BanMode.SOFT)
            await fetch_all(client, "/api/users/42", "/api/other")

        assert (len(origin.requests), origin.conditional) == (3, 1)

    @pytest.mark.parametrize("path", ["/", ""])
    async def test_the_root_is_the_endpoint(self, records, storage, path):
        await storage.invalidate_prefix(ENDPOINT, path, mode=BanMode.HARD)

        assert [ban.prefix for ban in await records.bans()] == [f"http://{ENDPOINT}/", f"https://{ENDPOINT}/"]

    @pytest.mark.parametrize("path", ["api", "/api?x=1", "/api#top", "/api\n", "/a pi"])
    async def test_a_path_that_is_not_one_is_refused_and_bans_nothing(self, records, storage, path):
        with pytest.raises(InvalidationError):
            await storage.invalidate_prefix(ENDPOINT, path, mode=BanMode.HARD)

        assert await records.bans() == []

    async def test_a_ban_that_cannot_be_recorded_is_an_invalidation_error(self, records, storage, monkeypatch):
        async def failing(*args):
            raise RuntimeError("database down")

        monkeypatch.setattr(records, "ban", failing)

        with pytest.raises(InvalidationError):
            await storage.invalidate_prefix(ENDPOINT, "/api", mode=BanMode.HARD)


@pytest.mark.asyncio
class TestReclamation:
    async def test_the_entries_a_ban_covers_are_deleted_and_the_ban_retired(self, records, storage):
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await fetch_all(client, "/api/users/1", "/api/users/2", "/api/other")
            await storage.invalidate_prefix(ENDPOINT, "/api/users", mode=BanMode.HARD)

            reclaimed = await storage.reclaim(grace=0)

        assert (reclaimed.retired, reclaimed.deleted) == (2, 2)
        assert await records.bans() == []
        assert await records.list_keys() == [f"http://{ENDPOINT}/api/other"]

    async def test_a_young_ban_is_kept_for_the_fills_that_may_still_be_in_flight(self, records, storage):
        await storage.invalidate_prefix(ENDPOINT, "/api/users", mode=BanMode.HARD)

        await storage.reclaim()

        assert len(await records.bans()) == 2

    async def test_a_run_goes_on_until_its_limits_are_met(self, records, storage, monkeypatch):
        monkeypatch.setattr("harp_apps.http_cache.storages.RECLAIM_ENTRIES", 2)
        monkeypatch.setattr("harp_apps.http_cache.storages.RECLAIM_ROUNDS", 3)
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await fetch_all(client, *(f"/api/users/{n}" for n in range(8)))
            await storage.invalidate_prefix(ENDPOINT, "/api/users", mode=BanMode.HARD)

            first = await storage.reclaim(grace=0)
            second = await storage.reclaim(grace=0)

        assert (first.deleted, first.pending) == (6, True)
        assert (second.deleted, second.pending) == (2, False)
        assert await records.bans() == []

    async def test_a_response_fetched_before_a_reclaimed_ban_does_not_come_back(self, records, storage):
        origin = SlowOrigin()
        async with make_client(origin, storage) as client:
            slow_get = asyncio.create_task(client.get(f"{HOST}/api/users/1"))
            await _until(lambda: origin.gets("/api/users/1") == 1)

            await storage.invalidate_prefix(ENDPOINT, "/api/users", mode=BanMode.HARD)
            await storage.reclaim(grace=0)
            assert await records.bans() == []
            origin.release.set()
            await slow_get

            origin.slow_paths.clear()
            await client.get(f"{HOST}/api/users/1")

        assert origin.gets("/api/users/1") == 2

    @pytest.mark.parametrize("ttl", [86400, None])
    async def test_without_a_janitor_the_storage_reclaims_in_its_own_sweep(self, records, monkeypatch, ttl):
        monkeypatch.setattr("harp_apps.http_cache.storages.BAN_GRACE", 0)
        storage = AsyncStorage(records, ttl=ttl, check_ttl_every=0)
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await fetch_all(client, "/api/users/1")
            await storage.wait_for_sweep()  # the one that store started, before the ban
            await storage.invalidate_prefix(ENDPOINT, "/api/users", mode=BanMode.HARD)

            await fetch_all(client, "/api/other")  # a store starts a sweep, when one is due
            await storage.wait_for_sweep()

        assert await records.bans() == []

    async def test_with_a_janitor_the_storage_leaves_reclaiming_to_it(self, records, monkeypatch):
        monkeypatch.setattr("harp_apps.http_cache.storages.BAN_GRACE", 0)
        storage = AsyncStorage(records, check_ttl_every=0)
        storage.reclaimed_by_janitor = True
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await storage.invalidate_prefix(ENDPOINT, "/api/users", mode=BanMode.HARD)

            await fetch_all(client, "/api/other")
            await storage.wait_for_sweep()

        assert len(await records.bans()) == 2

    async def test_a_soft_banned_entry_is_revalidated_not_lost_and_its_ban_retired_after(self, records, storage):
        origin = ValidatedOrigin()
        async with make_client(origin, storage) as client:
            await fetch_all(client, "/api/users/1")
            await storage.invalidate_prefix(ENDPOINT, "/api/users", mode=BanMode.SOFT)

            first = await storage.reclaim(grace=0)
            assert [ban.prefix for ban in await records.bans()] == [f"http://{ENDPOINT}/api/users"]
            await fetch_all(client, "/api/users/1")
            second = await storage.reclaim(grace=0)

        assert (first.retired, first.deleted) == (1, 0)  # the https one: nothing stale under it
        assert origin.conditional == 1
        assert second.retired == 1
        assert await records.bans() == []
