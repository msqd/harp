"""What only the SQL records have to get right: transactions, locks, and what is retried."""

import asyncio
import time
import uuid
from dataclasses import replace

import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError

from harp_apps.http_cache.models import CacheBody, CacheResource, CacheVariant
from harp_apps.http_cache.records import BanKind, BanMode, EndpointStats
from harp_apps.http_cache.records import sql as sql_module
from harp_apps.http_cache.records.sql import SqlCacheRecords, _is_concurrency
from harp_apps.http_cache.tests.test_records import make_record, put


@pytest.fixture
def sql_records(records):
    if not isinstance(records, SqlCacheRecords):
        pytest.skip("sql records only")
    return records


async def test_a_second_instance_cannot_bring_back_what_the_first_purged(sql_records):
    other = SqlCacheRecords(sql_records.engine)
    old = await put(sql_records)
    await other.delete_key(old.key)

    await sql_records.put(replace(old, stored_at=2000.0), b"fresher", keep=8, replaces=old.entry_id)

    assert await other.list_keys() == []


async def test_a_failed_write_changes_neither_counters_nor_bodies(sql_records, monkeypatch):
    first = await put(sql_records, make_record("http://api/a", body=b"kept"), b"kept")

    async def failing(*args, **kwargs):
        raise RuntimeError("boom after the rows were written")

    monkeypatch.setattr(SqlCacheRecords, "_forget", failing)
    with pytest.raises(RuntimeError):
        await put(sql_records, make_record("http://api/b", body=b"lost"), b"lost")
    monkeypatch.undo()

    assert await sql_records.list_keys() == [first.key]
    assert await sql_records.stats() == [EndpointStats("api", 1, 4)]
    assert len(await sql_records.body_digests()) == 1


async def test_a_duplicate_entry_id_raises_at_once(sql_records, monkeypatch):
    sleeps = []

    async def sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(sql_module.asyncio, "sleep", sleep)
    first = await put(sql_records, make_record("http://api/a"))

    with pytest.raises(IntegrityError):
        await put(sql_records, make_record("http://api/b", entry_id=first.entry_id))

    assert sleeps == []


async def test_a_foreign_key_race_is_the_one_integrity_error_that_is_retried(sql_records):
    async with sql_records.engine.connect() as conn:
        from sqlalchemy import insert

        record = make_record("http://api/a")
        with pytest.raises(IntegrityError) as foreign_key:
            await conn.execute(
                insert(CacheVariant).values(
                    **{name: getattr(record, name) for name in CacheVariant.__table__.columns.keys()}
                )
            )
        await conn.rollback()
    first = await put(sql_records, make_record("http://api/b"))
    with pytest.raises(IntegrityError) as duplicate:
        async with sql_records.engine.begin() as conn:
            other = make_record("http://api/b", variant="x", entry_id=first.entry_id)
            await conn.execute(
                insert(CacheVariant).values(**{n: getattr(other, n) for n in CacheVariant.__table__.columns.keys()})
            )

    assert _is_concurrency(foreign_key.value) is True
    assert _is_concurrency(duplicate.value) is False


@pytest.mark.parametrize("racer", ["sweep", "delete_key"])
async def test_a_put_racing_the_sweep_or_a_purge_neither_deadlocks_nor_drifts(sql_records, racer):
    for round_ in range(15):
        records = [
            put(
                sql_records,
                make_record("http://api/shared", variant=str(n), stored_at=1.0 + n, body=bytes([n + 1] * 3)),
            )
            for n in range(4)
        ]
        if racer == "sweep":
            records.append(sql_records.delete_stored_before(3.0, limit=100))
        else:
            records.append(sql_records.delete_key("http://api/shared"))
        await asyncio.gather(*records)

    stored = await sql_records.get_variants("http://api/shared")
    assert await sql_records.stats() == (
        [EndpointStats("api", len(stored), sum(r.body_size for r, _ in stored))] if stored else []
    )
    assert await sql_records.body_digests() == {r.body_digest for r, _ in stored}
    assert (await sql_records.list_keys() != []) == bool(stored)


