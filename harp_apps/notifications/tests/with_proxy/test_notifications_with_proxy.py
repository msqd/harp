from unittest import mock

from harp.config import ConfigurationBuilder
from harp.utils.testing.communicators import ASGICommunicator


async def test_notifications_with_proxy(httpbin):
    """
    Test that notifications are sent for 5xx errors from proxied requests.

    This test verifies that:
    1. The proxy correctly handles error responses (including 502)
    2. The notification system correctly extracts the reason_phrase from responses
    3. The notification is triggered with the correct status code and message

    Regression test for: reason_phrase property should handle both str and bytes values
    """
    settings = {
        "applications": ["http_client", "proxy", "notifications"],
        "proxy": {"endpoints": [{"name": "httpbin", "port": 80, "url": httpbin}]},
        "notifications": {
            "slack_webhook_url": "https://slack.com",
            "google_chat_webhook_url": "https://chat.google.com",
        },
    }

    system = await ConfigurationBuilder(settings, use_default_applications=False).abuild_system(
        validate_dependencies=False
    )

    client = ASGICommunicator(system.asgi_app)
    await client.asgi_lifespan_startup()

    with mock.patch("harp_apps.notifications.subscriber.NotificationSubscriber.send_notification") as send_notification:
        # Request a 502 status from httpbin
        await client.http_get("/status/502")

        # Verify notification was triggered
        assert send_notification.called, "send_notification should be called for 5xx errors"

        # Extract the call arguments
        _, send_notification_kwargs = send_notification.call_args

        # Verify the notification contains the correct information
        assert send_notification_kwargs["status_code"] == 502, "Status code should be 502"
        assert send_notification_kwargs["message"] == "Bad Gateway", "Message should be 'Bad Gateway'"
        assert send_notification_kwargs["method"] == "GET", "HTTP method should be GET"
