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
from harp_apps.storage.worker import StorageAsyncWorkerQueue


def dropped(kind: str) -> float:
    return REGISTRY.get_sample_value("dropped_total", {"kind": kind}) or 0.0


@pytest.fixture
async def worker():
    worker = StorageAsyncWorkerQueue(MagicMock(), AsyncMock(), AsyncMock())
    worker.dispatcher = AsyncEventDispatcher()
    worker.register_events(worker.dispatcher)
    yield worker
    await worker.close()


@pytest.fixture
async def backlog(worker):
    """Stalls the consumer, returns a coroutine function that queues ``size`` items behind it."""
    release = asyncio.Event()

    async def stalled():
        await release.wait()

    async def noop():
        pass

    async def build(size: int):
        await worker.push(stalled)
        await asyncio.sleep(0)  # consumer is now stuck on the first item
        for _ in range(size):
            await worker.push(noop)

    yield build
    release.set()


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
    gauge = REGISTRY.get_sample_value("async_worker_queue_backlog", {"queue_id": str(id(worker))})

    assert worker.pressure >= 2
    assert dropped("bodies") == before + 1
    assert gauge >= 100
