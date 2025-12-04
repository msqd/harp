from typing import Optional

from harp.config import Configurable, ApplicationSettingsMixin


class NotificationsSettings(ApplicationSettingsMixin, Configurable):
    enabled: bool = True
    slack_webhook_url: Optional[str] = None
    google_chat_webhook_url: Optional[str] = None
