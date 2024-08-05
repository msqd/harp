import os

from slack_sdk.webhook.async_client import AsyncWebhookClient

URL = os.getenv("SLACK_WEBHOOK_URL", "")


client = AsyncWebhookClient(URL)


async def send_slack_notification(method: str, url: str, status_code: int, message: str, transaction_id: str) -> None:
    slack_message = _format_error_message(method, url, status_code, message, transaction_id)
    response = await client.send(text="ERROR NOTIFICATION", blocks=slack_message["blocks"])
    assert response.status_code == 200
    assert response.body == "ok"


def _format_error_message(method: str, url: str, status_code: int, message: str, transaction_id: str) -> dict:
    return {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": ":red_circle: Error Notification", "emoji": True},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"Error in {method} request to {url}"},
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
                "elements": [{"type": "mrkdwn", "text": f":pager: *Transaction ID:* `{transaction_id}`"}],
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Logs", "emoji": True},
                        "url": "https://example.com/logs",
                        "style": "primary",
                    },
                ],
            },
        ]
    }
