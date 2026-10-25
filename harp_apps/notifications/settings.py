from typing import Optional

from harp.config import ApplicationSettingsMixin, Configurable, Secret


class NotificationsSettings(ApplicationSettingsMixin, Configurable):
    slack_webhook_url: Optional[Secret] = None
    google_chat_webhook_url: Optional[Secret] = None

    #: Seconds each sender gets to deliver one notification before it is abandoned.
    timeout: float = 5.0
    #: Maximum notifications waiting to be sent; beyond that, new ones are dropped.
    queue_size: int = 100
