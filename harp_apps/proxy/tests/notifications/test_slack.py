from unittest import mock

import pytest
import respx
from httpx import AsyncClient, NetworkError, RemoteProtocolError, Response, TimeoutException

from harp.http import HttpRequest
from harp.http.tests.stubs import HttpRequestStubBridge
from harp_apps.proxy.controllers import HttpProxyController


@pytest.mark.parametrize(
    "status_code, reason_phrase",
    [
        (500, "Internal Server Error"),
        (501, "Not Implemented"),
        (502, "Bad Gateway"),
        (503, "Service Unavailable"),
        (504, "Gateway Timeout"),
        (505, "HTTP Version Not Supported"),
        (506, "Variant Also Negotiates"),
        (507, "Insufficient Storage"),
        (508, "Loop Detected"),
        (510, "Not Extended"),
        (511, "Network Authentication Required"),
    ],
)
@respx.mock
async def test_send_slack_notification_when_error(status_code, reason_phrase):
    http_client = AsyncClient()
    controller = HttpProxyController("http://example.com/", http_client=http_client)
    respx.get("http://example.com/").mock(return_value=Response(status_code, content=b"{}"))

    request = HttpRequest(HttpRequestStubBridge(method="GET"))

    with mock.patch("harp_apps.proxy.controllers.send_slack_notification") as mock_send_slack_notification, mock.patch(
        "asyncio.create_task"
    ) as mock_create_task:
        # Call the controller which should trigger the slack notification
        await controller(request)

        # Check if create_task was called
        assert mock_create_task.called

        # Check if send_slack_notification was called within create_task
        assert mock_send_slack_notification.called

        # Extract the arguments passed to send_slack_notification
        _, notification_kwargs = mock_send_slack_notification.call_args

        # Validate the arguments of send_slack_notification
        assert notification_kwargs["status_code"] == status_code
        assert notification_kwargs["message"] == reason_phrase


@pytest.mark.parametrize(
    "exception,status_code,  expected_message",
    [
        (NetworkError(""), 503, "Service Unavailable (remote server unavailable)"),
        (TimeoutException(""), 504, "Gateway Timeout (remote server timeout)"),
        (RemoteProtocolError(""), 502, "Bad Gateway (remote server disconnected)"),
    ],
)
@respx.mock
async def test_send_slack_notification_on_http_client_exception(exception, status_code, expected_message):
    http_client = AsyncClient()
    controller = HttpProxyController("http://example.com/", http_client=http_client)
    respx.get("http://example.com/").mock(side_effect=exception)
    request = HttpRequest(HttpRequestStubBridge(method="GET"))

    with mock.patch("harp_apps.proxy.controllers.send_slack_notification") as mock_send_slack_notification, mock.patch(
        "asyncio.create_task"
    ) as mock_create_task:
        # Call the controller which should handle the exception
        await controller(request)

        # Check if create_task was called
        assert mock_create_task.called

        # Check if send_slack_notification was called within create_task
        assert mock_send_slack_notification.called

        # Extract the arguments passed to send_slack_notification
        _, notification_kwargs = mock_send_slack_notification.call_args

        # Validate the arguments of send_slack_notification
        assert notification_kwargs["status_code"] == status_code
        assert notification_kwargs["message"] == expected_message
