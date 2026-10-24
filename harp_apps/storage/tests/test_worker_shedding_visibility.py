import asyncio
import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from prometheus_client import REGISTRY
from whistle import AsyncEventDispatcher

from harp.http import HttpRequest
from harp.models import Transaction
from harp.utils.guids import generate_transaction_id_ksuid
from harp_apps.proxy.events import (
    EVENT_TRANSACTION_MESSAGE,
    EVENT_TRANSACTION_STARTED,
    HttpMessageEvent,
    TransactionEvent,
)
from harp_apps.storage.worker import DROPPED_KINDS, StorageAsyncWorkerQueue


def dropped(kind: str) -> float:
    return REGISTRY.get_sample_value("dropped_total", {"kind": kind}) or 0.0


class Clock:
    """Stands in for the event loop clock, so a hold is tested without sleeping."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float):
        self.now += seconds


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
async def worker(clock):
    worker = StorageAsyncWorkerQueue(MagicMock(), AsyncMock(), AsyncMock())
    worker.clock = clock
    worker.dispatcher = AsyncEventDispatcher()
    worker.register_events(worker.dispatcher)
    yield worker
    await worker.close()


@pytest.fixture
async def stall(worker):
    """Returns a coroutine function that queues an item blocking the consumer until the event it returns is set.

    Every stall is released at teardown, so a failing test does not hang the worker's close.
    """
    releases = []

    async def queue_stall(on_start=None) -> asyncio.Event:
        release = asyncio.Event()

        async def stalled():
            if on_start:
                on_start.set()
            await release.wait()

        await worker.push(stalled)
        releases.append(release)
        return release

    yield queue_stall
    for release in releases:
        release.set()


async def fill(worker, size: int):
    """Queues ``size`` items that do nothing."""

    async def noop():
        pass

    for _ in range(size):
        await worker.push(noop)


@pytest.fixture
def backlog(worker, stall, clock):
    """Returns a coroutine function that stalls the consumer and queues ``size`` items behind it.

    The backlog is held for the pressure hold unless ``held=False``.
    """

    async def build(size: int, *, held: bool = True):
        await stall()
        await asyncio.sleep(0)  # consumer is now stuck on the first item
        await fill(worker, size)
        if held:
            clock.advance(worker.pressure_hold)

    return build


def backlog_gauge(worker) -> float:
    return REGISTRY.get_sample_value("async_worker_queue_backlog", {"queue_id": str(id(worker))})


def new_transaction() -> Transaction:
    return Transaction(id=generate_transaction_id_ksuid(), type="http", endpoint="/test", started_at=datetime.now(UTC))


async def start(worker, transaction):
    await worker.dispatcher.adispatch(EVENT_TRANSACTION_STARTED, TransactionEvent(transaction=transaction))


async def message(worker, transaction):
    event = HttpMessageEvent(transaction=transaction, message=HttpRequest(method="GET", path="/", body=b"x"))
    await worker.dispatcher.adispatch(EVENT_TRANSACTION_MESSAGE, event)


async def test_dropped_transactions_are_counted_and_warned(worker, backlog, caplog):
    await backlog(10_000)
    before = dropped("transactions")

    with caplog.at_level(logging.WARNING):
        await start(worker, new_transaction())

    assert dropped("transactions") == before + 1
    assert "transactions=1" in caplog.text


async def test_dropped_messages_are_counted(worker, backlog):
    await backlog(1000)
    before = dropped("messages")
    transaction = new_transaction()

    await start(worker, transaction)
    await message(worker, transaction)

    assert dropped("messages") == before + 1


async def test_dropped_bodies_are_counted_without_headers(worker, backlog):
    await backlog(100)
    before_bodies, before_headers = dropped("bodies"), dropped("headers")
    transaction = new_transaction()

    await message(worker, transaction)

    assert dropped("bodies") == before_bodies + 1
    assert dropped("headers") == before_headers


async def test_dropped_headers_are_counted(worker, monkeypatch):
    # Not reachable with integer pressure today (messages go first, at >= 3): force the branch.
    monkeypatch.setattr(StorageAsyncWorkerQueue, "pressure", 2.5)
    before = dropped("headers")

    await message(worker, new_transaction())

    assert dropped("headers") == before + 1


async def test_warning_is_periodic_and_carries_counts_since_last_warning(worker, backlog, caplog, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("harp_apps.storage.worker.monotonic", lambda: clock[0])
    await backlog(10_000)

    with caplog.at_level(logging.WARNING):
        await start(worker, new_transaction())  # first drop warns right away
        await start(worker, new_transaction())  # within the interval: silent
        await start(worker, new_transaction())
        assert caplog.text.count("transactions=") == 1

        clock[0] += worker.shed_warning_interval
        await start(worker, new_transaction())

    assert caplog.text.count("transactions=") == 2
    assert "transactions=3" in caplog.text


async def test_pressure_follows_pushes_while_consumer_is_stalled(worker, backlog):
    await backlog(100)

    before = dropped("bodies")
    await message(worker, new_transaction())

    assert worker.pressure >= 2
    assert dropped("bodies") == before + 1
    assert backlog_gauge(worker) >= 100


async def test_burst_drained_within_the_hold_is_recorded_in_full(worker, backlog, clock):
    await backlog(10_000, held=False)
    clock.advance(1.9)
    before = {kind: dropped(kind) for kind in DROPPED_KINDS}
    transaction = new_transaction()

    await start(worker, transaction)
    await message(worker, transaction)

    assert transaction.markers == set()
    assert {kind: dropped(kind) for kind in DROPPED_KINDS} == before


async def test_a_level_engages_after_two_seconds_at_or_above_it(worker, backlog, clock):
    await backlog(100, held=False)

    clock.advance(1.9)
    assert worker.pressure == 0

    clock.advance(0.1)
    assert worker.pressure == 2


async def test_each_level_engages_once_held_at_or_above_it(worker, backlog, clock):
    await backlog(100, held=False)
    clock.advance(1.5)
    await fill(worker, 900)  # backlog now 1,000 and more

    clock.advance(0.5)
    assert worker.pressure == 2  # 100+ held 2 s, 1,000+ only 0.5 s

    clock.advance(1.5)
    assert worker.pressure == 3


async def test_shedding_stops_as_soon_as_backlog_falls_below_the_level(worker, stall, clock):
    first = await stall()
    await asyncio.sleep(0)
    await fill(worker, 50)
    reached = asyncio.Event()
    await stall(on_start=reached)
    await fill(worker, 60)
    clock.advance(worker.pressure_hold)
    assert worker.pressure == 2

    first.set()
    await reached.wait()  # the consumer ran 50 jobs, 60 are left
    transaction = new_transaction()
    await message(worker, transaction)

    assert transaction.markers == set()


async def test_pressure_and_gauge_return_to_zero_once_drained(worker, stall, clock):
    release = await stall()
    await asyncio.sleep(0)
    await fill(worker, 10_000)
    clock.advance(worker.pressure_hold)
    assert worker.pressure == 4

    release.set()
    await worker.wait_until_empty()

    assert worker.pressure == 0
    assert backlog_gauge(worker) == 0
