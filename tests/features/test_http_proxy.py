"""
Initial implementation : https://trello.com/c/yCdcY7Og/1-5-http-proxy
"""
import os

import pytest

from harp import ProxyFactory
from harp.applications.proxy.controllers import HttpProxyController
from harp.core.asgi.kernel import ASGIKernel
from harp.core.asgi.resolvers import ProxyControllerResolver
from harp.utils.testing.communicators import ASGICommunicator
from harp.utils.testing.http import parametrize_with_http_methods, parametrize_with_http_status_codes


class TestAsgiProxyWithoutEndpoints:
    """
    A proxy without configured endpoint will send back 404 responses.

    """

    @pytest.fixture
    def kernel(self):
        return ASGIKernel()

    @pytest.fixture
    async def client(self, kernel):
        client = ASGICommunicator(kernel)
        await client.asgi_lifespan_startup()
        return client

    @pytest.mark.asyncio
    async def test_asgi_proxy_get_no_endpoint(self, client):
        response = await client.http_get("/")
        assert response["status"] == 404
        assert response["body"] == b"Not found."
        assert response["headers"] == ((b"content-type", b"text/plain"),)


class TestAsgiProxyWithMissingStartup:
    @pytest.fixture
    def kernel(self, test_api):
        resolver = ProxyControllerResolver()
        resolver.add(80, HttpProxyController(test_api.url))
        return ASGIKernel(resolver=resolver)

    @pytest.fixture
    async def client(self, kernel):
        return ASGICommunicator(kernel)

    async def test_missing_lifecycle_startup(self, client):
        response = await client.http_get("/echo")
        assert response["status"] == 500
        assert response["body"] == (
            b"Unhandled server error: Cannot access service provider, the lifespan.startup asgi event probably never "
            b"went through."
        )
        assert response["headers"] == ((b"content-type", b"text/plain"),)


class TestAsgiProxyWithStubApi:
    """
    A proxy with an endpoint configured will forward requests to the api, if it has been started first (see asgi's
    lifespan.startup event).

    """

    @pytest.fixture
    async def kernel(self, test_api):
        factory = ProxyFactory()
        factory.add(80, test_api.url)
        return await factory.create()

    @pytest.fixture
    async def client(self, kernel):
        client = ASGICommunicator(kernel)
        await client.asgi_lifespan_startup()
        return client

    @parametrize_with_http_methods(include_non_standard=True, exclude=("CONNECT", "HEAD"))
    async def test_all_methods(self, client: ASGICommunicator, method):
        response = await client.http_request(method, "/echo")
        assert response["status"] == 200
        assert response["body"] == method.encode("utf-8") + b" /echo"
        assert response["headers"] == ((b"content-type", b"text/html; charset=utf-8"),)

    async def test_head_request(self, client: ASGICommunicator):
        response = await client.asgi_http_head("/echo")
        assert response["status"] == 200
        assert response["body"] == b""
        assert response["headers"] == ((b"content-type", b"text/html; charset=utf-8"),)

    @parametrize_with_http_methods(include_having_request_body=True)
    async def test_requests_with_body(self, client: ASGICommunicator, method):
        response = await client.http_request(method, "/echo/body", body=b"Hello, world.")
        assert response["status"] == 200
        assert response["body"] == method.encode("utf-8") + b" /echo/body\nb'Hello, world.'"
        assert response["headers"] == ((b"content-type", b"text/html; charset=utf-8"),)

    @parametrize_with_http_methods(include_having_request_body=True)
    async def test_requests_with_binary_body(self, client: ASGICommunicator, method):
        body = bytes(os.urandom(8))
        response = await client.http_request(method, "/echo/body", body=body)
        assert response["status"] == 200
        assert response["body"] == method.encode("utf-8") + b" /echo/body\n" + repr(body).encode("ascii")
        assert response["headers"] == ((b"content-type", b"text/html; charset=utf-8"),)

    @parametrize_with_http_methods(include_having_response_body=True, include_maybe_having_response_body=True)
    async def test_requests_with_response_body(self, client: ASGICommunicator, method):
        response = await client.http_request(method, "/binary")
        assert response["status"] == 200
        assert len(response["body"]) == 32
        assert response["headers"] == ((b"content-type", b"application/octet-stream"),)

    @parametrize_with_http_status_codes(include=(2, 3, 4, 5))
    @parametrize_with_http_methods(exclude={"CONNECT", "HEAD"})
    async def test_response_status(self, client: ASGICommunicator, method, status_code):
        response = await client.http_request(method, f"/status/{status_code}")
        assert response["status"] == status_code

    @parametrize_with_http_methods(exclude={"CONNECT", "HEAD"})
    async def test_headers(self, client: ASGICommunicator, method):
        response = await client.http_request(method, "/headers")
        assert response["headers"] == ((b"X-Foo", b"Bar"), (b"content-type", b"application/octet-stream"))
