import hashlib
import time

from whistle import Event

from harp import get_logger
from harp.contrib.sqlite_storage.connect import connect_to_sqlite
from harp.core.asgi.events import TransactionMessageEvent

logger = get_logger(__name__)


async def on_startup(event: Event):
    try:
        async with connect_to_sqlite() as db:
            await db.execute("DROP TABLE IF EXISTS messages")
            await db.execute("DROP TABLE IF EXISTS blobs")
            await db.execute("DROP TABLE IF EXISTS transactions")
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT,
                    started_at INTEGER
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id INTEGER,
                    kind TEXT,
                    summary TEXT,
                    headers TEXT,
                    body TEXT,
                    FOREIGN KEY(transaction_id) REFERENCES transactions(id),
                    FOREIGN KEY(headers) REFERENCES blobs(id),
                    FOREIGN KEY(body) REFERENCES blobs(id)
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS blobs (
                    id TEXT PRIMARY KEY UNIQUE,
                    content BLOB
                )
                """
            )
            await db.commit()
    except Exception as exc:
        logger.exception("Unable to initialize database.", exc_info=exc)


async def insert_blob(db, content):
    if not isinstance(content, bytes):
        content = content.encode("utf-8")
    hash = hashlib.sha1(content).hexdigest()
    await db.execute("INSERT OR IGNORE INTO blobs (id, content) VALUES(?, ?)", (hash, content))
    return hash


async def on_transaction_started(event: TransactionMessageEvent):
    # event.request.
    async with connect_to_sqlite() as db:
        c = await db.execute(
            "INSERT INTO transactions (uuid, started_at) VALUES (?, ?)", (event.transaction_id, time.time())
        )
        transaction_id = c.lastrowid

        headers_blob_id = await insert_blob(db, event.content.serialized_headers)
        content_blob_id = await insert_blob(db, event.content.serialized_body)

        c = await db.execute(
            "INSERT INTO messages (transaction_id, kind, summary, headers, body) VALUES (?, ?, ?, ?, ?)",
            (
                transaction_id,
                event.kind,
                event.content.serialized_summary,
                headers_blob_id,
                content_blob_id,
            ),
        )
        await db.commit()


async def on_transaction_ended(event: TransactionMessageEvent):
    pass
