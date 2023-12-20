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

    assert request.cookies == {"name": "value", "name2": "value2", "name3": "value3"}


def test_cookies_more():
    request = ASGIRequest(
        {
            **_http_scope(),
            "path": "/",
            "query_string": b"",
            "headers": [
                (
                    b"cookie",
                    b"bab_locale=fr; bab_original=fr; bab_block=1690; _fbp=fb.1.1687.19100; "
                    b"_ga_6F3R65C=GS1.1.1452.9.0.1732.0.0.0; _ga_D73X6=GS1.1.1762.30.1.1796.0.0.0; "
                    b"harp=421 balloons flying; _ga_X8BC7QX9TE=GS1.1.7712.22.1.1753.0.0.0; "
                    b"_ga=GA1.1.7767.1438; _ga_PPPB3LT24D=GS1.1.1784.84.0.1784.0.0.0",
                ),
            ],
        },
        AsyncMock(),
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


def test_basic_auth_unset():
    request = ASGIRequest({**_http_scope()}, AsyncMock())
    assert request.basic_auth is None


def test_basic_auth():
    request = ASGIRequest({**_http_scope(), "headers": [(b"authorization", b"Basic dXNlcjpwYXNz")]}, AsyncMock())
    assert request.basic_auth == ["user", "pass"]
