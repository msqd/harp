from unittest.mock import AsyncMock

from harp.core.asgi.messages.requests import ASGIRequest


def _http_scope(*, method="GET", scheme="http"):
    return {
        "type": "http",
        "http_version": "1.1",
        "asgi": {"spec_version": "2.1", "version": "3.0"},
        "method": method,
        "scheme": scheme,
    }


def test_headers():
    request = ASGIRequest(
        {
            **_http_scope(),
            "path": "/",
            "query_string": b"",
            "headers": [
                (b"host", b"localhost:4080"),
                (b"connection", b"keep-alive"),
                (b"origin", b"http://localhost:4080"),
                (b"accept", b"*/*"),
                (b"referer", b"http://localhost:4080/"),
                (b"accept-encoding", b"gzip, deflate, br"),
                (b"accept-language", b"fr-FR,fr;q=0.9,en;q=0.8,fr-CA;q=0.7"),
            ],
        },
        AsyncMock(),
    )

    headers = request.headers

    assert headers["host"] == "localhost:4080"
    assert request.serialized_headers == (
        "host: localhost:4080\n"
        "connection: keep-alive\n"
        "origin: http://localhost:4080\n"
        "accept: */*\n"
        "referer: http://localhost:4080/\n"
        "accept-encoding: gzip, deflate, br\n"
        "accept-language: fr-FR,fr;q=0.9,en;q=0.8,fr-CA;q=0.7"
    )


def test_cookies_empty():
    request = ASGIRequest(
        {
            **_http_scope(),
            "path": "/",
            "query_string": b"",
            "headers": [],
        },
        AsyncMock(),
    )

    assert request.cookies == {}


def test_cookies_basics():
    request = ASGIRequest(
        {
            **_http_scope(),
            "path": "/",
            "query_string": b"",
            "headers": [
                (b"cookie", b"name=value; name2=value2; name3=value3"),
            ],
        },
        AsyncMock(),
    )

    assert repr(request.cookies) == "<SimpleCookie: name='value' name2='value2' name3='value3'>"
