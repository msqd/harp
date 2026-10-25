"""A configuration validation error names the offending key, never the value it was given."""

import pytest
from pydantic import ValidationError

from harp_apps.contrib.sentry.settings import SentrySettings
from harp_apps.notifications.settings import NotificationsSettings

WEBHOOK = "https://hooks.slack.example/services/T000/B000/FAKESECRET"
DSN = "https://fakekey@o0.ingest.sentry.example/0"


@pytest.mark.parametrize(
    "settings_type, values, key",
    [
        (NotificationsSettings, {"webhook_url": WEBHOOK}, "webhook_url"),
        (SentrySettings, {"dns": DSN}, "dns"),
        (NotificationsSettings, {"slack_webhook_url": WEBHOOK, "timeout": WEBHOOK}, "timeout"),
    ],
)
def test_error_names_the_key_and_hides_the_value(settings_type, values, key):
    with pytest.raises(ValidationError) as exc_info:
        settings_type(**values)

    message = str(exc_info.value)
    assert key in message
    assert "FAKESECRET" not in message
    assert "fakekey" not in message
