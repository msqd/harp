import pytest

from harp.http.requests import WrappedHttpRequest
from harp.http.tests.test_requests import BaseHttpRequestTest


class TestWrappedHttpRequest(BaseHttpRequestTest):
    def create_request_and_wrapped_request(self, **kwargs):
        request = self.create_request(**kwargs)
        wrapped = WrappedHttpRequest(request)
        return request, wrapped

    def test_basics(self):
        initial_headers = {
            "host": "localhost",
            "connection": "keep-alive",
        }
        request, wrapped = self.create_request_and_wrapped_request(headers=initial_headers)

        # override one header
        wrapped.headers["host"] = "example.com"

        # original headers were not modified (key by key, and by full value)
        assert request.headers["host"] == "localhost"
        assert request.headers["connection"] == "keep-alive"
        assert request.headers == initial_headers

        # wrapped headers contains our overrides, and the untouched values from the original request
        assert wrapped.headers["host"] == "example.com"
        assert wrapped.headers["connection"] == "keep-alive"
        assert wrapped.headers == initial_headers | {"host": "example.com"}

    def test_delete_not_set(self):
        initial_headers = {
            "host": "localhost",
            "connection": "keep-alive",
        }
        request, wrapped = self.create_request_and_wrapped_request(headers=initial_headers)

        with pytest.raises(TypeError):
            del request.headers["foo"]

        assert request.headers == initial_headers
        assert list(request.headers.items()) == list(initial_headers.items())

        with pytest.raises(KeyError):
            del wrapped.headers["foo"]

        assert request.headers == initial_headers
        assert list(request.headers.items()) == list(initial_headers.items())

    def test_delete_set(self):
        initial_headers = {
            "host": "localhost",
            "connection": "keep-alive",
        }
        request, wrapped = self.create_request_and_wrapped_request(headers=initial_headers)

        del wrapped.headers["host"]
        assert "host" not in wrapped.headers
        assert "host" in request.headers
        assert request.headers["host"] == "localhost"
        assert dict(wrapped.headers) == {"connection": "keep-alive"}
        assert list(wrapped.headers.items()) == [("connection", "keep-alive")]
        assert wrapped.headers == {"connection": "keep-alive"}

    def test_pop(self):
        initial_headers = {
            "host": "localhost",
            "connection": "keep-alive",
        }
        request, wrapped = self.create_request_and_wrapped_request(headers=initial_headers)

        assert wrapped.headers.pop("host") == "localhost"
        assert "host" not in wrapped.headers
        assert "host" in request.headers
        assert request.headers["host"] == "localhost"
        assert wrapped.headers == {"connection": "keep-alive"}
        assert list(wrapped.headers.items()) == [("connection", "keep-alive")]

        wrapped.headers["host"] = "example.com"
        assert wrapped.headers.pop("host") == "example.com"
        assert "host" not in wrapped.headers
