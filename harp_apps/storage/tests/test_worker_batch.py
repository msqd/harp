import asyncio
from types import SimpleNamespace

import pytest
from prometheus_client import REGISTRY
from sqlalchemy import func, select, text
from whistle import AsyncEventDispatcher

from harp_apps.storage.models import Tag, TagValue
from harp_apps.storage.tests.test_worker_write_once import (
    Recording,
    end,
    messages,
    new_transaction,
    one_commit_only,
    start,
)
from harp_apps.storage.worker import StorageAsyncWorkerQueue


def make_worker(sql_storage, sql_blob_storage, **settings):
    worker = StorageAsyncWorkerQueue(sql_storage.engine, sql_storage, sql_blob_storage, **settings)
    worker.dispatcher = AsyncEventDispatcher()
    worker.register_events(worker.dispatcher)
    return worker


async def count(sql_storage) -> int:
    async with sql_storage.engine.connect() as conn:  # a plain read: no commit to confuse the recording
        return (await conn.execute(text("SELECT count(*) FROM transactions"))).scalar_one()


async def run(worker, transaction, **kwargs):
    await start(worker, transaction)
    await messages(worker, transaction, **kwargs)
    await end(worker, transaction)


def failures() -> float:
    return REGISTRY.get_sample_value("storage_flush_failures_total") or 0.0


async def test_ended_transactions_wait_for_the_flush_interval_then_go_together(sql_storage, sql_blob_storage):
    one_commit_only(sql_storage)
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=0.3, early_insert_after=60)
    recording = Recording(sql_storage.engine)
    try:
        for _ in range(3):
            await run(worker, new_transaction())
        await asyncio.sleep(0.1)
        assert await count(sql_storage) == 0

        await asyncio.sleep(0.5)
        assert await count(sql_storage) == 3
        assert recording.commits == 1
    finally:
        await worker.close()


async def test_a_full_batch_is_flushed_without_waiting(sql_storage, sql_blob_storage):
    one_commit_only(sql_storage)
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=60, flush_batch_size=2, early_insert_after=60)
    recording = Recording(sql_storage.engine)
    try:
        await run(worker, new_transaction())
        await asyncio.sleep(0.1)
        assert await count(sql_storage) == 0

        await run(worker, new_transaction())
        await asyncio.sleep(0.3)
        assert await count(sql_storage) == 2
        assert recording.commits == 1
    finally:
        await worker.close()


async def test_closing_flushes_what_is_pending(sql_storage, sql_blob_storage):
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=60, early_insert_after=60)
    for _ in range(2):
        await run(worker, new_transaction())

    await worker.close()

    assert await count(sql_storage) == 2


async def test_waiting_until_empty_flushes_what_ended(sql_storage, sql_blob_storage):
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=60, early_insert_after=60)
    try:
        await run(worker, new_transaction())
        await worker.wait_until_empty()
        assert await count(sql_storage) == 1
    finally:
        await worker.close()


async def test_open_transactions_are_inserted_with_the_batch(sql_storage, sql_blob_storage):
    one_commit_only(sql_storage)
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=0.3, early_insert_after=0.05)
    recording = Recording(sql_storage.engine)
    try:
        open_ = new_transaction()
        await start(worker, open_)
        await messages(worker, open_)
        await run(worker, new_transaction())
        await asyncio.sleep(0.6)

        assert recording.commits == 1
        rows = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        assert len(rows) == 2
        assert {t.finished_at is None for t in rows} == {True, False}
    finally:
        await worker.close()


async def test_silent_transactions_are_forgotten_by_the_sweep(sql_storage, sql_blob_storage):
    worker = make_worker(
        sql_storage, sql_blob_storage, flush_interval=0.1, early_insert_after=0.05, pending_max_age=0.3
    )
    try:
        transaction = new_transaction()
        await start(worker, transaction)
        await asyncio.sleep(0.8)
        assert transaction.id not in worker._pending
    finally:
        await worker.close()


