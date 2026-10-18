import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from prometheus_client import REGISTRY
from whistle import AsyncEventDispatcher

from harp.http import HttpRequest
from harp.models import Transaction
from harp.utils.guids import generate_transaction_id_ksuid
from harp_apps.proxy.events import (
    EVENT_TRANSACTION_ENDED,
    EVENT_TRANSACTION_MESSAGE,
    EVENT_TRANSACTION_STARTED,
    HttpMessageEvent,
    TransactionEvent,
)
from harp_apps.storage.constants import SHED_BODIES, SHED_HEADERS, SHED_MESSAGES, SKIP_STORAGE
from harp_apps.storage.worker import StorageAsyncWorkerQueue

LIMIT = 1000


def dropped(kind: str) -> float:
    return REGISTRY.get_sample_value("dropped_total", {"kind": kind}) or 0.0


def make_worker(engine, storage, blob_storage, **kwargs):
    worker = StorageAsyncWorkerQueue(engine, storage, blob_storage, early_insert_after=60, **kwargs)
    worker.dispatcher = AsyncEventDispatcher()
    worker.register_events(worker.dispatcher)
    return worker


@pytest.fixture
async def worker():
    worker = make_worker(MagicMock(), AsyncMock(), AsyncMock(), pending_max_bytes=LIMIT)
    yield worker
    await worker.close()


def new_transaction() -> Transaction:
    return Transaction(id=generate_transaction_id_ksuid(), type="http", endpoint="/test", started_at=datetime.now(UTC))


async def start(worker, transaction):
    await worker.dispatcher.adispatch(EVENT_TRANSACTION_STARTED, TransactionEvent(transaction=transaction))


async def request(worker, transaction, body=b"x"):
    event = HttpMessageEvent(transaction=transaction, message=HttpRequest(method="POST", path="/", body=body))
    await worker.dispatcher.adispatch(EVENT_TRANSACTION_MESSAGE, event)


async def started(worker, pending_bytes=0):
    transaction = new_transaction()
    await start(worker, transaction)
    worker._pending_bytes = pending_bytes
    return transaction


def stored(worker, transaction):
    (message,) = worker._pending[transaction.id].messages
    return message


async def test_default_limit_is_64_mib():
    assert StorageAsyncWorkerQueue(MagicMock(), AsyncMock(), AsyncMock()).pending_max_bytes == 64 * 1024 * 1024


async def test_payload_of_a_pending_transaction_is_counted(worker):
    transaction = await started(worker)

    await request(worker, transaction, body=b"x" * 100)

    assert worker._pending_bytes >= 100
    assert worker._pending[transaction.id].payload_bytes == worker._pending_bytes


async def test_below_the_limit_nothing_is_shed(worker):
    transaction = await started(worker, LIMIT - 1)

    await request(worker, transaction)

    message = stored(worker, transaction)
    assert message["body"] and message["headers"]
    assert not transaction.markers & {SHED_BODIES, SHED_HEADERS, SHED_MESSAGES}


async def test_past_the_limit_new_bodies_are_shed_and_marked(worker):
    transaction = await started(worker, LIMIT)
    before = dropped("bodies")

    await request(worker, transaction)

    message = stored(worker, transaction)
    assert message["body"] is None and message["headers"]
    assert SHED_BODIES in transaction.markers
    assert dropped("bodies") == before + 1


async def test_further_past_the_limit_headers_are_shed_too(worker):
    transaction = await started(worker, int(LIMIT * 1.25))
    before = dropped("headers")

    await request(worker, transaction)

    message = stored(worker, transaction)
    assert message["body"] is None and message["headers"] is None
    assert {SHED_BODIES, SHED_HEADERS} <= transaction.markers
    assert dropped("headers") == before + 1


async def test_further_still_whole_messages_are_shed(worker):
    transaction = await started(worker, int(LIMIT * 1.5))
    before = dropped("messages")

    await request(worker, transaction)

    assert worker._pending[transaction.id].messages == []
    assert SHED_MESSAGES in transaction.markers
    assert dropped("messages") == before + 1


