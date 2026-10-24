from decimal import Decimal

from pydantic import HttpUrl

from harp.views.json import serialize


def test_decimal_serialization():
    decimal = Decimal("3.14")
    assert serialize(decimal) == b'"3.14"'


def test_url_serialization():
    url = HttpUrl("https://example.com")
    assert serialize(url) == b'"https://example.com/"'


class _Unserializable:
    def __repr__(self):
        return "SECRET-REPR"


async def _serialize_failure_body(monkeypatch, debug):
    import orjson

    import harp
    from harp.asgi.events import ViewEvent
    from harp.http import HttpRequest
    from harp.views.json import json, on_json_response

    monkeypatch.setattr(harp, "DEBUG", debug)
    event = ViewEvent(HttpRequest.__new__(HttpRequest), json({"foo": _Unserializable()}))
    await on_json_response(event)
    assert event.response.status == 500
    return orjson.loads(event.response.body)


async def test_serialization_error_is_generic_without_debug(monkeypatch):
    body = await _serialize_failure_body(monkeypatch, debug=False)
    assert body == {"error": "Cannot serialize response to json.", "type": "TypeError"}


async def test_serialization_error_logs_traceback_without_debug(monkeypatch):
    from structlog.testing import capture_logs

    with capture_logs() as logs:
        await _serialize_failure_body(monkeypatch, debug=False)
    assert any(entry.get("exc_info") for entry in logs)


async def test_serialization_error_is_detailed_with_debug(monkeypatch):
    body = await _serialize_failure_body(monkeypatch, debug=True)
    assert "Traceback" in body["traceback"]
    assert "SECRET-REPR" in body["value"]
