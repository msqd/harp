import httpx
import pytest
import respx

from harp.http import HttpRequest
from harp_apps.proxy.constants import DOWN, UP
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.settings.remote import Remote

BASE_URL = "http://example.com"


@respx.mock
async def test_basic():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200))

    remote = Remote.from_settings_dict({"endpoints": [{"url": BASE_URL}]})
    controller = HttpProxyController(remote, http_client=httpx.AsyncClient())
    response = await controller(HttpRequest())

    assert response.status == 200
    assert remote[BASE_URL].status == UP


@respx.mock
@pytest.mark.parametrize("status", [500, 502, 503, 504])
@pytest.mark.parametrize("is_http_server_error_a_down_signal", [False, True])
async def test_break_on_5xx(status, is_http_server_error_a_down_signal):
    respx.get(BASE_URL).mock(return_value=httpx.Response(status))

    remote = Remote.from_settings_dict(
        {
            "endpoints": [{"url": BASE_URL}],
            "break_on": (["http_5xx", "network_error"] if is_http_server_error_a_down_signal else ["network_error"]),
        }
    )
    endpoint = remote[BASE_URL]

    controller = HttpProxyController(remote, http_client=httpx.AsyncClient())
    initial_status = endpoint.status

    response = await controller(HttpRequest())
    if is_http_server_error_a_down_signal:
        assert response.status == status
        assert endpoint.status == DOWN
    else:
        assert response.status == status
        assert endpoint.status == initial_status

    response = await controller(HttpRequest())
    if is_http_server_error_a_down_signal:
        assert response.status == 503
        assert endpoint.status == DOWN
    else:
        assert response.status == status
        assert endpoint.status == initial_status


@respx.mock
@pytest.mark.parametrize("status", [400, 401, 403, 404])
@pytest.mark.parametrize("is_client_error_a_down_signal", [False, True])
async def test_break_on_4xx(status, is_client_error_a_down_signal):
    respx.get(BASE_URL).mock(return_value=httpx.Response(status))

    remote = Remote.from_settings_dict(
        {
            "endpoints": [{"url": BASE_URL}],
            "break_on": (["http_4xx", "network_error"] if is_client_error_a_down_signal else ["network_error"]),
        }
    )
    endpoint = remote[BASE_URL]

    controller = HttpProxyController(remote, http_client=httpx.AsyncClient())
    initial_status = endpoint.status

    response = await controller(HttpRequest())
    if is_client_error_a_down_signal:
        assert response.status == status
        assert endpoint.status == DOWN
    else:
        assert response.status == status
        assert endpoint.status == initial_status

    response = await controller(HttpRequest())
    if is_client_error_a_down_signal:
        assert response.status == 503
        assert endpoint.status == DOWN
    else:
        assert response.status == status
        assert endpoint.status == initial_status


@respx.mock
@pytest.mark.parametrize("status", [400, 401, 403, 404, 500, 502, 503, 504])
async def test_do_not_break_if_explicitely_set(status):
    respx.get(BASE_URL).mock(return_value=httpx.Response(status))

    remote = Remote.from_settings_dict(
        {
            "endpoints": [{"url": BASE_URL}],
            "break_on": [],
        }
    )
    endpoint = remote[BASE_URL]

    controller = HttpProxyController(remote, http_client=httpx.AsyncClient())
    initial_status = endpoint.status

    response = await controller(HttpRequest())
    assert response.status == status
    assert endpoint.status == initial_status

    response = await controller(HttpRequest())
    assert response.status == status
    assert endpoint.status == initial_status


@respx.mock
@pytest.mark.parametrize(
    ["error", "error_status"],
    [
        [httpx.NetworkError("oups"), 503],
        [httpx.TimeoutException("oups"), 504],
        [httpx.RemoteProtocolError("oups"), 502],
    ],
)
async def test_break_on_network_error(error, error_status):
    respx.get(BASE_URL).mock(side_effect=error)

    remote = Remote.from_settings_dict({"endpoints": [{"url": BASE_URL}]})
    endpoint = remote[BASE_URL]

    controller = HttpProxyController(remote, http_client=httpx.AsyncClient())

    response = await controller(HttpRequest())
    assert response.status == error_status
    assert endpoint.status == DOWN

    response = await controller(HttpRequest())
    assert response.status == 503
    assert endpoint.status == DOWN