async def test_tags_of_a_batch_are_written_in_its_database_transaction(sql_storage, sql_blob_storage):
    one_commit_only(sql_storage)
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=60, early_insert_after=60)
    recording = Recording(sql_storage.engine)
    try:
        first, second, untagged = new_transaction(), new_transaction(), new_transaction()
        first.tags = {"env": "prod", "team": "a"}
        second.tags = {"env": "prod", "team": "b"}
        for transaction in (first, second, untagged):
            await run(worker, transaction)
        await worker.wait_until_empty()

        assert recording.commits == 1
        rows = {t.id: t for t in await sql_storage.get_transaction_list(username="anonymous", with_messages=True)}
        assert rows[first.id].tags == {"env": "prod", "team": "a"}
        assert rows[second.id].tags == {"env": "prod", "team": "b"}
        assert rows[untagged.id].tags == {}
        async with sql_storage.engine.connect() as conn:
            assert (await conn.execute(select(func.count()).select_from(Tag))).scalar_one() == 2
            assert (await conn.execute(select(func.count()).select_from(TagValue))).scalar_one() == 3
    finally:
        await worker.close()


async def test_tags_reuse_what_is_already_stored(sql_storage, sql_blob_storage):
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=60, early_insert_after=60)
    try:
        for _ in range(2):
            transaction = new_transaction()
            transaction.tags = {"env": "prod"}
            await run(worker, transaction)
            await worker.wait_until_empty()
        async with sql_storage.engine.connect() as conn:
            assert (await conn.execute(select(func.count()).select_from(TagValue))).scalar_one() == 1
    finally:
        await worker.close()


async def test_a_failed_batch_is_counted_and_costs_only_the_bad_transaction(sql_storage, sql_blob_storage):
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=60, early_insert_after=60)
    try:
        bad, good = new_transaction(), new_transaction()
        await run(worker, bad)
        await worker.wait_until_empty()  # `bad` is stored
        before = failures()

        await run(worker, new_transaction())
        again = new_transaction()
        again.id = bad.id  # same primary key: the insert fails
        await run(worker, again)
        await run(worker, good)
        await worker.wait_until_empty()

        assert failures() == before + 2  # the batch, then the bad transaction alone
        assert await count(sql_storage) == 3  # bad, and the two others, written one by one after the failed batch
    finally:
        await worker.close()


async def test_the_proxy_is_never_blocked_by_a_failing_database(sql_storage, sql_blob_storage, monkeypatch):
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=60, early_insert_after=60)

    def broken(*args, **kwargs):
        raise RuntimeError("database down")

    monkeypatch.setattr(worker, "engine", SimpleNamespace(begin=broken, dialect=sql_storage.engine.dialect))
    try:
        await run(worker, new_transaction())
        await worker.wait_until_empty()
        assert failures() > 0
    finally:
        await worker.close()


async def test_waiting_for_the_flush_interval_is_not_pressure(sql_storage, sql_blob_storage):
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=60, early_insert_after=60)
    try:
        for _ in range(300):
            await run(worker, new_transaction())
        worker.cleanup()
        assert worker.pressure == 0
    finally:
        await worker.close()


async def test_pressure_is_what_ended_while_the_writer_was_busy(sql_storage, sql_blob_storage):
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=60, early_insert_after=60)
    release = asyncio.Event()
    original = worker._write

    async def slow_write(pendings):
        await release.wait()
        return await original(pendings)

    worker._write = slow_write
    try:
        await run(worker, new_transaction())
        worker._schedule_flush()
        await asyncio.sleep(0.05)  # the writer holds the first one
        for _ in range(150):
            await run(worker, new_transaction())
        assert worker._pressure == 150
        assert worker.pressure == 2  # bodies are shed from here

        release.set()
        await worker.wait_until_empty()
        assert worker._pressure == 0
    finally:
        release.set()
        await worker.close()


async def test_a_big_batch_is_written_in_chunks_of_one_database_transaction(sql_storage, sql_blob_storage):
    one_commit_only(sql_storage)
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=60, early_insert_after=60)
    recording = Recording(sql_storage.engine)
    try:
        for i in range(120):
            await run(worker, new_transaction(), request_body=b"request %d" % i)
        await worker.wait_until_empty()

        assert recording.commits == 1
        assert recording.statements.count("INSERT") >= 7  # 120 rows, 240 messages and ~120 blobs, 100 per statement
        assert await count(sql_storage) == 120
    finally:
        await worker.close()


async def test_the_bytes_of_a_batch_are_given_back_when_it_commits(sql_storage, sql_blob_storage):
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=60, early_insert_after=60)
    try:
        for _ in range(3):
            await run(worker, new_transaction(), request_body=b"x" * 500)
        assert worker._pending_bytes >= 1500

        await worker.wait_until_empty()

        assert worker._pending_bytes == 0
    finally:
        await worker.close()


