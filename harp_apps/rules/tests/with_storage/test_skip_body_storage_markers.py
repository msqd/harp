import respx
from httpx import Response

from harp.utils.testing.communicators import ASGICommunicator
from harp_apps.storage.types import IBlobStorage, IStorage
from harp_apps.storage.worker import StorageAsyncWorkerQueue

from .._base import BaseRulesFlowTest


class TestSkipBodyStorageMarkers(BaseRulesFlowTest):
    """Integration tests for skip body storage markers set through rules."""

    applications = ["http_client", "proxy", "rules", "storage"]

    @respx.mock
    async def test_skip_request_body_storage_via_rules(self, httpbin):
        """Test that skip-request-body-storage marker set in rules prevents request body storage."""
        respx.post(httpbin).mock(return_value=Response(200, content=b"upstream response"))

        # Configure rules to add the skip-request-body-storage marker
        system = await self.create_system(
            {
                "proxy": {"endpoints": [{"name": "httpbin", "port": 80, "url": httpbin}]},
                "rules": {
                    "*": {
                        "*": {
                            "on_request": 'transaction.markers.add("skip-request-body-storage")',
                        }
                    }
                },
            },
            mock=lambda ctx: None,  # dummy mock
        )

        client = ASGICommunicator(system.asgi_app)
        await client.asgi_lifespan_startup()

        # Make a POST request with a body
        await client.http_post("/", body=b"sensitive request data")

        # Wait for storage worker to process events
        worker = system.provider.get(StorageAsyncWorkerQueue)
        await worker.wait_until_empty()

        # Get storage instances from system
        sql_storage = system.provider.get(IStorage)
        blob_storage = system.provider.get(IBlobStorage)

        # Verify transaction was stored
        transactions = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        assert len(transactions) == 1

        # Find request message
        request_msg = next(msg for msg in transactions[0].messages if msg.kind == "request")
        response_msg = next(msg for msg in transactions[0].messages if msg.kind == "response")

        # Verify request body was NOT stored
        assert request_msg.body is None

        # Verify request headers WERE stored
        assert request_msg.headers is not None

        # Verify response body WAS stored (marker only affects request)
        assert response_msg.body is not None
        response_blob = await blob_storage.get(response_msg.body)
        assert response_blob.data == b"upstream response"

    @respx.mock
    async def test_skip_response_body_storage_via_rules(self, httpbin):
        """Test that skip-response-body-storage marker set in rules prevents response body storage."""
        respx.get(httpbin).mock(return_value=Response(200, content=b"sensitive response data"))

        # Configure rules to add the skip-response-body-storage marker
        system = await self.create_system(
            {
                "proxy": {"endpoints": [{"name": "httpbin", "port": 80, "url": httpbin}]},
                "rules": {
                    "*": {
                        "*": {
                            "on_response": 'transaction.markers.add("skip-response-body-storage")',
                        }
                    }
                },
            },
            mock=lambda ctx: None,
        )

        client = ASGICommunicator(system.asgi_app)
        await client.asgi_lifespan_startup()

        # Make a GET request
        await client.http_get("/")

        # Wait for storage worker to process events
        worker = system.provider.get(StorageAsyncWorkerQueue)
        await worker.wait_until_empty()

        # Get storage instances from system
        sql_storage = system.provider.get(IStorage)

        # Verify transaction was stored
        transactions = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        assert len(transactions) == 1

        # Find messages
        request_msg = next(msg for msg in transactions[0].messages if msg.kind == "request")
        response_msg = next(msg for msg in transactions[0].messages if msg.kind == "response")

        # Verify request body WAS stored (marker only affects response)
        assert request_msg.body is not None

        # Verify response body was NOT stored
        assert response_msg.body is None

        # Verify response headers WERE stored
        assert response_msg.headers is not None

    @respx.mock
    async def test_skip_both_bodies_via_rules(self, httpbin):
        """Test that both markers set in rules prevents both request and response body storage."""
        respx.post(httpbin).mock(return_value=Response(200, content=b"response data"))

        # Configure rules to add both markers
        system = await self.create_system(
            {
                "proxy": {"endpoints": [{"name": "httpbin", "port": 80, "url": httpbin}]},
                "rules": {
                    "*": {
                        "*": {
                            "on_request": 'transaction.markers.add("skip-request-body-storage")',
                            "on_response": 'transaction.markers.add("skip-response-body-storage")',
                        }
                    }
                },
            },
            mock=lambda ctx: None,
        )

        client = ASGICommunicator(system.asgi_app)
        await client.asgi_lifespan_startup()

        # Make a POST request with a body
        await client.http_post("/", body=b"request data")

        # Wait for storage worker to process events
        worker = system.provider.get(StorageAsyncWorkerQueue)
        await worker.wait_until_empty()

        # Get storage instances from system
        sql_storage = system.provider.get(IStorage)

        # Verify transaction was stored
        transactions = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        assert len(transactions) == 1

        # Find messages
        request_msg = next(msg for msg in transactions[0].messages if msg.kind == "request")
        response_msg = next(msg for msg in transactions[0].messages if msg.kind == "response")

        # Verify neither body was stored
        assert request_msg.body is None
        assert response_msg.body is None

        # Verify headers WERE still stored for both
        assert request_msg.headers is not None
        assert response_msg.headers is not None

    @respx.mock
    async def test_conditional_skip_based_on_endpoint(self, httpbin):
        """Test that markers can be conditionally applied based on endpoint/path."""
        respx.post(f"{httpbin}/upload").mock(return_value=Response(200, content=b"upload ok"))
        respx.post(f"{httpbin}/process").mock(return_value=Response(200, content=b"process ok"))

        # Configure rules to skip only for /upload endpoint
        system = await self.create_system(
            {
                "proxy": {"endpoints": [{"name": "httpbin", "port": 80, "url": httpbin}]},
                "rules": {
                    "*": {
                        "POST /upload": {
                            "on_request": 'transaction.markers.add("skip-request-body-storage")',
                        }
                    }
                },
            },
            mock=lambda ctx: None,
        )

        client = ASGICommunicator(system.asgi_app)
        await client.asgi_lifespan_startup()

        # Make request to /upload (should skip)
        await client.http_post("/upload", body=b"large file data")

        # Make request to /process (should NOT skip)
        await client.http_post("/process", body=b"process data")

        # Wait for storage worker to process events
        worker = system.provider.get(StorageAsyncWorkerQueue)
        await worker.wait_until_empty()

        # Get storage instances from system
        sql_storage = system.provider.get(IStorage)
        blob_storage = system.provider.get(IBlobStorage)

        # Verify both transactions were stored
        transactions = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        assert len(transactions) == 2

        # Find transactions by their paths (order may vary)
        upload_transaction = next(t for t in transactions if any("upload" in msg.summary for msg in t.messages))
        process_transaction = next(t for t in transactions if any("process" in msg.summary for msg in t.messages))

        upload_request_msg = next(msg for msg in upload_transaction.messages if msg.kind == "request")
        process_request_msg = next(msg for msg in process_transaction.messages if msg.kind == "request")

        # Verify upload request body was NOT stored
        assert upload_request_msg.body is None

        # Verify process request body WAS stored
        assert process_request_msg.body is not None
        process_blob = await blob_storage.get(process_request_msg.body)
        assert process_blob.data == b"process data"

    @respx.mock
    async def test_skip_request_headers_storage_via_rules(self, httpbin):
        """Test that skip-request-headers-storage marker set in rules prevents request headers storage."""
        respx.post(httpbin).mock(return_value=Response(200, content=b"upstream response"))

        # Configure rules to add the skip-request-headers-storage marker
        system = await self.create_system(
            {
                "proxy": {"endpoints": [{"name": "httpbin", "port": 80, "url": httpbin}]},
                "rules": {
                    "*": {
                        "*": {
                            "on_request": 'transaction.markers.add("skip-request-headers-storage")',
                        }
                    }
                },
            },
            mock=lambda ctx: None,
        )

        client = ASGICommunicator(system.asgi_app)
        await client.asgi_lifespan_startup()

        # Make a POST request
        await client.http_post("/", body=b"request data")

        # Wait for storage worker to process events
        worker = system.provider.get(StorageAsyncWorkerQueue)
        await worker.wait_until_empty()

        # Get storage instances from system
        sql_storage = system.provider.get(IStorage)
        blob_storage = system.provider.get(IBlobStorage)

        # Verify transaction was stored
        transactions = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        assert len(transactions) == 1

        # Find request message
        request_msg = next(msg for msg in transactions[0].messages if msg.kind == "request")
        response_msg = next(msg for msg in transactions[0].messages if msg.kind == "response")

        # Verify request headers were NOT stored
        assert request_msg.headers is None

        # Verify request body WAS stored
        assert request_msg.body is not None
        request_blob = await blob_storage.get(request_msg.body)
        assert request_blob.data == b"request data"

        # Verify response headers WAS stored (marker only affects request)
        assert response_msg.headers is not None

    @respx.mock
    async def test_skip_request_storage_via_rules(self, httpbin):
        """Test that skip-request-storage marker set in rules prevents entire request message storage."""
        respx.post(httpbin).mock(return_value=Response(200, content=b"upstream response"))

        # Configure rules to add the skip-request-storage marker
        system = await self.create_system(
            {
                "proxy": {"endpoints": [{"name": "httpbin", "port": 80, "url": httpbin}]},
                "rules": {
                    "*": {
                        "*": {
                            "on_request": 'transaction.markers.add("skip-request-storage")',
                        }
                    }
                },
            },
            mock=lambda ctx: None,
        )

        client = ASGICommunicator(system.asgi_app)
        await client.asgi_lifespan_startup()

        # Make a POST request with a body
        await client.http_post("/", body=b"request data")

        # Wait for storage worker to process events
        worker = system.provider.get(StorageAsyncWorkerQueue)
        await worker.wait_until_empty()

        # Get storage instances from system
        sql_storage = system.provider.get(IStorage)
        blob_storage = system.provider.get(IBlobStorage)

        # Verify transaction was stored
        transactions = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        assert len(transactions) == 1

        # Verify only response message was stored (request was skipped)
        assert len(transactions[0].messages) == 1
        response_msg = transactions[0].messages[0]

        # Verify it's the response message
        assert response_msg.kind == "response"
        assert response_msg.headers is not None
        assert response_msg.body is not None
        response_blob = await blob_storage.get(response_msg.body)
        assert response_blob.data == b"upstream response"

    @respx.mock
    async def test_skip_response_storage_via_rules(self, httpbin):
        """Test that skip-response-storage marker set in rules prevents entire response message storage."""
        respx.post(httpbin).mock(return_value=Response(200, content=b"upstream response"))

        # Configure rules to add the skip-response-storage marker
        system = await self.create_system(
            {
                "proxy": {"endpoints": [{"name": "httpbin", "port": 80, "url": httpbin}]},
                "rules": {
                    "*": {
                        "*": {
                            "on_response": 'transaction.markers.add("skip-response-storage")',
                        }
                    }
                },
            },
            mock=lambda ctx: None,
        )

        client = ASGICommunicator(system.asgi_app)
        await client.asgi_lifespan_startup()

        # Make a POST request with a body
        await client.http_post("/", body=b"request data")

        # Wait for storage worker to process events
        worker = system.provider.get(StorageAsyncWorkerQueue)
        await worker.wait_until_empty()

        # Get storage instances from system
        sql_storage = system.provider.get(IStorage)
        blob_storage = system.provider.get(IBlobStorage)

        # Verify transaction was stored
        transactions = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        assert len(transactions) == 1

        # Verify only request message was stored (response was skipped)
        assert len(transactions[0].messages) == 1
        request_msg = transactions[0].messages[0]

        # Verify it's the request message
        assert request_msg.kind == "request"
        assert request_msg.headers is not None
        assert request_msg.body is not None
        request_blob = await blob_storage.get(request_msg.body)
        assert request_blob.data == b"request data"
