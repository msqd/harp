import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import event, func, insert, select, text
from whistle import AsyncEventDispatcher

from harp.http import HttpRequest, HttpResponse
from harp.models import Blob, Transaction
from harp.utils.guids import generate_transaction_id_ksuid
from harp_apps.proxy.events import (
    EVENT_TRANSACTION_ENDED,
    EVENT_TRANSACTION_MESSAGE,
    EVENT_TRANSACTION_STARTED,
    HttpMessageEvent,
    TransactionEvent,
)
from harp_apps.storage.models import Blob as SqlBlob
from harp_apps.storage.models.blobs import ORPHAN_GRACE
from harp_apps.storage.services.blob_storages.memory import MemoryBlobStorage
from harp_apps.storage.worker import StorageAsyncWorkerQueue


class Recording:
    """Counts what the database sees: commits, and statements by their first word."""

    def __init__(self, engine):
        self.commits = 0
        self.statements = []
        event.listen(engine.sync_engine, "commit", lambda conn: setattr(self, "commits", self.commits + 1))
        event.listen(
            engine.sync_engine,
            "before_cursor_execute",
            lambda conn, cursor, statement, *args: self.statements.append(statement.split()[0].upper()),
        )

    def reset(self):
        self.commits = 0
        self.statements = []


@pytest.fixture
async def worker(sql_storage, sql_blob_storage):
    worker = StorageAsyncWorkerQueue(sql_storage.engine, sql_storage, sql_blob_storage, early_insert_after=60)
    worker.dispatcher = AsyncEventDispatcher()
    worker.register_events(worker.dispatcher)
    yield worker
    await worker.close()


def new_transaction() -> Transaction:
    return Transaction(id=generate_transaction_id_ksuid(), type="http", endpoint="/test", started_at=datetime.now(UTC))


async def start(worker, transaction):
    await worker.dispatcher.adispatch(EVENT_TRANSACTION_STARTED, TransactionEvent(transaction=transaction))


async def messages(worker, transaction, request_body=b"request", response_body=b"response"):
    for message in (
        HttpRequest(method="POST", path="/test", body=request_body),
        HttpResponse(response_body, status=200),
    ):
        await worker.dispatcher.adispatch(
            EVENT_TRANSACTION_MESSAGE, HttpMessageEvent(transaction=transaction, message=message)
        )


async def end(worker, transaction):
    transaction.finished_at = datetime.now(UTC)
    await worker.dispatcher.adispatch(EVENT_TRANSACTION_ENDED, TransactionEvent(transaction=transaction))


async def test_nothing_is_written_before_the_transaction_ends(worker, sql_storage):
    transaction = new_transaction()
    await start(worker, transaction)
    await messages(worker, transaction)
    await worker.wait_until_empty()

    assert len(await sql_storage.get_transaction_list(username="anonymous", with_messages=True)) == 0


async def test_an_ended_transaction_is_written_in_one_database_transaction(worker, sql_storage):
    recording = Recording(sql_storage.engine)
    transaction = new_transaction()
    await start(worker, transaction)
    await messages(worker, transaction)
    await end(worker, transaction)
    await worker.wait_until_empty()

    assert recording.commits == 1
    (row,) = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
    assert row.id == transaction.id
    assert row.finished_at is not None
    assert [m.kind for m in row.messages] == ["request", "response"]
    assert recording.statements.count("INSERT") <= 4  # blobs, transaction, messages (and a renewal UPDATE)


async def test_a_blob_shared_by_two_messages_is_stored_once(worker, sql_storage):
    transaction = new_transaction()
    await start(worker, transaction)
    await messages(worker, transaction, request_body=b"same", response_body=b"same")
    await end(worker, transaction)
    await worker.wait_until_empty()

    (row,) = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
    request, response = row.messages
    assert request.body == response.body
    async with sql_storage.engine.connect() as conn:
        count = (
            await conn.execute(select(func.count()).select_from(SqlBlob).where(SqlBlob.id == request.body))
        ).scalar_one()
    assert count == 1


