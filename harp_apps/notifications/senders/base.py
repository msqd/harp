from typing import Optional

from httpx import AsyncClient


class WebhookNotificationSender:
    """Posts a notification to a webhook; subclasses only build the JSON payload."""

    def __init__(self, webhook_url: str, public_url: Optional[str] = None, timeout: float = 5.0) -> None:
        self.webhook_url = webhook_url
        self.public_url = public_url
        self._client = AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    def _build_payload(
        self,
        method: Optional[str],
        url: Optional[str],
        status_code: int,
        message: str,
        transaction_id: Optional[str],
    ) -> dict:
        raise NotImplementedError

    async def send_notification(
        self,
        method: Optional[str],
        url: Optional[str],
        status_code: int,
        message: str,
        transaction_id: Optional[str],
    ) -> None:
        payload = self._build_payload(method, url, status_code, message, transaction_id)
        response = await self._client.post(self.webhook_url, json=payload)
        response.raise_for_status()
