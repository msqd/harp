from typing import cast
from unittest import mock

import pytest
import respx
from whistle import AsyncEventDispatcher, IAsyncEventDispatcher

from harp.asgi.events import EVENT_CORE_RESPONSE, ResponseEvent
from harp.http import HttpRequest, HttpResponse
from harp_apps.notifications.settings import NotificationsSettings
from harp_apps.notifications.subscriber import NotificationSubscriber


async def test_send_one_notification_per_sender():
    notification_manager = NotificationSubscriber(NotificationsSettings())
    notification_manager.senders = [mock.Mock(), mock.Mock()]
    for sender in notification_manager.senders:
        sender.send_notification = mock.AsyncMock()

    await notification_manager.send_notification("GET", "http://example.com/", 500, "Internal Server Error", "123")

    assert all(sender.send_notification.called for sender in notification_manager.senders)
    assert all(  # Check if the arguments are passed correctly
        sender.send_notification.call_args
        == mock.call("GET", "http://example.com/", 500, "Internal Server Error", "123")
        for sender in notification_manager.senders
    )


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
async def test_notification_subscriber(status_code, reason_phrase):
    request = HttpRequest(extensions={"remote_url": "http://example.com", "remote_method": "GET"})
    response = HttpResponse(b"", status=status_code)
    event = ResponseEvent(request, response)
    dispatcher = cast(IAsyncEventDispatcher, AsyncEventDispatcher())
    notification_subscriber = NotificationSubscriber(NotificationsSettings())
    notification_subscriber.subscribe(dispatcher)

    with mock.patch("harp_apps.notifications.subscriber.NotificationSubscriber.send_notification") as send_notification:
        await dispatcher.adispatch(EVENT_CORE_RESPONSE, event)
        assert send_notification.called
        _, send_notification_kwargs = send_notification.call_args

        assert send_notification_kwargs["method"] == "GET"
        assert send_notification_kwargs["url"] == "http://example.com"
        assert send_notification_kwargs["status_code"] == status_code
        assert send_notification_kwargs["message"] == reason_phrase