async def test_a_transaction_still_open_after_the_threshold_is_inserted_then_updated(sql_storage, sql_blob_storage):
    worker = StorageAsyncWorkerQueue(sql_storage.engine, sql_storage, sql_blob_storage, early_insert_after=0.05)
    worker.dispatcher = AsyncEventDispatcher()
    worker.register_events(worker.dispatcher)
    try:
        transaction = new_transaction()
        await start(worker, transaction)
        await messages(worker, transaction)
        await asyncio.sleep(0.3)
        await worker.wait_until_empty()

        (early,) = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        assert early.id == transaction.id
        assert early.finished_at is None
        assert len(early.messages) == 0

        await end(worker, transaction)
        await worker.wait_until_empty()

        (final,) = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        assert final.finished_at is not None
        assert [m.kind for m in final.messages] == ["request", "response"]
    finally:
        await worker.close()


async def test_a_transaction_ended_before_the_threshold_is_never_inserted_early(sql_storage, sql_blob_storage):
    worker = StorageAsyncWorkerQueue(sql_storage.engine, sql_storage, sql_blob_storage, early_insert_after=0.1)
    worker.dispatcher = AsyncEventDispatcher()
    worker.register_events(worker.dispatcher)
    recording = Recording(sql_storage.engine)
    try:
        transaction = new_transaction()
        await start(worker, transaction)
        await end(worker, transaction)
        await asyncio.sleep(0.3)
        await worker.wait_until_empty()
        assert recording.commits == 1
    finally:
        await worker.close()


async def test_blob_renewal_shares_the_database_transaction_of_the_message(worker, sql_storage):
    old = Blob.from_data(b"request")
    async with sql_storage.engine.begin() as conn:
        await conn.execute(
            insert(SqlBlob).values(
                id=old.id,
                data=old.data,
                content_type=old.content_type,
                created_at=datetime.now(UTC) - ORPHAN_GRACE,
            )
        )
    transaction = new_transaction()
    await start(worker, transaction)
    await messages(worker, transaction, request_body=b"request")
    await end(worker, transaction)
    recording = Recording(sql_storage.engine)
    await worker.wait_until_empty()

    async with sql_storage.engine.connect() as conn:
        created_at = (await conn.execute(select(SqlBlob.created_at).where(SqlBlob.id == old.id))).scalar_one()
    created_at = created_at.replace(tzinfo=UTC)
    assert created_at > datetime.now(UTC) - ORPHAN_GRACE / 2
    assert recording.commits == 1


async def test_transactions_ended_together_can_be_flushed_in_one_database_transaction(worker, sql_storage):
    first, second = new_transaction(), new_transaction()
    for transaction in (first, second):
        await start(worker, transaction)
        await messages(worker, transaction)
        transaction.finished_at = datetime.now(UTC)
    ended = [worker.take_pending(first), worker.take_pending(second)]
    recording = Recording(sql_storage.engine)

    await worker.flush(ended)

    assert recording.commits == 1
    assert {t.id for t in await sql_storage.get_transaction_list(username="anonymous", with_messages=True)} == {
        first.id,
        second.id,
    }


async def test_blobs_of_another_blob_storage_are_put_there(sql_storage):
    blobs = MemoryBlobStorage()
    worker = StorageAsyncWorkerQueue(sql_storage.engine, sql_storage, blobs, early_insert_after=60)
    worker.dispatcher = AsyncEventDispatcher()
    worker.register_events(worker.dispatcher)
    try:
        transaction = new_transaction()
        await start(worker, transaction)
        await messages(worker, transaction, request_body=b"elsewhere")
        await end(worker, transaction)
        await worker.wait_until_empty()

        (row,) = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        assert (await blobs.get(row.messages[0].body)).data == b"elsewhere"
        async with sql_storage.engine.connect() as conn:
            assert (await conn.execute(text("SELECT count(*) FROM blobs"))).scalar_one() == 0
    finally:
        await worker.close()


async def test_tags_are_stored(worker, sql_storage):
    transaction = new_transaction()
    transaction.tags = {"color": "blue"}
    await start(worker, transaction)
    await end(worker, transaction)
    await worker.wait_until_empty()

    (row,) = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
    assert row.tags == {"color": "blue"}
