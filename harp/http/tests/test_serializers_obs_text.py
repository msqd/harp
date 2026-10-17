"""Headers travel as latin-1 text (one char per byte); stored and displayed, utf-8 values read as utf-8."""

from harp.http import HttpRequest, HttpResponse
from harp.http.serializers import HttpRequestSerializer, HttpResponseSerializer


def _wire(value: bytes) -> str:
    return value.decode("latin-1")


def test_utf8_header_value_is_stored_readable():
    request = HttpRequest(method="GET", path="/", headers={"x-name": _wire("Zoë".encode("utf-8"))})
    assert HttpRequestSerializer(request).headers == "x-name: Zoë"


def test_obs_text_header_value_is_stored_without_error():
    response = HttpResponse(b"", headers={"etag": _wire(b'"abcdef\xfc"')})
    assert HttpResponseSerializer(response).headers == 'etag: "abcdefü"'
