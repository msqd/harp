import json

import httpx
import pytest
import respx

from harp_apps.notifications.senders import SlackNotificationSender


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


@respx.mock
async def test_send_notification():
    route = respx.post("http://example.com/webhook").mock(return_value=httpx.Response(200, text="ok"))
    sender = SlackNotificationSender("http://example.com/webhook", "http://example.com")

    await sender.send_notification("POST", "http://example.com/api", 500, "Internal Server Error", "12345")

    assert route.call_count == 1
    payload = json.loads(route.calls.last.request.content)
    assert payload["text"] == "ERROR NOTIFICATION"
    assert payload["blocks"][0]["type"] == "header"


@respx.mock
async def test_send_notification_reports_failure_as_http_error_and_reuses_client():
    respx.post("http://example.com/webhook").mock(return_value=httpx.Response(500, text="boom"))
    sender = SlackNotificationSender("http://example.com/webhook")
    client = sender._client

    for _ in range(2):
        with pytest.raises(httpx.HTTPStatusError):
            await sender.send_notification("GET", "http://example.com/", 500, "Error", "1")

    assert sender._client is client
    await sender.aclose()


def test_message_escapes_mrkdwn_control_characters():
    message = SlackNotificationSender._format_error_message(
        "GET", "https://example.com/a<b>&y", 500, "<!channel> & co", "123"
    )

    rendered = json.dumps(message)
    assert "<!channel>" not in rendered
    assert "https://example.com/a&lt;b&gt;&amp;y" in rendered
    assert "&lt;!channel&gt; &amp; co" in rendered
