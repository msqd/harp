import asyncio
import logging
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
        await notification_subscriber.join()
        assert send_notification.called
        _, send_notification_kwargs = send_notification.call_args

        assert send_notification_kwargs["method"] == "GET"
        assert send_notification_kwargs["url"] == "http://example.com"
        assert send_notification_kwargs["status_code"] == status_code
        assert send_notification_kwargs["message"] == reason_phrase


def _subscriber_with(*senders, **settings):
    subscriber = NotificationSubscriber(NotificationsSettings(**settings))
    subscriber.senders = list(senders)
    return subscriber


def _sender(side_effect=None):
    sender = mock.Mock(spec=["send_notification"])
    sender.send_notification = mock.AsyncMock(side_effect=side_effect)
    return sender


async def _notify(subscriber, status=502):
    event = ResponseEvent(
        HttpRequest(extensions={"remote_url": "http://example.com", "remote_method": "GET"}),
        HttpResponse(b"", status=status),
    )
    await subscriber.on_response_send_error_notifications(event)


async def test_response_does_not_wait_for_senders():
    release = asyncio.Event()

    async def slow(*args):
        await release.wait()

    sender = _sender(side_effect=slow)
    subscriber = _subscriber_with(sender)

    await asyncio.wait_for(_notify(subscriber), timeout=1)
    release.set()
    await subscriber.join()

    assert sender.send_notification.called
    await subscriber.aclose()


async def test_failing_sender_does_not_raise_nor_cancel_others(caplog):
    failing = _sender(side_effect=ConnectionError("boom"))
    healthy = _sender()
    subscriber = _subscriber_with(failing, healthy)

    with caplog.at_level(logging.WARNING):
        await _notify(subscriber)
        await subscriber.join()

    assert healthy.send_notification.called
    assert any(r.levelno == logging.WARNING and "boom" in r.getMessage() for r in caplog.records)
    await subscriber.aclose()


async def test_slow_sender_times_out_without_blocking_others(caplog):
    async def hang(*args):
        await asyncio.sleep(60)

    slow = _sender(side_effect=hang)
    healthy = _sender()
    subscriber = _subscriber_with(slow, healthy, timeout=0.05)

    with caplog.at_level(logging.WARNING):
        await _notify(subscriber)
        await asyncio.wait_for(subscriber.join(), timeout=2)

    assert healthy.send_notification.called
    assert any(r.levelno == logging.WARNING for r in caplog.records)
    await subscriber.aclose()


async def test_burst_is_bounded_and_overflow_is_dropped(caplog):
    release = asyncio.Event()

    async def slow(*args):
        await release.wait()

    sender = _sender(side_effect=slow)
    subscriber = _subscriber_with(sender, queue_size=2)

    with caplog.at_level(logging.WARNING):
        for _ in range(10):
            await _notify(subscriber)
        await asyncio.sleep(0)  # worker takes the first one
        release.set()
        await subscriber.join()

    assert sender.send_notification.call_count <= 3
    assert any("dropped" in r.getMessage() for r in caplog.records)
    await subscriber.aclose()
