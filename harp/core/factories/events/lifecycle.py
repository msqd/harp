"""Eventes related to transactions lifecyle. Responsible for creating a transaction id and dispatching events related
to things happening within."""

import time

from httpx import codes

from harp.core.asgi.events import (
    EVENT_TRANSACTION_ENDED,
    EVENT_TRANSACTION_MESSAGE,
    EVENT_TRANSACTION_STARTED,
    TransactionEvent,
    TransactionMessageEvent,
)
from harp.core.asgi.kernel import logger
from harp.utils.guids import generate_transaction_id_ksuid


async def on_http_request(event):
    event.request.transaction_id = generate_transaction_id_ksuid()
    event.request.transaction_started_at = time.time()
    logger.info(
        f"▶ {event.request.method} {event.request.path}",
        transaction_id=getattr(event.request, "transaction_id", None),
    )
    # we don't really want to await this, should run in background ? or use an async queue ?
    await event.dispatcher.dispatch(EVENT_TRANSACTION_STARTED, TransactionEvent(event.request.transaction_id))
    await event.dispatcher.dispatch(
        EVENT_TRANSACTION_MESSAGE, TransactionMessageEvent(event.request.transaction_id, "request", event.request)
    )


async def on_http_response(event):
    status = event.response.status
    reason = codes.get_reason_phrase(status)
    spent = int((time.time() - event.request.transaction_started_at) * 100000) / 100
    logger.info(
        f"◀ {status} {reason} ({spent}ms)",
        transaction_id=getattr(event.request, "transaction_id", None),
    )
    await event.dispatcher.dispatch(
        EVENT_TRANSACTION_MESSAGE, TransactionMessageEvent(event.request.transaction_id, "response", event.response)
    )
    await event.dispatcher.dispatch(EVENT_TRANSACTION_ENDED, TransactionEvent(event.request.transaction_id))
