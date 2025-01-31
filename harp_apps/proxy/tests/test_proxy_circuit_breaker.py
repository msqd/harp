import httpx
import pytest
import respx

from harp.http import HttpRequest
from harp_apps.proxy.constants import DOWN, UP
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.settings.remote import Remote

BASE_URL = "http://example.com"


@respx.mock
@pytest.mark.parametrize("liveness_type", [None, "ignore", "naive", "inherit", "leaky"])
async def test_basic(liveness_type):
    """
    This test ensures that the controller can make a request to a remote server and return the response. It's the
    baseline asumption for all other tests. This should be true for any liveness implementation.
    """
    respx.get(BASE_URL).mock(return_value=httpx.Response(200))

    remote = Remote.from_settings_dict(
        {
            **({"liveness": {"type": liveness_type}} if liveness_type is not None else {}),
            "endpoints": [{"url": BASE_URL}],
        }
    )
    controller = HttpProxyController(remote, http_client=httpx.AsyncClient())
    response = await controller(HttpRequest())

    assert response.status == 200
    assert remote[BASE_URL].status == UP


@respx.mock
@pytest.mark.parametrize("status", [500, 502, 503, 504])
@pytest.mark.parametrize("is_http_server_error_a_down_signal", [False, True])
async def test_break_on_5xx(status, is_http_server_error_a_down_signal):
    """
    This test ensures that the circuit breaker is triggered (opened) when a 5xx error is returned by the server, using
    the default settings. After opening, the next request should return a 503 status code.

    This requires a liveness implementation to be configured, as the default is now to "ignore".

    """
    respx.get(BASE_URL).mock(return_value=httpx.Response(status))

    remote = Remote.from_settings_dict(
        {
            "liveness": {"type": "naive"},
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
async def test_break_on_4xx_if_configured(status, is_client_error_a_down_signal):
    """
    This test ensures that the circuit breaker is triggered (opened) when a 4xx error is returned by the server, if and
    only if the "break_on" setting contains "http_4xx". It requires a liveness alorithm to be configured.
    """

    respx.get(BASE_URL).mock(return_value=httpx.Response(status))

    remote = Remote.from_settings_dict(
        {
            "liveness": {"type": "naive"},
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
async def test_do_not_break_if_break_on_explicitely_set(status):
    """
    This test ensures that the circuit breaker is not triggered when configured to break on nothing. It indirectly
    ensures that the break on setting is actually used.
    """
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
    """
    This test ensures that the circuit breaker is triggered (opened) when a network error is raised (a network (L4)
    error is an error happening before we're actually talking HTTP (L7)). It requires a liveness alorithm to be
    selected, as the default "ignore" algorithm won't do anything.
    """
    respx.get(BASE_URL).mock(side_effect=error)

    remote = Remote.from_settings_dict(
        {
            "liveness": {"type": "naive"},
            "endpoints": [{"url": BASE_URL}],
        }
    )
    endpoint = remote[BASE_URL]

    controller = HttpProxyController(remote, http_client=httpx.AsyncClient())

    response = await controller(HttpRequest())
    assert response.status == error_status
    assert endpoint.status == DOWN

    response = await controller(HttpRequest())
    assert response.status == 503
    assert endpoint.status == DOWN
