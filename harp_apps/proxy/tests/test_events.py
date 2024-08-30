from decimal import Decimal

import pytest

from harp.http import HttpRequest, HttpResponse

from ..events import ProxyFilterEvent


def valid_response_script(context):
    context["response"] = HttpResponse("Ok.", status=200)


def invalid_response_script(context):
    context["response"] = Decimal(200)


def none_response_script(context):
    context["response"] = None


def test_execution():
    event = ProxyFilterEvent("api", request=HttpRequest())

    event.execute_script(valid_response_script)
    assert event.response.status == 200

    with pytest.raises(ValueError):
        event.execute_script(invalid_response_script)
    assert event.response.status == 200

    event.execute_script(none_response_script)
    assert event.response is None
