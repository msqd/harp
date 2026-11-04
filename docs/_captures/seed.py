"""
Fixed data for the documentation captures.

Everything here is derived from constants and a seeded random generator: the same call always writes the same
transactions, so a capture only changes when the UI does.
"""

import json
import random
from datetime import UTC, datetime, timedelta

from httpx import codes
from sqlalchemy.ext.asyncio import create_async_engine

from harp.models import Blob, Transaction
from harp.utils.tpdex import tpdex
from harp_apps.storage.services.blob_storages.sql import SqlBlobStorage
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.settings import StorageSettings

#: The instant every capture pretends to be taken at (server clock and browser clock).
NOW = datetime(2026, 3, 12, 14, 30, tzinfo=UTC)

ENDPOINTS = {
    # name: (weight, [(method, path, status, elapsed milliseconds)])
    "payments": (
        3,
        [
            ("GET", "/v2/customers/cus_4f2a", 200, 81),
            ("POST", "/v2/charges", 201, 412),
            ("POST", "/v2/charges", 402, 236),
            ("GET", "/v2/charges/ch_91c3", 200, 94),
        ],
    ),
    "geocoding": (
        4,
        [
            ("GET", "/search?q=place+de+la+bourse", 200, 54),
            ("GET", "/search?q=rue+de+rivoli", 200, 47),
            ("GET", "/reverse?lat=48.8566&lon=2.3522", 200, 61),
        ],
    ),
    "weather": (
        2,
        [
            ("GET", "/forecast?city=paris", 200, 128),
            ("GET", "/forecast?city=lyon", 200, 133),
            ("GET", "/forecast?city=nowhere", 404, 41),
            ("GET", "/forecast?city=paris", 503, 640),
        ],
    ),
}

REQUEST_HEADERS = (
    "Host: payments.example.com\nAccept: application/json\nUser-Agent: shop-backend/4.2\nX-Request-Id: req-7d41"
)
RESPONSE_HEADERS = (
    "Content-Type: application/json\nContent-Length: {length}\nServer: example\nCache-Control: max-age=60"
)
REQUEST_BODY = {"amount": 4200, "currency": "eur", "customer": "cus_4f2a", "source": "tok_visa"}
RESPONSE_BODY = {"id": "ch_91c3", "object": "charge", "amount": 4200, "currency": "eur", "status": "succeeded"}

#: Transaction shown in the details capture.
DETAILS_TRANSACTION_ID = "2gKXOnPpDLBrw0yJDGJ4g5r3qI1"
FAVORITE_TRANSACTION_ID = "2gKXOnPpDLBrw0yJDGJ4g5r3qI2"


def _transaction_id(index: int) -> str:
    return f"2gKXOnPpDLBrw0yJDGJ4g5r{index:04d}"[-27:]


def build_transactions(count: int = 400):
    """Yield ``(transaction, request message data, response message data)`` for each seeded transaction."""
    rng = random.Random(1440)
    names = list(ENDPOINTS)
    weights = [ENDPOINTS[name][0] for name in names]

    for index in range(count):
        endpoint = rng.choices(names, weights)[0]
        method, path, status, elapsed = rng.choice(ENDPOINTS[endpoint][1])
        elapsed = round(elapsed * rng.uniform(0.8, 1.25), 1)
        # Dense in the last day, thinner over the rest of the week.
        span = 24 * 60 if rng.random() < 0.6 else 7 * 24 * 60
        started_at = NOW - timedelta(minutes=rng.uniform(1, span))
        status_class = f"{status // 100}xx"
        transaction = Transaction(
            id=DETAILS_TRANSACTION_ID
            if index == 0
            else FAVORITE_TRANSACTION_ID
            if index == 1
            else _transaction_id(index),
            type="http",
            endpoint=endpoint,
            started_at=started_at,
            finished_at=started_at + timedelta(milliseconds=elapsed),
            elapsed=elapsed,
            tpdex=tpdex(elapsed),
            extras={
                "method": method,
                "status_class": status_class,
                "cached": method == "GET" and status == 200 and rng.random() < 0.3,
            },
        )
        yield transaction, (method, path, status)


async def seed(url: str) -> None:
    """Write the fixed data into the (already migrated) database at ``url``."""
    engine = create_async_engine(url)
    blob_storage = SqlBlobStorage(engine)
    storage = SqlStorage(engine, blob_storage, StorageSettings(url=url))
    await storage.initialize()

    request_body = json.dumps(REQUEST_BODY, indent=2).encode()
    response_body = json.dumps(RESPONSE_BODY, indent=2).encode()
    blobs = {
        "request_headers": await blob_storage.put(Blob.from_data(REQUEST_HEADERS, content_type="http/headers")),
        "response_headers": await blob_storage.put(
            Blob.from_data(RESPONSE_HEADERS.format(length=len(response_body)), content_type="http/headers")
        ),
        "request_body": await blob_storage.put(Blob.from_data(request_body, content_type="application/json")),
        "response_body": await blob_storage.put(Blob.from_data(response_body, content_type="application/json")),
    }

    for transaction, (method, path, status) in build_transactions():
        await storage.transactions.create(transaction.as_storable_dict())
        await storage.messages.create(
            {
                "transaction_id": transaction.id,
                "kind": "request",
                "summary": f"{method} {path} HTTP/1.1",
                "headers": blobs["request_headers"].id,
                **({"body": blobs["request_body"].id} if method == "POST" else {}),
                "created_at": transaction.started_at,
            }
        )
        await storage.messages.create(
            {
                "transaction_id": transaction.id,
                "kind": "response",
                "summary": f"HTTP/1.1 {status} {codes.get_reason_phrase(status)}",
                "headers": blobs["response_headers"].id,
                "body": blobs["response_body"].id,
                "created_at": transaction.finished_at,
            }
        )

    await storage.set_user_flag(transaction_id=FAVORITE_TRANSACTION_ID, username="anonymous", flag=1)
    await engine.dispose()