async def test_a_forgotten_transaction_gives_its_bytes_back(worker):
    transaction = await started(worker)
    await request(worker, transaction, body=b"x" * 100)
    pending = worker._pending[transaction.id]

    worker._expire(pending)

    assert worker._pending_bytes == 0


async def test_a_transaction_not_stored_gives_its_bytes_back(worker):
    transaction = await started(worker)
    await request(worker, transaction, body=b"x" * 100)
    transaction.markers.add(SKIP_STORAGE)
    transaction.finished_at = datetime.now(UTC)

    await worker.dispatcher.adispatch(EVENT_TRANSACTION_ENDED, TransactionEvent(transaction=transaction))

    assert worker._pending_bytes == 0


async def test_a_message_of_an_unknown_transaction_is_not_counted(worker):
    await request(worker, new_transaction(), body=b"x" * 100)

    assert worker._pending_bytes == 0


async def test_written_bytes_are_given_back(sql_storage, sql_blob_storage):
    worker = make_worker(sql_storage.engine, sql_storage, sql_blob_storage, pending_max_bytes=10_000)
    try:
        transaction = new_transaction()
        await start(worker, transaction)
        await request(worker, transaction, body=b"x" * 100)
        assert worker._pending_bytes >= 100
        transaction.finished_at = datetime.now(UTC)
        await worker.dispatcher.adispatch(EVENT_TRANSACTION_ENDED, TransactionEvent(transaction=transaction))
        await worker.wait_until_empty()

        assert worker._pending_bytes == 0
    finally:
        await worker.close()


async def test_bytes_of_a_failed_write_are_given_back():
    engine = MagicMock()
    engine.begin.side_effect = RuntimeError("database is gone")
    worker = make_worker(engine, AsyncMock(), AsyncMock(), pending_max_bytes=10_000)
    try:
        transaction = new_transaction()
        await start(worker, transaction)
        await request(worker, transaction, body=b"x" * 100)
        transaction.finished_at = datetime.now(UTC)
        await worker.dispatcher.adispatch(EVENT_TRANSACTION_ENDED, TransactionEvent(transaction=transaction))
        await worker.wait_until_empty()

        assert worker._pending_bytes == 0
    finally:
        await worker.close()


async def _written_row(worker, sql_storage, transaction):
    transaction.finished_at = datetime.now(UTC)
    await worker.dispatcher.adispatch(EVENT_TRANSACTION_ENDED, TransactionEvent(transaction=transaction))
    await worker.wait_until_empty()
    (row,) = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
    return row


async def test_every_shed_item_is_marked_on_the_written_transaction(sql_storage, sql_blob_storage):
    worker = make_worker(sql_storage.engine, sql_storage, sql_blob_storage, pending_max_bytes=LIMIT)
    try:
        transaction = new_transaction()
        await start(worker, transaction)
        worker._pending_bytes = int(LIMIT * 1.25)  # headers and bodies are shed, the message itself is kept
        await request(worker, transaction)

        row = await _written_row(worker, sql_storage, transaction)

        (message,) = row.messages
        assert message.headers is None and message.body is None
        assert {SHED_HEADERS, SHED_BODIES} <= set(row.markers)
    finally:
        await worker.close()


async def test_a_transaction_still_open_has_no_markers_yet(sql_storage, sql_blob_storage):
    """Early inserted, it shows a missing body and no marker until it ends: not a loss, the marker comes with the end."""
    worker = make_worker(sql_storage.engine, sql_storage, sql_blob_storage, pending_max_bytes=LIMIT)
    worker.early_insert_after = 0.01
    try:
        transaction = new_transaction()
        await start(worker, transaction)
        worker._pending_bytes = LIMIT
        await request(worker, transaction)
        await asyncio.sleep(0.05)
        await worker.wait_until_empty()

        (row,) = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        assert row.finished_at is None and SHED_BODIES not in set(row.markers)

        row = await _written_row(worker, sql_storage, transaction)
        assert SHED_BODIES in set(row.markers)
    finally:
        await worker.close()
