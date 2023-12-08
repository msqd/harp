import hashlib

from sqlalchemy import func, select

from harp.contrib.sqlalchemy_storage.engine import engine
from harp.contrib.sqlalchemy_storage.tables import MessagesTable, TransactionsTable, metadata
from harp.core.asgi.events.message import MessageEvent
from harp.core.asgi.events.transaction import TransactionEvent


async def on_startup(event: TransactionEvent):
    async with engine.begin() as conn:
        if {"drop_tables": True}.get("drop_tables", False):
            await conn.run_sync(metadata.drop_all)
        await conn.run_sync(metadata.create_all)


async def on_transaction_started(event: TransactionEvent):
    async with engine.begin() as conn:
        await conn.execute(
            TransactionsTable.insert().values(
                id=event.transaction.id,
                type=event.transaction.type,
                started_at=event.transaction.started_at,
            )
        )


async def insert_blob(conn, data):
    if not isinstance(data, bytes):
        data = data.encode()
    hash = hashlib.sha1(data).hexdigest()

    query = select(func.count()).where(metadata.tables["sa_blobs"].c.id == hash)

    if not await conn.scalar(query):
        await conn.execute(metadata.tables["sa_blobs"].insert().values(id=hash, data=data))
    return hash


async def on_transaction_message(event: MessageEvent):
    async with engine.begin() as conn:
        headers_blob_id = await insert_blob(conn, event.message.serialized_headers)
        body_blob_id = await insert_blob(conn, event.message.serialized_body)
        await conn.execute(
            MessagesTable.insert().values(
                transaction_id=event.transaction.id,
                kind=event.message.kind,
                summary=event.message.serialized_summary,
                headers=headers_blob_id,
                body=body_blob_id,
                created_at=event.message.created_at,
            )
        )


async def on_transaction_ended(event: TransactionEvent):
    async with engine.begin() as conn:
        await conn.execute(
            TransactionsTable.update()
            .where(metadata.tables["sa_transactions"].c.id == event.transaction.id)
            .values(
                finished_at=event.transaction.finished_at,
                ellapsed=event.transaction.ellapsed,
            )
        )
