from unittest import mock

import pytest

from harp_apps.notifications.senders import SlackNotificationSender
from harp_apps.notifications.senders.slack import AsyncWebhookClient


@pytest.mark.parametrize(
    "public_url, expected_link",
    [
        ("https://example.com", True),
        (None, False),
    ],
)
def test_message_does_not_contain_link_if_no_public_url(public_url, expected_link):
    notification_sender = SlackNotificationSender("https://slack.com/webhook")

    message = notification_sender._format_error_message(
        "GET", "https://example.com", 500, "Server Error", "123", public_url
    )

    blocks = message["blocks"]

    # check that block does not contain any "action" typed elements
    link_button = any(v == "actions" for block in blocks for k, v in block.items())

    assert link_button == expected_link


async def test_send_notification():
    with mock.patch.object(AsyncWebhookClient, "send", new_callable=mock.AsyncMock) as mock_send:
        webhook_url = "http://example.com/webhook"
        public_url = "http://example.com"
        sender = SlackNotificationSender(webhook_url, public_url)

        mock_send.return_value.status_code = 200
        mock_send.return_value.body = "ok"

        method = "POST"
        url = "http://example.com/api"
        status_code = 500
        message = "Internal Server Error"
        transaction_id = "12345"

        await sender.send_notification(method, url, status_code, message, transaction_id)
        mock_send.assert_called_once()
        assert mock_send.call_args[1]["text"] == "ERROR NOTIFICATION"