async def test_the_bytes_of_a_batch_that_cannot_be_written_are_given_back(sql_storage, sql_blob_storage, monkeypatch):
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=60, early_insert_after=60)

    def broken(*args, **kwargs):
        raise RuntimeError("database down")

    monkeypatch.setattr(worker, "engine", SimpleNamespace(begin=broken, dialect=sql_storage.engine.dialect))
    try:
        for _ in range(3):
            await run(worker, new_transaction(), request_body=b"x" * 500)
        await worker.wait_until_empty()  # ended entries are not retried: nothing will write them again

        assert worker._pending_bytes == 0
    finally:
        await worker.close()


async def test_an_open_transaction_keeps_its_bytes_when_the_early_insert_fails(
    sql_storage, sql_blob_storage, monkeypatch
):
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=60, early_insert_after=0)

    def broken(*args, **kwargs):
        raise RuntimeError("database down")

    try:
        open_ = new_transaction()
        await start(worker, open_)
        await messages(worker, open_, request_body=b"x" * 500)
        held = worker._pending_bytes
        assert held >= 500

        monkeypatch.setattr(worker, "engine", SimpleNamespace(begin=broken, dialect=sql_storage.engine.dialect))
        await worker.wait_until_empty()  # the sweep tries to insert it: fails, it stays for its end
        monkeypatch.undo()
        assert worker._pending_bytes == held
    finally:
        await worker.close()


async def test_flushes_are_reported_to_the_loop_probe(sql_storage, sql_blob_storage, monkeypatch, tmp_path):
    from harp.utils import loop_probe

    monkeypatch.setenv(loop_probe.ENV, str(tmp_path / "probe.jsonl"))
    probe = loop_probe.start_from_environment()
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=0.05, early_insert_after=60)
    try:
        for _ in range(3):
            await run(worker, new_transaction())
        await asyncio.sleep(0.2)
        await worker.wait_until_empty()
    finally:
        await worker.close()
        loop_probe.stop()

    flushes = [e for e in probe.events if e["k"] == "flush"]
    assert sum(f["transactions"] for f in flushes) == 3
    assert sum(f["messages"] for f in flushes) == 6
    assert all(f["ms"] > 0 and f["cpu_ms"] >= 0 for f in flushes)
    assert any(f["wait_ms"] is not None for f in flushes)


async def test_nothing_is_recorded_without_the_probe(sql_storage, sql_blob_storage):
    from harp.utils import loop_probe

    assert loop_probe.current() is None
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=0.05, early_insert_after=60)
    try:
        await run(worker, new_transaction())
        await worker.wait_until_empty()
        assert await count(sql_storage) == 1
    finally:
        await worker.close()


async def test_ticks_are_jittered_around_the_interval(sql_storage, sql_blob_storage):
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=1.0, early_insert_after=60)
    try:
        delays = [worker._next_delay() for _ in range(500)]
        assert len(set(delays)) > 100  # not one fixed period: it must not lock onto a periodic load
        assert min(delays) >= 0.9 and max(delays) <= 1.1
        assert 0.98 < sum(delays) / len(delays) < 1.02
    finally:
        await worker.close()


async def test_every_tick_rearms_with_its_own_delay(sql_storage, sql_blob_storage, monkeypatch):
    worker = make_worker(sql_storage, sql_blob_storage, flush_interval=60, early_insert_after=60)
    try:
        monkeypatch.setattr(worker, "_next_delay", lambda: 0.123)
        worker._tick()
        loop = asyncio.get_running_loop()
        assert worker._tick_handle.when() - loop.time() == pytest.approx(0.123, abs=0.02)
    finally:
        await worker.close()


async def test_the_first_tick_is_jittered_too(sql_storage, sql_blob_storage):
    # Started with a fixed delay, every worker would tick on the same phase of its second.
    delays = []
    for _ in range(20):
        worker = make_worker(sql_storage, sql_blob_storage, flush_interval=10.0, early_insert_after=60)
        delays.append(worker._tick_handle.when() - asyncio.get_running_loop().time())
        await worker.close()
    assert len({round(d, 2) for d in delays}) > 5
