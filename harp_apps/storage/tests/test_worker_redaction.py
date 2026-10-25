from datetime import UTC, datetime

from multidict import MultiDict
from whistle import AsyncEventDispatcher

from harp.http import HttpRequest, HttpResponse
from harp.models import Transaction
from harp.models.redaction import REDACTED
from harp.utils.guids import generate_transaction_id_ksuid
from harp_apps.proxy.events import (
    EVENT_TRANSACTION_ENDED,
    EVENT_TRANSACTION_MESSAGE,
    EVENT_TRANSACTION_STARTED,
    HttpMessageEvent,
    TransactionEvent,
)
from harp_apps.storage.services.sql import SqlStorage
from harp_apps.storage.types import IBlobStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin
from harp_apps.storage.worker import StorageAsyncWorkerQueue


class TestStorageWorkerRedaction(StorageTestFixtureMixin):
    """Credentials are replaced by the placeholder before they reach the database or the blob storage."""

    async def record(self, sql_storage: SqlStorage, blob_storage: IBlobStorage, *, redact_query=(), redact_headers=()):
        dispatcher = AsyncEventDispatcher()
        worker = StorageAsyncWorkerQueue(sql_storage.engine, sql_storage, blob_storage)
        worker.register_events(dispatcher)

        transaction = Transaction(
            id=generate_transaction_id_ksuid(), type="http", endpoint="/test", started_at=datetime.now(UTC)
        )
        transaction.redaction.query.update(redact_query)
        transaction.redaction.headers.update(redact_headers)

        request = HttpRequest(
            method="GET",
            path="/oauth/token",
            headers={"Authorization": "Bearer secret-token", "x-api-key": "key-123", "accept": "*/*"},
        )
        request.query = MultiDict([("client_secret", "s3cr3t"), ("page", "2")])
        response = HttpResponse(b"ok", status=200, headers={"Set-Cookie": "sid=abc", "etag": '"1"'})

        await dispatcher.adispatch(EVENT_TRANSACTION_STARTED, TransactionEvent(transaction=transaction))
        await dispatcher.adispatch(EVENT_TRANSACTION_MESSAGE, HttpMessageEvent(transaction, request))
        await dispatcher.adispatch(EVENT_TRANSACTION_MESSAGE, HttpMessageEvent(transaction, response))
        transaction.finished_at = datetime.now(UTC)
        await dispatcher.adispatch(EVENT_TRANSACTION_ENDED, TransactionEvent(transaction=transaction))
        await worker.wait_until_empty()

        stored = (await sql_storage.get_transaction_list(username="anonymous", with_messages=True))[0]
        request_message, response_message = stored.messages
        return (
            request_message.summary,
            (await blob_storage.get(request_message.headers)).data.decode(),
            (await blob_storage.get(response_message.headers)).data.decode(),
            request,
            response,
        )

    async def test_credential_headers_are_redacted_by_default(self, sql_storage, blob_storage):
        _, request_headers, response_headers, _, _ = await self.record(sql_storage, blob_storage)

        assert f"Authorization: {REDACTED}" in request_headers
        assert "secret-token" not in request_headers
        assert "x-api-key: key-123" in request_headers
        assert f"Set-Cookie: {REDACTED}" in response_headers
        assert "sid=abc" not in response_headers
        assert 'etag: "1"' in response_headers

    async def test_a_rule_adds_a_query_parameter_and_a_header(self, sql_storage, blob_storage):
        summary, request_headers, _, _, _ = await self.record(
            sql_storage, blob_storage, redact_query=["client_secret"], redact_headers=["X-Api-Key"]
        )

        assert summary == f"GET /oauth/token?client_secret={REDACTED}&page=2 HTTP/1.1"
        assert f"x-api-key: {REDACTED}" in request_headers

    async def test_query_is_stored_in_clear_when_no_rule_names_it(self, sql_storage, blob_storage):
        summary, *_ = await self.record(sql_storage, blob_storage)

        assert "client_secret=s3cr3t" in summary

    async def test_the_messages_themselves_are_left_untouched(self, sql_storage, blob_storage):
        *_, request, response = await self.record(sql_storage, blob_storage, redact_query=["client_secret"])

        assert request.headers["authorization"] == "Bearer secret-token"
        assert request.query["client_secret"] == "s3cr3t"
        assert response.headers["set-cookie"] == "sid=abc"
