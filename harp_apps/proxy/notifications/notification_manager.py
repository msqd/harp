import asyncio
from typing import List, Optional, Protocol

from harp_apps.notifications.settings import NotificationsSettings
from harp_apps.proxy.notifications.google_chat import GoogleChatNotificationSender
from harp_apps.proxy.notifications.slack import SlackNotificationSender

AVAILABLE_WEBHOOK_URLS = ["slack_webhook_url", "google_chat_webhook_url"]


class NotificationSender(Protocol):
    async def send_notification(
        self, method: str, url: str, status_code: int, message: str, transaction_id: str
    ) -> None: ...


class NotificationManager:
    def __init__(self, settings: NotificationsSettings, public_url: Optional[str] = None):
        self.senders: List[NotificationSender] = []
        for name in AVAILABLE_WEBHOOK_URLS:
            if name == "google_chat_webhook_url":
                try:
                    webhook_url = getattr(settings, name)
                    self.senders.append(GoogleChatNotificationSender(webhook_url, public_url)) if webhook_url else None
                except AttributeError:
                    pass
            elif name == "slack_webhook_url":
                try:
                    webhook_url = getattr(settings, name)
                    self.senders.append(SlackNotificationSender(webhook_url, public_url)) if webhook_url else None
                except AttributeError:
                    pass

    async def send_notification(
        self, method: str, url: str, status_code: int, message: str, transaction_id: str
    ) -> None:
        async with asyncio.TaskGroup() as tg:
            for sender in self.senders:
                tg.create_task(sender.send_notification(method, url, status_code, message, transaction_id))
