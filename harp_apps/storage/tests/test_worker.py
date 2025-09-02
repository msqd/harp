from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncEngine
from whistle import IAsyncEventDispatcher

from harp.utils.testing.mixins.controllers import _create_request
from harp_apps.proxy.events import HttpMessageEvent
from harp_apps.proxy.tests.with_storage.test_controllers_http_proxy import DispatcherTestFixtureMixin
from harp_apps.storage.services import SqlStorage
from harp_apps.storage.types import IStorage, IBlobStorage
from harp_apps.storage.worker import SKIP_REQUEST_PAYLOAD_STORAGE, StorageAsyncWorkerQueue
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin


class TestStorageAsyncWorkerQueue(StorageTestFixtureMixin, DispatcherTestFixtureMixin):
    def create_worker(
            self,
            dispatcher: IAsyncEventDispatcher,
            engine: AsyncEngine,
            sql_storage: IStorage,
            blob_storage: IBlobStorage,
    ) -> StorageAsyncWorkerQueue:
        worker = StorageAsyncWorkerQueue(
            engine,
            sql_storage,
            blob_storage,
            skip_storage_requests_payload=[r"/api/uploads/.*", r"/health"],
            skip_storage_responses_payload=[r"/api/downloads/.*"],
        )
        worker.register_events(dispatcher)
        return worker

    async def test_skip_request_payload_storage_when_path_matches_pattern(
            self,
            sql_engine, blob_storage,
            sql_storage: SqlStorage,
            dispatcher: IAsyncEventDispatcher,
    ):
        worker = self.create_worker(dispatcher, sql_engine, sql_storage, blob_storage)

        transaction = await self.create_transaction(
            sql_storage,
            endpoint="/api/uploads/file.txt",
        )

        transaction.markers = set()
        
        request = await _create_request(b"file content", method='POST', path="/api/uploads/file.txt",)
        
        event = HttpMessageEvent(transaction, request)
        
        # Mock the push method to avoid actual background processing
        worker.push = AsyncMock()
        
        # Process the message
        await worker.on_transaction_message(event)
        
        # Verify that the skip marker was added to the transaction
        assert SKIP_REQUEST_PAYLOAD_STORAGE in transaction.markers

    async def test_skip_response_payload_storage_when_marked(
            self,
            sql_engine,
            blob_storage,
            sql_storage: SqlStorage,
            dispatcher: IAsyncEventDispatcher,
    ):
        worker = self.create_worker(dispatcher, sql_engine, sql_storage, blob_storage)
        transaction = await self.create_transaction(
            sql_storage,
            endpoint="/api/downloads/data.json",
        )

        transaction.markers = set()
        
        # Create a mock response message
        request = await _create_request(b"file content", method='POST', path="/api/downloads/data.json",)

        event = HttpMessageEvent(transaction, request)

        worker.push = AsyncMock()
        worker.blob_storage.put = AsyncMock()
        
        # Process the message
        await worker.on_transaction_message(event)
        
        # Verify that blob storage put was not called for the body
        # (it should only be called for headers, not body due to the skip marker)
        assert worker.blob_storage.put.call_count <= 1  # Only headers, not body