async def test_get_by_id_of_unknown(sql_records):
    assert await sql_records.get_by_id(uuid.uuid4()) is None


@pytest.fixture
def postgres_records(sql_records):
    if sql_records.engine.dialect.name != "postgresql":
        pytest.skip("row locks: postgresql only")
    return sql_records


class TestReclamationAgainstFillsInFlight:
    """A fill that started before a ban may commit after the ban was reclaimed. It must not come back."""

    EVERYTHING = {"older_than": time.time() + 3600, "bans": 100, "entries": 100}

    @pytest.fixture
    def pausing_fill(self, monkeypatch):
        """Make the fills stop once written, just before they commit."""
        paused, release = asyncio.Event(), asyncio.Event()
        original = SqlCacheRecords._forget

        async def pausing(self, conn, removed, *, added=()):
            if added:
                paused.set()
                await release.wait()
            return await original(self, conn, removed, added=added)

        monkeypatch.setattr(SqlCacheRecords, "_forget", pausing)
        return paused, release

    async def create_the_floor(self, records):
        """Reclaim a first ban: the row of the floor then exists, and a reclamation waits on its lock, not on its birth."""
        await records.ban(BanKind.EXACT, "http://api/first", BanMode.HARD)
        await records.reclaim(**self.EVERYTHING)

    @pytest.mark.parametrize("floor_exists", [True, False])
    async def test_the_reclamation_waits_for_the_fill_and_deletes_what_it_stored(
        self, postgres_records, pausing_fill, floor_exists
    ):
        paused, release = pausing_fill
        if floor_exists:
            await self.create_the_floor(postgres_records)
        stamp = await postgres_records.counter()
        fill = asyncio.create_task(put(postgres_records, make_record("http://api/users/1", stamp=stamp)))
        await paused.wait()
        # the fill passed its own check, and the ban lands: only the lookup hides what the fill stores
        await postgres_records.ban(BanKind.PREFIX, "http://api/users", BanMode.HARD)

        reclaim = asyncio.create_task(postgres_records.reclaim(**self.EVERYTHING))
        await asyncio.sleep(0.5)
        waiting = not reclaim.done()
        release.set()
        await fill
        reclaimed = await reclaim

        assert waiting, "the fill in flight holds the floor"
        assert reclaimed.retired == 1 and reclaimed.deleted == 1
        assert await postgres_records.bans() == []
        assert await postgres_records.list_keys() == []
        assert await postgres_records.stats() == []

    async def test_fills_racing_the_reclamation_are_refused_or_deleted_never_left(self, postgres_records):
        for round_ in range(5):
            stamp = await postgres_records.counter()
            await postgres_records.ban(BanKind.PREFIX, "http://api/users", BanMode.HARD)
            fills = [
                put(
                    postgres_records,
                    make_record(f"http://api/users/{n}", body=bytes([n + 1]), stamp=stamp),
                    bytes([n + 1]),
                )
                for n in range(12)
            ]
            reclaims = [postgres_records.reclaim(**self.EVERYTHING) for _ in range(3)]

            await asyncio.gather(*fills, *reclaims)
            await postgres_records.reclaim(**self.EVERYTHING)

            assert await postgres_records.bans() == []
            assert await postgres_records.list_keys() == [], f"round {round_}"
            assert await postgres_records.stats() == []
            assert await postgres_records.body_digests() == set()

    async def test_the_orphans_of_a_crashed_writer_are_reclaimed(self, postgres_records):
        async with postgres_records.engine.begin() as conn:
            await conn.execute(insert(CacheBody).values(digest="orphan", data=b"x"))
            await conn.execute(insert(CacheResource).values(key="http://api/lost", endpoint="api"))
        kept = await put(postgres_records, make_record("http://api/kept"))

        assert await postgres_records.reclaim_orphans(limit=100) == 2
        assert await postgres_records.body_digests() == {kept.body_digest}
        assert await postgres_records.list_keys() == [kept.key]
