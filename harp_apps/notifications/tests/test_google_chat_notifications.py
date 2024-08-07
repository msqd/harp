from unittest import mock

import pytest

from harp_apps.notifications.senders import GoogleChatNotificationSender
from harp_apps.notifications.senders.google_chat import AsyncClient


@pytest.mark.parametrize(
    "public_url, expected_link",
    [
        ("https://example.com", True),
        (None, False),
    ],
)
def test_message_does_not_contain_link_if_no_public_url(public_url, expected_link):
    notification_sender = GoogleChatNotificationSender("https://slack.com/webhook")

    message = notification_sender._format_error_message(
        "GET", "https://example.com", 500, "Server Error", "123", public_url
    )

    sections = message["cards"][0]["sections"]

    def widget_contains_buttons(section):
        widgets = section.get("widgets")
        return any("buttons" in widget for widget in widgets)

    # check that block does not contain any "action" typed elements
    link_button = any(widget_contains_buttons(section) for section in sections)

    assert link_button == expected_link


async def test_send_notification():
    with mock.patch.object(AsyncClient, "post", new_callable=mock.AsyncMock) as mock_post:
        webhook_url = "http://example.com/webhook"
        public_url = "http://example.com"
        sender = GoogleChatNotificationSender(webhook_url, public_url)

        mock_post.return_value.status_code = 200

        method = "POST"
        url = "http://example.com/api"
        status_code = 500
        message = "Internal Server Error"
        transaction_id = "12345"

        await sender.send_notification(method, url, status_code, message, transaction_id)
        mock_post.assert_called_once()
        assert mock_post.call_args[0][0] == webhook_url
