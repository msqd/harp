from unittest.mock import AsyncMock

import respx
from httpx import AsyncClient, Response
from whistle import AsyncEventDispatcher

from harp.apps.proxy.controllers import HttpProxyController
from harp.apps.proxy.events import EVENT_TRANSACTION_STARTED
from harp.core.asgi.messages import ASGIRequest, ASGIResponse


class TestHttpProxyController:
    @respx.mock
    async def test_basic_get(self):
        # mock our remote endpoint and asgi-related stuff
        endpoint = respx.get("http://example.com/").mock(return_value=Response(200, content=b"Hello."))
        receive = AsyncMock(return_value={"body": b""})
        send = AsyncMock()
        request = ASGIRequest(
            {
                "method": "GET",
            },
            receive,
        )
        response = ASGIResponse(request, send)

        # create and call our controller
        controller = HttpProxyController("http://example.com/", http_client=AsyncClient())
        await controller(request, response)

        # check output and side effects
        assert endpoint.called and endpoint.call_count == 1
        assert response.snapshot() == {
            "status": 200,
            "headers": (),
            "body": b"Hello.",
        }

    @respx.mock
    async def test_get_with_tags(self):
        # mock our remote endpoint and asgi-related stuff
        endpoint = respx.get("http://example.com/").mock(return_value=Response(200, content=b"Hello."))
        receive = AsyncMock(return_value={"body": b""})
        send = AsyncMock()
        request = ASGIRequest(
            {
                "method": "GET",
                "headers": [
                    (b"x-harp-foo", b"bar"),
                    (b"accept", b"application/json"),
                    (b"vary", b"custom"),
                ],
            },
            receive,
        )
        response = ASGIResponse(request, send)
        transaction_started_handler = AsyncMock()

        # create and call our controller
        dispatcher = AsyncEventDispatcher()
        dispatcher.add_listener(EVENT_TRANSACTION_STARTED, transaction_started_handler)
        controller = HttpProxyController("http://example.com/", http_client=AsyncClient(), dispatcher=dispatcher)
        await controller(request, response)

        # check that our remote endpoint was passed custom headers, but not internal ones
        assert endpoint.called and endpoint.call_count == 1
        assert "x-harp-foo" not in endpoint.calls[0].request.headers
        assert endpoint.calls[0].request.headers["accept"] == "application/json"
        assert endpoint.calls[0].request.headers["vary"] == "custom"

        # check that the transaction was tagged with the expected values
        assert transaction_started_handler.called and transaction_started_handler.call_count == 1
        assert transaction_started_handler.call_args.args[0].transaction.tags == {"foo": "bar"}

        # check we got a valid response
        assert response.snapshot() == {
            "status": 200,
            "headers": (),
            "body": b"Hello.",
        }
