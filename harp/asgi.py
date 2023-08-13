from urllib.parse import urljoin

import httpx

import harp
from harp.apis.asgi import app as apiserver
from harp.models.message import Request, Response
from harp.models.transaction import Transaction
from harp.services.database.asyncpg import get_connection
from harp.services.database.fake import fake_db
from harp.services.http import client
from harp.settings import USE_STREAMING


def get_asgi_app_for_router(router: "harp.Harp"):
    async def _asgi_app(scope, receive, send):
        if scope["type"] == "lifespan":
            return await apiserver(scope, receive, send)

        elif scope["type"] != "http":
            return

        if scope["path"].startswith("/api/"):
            subscope = {**scope, "path": scope["path"][4:], "raw_path": scope["raw_path"][4:]}
            return await apiserver(subscope, receive, send)

        (
            target_url,
            scope_filters,
            request_filters,
            response_filters,
        ) = router.find_by_scope(scope)

        if not target_url:
            await send(
                {
                    "type": "http.response.start",
                    "status": 404,
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": bytes(f'No handler found for path "{scope["path"]}".', "utf-8"),
                }
            )
            return

        for scope_filter in scope_filters:
            await scope_filter(scope)

        response: httpx.Response

        if USE_STREAMING:
            async with client.stream(scope["method"], urljoin(target_url, scope["remote_path"])) as response:
                await send(
                    {
                        "type": "http.response.start",
                        "status": response.status_code,
                        "headers": [(k, v) for k, v in response.headers.raw if k.lower() not in (b"server", b"date")],
                    }
                )

                async for chunk in response.aiter_bytes():
                    await send({"type": "http.response.body", "body": chunk, "more_body": True})

                await send(
                    {
                        "type": "http.response.body",
                        "body": b"",
                    }
                )
        else:
            transaction = Transaction()

            url = urljoin(target_url, scope["remote_path"])
            request = client.request(scope["method"], url)
            transaction.request = Request(scope["method"], url, headers=(), body=None)
            response = await request
            headers = tuple(((k, v) for k, v in response.headers.raw if k.lower() not in (b"server", b"date")))

            await send(
                {
                    "type": "http.response.start",
                    "status": response.status_code,
                    "headers": headers,
                }
            )
            transaction.response = Response(response.status_code, headers, response.content)

            await send(
                {
                    "type": "http.response.body",
                    "body": response.content,
                }
            )

            db = await get_connection()
            db.execute()
            fake_db.rows.append(transaction)

    return _asgi_app
