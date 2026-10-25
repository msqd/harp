from html import escape
from typing import Optional

from httpx import AsyncClient  # noqa: F401  (patched by tests through this module)
from harp_apps.notifications.senders.base import WebhookNotificationSender


class GoogleChatNotificationSender(WebhookNotificationSender):
    def _build_payload(
        self,
        method: Optional[str],
        url: Optional[str],
        status_code: int,
        message: str,
        transaction_id: Optional[str],
    ) -> dict:
        return self._format_error_message(method, url, status_code, message, transaction_id, self.public_url)

    @staticmethod
    def _format_error_message(
        method: Optional[str],
        url: Optional[str],
        status_code: int,
        message: str,
        transaction_id: Optional[str],
        public_url: Optional[str] = None,
    ) -> dict:
        url, message = escape(url or "", quote=False), escape(message, quote=False)
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
