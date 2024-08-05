from httpx import AsyncClient


class GoogleChatNotificationSender:
    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url
        self.client = AsyncClient()

    async def send_notification(
        self, method: str, url: str, status_code: int, message: str, transaction_id: str
    ) -> None:
        error_message = self._format_error_message(method, url, status_code, message, transaction_id)
        async with self.client as client:
            response = await client.post(self.webhook_url, json=error_message)
            response.raise_for_status()
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    @staticmethod
    def _format_error_message(method: str, url: str, status_code: int, message: str, transaction_id: str) -> dict:
        return {
            "cards": [
                {
                    "header": {
                        "title": "🔴 Error Notification",
                    },
                    "sections": [
                        {"widgets": [{"textParagraph": {"text": f"<b>Error in {method} request to {url}</b>"}}]},
                        {
                            "widgets": [
                                {"keyValue": {"topLabel": "Error Code", "content": f"<b>{status_code}</b>"}},
                                {"keyValue": {"topLabel": "Status", "content": message}},
                            ]
                        },
                        {"widgets": [{"textParagraph": {"text": f"<i>Transaction ID:</i> <b>{transaction_id}</b>"}}]},
                        {
                            "widgets": [
                                {
                                    "buttons": [
                                        {
                                            "textButton": {
                                                "text": "VIEW LOGS",
                                                "onClick": {"openLink": {"url": "https://example.com/logs"}},
                                            }
                                        }
                                    ]
                                }
                            ]
                        },
                    ],
                }
            ]
        }
