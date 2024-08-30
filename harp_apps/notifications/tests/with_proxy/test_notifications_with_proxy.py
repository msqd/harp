from unittest import mock

from harp.config import ConfigurationBuilder
from harp.utils.testing.communicators import ASGICommunicator


async def test_notifications_with_proxy(httpbin):
    settings = {
        "applications": ["http_client", "proxy", "notifications"],
        "proxy": {"endpoints": [{"name": "httpbin", "port": 80, "url": httpbin}]},
        "notifications": {
            "slack_webhook_url": "https://slack.com",
            "google_chat_webhook_url": "https://chat.google.com",
        },
    }

    system = await ConfigurationBuilder(settings, use_default_applications=False).abuild_system()

    client = ASGICommunicator(system.kernel)
    await client.asgi_lifespan_startup()

    with mock.patch("harp_apps.notifications.subscriber.NotificationSubscriber.send_notification") as send_notification:
        await client.http_get("/status/502")
        assert send_notification.called
        _, send_notification_kwargs = send_notification.call_args
        assert send_notification_kwargs["status_code"] == 502
        assert send_notification_kwargs["message"] == "Bad Gateway"
        assert send_notification_kwargs["method"] == "GET"
