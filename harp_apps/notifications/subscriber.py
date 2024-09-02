import asyncio
from typing import List, Optional

from whistle import IAsyncEventDispatcher

from harp.asgi.events import EVENT_CORE_RESPONSE, ResponseEvent
from harp_apps.notifications.senders.google_chat import GoogleChatNotificationSender
from harp_apps.notifications.senders.slack import SlackNotificationSender
from harp_apps.notifications.settings import NotificationsSettings
from harp_apps.notifications.typing import NotificationSender

AVAILABLE_WEBHOOK_URLS = ["slack_webhook_url", "google_chat_webhook_url"]


class NotificationSubscriber:
    def __init__(self, settings: NotificationsSettings, public_url: Optional[str] = None):
        self.senders: List[NotificationSender] = []
        for name in AVAILABLE_WEBHOOK_URLS:
            if name == "google_chat_webhook_url":
                try:
                    webhook_url = getattr(settings, name)
                    (
                        self.senders.append(GoogleChatNotificationSender(webhook_url, public_url))
                        if webhook_url
                        else None
                    )
                except AttributeError:
                    pass
            elif name == "slack_webhook_url":
                try:
                    webhook_url = getattr(settings, name)
                    (self.senders.append(SlackNotificationSender(webhook_url, public_url)) if webhook_url else None)
                except AttributeError:
                    pass

    def subscribe(self, dispatcher: IAsyncEventDispatcher):
        dispatcher.add_listener(EVENT_CORE_RESPONSE, self.on_response_send_error_notifications)

    def unsubscribe(self, dispatcher: IAsyncEventDispatcher):
        dispatcher.remove_listener(EVENT_CORE_RESPONSE, self.on_response_send_error_notifications)

    async def on_response_send_error_notifications(self, event: ResponseEvent):
        if 500 <= event.response.status < 600:
            transaction = event.request.extensions.get("transaction")
            await self.send_notification(
                method=event.request.extensions.get("remote_method"),
                url=event.request.extensions.get("remote_url"),
                status_code=event.response.status,
                message=event.response.reason_phrase,
                transaction_id=transaction.id if transaction else None,
            )

    async def send_notification(
        self,
        method: Optional[str],
        url: Optional[str],
        status_code: int,
        message: str,
        transaction_id: Optional[str],
    ) -> None:
        async with asyncio.TaskGroup() as tg:
            for sender in self.senders:
                tg.create_task(sender.send_notification(method, url, status_code, message, transaction_id))
