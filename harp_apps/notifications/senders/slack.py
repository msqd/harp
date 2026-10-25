from typing import Optional

from harp_apps.notifications.senders.base import WebhookNotificationSender


def _escape_mrkdwn(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class SlackNotificationSender(WebhookNotificationSender):
    def _build_payload(
        self,
        method: Optional[str],
        url: Optional[str],
        status_code: int,
        message: str,
        transaction_id: Optional[str],
    ) -> dict:
        slack_message = self._format_error_message(method, url, status_code, message, transaction_id, self.public_url)
        return {"text": "ERROR NOTIFICATION", "blocks": slack_message["blocks"]}

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
