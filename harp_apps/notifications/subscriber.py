import asyncio
from typing import List, Optional
from urllib.parse import urlsplit, urlunsplit

from harp import get_logger
from whistle import IAsyncEventDispatcher

from harp.asgi.events import EVENT_CORE_RESPONSE, ResponseEvent
from harp_apps.notifications.senders.google_chat import GoogleChatNotificationSender
from harp_apps.notifications.senders.slack import SlackNotificationSender
from harp_apps.notifications.settings import NotificationsSettings
from harp_apps.notifications.typing import NotificationSender

logger = get_logger(__name__)

AVAILABLE_WEBHOOK_URLS = ["slack_webhook_url", "google_chat_webhook_url"]


def _without_query(url: Optional[str]) -> Optional[str]:
    """Keep scheme, host and path only: the query string and fragment can hold credentials."""
    if not url:
        return url
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc.rpartition("@")[2], parts.path, "", ""))


class NotificationSubscriber:
    def __init__(self, settings: NotificationsSettings, public_url: Optional[str] = None):
        self.senders: List[NotificationSender] = []
        self.timeout = settings.timeout
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=settings.queue_size)
        self._worker: Optional[asyncio.Task] = None
        for name in AVAILABLE_WEBHOOK_URLS:
            if name == "google_chat_webhook_url":
                try:
                    webhook_url = getattr(settings, name)
                    (
                        self.senders.append(GoogleChatNotificationSender(webhook_url, public_url, self.timeout))
                        if webhook_url
                        else None
                    )
                except AttributeError:
                    pass
            elif name == "slack_webhook_url":
                try:
                    webhook_url = getattr(settings, name)
                    (
                        self.senders.append(SlackNotificationSender(webhook_url, public_url, self.timeout))
                        if webhook_url
                        else None
                    )
                except AttributeError:
                    pass

    def subscribe(self, dispatcher: IAsyncEventDispatcher):
        dispatcher.add_listener(EVENT_CORE_RESPONSE, self.on_response_send_error_notifications)

    def unsubscribe(self, dispatcher: IAsyncEventDispatcher):
        dispatcher.remove_listener(EVENT_CORE_RESPONSE, self.on_response_send_error_notifications)

    async def on_response_send_error_notifications(self, event: ResponseEvent):
        if 500 <= event.response.status < 600:
            transaction = event.request.extensions.get("transaction")
            self._enqueue(
                dict(
                    method=event.request.extensions.get("remote_method"),
                    url=_without_query(event.request.extensions.get("remote_url")),
                    status_code=event.response.status,
                    message=event.response.reason_phrase,
                    transaction_id=transaction.id if transaction else None,
                )
            )

    def _enqueue(self, notification: dict) -> None:
        """Queue a notification without ever blocking the response; drop it when the queue is full."""
        if self._worker is None or self._worker.done():
            self._worker = asyncio.get_running_loop().create_task(self._run())
        try:
            self._queue.put_nowait(notification)
        except asyncio.QueueFull:
            logger.warning("notifications queue is full, notification dropped", status_code=notification["status_code"])

    async def _run(self) -> None:
        while True:
            notification = await self._queue.get()
            try:
                await self.send_notification(**notification)
            except Exception as exc:  # the worker must outlive any failure
                logger.warning("notification failed", error=repr(exc))
            finally:
                self._queue.task_done()

    async def join(self) -> None:
        """Wait until every queued notification has been handled."""
        await self._queue.join()

    async def aclose(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            await asyncio.gather(self._worker, return_exceptions=True)
            self._worker = None
        for sender in self.senders:
            close = getattr(sender, "aclose", None)
            if close:
                await close()

    async def send_notification(
        self,
        method: Optional[str],
        url: Optional[str],
        status_code: int,
        message: str,
        transaction_id: Optional[str],
    ) -> None:
        await asyncio.gather(
            *(
                self._send_with_sender(sender, method, url, status_code, message, transaction_id)
                for sender in self.senders
            )
        )

    async def _send_with_sender(self, sender: NotificationSender, *args) -> None:
        """Deliver through one sender; its timeout or failure is logged, never raised."""
        try:
            async with asyncio.timeout(self.timeout):
                await sender.send_notification(*args)
        except Exception as exc:
            logger.warning(
                "notification sender failed", sender=type(sender).__name__, error=repr(exc) or type(exc).__name__
            )
