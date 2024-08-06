import pytest

from harp_apps.notifications.senders import GoogleChatNotificationSender


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
