import respx
from httpx import Response

from harp.models.redaction import REDACTED
from harp.utils.testing.communicators import ASGICommunicator
from harp_apps.storage.types import IBlobStorage, IStorage
from harp_apps.storage.worker import StorageAsyncWorkerQueue

from .._base import BaseRulesFlowTest


class TestRedactionRules(BaseRulesFlowTest):
    """A rule edits what is redacted; the origin still receives the real values (ADR-0009)."""

    applications = ["http_client", "proxy", "rules", "storage"]

    @respx.mock
    async def test_rule_redacts_stored_values_but_not_the_forwarded_request(self, httpbin):
        route = respx.get(httpbin, path="/token").mock(return_value=Response(200, content=b"ok"))
        system = await self.create_system(
            {
                "proxy": {"endpoints": [{"name": "httpbin", "port": 80, "url": httpbin}]},
                "rules": {
                    "*": {
                        "*": {
                            "on_request": (
                                'transaction.redaction.query.add("client_secret")\n'
                                'transaction.redaction.headers.add("X-Api-Key")'
                            ),
                        }
                    }
                },
            },
            mock=lambda ctx: None,
        )
        client = ASGICommunicator(system.asgi_app)
        await client.asgi_lifespan_startup()

        await client.http_get(
            "/token?client_secret=s3cr3t&page=2",
            headers=[(b"authorization", b"Bearer abc"), (b"x-api-key", b"key-123")],
        )
        await system.provider.get(StorageAsyncWorkerQueue).wait_until_empty()

        sent = route.calls.last.request
        assert sent.url.query == b"client_secret=s3cr3t&page=2"
        assert sent.headers["authorization"] == "Bearer abc"
        assert sent.headers["x-api-key"] == "key-123"

        sql_storage = system.provider.get(IStorage)
        blob_storage = system.provider.get(IBlobStorage)
        (transaction,) = await sql_storage.get_transaction_list(username="anonymous", with_messages=True)
        request_message = next(message for message in transaction.messages if message.kind == "request")
        headers = (await blob_storage.get(request_message.headers)).data.decode()

        assert f"client_secret={REDACTED}&page=2" in request_message.summary
        assert "s3cr3t" not in request_message.summary
        assert f"authorization: {REDACTED}" in headers
        assert f"x-api-key: {REDACTED}" in headers
        assert "abc" not in headers and "key-123" not in headers
