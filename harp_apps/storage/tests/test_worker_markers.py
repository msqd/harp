from datetime import UTC, datetime

from whistle import AsyncEventDispatcher

from harp.http import HttpRequest, HttpResponse
from harp.models import Transaction
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


class TestStorageWorkerMarkers(StorageTestFixtureMixin):
    """Test storage worker behavior with body storage skip markers."""

    def create_worker(
        self,
        dispatcher: AsyncEventDispatcher,
        sql_storage: SqlStorage,
        blob_storage: IBlobStorage,
    ) -> StorageAsyncWorkerQueue:
        """Create and register a storage worker."""
        worker = StorageAsyncWorkerQueue(sql_storage.engine, sql_storage, blob_storage)
        worker.register_events(dispatcher)
        return worker

    async def create_transaction_and_messages(
        self,
        dispatcher: AsyncEventDispatcher,
        sql_storage: SqlStorage,
        blob_storage: IBlobStorage,
        markers: set[str] | None = None,
        request_body: bytes = b"request content",
        response_body: bytes = b"response content",
    ) -> Transaction:
        """Helper to create a transaction with request/response messages through events."""
        worker = self.create_worker(dispatcher, sql_storage, blob_storage)

        # Create transaction
        transaction = Transaction(
            id=generate_transaction_id_ksuid(),
            type="http",
            endpoint="/test",
            started_at=datetime.now(UTC),
        )
        if markers:
            transaction.markers = markers

        # Dispatch transaction started event
        await dispatcher.adispatch(EVENT_TRANSACTION_STARTED, TransactionEvent(transaction=transaction))

        # Create and dispatch request message event
        request = HttpRequest(method="POST", path="/test", body=request_body)
        request_event = HttpMessageEvent(transaction=transaction, message=request)
        await dispatcher.adispatch(EVENT_TRANSACTION_MESSAGE, request_event)

        # Create and dispatch response message event
        response = HttpResponse(response_body, status=200)
        response_event = HttpMessageEvent(transaction=transaction, message=response)
        await dispatcher.adispatch(EVENT_TRANSACTION_MESSAGE, response_event)

        # Mark transaction as finished
        transaction.finished_at = datetime.now(UTC)
        await dispatcher.adispatch(EVENT_TRANSACTION_ENDED, TransactionEvent(transaction=transaction))

        # Wait for worker to process all events
        await worker.wait_until_empty()

        return transaction

    async def test_normal_storage_without_markers(self, sql_storage: SqlStorage, blob_storage: IBlobStorage):
        """Test that request and response bodies are stored normally when no markers are present."""
        dispatcher = AsyncEventDispatcher()

        transaction = await self.create_transaction_and_messages(
            dispatcher,
            sql_storage,
            blob_storage,
            request_body=b"request data",
            response_body=b"response data",
        )

        # Verify transaction was stored
        transactions = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        assert len(transactions) == 1
        stored_transaction = transactions[0]
        assert stored_transaction.id == transaction.id

        # Verify messages were stored
        assert len(stored_transaction.messages) == 2
        request_msg = stored_transaction.messages[0]
        response_msg = stored_transaction.messages[1]

        assert request_msg.kind == "request"
        assert response_msg.kind == "response"

        # Verify both bodies were stored
        assert request_msg.body is not None
        request_blob = await blob_storage.get(request_msg.body)
        assert request_blob.data == b"request data"

        assert response_msg.body is not None
        response_blob = await blob_storage.get(response_msg.body)
        assert response_blob.data == b"response data"

    async def test_skip_request_body_storage(self, sql_storage: SqlStorage, blob_storage: IBlobStorage):
        """Test that request body is not stored when skip-request-body-storage marker is set."""
        dispatcher = AsyncEventDispatcher()

        await self.create_transaction_and_messages(
            dispatcher,
            sql_storage,
            blob_storage,
            markers={"skip-request-body-storage"},
            request_body=b"sensitive request data",
            response_body=b"response data",
        )

        # Verify transaction was stored
        transactions = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        assert len(transactions) == 1
        stored_transaction = transactions[0]

        # Verify messages were stored
        assert len(stored_transaction.messages) == 2
        request_msg = stored_transaction.messages[0]
        response_msg = stored_transaction.messages[1]

        # Verify request body was NOT stored
        assert request_msg.kind == "request"
        assert request_msg.body is None

        # Verify request headers WERE stored
        assert request_msg.headers is not None

        # Verify response body WAS stored (marker only affects request)
        assert response_msg.kind == "response"
        assert response_msg.body is not None
        response_blob = await blob_storage.get(response_msg.body)
        assert response_blob.data == b"response data"

    async def test_skip_response_body_storage(self, sql_storage: SqlStorage, blob_storage: IBlobStorage):
        """Test that response body is not stored when skip-response-body-storage marker is set."""
        dispatcher = AsyncEventDispatcher()

        await self.create_transaction_and_messages(
            dispatcher,
            sql_storage,
            blob_storage,
            markers={"skip-response-body-storage"},
            request_body=b"request data",
            response_body=b"sensitive response data",
        )

        # Verify transaction was stored
        transactions = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        assert len(transactions) == 1
        stored_transaction = transactions[0]

        # Verify messages were stored
        assert len(stored_transaction.messages) == 2
        request_msg = stored_transaction.messages[0]
        response_msg = stored_transaction.messages[1]

        # Verify request body WAS stored (marker only affects response)
        assert request_msg.kind == "request"
        assert request_msg.body is not None
        request_blob = await blob_storage.get(request_msg.body)
        assert request_blob.data == b"request data"

        # Verify response body was NOT stored
        assert response_msg.kind == "response"
        assert response_msg.body is None

        # Verify response headers WERE stored
        assert response_msg.headers is not None

    async def test_skip_both_request_and_response_body_storage(
        self, sql_storage: SqlStorage, blob_storage: IBlobStorage
    ):
        """Test that both request and response bodies are not stored when both markers are set."""
        dispatcher = AsyncEventDispatcher()

        await self.create_transaction_and_messages(
            dispatcher,
            sql_storage,
            blob_storage,
            markers={"skip-request-body-storage", "skip-response-body-storage"},
            request_body=b"sensitive request",
            response_body=b"sensitive response",
        )

        # Verify transaction was stored
        transactions = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        assert len(transactions) == 1
        stored_transaction = transactions[0]

        # Verify messages were stored
        assert len(stored_transaction.messages) == 2
        request_msg = stored_transaction.messages[0]
        response_msg = stored_transaction.messages[1]

        # Verify neither body was stored
        assert request_msg.kind == "request"
        assert request_msg.body is None
        assert response_msg.kind == "response"
        assert response_msg.body is None

        # Verify headers WERE still stored for both
        assert request_msg.headers is not None
        assert response_msg.headers is not None

    async def test_headers_stored_when_body_skipped(self, sql_storage: SqlStorage, blob_storage: IBlobStorage):
        """Test that headers are always stored even when body storage is skipped."""
        dispatcher = AsyncEventDispatcher()

        await self.create_transaction_and_messages(
            dispatcher,
            sql_storage,
            blob_storage,
            markers={"skip-request-body-storage"},
        )

        # Verify transaction was stored
        transactions = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        assert len(transactions) == 1
        stored_transaction = transactions[0]

        request_msg = stored_transaction.messages[0]

        # Verify headers were stored even though body was skipped
        assert request_msg.headers is not None
        headers_blob = await blob_storage.get(request_msg.headers)
        assert headers_blob.content_type == "http/headers"

        # Verify message metadata is complete
        assert request_msg.summary is not None
        assert request_msg.created_at is not None
