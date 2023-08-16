import traceback
from copy import deepcopy
from types import MappingProxyType
from urllib.parse import urljoin

import httpx
import structlog
from httpx._status_codes import codes

from harp import logging
from harp.apis.asgi import app as apiserver
from harp.models.message import Request, Response
from harp.models.transaction import Transaction
from harp.services.database.fake import fake_db
from harp.services.http import client

auto = object()


logger = logging.getLogger(__name__)


class asgi:
    class http:
        class response:
            @staticmethod
            def start(**kwargs):
                return {"type": "http.response.start", **kwargs}

            @staticmethod
            def body(**kwargs):
                return {"type": "http.response.body", **kwargs}


class ProxyEndpoint:
    def __init__(self, url):
        self.url = url


class AsgiContext:
    @property
    def scope(self):
        return self._scope

    @property
    def type(self):
        return self._scope["type"]

    def __init__(self, scope, receive, send):
        self._scope = scope
        self._receive = receive
        self._send = send

    def __enter__(self):
        logger.debug(f"◁ RECV {self.type}", **self._scope)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return

    def send(self, ctx):
        logger.debug(f"▷ SEND {ctx['type']}", **ctx)
        return self._send(ctx)

    async def send_all(self, *ctxs):
        for ctx in ctxs:
            await self.send(ctx)

    def receive(self, *args, **kwargs):
        raise NotImplementedError()


class Proxy:
    def __init__(self, *, ports):
        self.ports = ports

    def response(self, type, **kwargs):
        return {"type": f"http.response.{type}", **kwargs}

    async def __call__(self, scope, receive, send):
        with AsgiContext(scope, receive, send) as ctx:
            return await self.handle(ctx)

    async def handle(self, ctx: AsgiContext):
        if ctx.type == "lifespan":
            return await apiserver(ctx.scope, ctx.receive, ctx.send)
        elif ctx.type != "http":
            return

        if ctx.scope["path"].startswith("/api/"):
            subscope = {**ctx.scope, "path": ctx.scope["path"][4:], "raw_path": ctx.scope["raw_path"][4:]}
            return await apiserver(subscope, ctx.receive, ctx.send)

        endpoint = self.ports.get(ctx.scope["server"][1], None)

        if not endpoint:
            await ctx.send_all(
                asgi.http.response.start(status=404),
                asgi.http.response.body(body=bytes(f'No endpoint found for path "{ctx.scope["path"]}".', "utf-8")),
            )
            return

        ctx.scope["proxy"] = {
            "target": endpoint.url,
            "path": ctx.scope["raw_path"].decode("utf-8")
            + (("?" + ctx.scope["query_string"].decode("utf-8")) if ctx.scope["query_string"] else ""),
        }

        logger.info(f"◀ {ctx.scope['method']} {ctx.scope['proxy']['path']}")

        scope_filters = ()
        for scope_filter in scope_filters:
            await scope_filter(ctx.scope)

        response: httpx.Response
        transaction = Transaction()

        url = urljoin(ctx.scope["proxy"]["target"], ctx.scope["proxy"]["path"])
        request = client.request(ctx.scope["method"], url)
        transaction.request = Request(ctx.scope["method"], url, headers=(), body=None)
        try:
            logger.info(f"▶▶ {ctx.scope['method']} {transaction.request.url}", **transaction.request.asdict())
            response = await request
            logger.info(f"◀◀ {response.status_code} {response.reason_phrase}")
        except Exception as exc:
            logger.info(f"▶ 503 {codes.get_reason_phrase(503)}")
            tb = "\n".join(traceback.format_exception(exc))
            await ctx.send_all(
                asgi.http.response.start(status=503),
                asgi.http.response.body(
                    body=bytes(f"<h1>503 - Service Unavailable<h1>\n<pre>{tb}</pre>", "utf-8"),
                ),
            )

        # TODO content encoding removed because of gzip. we should handle that
        # TODO contant length removed because some api sends bullshit here that we cannot reuse
        headers = tuple(
            (
                (k, v)
                for k, v in response.headers.raw
                if k.lower() not in (b"server", b"date", b"content-encoding", b"content-length")
            )
        )

        logger.info(
            f"▶ {response.status_code} {codes.get_reason_phrase(response.status_code)}",
            **dict((k.decode("utf-8"), v.decode("utf-8")) for k, v in headers),
        )
        await ctx.send(asgi.http.response.start(status=response.status_code, headers=headers))
        transaction.response = Response(response.status_code, headers, response.content)

        await ctx.send(asgi.http.response.body(body=response.content))

        # db = await get_connection()
        # db.execute()
        fake_db.rows.append(transaction)


class ProxyFactory:
    ProxyType = Proxy

    def __init__(self, *, port=4000):
        self.ports = {}
        self._next_available_port = port

    def add(self, target, *, port=auto):
        if port is auto:
            while self._next_available_port in self.ports:
                self._next_available_port += 1
            port = self._next_available_port
            self._next_available_port += 1

        self.ports[port] = ProxyEndpoint(target)
        return self.ports[port]

    def create(self):
        # Make it has hard as possible to modify configuration at runtime, outside the factory. Of course, if you really
        # want to write a # shitload of crappy code, you can.
        return self.ProxyType(ports=MappingProxyType(deepcopy(self.ports)))

    def run(self):
        import asyncio

        import uvloop
        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        proxy = self.create()

        config = Config()
        config.bind = [f"0.0.0.0:{port}" for port in proxy.ports]
        config.accesslog = structlog.getLogger("hypercorn.access")
        config.errorlog = structlog.getLogger("hypercorn.error")

        uvloop.install()

        loop = asyncio.get_event_loop()
        server = serve(proxy, config)
        loop.run_until_complete(server)


class Harp:
    def __init__(self, *, port=4000):
        self._next_available_port = port
        self.ports = {}
