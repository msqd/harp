from unittest.mock import AsyncMock
from urllib.parse import urlencode

import pytest
from multidict import MultiDict

from harp.http import HttpRequestAsgiBridge
from harp.utils.http import HTTP_METHODS

DEFAULT_SERVER_IPADDR = "127.0.0.1"
DEFAULT_SERVER_PORT = 80


unset = object()


class BaseTestHttpRequestAsgiBridge:
    def factory(self, **scope) -> HttpRequestAsgiBridge:
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
            AsyncMock(),
        )


class TestHttpRequestAsgiBridgeServer(BaseTestHttpRequestAsgiBridge):
    def test_get_server_default(self):
        bridge = self.factory()
        assert bridge.get_server_ipaddr() == DEFAULT_SERVER_IPADDR
        assert bridge.get_server_port() == DEFAULT_SERVER_PORT

    @pytest.mark.parametrize("server", [None, [], [None], [None, None], unset])
    def test_get_server_invalid_none(self, server):
        bridge = self.factory(server=server)
        assert bridge.get_server_ipaddr() is None
        assert bridge.get_server_port() is None

    @pytest.mark.parametrize("ipaddr", ["127.0.0.1", "172.16.6.1"])
    def test_get_server_override(self, ipaddr):
        bridge = self.factory(server=[ipaddr])
        assert bridge.get_server_ipaddr() == ipaddr
        assert bridge.get_server_port() is None

        bridge = self.factory(server=[ipaddr, 80])
        assert bridge.get_server_ipaddr() == ipaddr
        assert bridge.get_server_port() == 80


class TestHttpRequestAsgiBridgeMethod(BaseTestHttpRequestAsgiBridge):
    def test_get_method_default(self):
        bridge = self.factory()
        assert bridge.get_method() == "GET"

    def test_get_method_not_set(self):
        bridge = self.factory(method=unset)
        assert bridge.get_method() is None

    @pytest.mark.parametrize("method", list(HTTP_METHODS.keys()))
    def test_get_method(self, method):
        bridge = self.factory(method=method)
        assert bridge.get_method() == method


class TestHttpRequestAsgiBridgePath(BaseTestHttpRequestAsgiBridge):
    def test_get_path_default(self):
        bridge = self.factory()
        assert bridge.get_path() == "/"

    @pytest.mark.parametrize("raw_path", [b"/", b"/foo/bar"])
    def test_get_path_from_raw_path(self, raw_path):
        # raw path has precedence over path
        bridge = self.factory(raw_path=raw_path)
        assert bridge.get_path() == raw_path.decode("utf-8")

        bridge = self.factory(raw_path=raw_path, path=unset)
        assert bridge.get_path() == raw_path.decode("utf-8")

    @pytest.mark.parametrize("path", ["/", "/foo/bar"])
    def test_get_path_from_path(self, path):
        # path is only read if there is no raw path
        bridge = self.factory(path=path, raw_path=unset)
        assert bridge.get_path() == path


class TestHttpRequestAsgiBridgeQuery(BaseTestHttpRequestAsgiBridge):
    def test_get_query_default(self):
        bridge = self.factory()
        assert bridge.get_query() == {}

    def test_get_query_string_basic(self):
        bridge = self.factory(query_string=b"foo=bar&baz=qux")
        assert bridge.get_query() == {"foo": "bar", "baz": "qux"}
        assert urlencode(bridge.get_query()) == "foo=bar&baz=qux"

    def test_get_query_string_multi(self):
        bridge = self.factory(query_string=b"foo=bar&foo=baz&baz=qux")
        assert bridge.get_query() == MultiDict([("foo", "bar"), ("foo", "baz"), ("baz", "qux")])
        assert urlencode(bridge.get_query()) == "foo=bar&foo=baz&baz=qux"


class TestHttpRequestAsgiBridgeHeaders(BaseTestHttpRequestAsgiBridge):
    def test_get_headers_default(self):
        bridge = self.factory()
        assert bridge.get_headers() == {}

    def test_get_headers(self):
        bridge = self.factory(headers=[(b"content-type", b"application/json"), (b"content-length", b"42")])
        assert bridge.get_headers() == {"content-type": "application/json", "content-length": "42"}
