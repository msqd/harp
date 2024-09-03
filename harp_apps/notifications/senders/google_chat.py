from typing import Optional

from httpx import AsyncClient


class GoogleChatNotificationSender:
    def __init__(self, webhook_url: str, public_url: Optional[str] = None) -> None:
        self.webhook_url = webhook_url
        self.public_url = public_url

    async def send_notification(
        self,
        method: Optional[str],
        url: Optional[str],
        status_code: int,
        message: str,
        transaction_id: Optional[str],
    ) -> None:
        error_message = self._format_error_message(method, url, status_code, message, transaction_id, self.public_url)
        async with AsyncClient() as client:
            response = await client.post(self.webhook_url, json=error_message)
            response.raise_for_status()
            assert response.status_code == 200

    @staticmethod
    def _format_error_message(
        method: Optional[str],
        url: Optional[str],
        status_code: int,
        message: str,
        transaction_id: Optional[str],
        public_url: Optional[str] = None,
    ) -> dict:
        sections = [
            {"widgets": [{"textParagraph": {"text": f"<b>Error in {method} request to {url}</b>"}}]},
            {
                "widgets": [
                    {
                        "keyValue": {
                            "topLabel": "Error Code",
                            "content": f"<b>{status_code}</b>",
                        }
                    },
                    {"keyValue": {"topLabel": "Status", "content": message}},
                ]
            },
            {"widgets": [{"textParagraph": {"text": f"<i>Transaction ID:</i> <b>{transaction_id}</b>"}}]},
        ]

        if public_url:
            sections.append(
                {
                    "widgets": [
                        {
                            "buttons": [
                                {
                                    "textButton": {
                                        "text": "VIEW LOGS",
                                        "onClick": {"openLink": {"url": f"{public_url}/transactions/{transaction_id}"}},
                                    }
                                }
                            ]  # type: ignore
                        }
                    ]
                }
            )
        return {
            "cards": [
                {
                    "header": {
                        "title": "🔴 Error Notification",
                    },
                    "sections": sections,
                }
            ]
        }
