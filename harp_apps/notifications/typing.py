from typing import Optional, Protocol


class NotificationSender(Protocol):
    async def send_notification(
        self,
        method: Optional[str],
        url: Optional[str],
        status_code: int,
        message: str,
        transaction_id: Optional[str],
    ) -> None: ...
