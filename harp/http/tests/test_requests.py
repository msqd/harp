import pytest
from httpx import ByteStream

from harp.http import HttpRequest, HttpRequestSerializer


class BaseHttpRequestTest:
    """
    Base class for testing HTTP requests, without focusing on a specific underlying protocol bridge implementation.
    """

    RequestType = HttpRequest

    def create_request(self, **kwargs) -> HttpRequest:
        return self.RequestType(**kwargs)


class TestHttpRequestPath(BaseHttpRequestTest):
    """
    Test path-related stuff on HTTP requests.
    """

    def test_default(self):
        request = self.create_request()
        assert request.path == "/"

    def test_simple(self):
        request = self.create_request(path="/foo/bar")
        assert request.path == "/foo/bar"


class TestHttpRequestQuery(BaseHttpRequestTest):
    """
    Test query string-related stuff on HTTP requests.
    """

    def test_simple(self):
        request = self.create_request(
            query="foo=bar&baz=qux",
        )

        assert list(sorted(request.query.items())) == [("baz", "qux"), ("foo", "bar")]

    def test_multi_keys(self):
        request = self.create_request(
            query="foo=bar&baz=qux&foo=more&foo=stuff&john=doe",
        )

        assert list(sorted(request.query.items())) == [
            ("baz", "qux"),
            ("foo", "bar"),
            ("foo", "more"),
            ("foo", "stuff"),
            ("john", "doe"),
        ]

    def test_multi_values(self):
        request = self.create_request(
            query="foo=bar&foo=bar&foo=bar",
        )

        assert list(sorted(request.query.items())) == [
            ("foo", "bar"),
            ("foo", "bar"),
            ("foo", "bar"),
        ]


class TestHttpRequestBasicAuthentication(BaseHttpRequestTest):
    """
    Test basic authentication-related stuff on HTTP requests.

    (cf https://developer.mozilla.org/fr/docs/Web/HTTP/Headers/Authorization)
    """

    def test_default_is_unset(self):
        request = self.create_request()
        assert request.basic_auth is None

    def test_simple(self):
        request = self.create_request(headers={"authorization": "Basic dXNlcjpwYXNz"})
        assert request.basic_auth == ("user", "pass")


class TestHttpRequestHeaders(BaseHttpRequestTest):
    """
    Test headers-related stuff on HTTP requests (except cookie which will get their own home).
    """

    def test_headers(self):
        request = self.create_request(
            headers={
                "host": "localhost:4080",
                "connection": "keep-alive",
                "origin": "http://localhost:4080",
                "accept": "*/*",
                "referer": "http://localhost:4080/",
                "accept-encoding": "gzip, deflate, br",
                "accept-language": "fr-FR,fr;q=0.9,en;q=0.8,fr-CA;q=0.7",
            }
        )

        assert request.headers == {
            "host": "localhost:4080",
            "connection": "keep-alive",
            "origin": "http://localhost:4080",
            "accept": "*/*",
            "referer": "http://localhost:4080/",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "fr-FR,fr;q=0.9,en;q=0.8,fr-CA;q=0.7",
        }

        # TODO move into serializer tests
        serializer = HttpRequestSerializer(request)
        assert serializer.headers == (
            "host: localhost:4080\n"
            "connection: keep-alive\n"
            "origin: http://localhost:4080\n"
            "accept: */*\n"
            "referer: http://localhost:4080/\n"
            "accept-encoding: gzip, deflate, br\n"
            "accept-language: fr-FR,fr;q=0.9,en;q=0.8,fr-CA;q=0.7"
        )


class TestHttpRequestCookies(BaseHttpRequestTest):
    """
    Test cookie-related stuff on HTTP requests.
    """

    def test_cookies_empty(self):
        request = self.create_request()
        assert request.cookies == {}

    def test_cookies_basics(self):
        request = self.create_request(headers={"cookie": "name=value; name2=value2; name3=value3"})
        assert request.cookies == {
            "name": "value",
            "name2": "value2",
            "name3": "value3",
        }

    def test_cookies_more(self):
        request = self.create_request(
            headers={
                "cookie": "bab_locale=fr; bab_original=fr; bab_block=1690; _fbp=fb.1.1687.19100; "
                "_ga_6F3R65C=GS1.1.1452.9.0.1732.0.0.0; _ga_D73X6=GS1.1.1762.30.1.1796.0.0.0; "
                "harp=421 balloons flying; _ga_X8BC7QX9TE=GS1.1.7712.22.1.1753.0.0.0; "
                "_ga=GA1.1.7767.1438; _ga_PPPB3LT24D=GS1.1.1784.84.0.1784.0.0.0",
            }
        )

        assert request.cookies == {
            "_fbp": "fb.1.1687.19100",
            "_ga": "GA1.1.7767.1438",
            "_ga_6F3R65C": "GS1.1.1452.9.0.1732.0.0.0",
            "_ga_D73X6": "GS1.1.1762.30.1.1796.0.0.0",
            "_ga_PPPB3LT24D": "GS1.1.1784.84.0.1784.0.0.0",
            "_ga_X8BC7QX9TE": "GS1.1.7712.22.1.1753.0.0.0",
            "bab_block": "1690",
            "bab_locale": "fr",
            "bab_original": "fr",
            "harp": "421 balloons flying",
        }


class TestHttpRequestBody(BaseHttpRequestTest):
    async def test_body_must_be_read_first(self):
        request = self.create_request()
        with pytest.raises(RuntimeError):
            assert request.body == b""

    async def test_body_empty(self):
        request = self.create_request()
        await request.aread()
        assert request.body == b""

    async def test_body_one_chunk(self):
        request = self.create_request(body=b"foobar")
        await request.aread()
        assert request.body == b"foobar"

    async def test_body_many_chunks(self):
        request = self.create_request(body=[b"foo", b"bar", b"baz"])
        await request.aread()
        assert request.body == b"foobarbaz"

    async def test_body_can_be_read_more_than_once(self):
        request = self.create_request(body=[b"foo", b"bar", b"baz"])
        await request.aread()
        await request.aread()
        await request.aread()
        assert request.body == b"foobarbaz"

    async def test_stream_can_be_accessed_before_reading_body(self):
        request = self.create_request(body=[b"foo", b"bar", b"baz"])
        assert [chunk async for chunk in request.stream] == [b"foo", b"bar", b"baz"]
        request.stream = ByteStream(b"foobarbaz")
        await request.aread()
        assert request.body == b"foobarbaz"

    async def test_stream_can_be_accessed_after_reading_body(self):
        request = self.create_request(body=[b"foo", b"bar", b"baz"])
        await request.aread()
        assert [chunk async for chunk in request.stream] == [b"foobarbaz"]
        assert request.body == b"foobarbaz"
        assert isinstance(request.body, bytes)
        assert isinstance(request.stream, ByteStream)
