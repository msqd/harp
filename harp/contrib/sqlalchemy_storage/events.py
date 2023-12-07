import hashlib

from sqlalchemy import func, select

from harp.contrib.sqlalchemy_storage.engine import engine
from harp.contrib.sqlalchemy_storage.settings import HARP_SQLALCHEMY_STORAGE
from harp.contrib.sqlalchemy_storage.tables import metadata
from harp.core.asgi.events import TransactionEvent, TransactionMessageEvent


async def on_startup(event: TransactionEvent):
    async with engine.begin() as conn:
        if HARP_SQLALCHEMY_STORAGE.get("drop_tables", False):
            await conn.run_sync(metadata.drop_all)
        await conn.run_sync(metadata.create_all)


async def on_transaction_started(event: TransactionEvent):
    async with engine.begin() as conn:
        await conn.execute(
            metadata.tables["sa_transactions"]
            .insert()
            .values(
                id=event.transaction.id,
                type=event.transaction.type,
                started_at=event.transaction.started_at,
            )
        )


async def insert_blob(conn, content):
    if not isinstance(content, bytes):
        content = content.encode()
    hash = hashlib.sha1(content).hexdigest()
    if not await conn.scalar(select(func.count()).where(metadata.tables["sa_blobs"].c.id == hash)):
        await conn.execute(metadata.tables["sa_blobs"].insert().values(id=hash, content=content))
    return hash


async def on_transaction_message(event: TransactionMessageEvent):
    async with engine.begin() as conn:
        headers_blob_id = await insert_blob(conn, event.message.content.serialized_headers)
        body_blob_id = await insert_blob(conn, event.message.content.serialized_body)
        await conn.execute(
            metadata.tables["sa_messages"]
            .insert()
            .values(
                transaction_id=event.transaction.id,
                kind=event.message.type,
                summary=event.message.content.serialized_summary,
                headers=headers_blob_id,
                body=body_blob_id,
                created_at=event.message.created_at,
            )
        )


async def on_transaction_ended(event: TransactionEvent):
    async with engine.begin() as conn:
        await conn.execute(
            metadata.tables["sa_transactions"]
            .update()
            .where(metadata.tables["sa_transactions"].c.id == event.transaction.id)
            .values(
                finished_at=event.transaction.finished_at,
                ellapsed=event.transaction.ellapsed,
            )
        )
