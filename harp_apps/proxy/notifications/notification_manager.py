import asyncio
import os
from typing import List, Protocol

from harp_apps.proxy.notifications.google_chat import GoogleChatNotificationSender
from harp_apps.proxy.notifications.slack import SlackNotificationSender

WEBHOOK_URLS = {"google_chat": os.getenv("GOOGLE_CHAT_WEBHOOK_URL"), "slack": os.getenv("SLACK_WEBHOOK_URL")}


class NotificationSender(Protocol):
    async def send_notification(
        self, method: str, url: str, status_code: int, message: str, transaction_id: str
    ) -> None: ...


class NotificationManager:
    def __init__(self):
        self.senders: List[NotificationSender] = []
        for name, url in WEBHOOK_URLS.items():
            if url:
                if name == "google_chat":
                    self.senders.append(GoogleChatNotificationSender(url)) if url else None
                elif name == "slack":
                    self.senders.append(SlackNotificationSender(url)) if url else None

    async def send_notification(
        self, method: str, url: str, status_code: int, message: str, transaction_id: str
    ) -> None:
        async with asyncio.TaskGroup() as tg:
            for sender in self.senders:
                tg.create_task(sender.send_notification(method, url, status_code, message, transaction_id))
