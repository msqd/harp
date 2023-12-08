"""Eventes related to transactions lifecyle. Responsible for creating a transaction id and dispatching events related
to things happening within."""

import datetime
import time

from httpx import codes

from harp.core.asgi.events import EVENT_TRANSACTION_ENDED, EVENT_TRANSACTION_MESSAGE, EVENT_TRANSACTION_STARTED
from harp.core.asgi.events.message import MessageEvent
from harp.core.asgi.events.request import RequestEvent
from harp.core.asgi.events.transaction import TransactionEvent
from harp.core.asgi.kernel import logger
from harp.core.models.transactions import Transaction
from harp.utils.guids import generate_transaction_id_ksuid


async def on_http_request(event: RequestEvent):
    event.request.transaction = Transaction(
        id=generate_transaction_id_ksuid(),
        type=event.request.type,
        started_at=datetime.datetime.now(),
    )
    logger.info(
        f"▶ {event.request.method} {event.request.path}",
        transaction_id=event.request.transaction.id,
    )

    # dispatch transaction started event
    # we don't really want to await this, should run in background ? or use an async queue ?
    await event.dispatcher.dispatch(
        EVENT_TRANSACTION_STARTED,
        TransactionEvent(event.request.transaction),
    )

    # dispatch message event for request
    await event.dispatcher.dispatch(
        EVENT_TRANSACTION_MESSAGE,
        MessageEvent(
            event.request.transaction,
            event.request,
        ),
    )


async def on_http_response(event):
    status = event.response.status
    reason = codes.get_reason_phrase(status)
    spent = int((time.time() - event.request.transaction.started_at.timestamp()) * 100000) / 100
    logger.info(
        f"◀ {status} {reason} ({spent}ms)",
        transaction_id=getattr(event.request, "transaction_id", None),
    )

    # dispatch message event for response
    await event.dispatcher.dispatch(
        EVENT_TRANSACTION_MESSAGE,
        MessageEvent(
            event.request.transaction,
            event.response,
        ),
    )

    # dispatch transaction ended event
    await event.dispatcher.dispatch(
        EVENT_TRANSACTION_ENDED,
        TransactionEvent(event.request.transaction),
    )
