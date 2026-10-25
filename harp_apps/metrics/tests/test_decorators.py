import httpx
import pytest
from prometheus_client import REGISTRY

from harp.http import HttpRequest
from harp_apps.metrics.constants import CONTROLLER_EXCEPTIONS, REMOTE_EXCEPTIONS
from harp_apps.metrics.decorators import decorate_http_client_send, decorate_proxy_controller


def sample(metric: str, **labels):
    return REGISTRY.get_sample_value(metric, labels)


def series_count(metric) -> int:
    return len(metric.collect()[0].samples)


async def test_controller_records_requests_and_responses():
    async def controller(request):
        return type("Response", (), {"status": 201})()

    wrapped = decorate_proxy_controller(controller, name="ctl-ok", port=1111)
    labels = dict(name="ctl-ok", port="1111", method="GET")

    await wrapped(HttpRequest(method="GET", path="/x"))

    assert sample("controller_requests_count_total", **labels) == 1
    assert sample("controller_responses_count_total", **labels, status="201") == 1
    assert sample("controller_requests_in_progress", **labels) == 0


async def test_controller_exceptions_have_bounded_labels():
    async def controller(request):
        raise ValueError("boom")

    wrapped = decorate_proxy_controller(controller, name="ctl-bounded", port=2222)
    before = series_count(CONTROLLER_EXCEPTIONS)

    for i in range(20):
        with pytest.raises(ValueError):
            await wrapped(HttpRequest(method="GET", path=f"/p{i}", query={"q": str(i)}))

    assert series_count(CONTROLLER_EXCEPTIONS) == before + 2  # the _total and _created samples of one series
    assert (
        sample(
            "controller_exceptions_count_total", name="ctl-bounded", port="2222", method="GET", exception="ValueError"
        )
        == 20
    )


async def test_remote_exceptions_have_bounded_labels():
    async def send(request, *args, **kwargs):
        raise httpx.ConnectError("down")

    wrapped = decorate_http_client_send(send)
    before = series_count(REMOTE_EXCEPTIONS)

    for i in range(20):
        with pytest.raises(httpx.ConnectError):
            await wrapped(httpx.Request("GET", f"http://example.com/p{i}?token={i}"))

    assert series_count(REMOTE_EXCEPTIONS) == before + 2
    assert sample("remote_exceptions_count_total", name="-", method="GET", exception="ConnectError") == 20


async def test_remote_records_responses():
    async def send(request, *args, **kwargs):
        return httpx.Response(204)

    wrapped = decorate_http_client_send(send)
    await wrapped(httpx.Request("POST", "http://example.com/", extensions={"harp": {"endpoint": "ep-ok"}}))

    assert sample("remote_responses_count_total", name="ep-ok", method="POST", status="204") == 1
    assert sample("remote_requests_in_progress", name="ep-ok", method="POST") == 0
