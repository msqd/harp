from unittest.mock import AsyncMock
from urllib.parse import urlencode

import pytest
from multidict import MultiDict

from harp.asgi.bridge.requests import HttpRequestAsgiBridge
from harp.http import HttpRequestBridge
from harp.http.utils import HTTP_METHODS

DEFAULT_SERVER_IPADDR = "127.0.0.1"
DEFAULT_SERVER_PORT = 80


unset = object()


class BaseHttpRequestAsgiBridgeTest:
    """
    Base class for testing http requests using an ASGI bridge implementation.
    """

    def create_bridge(self, receive=None, /, **scope) -> HttpRequestBridge:
        return HttpRequestAsgiBridge(
            {
                k: v
                for k, v in {
                    "type": "http",
                    "http_version": "1.1",
                    "asgi": {"spec_version": "2.1", "version": "3.0"},
                    "method": "GET",
                    "scheme": "http",
                    "path": "/",
                    "raw_path": b"/",
                    "query_string": b"",
                    "root_path": "",
                    "headers": [],
                    "client": ["127.0.0.1", 16535],
                    "server": [DEFAULT_SERVER_IPADDR, DEFAULT_SERVER_PORT],
                    "extensions": {},
                    **scope,
                }.items()
                if v is not unset
            },
            receive or AsyncMock(),
        )


class TestHttpRequestAsgiBridgeServer(BaseHttpRequestAsgiBridgeTest):
    """
    Test "server" values from ASGI brigde implementation.
    """

    def test_get_server_default(self):
        bridge = self.create_bridge()
        assert bridge.get_server_ipaddr() == DEFAULT_SERVER_IPADDR
        assert bridge.get_server_port() == DEFAULT_SERVER_PORT

    @pytest.mark.parametrize("server", [None, [], [None], [None, None], unset])
    def test_get_server_invalid_none(self, server):
        bridge = self.create_bridge(server=server)
        assert bridge.get_server_ipaddr() is None
        assert bridge.get_server_port() is None

    @pytest.mark.parametrize("ipaddr", ["127.0.0.1", "172.16.6.1"])
    def test_get_server_override(self, ipaddr):
        bridge = self.create_bridge(server=[ipaddr])
        assert bridge.get_server_ipaddr() == ipaddr
        assert bridge.get_server_port() is None

        bridge = self.create_bridge(server=[ipaddr, 80])
        assert bridge.get_server_ipaddr() == ipaddr
        assert bridge.get_server_port() == 80


class TestHttpRequestAsgiBridgeMethod(BaseHttpRequestAsgiBridgeTest):
    """
    Test HTTP method value from ASGI brigde implementation.
    """

    def test_get_method_default(self):
        bridge = self.create_bridge()
        assert bridge.get_method() == "GET"

    def test_get_method_not_set(self):
        bridge = self.create_bridge(method=unset)
        assert bridge.get_method() is None

    @pytest.mark.parametrize("method", list(HTTP_METHODS.keys()))
    def test_get_method(self, method):
        bridge = self.create_bridge(method=method)
        assert bridge.get_method() == method


class TestHttpRequestAsgiBridgePath(BaseHttpRequestAsgiBridgeTest):
    """
    Test HTTP path (aka ARL, URI, resource ...) value from ASGI brigde implementation.
    """

    def test_get_path_default(self):
        bridge = self.create_bridge()
        assert bridge.get_path() == "/"

    @pytest.mark.parametrize("raw_path", [b"/", b"/foo/bar"])
    def test_get_path_from_raw_path(self, raw_path):
        # raw path has precedence over path
        bridge = self.create_bridge(raw_path=raw_path)
        assert bridge.get_path() == raw_path.decode("utf-8")

        bridge = self.create_bridge(raw_path=raw_path, path=unset)
        assert bridge.get_path() == raw_path.decode("utf-8")

    @pytest.mark.parametrize("path", ["/", "/foo/bar"])
    def test_get_path_from_path(self, path):
        # path is only read if there is no raw path
        bridge = self.create_bridge(path=path, raw_path=unset)
        assert bridge.get_path() == path


class TestHttpRequestAsgiBridgeQuery(BaseHttpRequestAsgiBridgeTest):
    """
    Test HTTP query string value from ASGI brigde implementation.
    """

    def test_get_query_default(self):
        bridge = self.create_bridge()
        assert bridge.get_query() == {}

    def test_get_query_string_basic(self):
        bridge = self.create_bridge(query_string=b"foo=bar&baz=qux")
        assert bridge.get_query() == {"foo": "bar", "baz": "qux"}
        assert urlencode(bridge.get_query()) == "foo=bar&baz=qux"

    def test_get_query_string_multi(self):
        bridge = self.create_bridge(query_string=b"foo=bar&foo=baz&baz=qux")
        assert bridge.get_query() == MultiDict([("foo", "bar"), ("foo", "baz"), ("baz", "qux")])
        assert urlencode(bridge.get_query()) == "foo=bar&foo=baz&baz=qux"

    def test_get_query_string_no_value(self):
        bridge = self.create_bridge(query_string=b"foo")
        assert bridge.get_query() == {"foo": ""}
        assert urlencode(bridge.get_query()) == "foo="


class TestHttpRequestAsgiBridgeHeaders(BaseHttpRequestAsgiBridgeTest):
    """
    Test HTTP headers value from ASGI brigde implementation.
    """

    def test_get_headers_default(self):
        bridge = self.create_bridge()
        assert bridge.get_headers() == {}

    def test_get_headers(self):
        bridge = self.create_bridge(headers=[(b"content-type", b"application/json"), (b"content-length", b"42")])
        assert bridge.get_headers() == {
            "content-type": "application/json",
            "content-length": "42",
        }


class TestHttpRequestAsgiBridgeBody(BaseHttpRequestAsgiBridgeTest):
    """
    Test HTTP body value from ASGI brigde implementation. This is one of the most comlpex parts of the bridge, as the
    ASGI protocol allows for streaming the body in chunks, thus we need to access this asynchronously.
    """

    def create_receive_stub(self, *messages):
        messages = list(messages)

        async def receive():
            return messages.pop(0)

        return receive, messages

    async def test_body_basic(self):
        receive, messages = self.create_receive_stub({"type": "http.request", "body": b'{"foo": "bar"}'})
        bridge = self.create_bridge(receive)

        chunks = []
        assert len(messages)
        async for chunk in bridge.get_stream():
            chunks.append(chunk)

        assert b"".join(chunks) == b'{"foo": "bar"}'
        assert len(chunks) == 1
        assert not len(messages)

    async def test_body_multi_chunk(self):
        receive, messages = self.create_receive_stub(
            {"type": "http.request", "body": b'{"foo":', "more_body": True},
            {"type": "http.request", "body": b' "bar"}'},
        )
        bridge = self.create_bridge(receive)

        chunks = []
        assert len(messages)
        async for chunk in bridge.get_stream():
            chunks.append(chunk)

        assert b"".join(chunks) == b'{"foo": "bar"}'
        assert len(chunks) == 2
        assert not len(messages)
