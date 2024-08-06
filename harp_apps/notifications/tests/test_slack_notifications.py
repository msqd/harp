import pytest

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
