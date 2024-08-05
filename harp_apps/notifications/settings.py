from typing import Optional

from harp.config import DisableableBaseSettings, settings_dataclass


@settings_dataclass
class NotificationsSettings(DisableableBaseSettings):
    slack_webhook_url: Optional[str] = None
    google_chat_webhook_url: Optional[str] = None
