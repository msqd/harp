from decimal import Decimal

import httpx
import pytest

from ..events import HttpClientFilterEvent


def valid_response_script(context):
    context["response"] = httpx.Response(200, text="Ok.")


def invalid_response_script(context):
    context["response"] = Decimal(200)


def none_response_script(context):
    context["response"] = None


def test_execution():
    event = HttpClientFilterEvent(httpx.Request("GET", "http://example.com"))

    event.execute_script(valid_response_script)
    assert event.response.status_code == 200

    with pytest.raises(ValueError):
        event.execute_script(invalid_response_script)
    assert event.response.status_code == 200

    event.execute_script(none_response_script)
    assert event.response is None
