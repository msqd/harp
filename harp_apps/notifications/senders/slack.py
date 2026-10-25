from typing import Optional

from httpx import AsyncClient


def _escape_mrkdwn(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class SlackNotificationSender:
    def __init__(self, webhook_url: str, public_url: Optional[str] = None, timeout: float = 5.0) -> None:
        self.webhook_url = webhook_url
        self.public_url = public_url
        self._client = AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def send_notification(
        self,
        method: Optional[str],
        url: Optional[str],
        status_code: int,
        message: str,
        transaction_id: Optional[str],
    ) -> None:
        slack_message = self._format_error_message(method, url, status_code, message, transaction_id, self.public_url)
        response = await self._client.post(
            self.webhook_url, json={"text": "ERROR NOTIFICATION", "blocks": slack_message["blocks"]}
        )
        response.raise_for_status()

    @staticmethod
    def _format_error_message(
        method: Optional[str],
        url: Optional[str],
        status_code: int,
        message: str,
        transaction_id: Optional[str],
        public_url: Optional[str] = None,
    ) -> dict:
        url, message = _escape_mrkdwn(url or ""), _escape_mrkdwn(message)
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":red_circle: Error Notification",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Error in {method} request to {url}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Error Code:*\n`{status_code}`"},
                    {"type": "mrkdwn", "text": f"*Status:*\n{message}"},
                ],
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f":pager: *Transaction ID:* `{transaction_id}`",
                    }
                ],
            },
        ]

        if public_url:
            blocks.append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Logs",
                                "emoji": True,
                            },
                            "url": f"{public_url}/transactions/{transaction_id}",
                            "style": "primary",
                        },
                    ],
                },
            )
        return {"blocks": blocks}
