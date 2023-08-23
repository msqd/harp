import pprint
import traceback
from copy import deepcopy
from functools import cached_property
from types import MappingProxyType
from urllib.parse import urljoin

import httpx
from httpx._status_codes import codes

from harp import logging
from harp.apis.asgi import ManagementApplication
from harp.models.message import Request, Response
from harp.models.proxy_endpoint import ProxyEndpoint
from harp.models.transaction import Transaction
from harp.services import create_config, create_container
from harp.services.http import client
from harp.services.storage.base import Storage

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
        logger.debug(f"◁ ENTER {self.type}", **self._scope)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return

    def send(self, ctx):
        logger.debug(f"▷ SEND {ctx['type']}", **ctx)
        return self._send(ctx)

    async def send_all(self, *ctxs):
        for ctx in ctxs:
            await self.send(ctx)

    async def receive(self):
        retval = await self._receive()
        logger.debug(f"◁ RECV {self.type}", **retval)
        return retval


class Proxy:
    def __init__(self, *, ports, container):
        self.ports = ports
        self.app = ManagementApplication(container=container)

    @cached_property
    def storage(self):
        return self.app.service_provider.get(Storage)

    async def __call__(self, scope, receive, send):
        with AsgiContext(scope, receive, send) as ctx:
            return await self.handle(ctx)

    async def handle(self, ctx: AsgiContext):
        if ctx.type == "lifespan":
            return await self.app(ctx.scope, ctx.receive, ctx.send)
        elif ctx.type != "http":
            return

        endpoint = self.ports.get(ctx.scope["server"][1], None)

        if endpoint.name == "ui" and (self.app.has_static_build or ctx.scope["path"].startswith("/api/")):
            return await self.app(ctx.scope, ctx.receive, ctx.send)

        if not endpoint:
            await ctx.send_all(
                asgi.http.response.start(status=404),
                asgi.http.response.body(body=bytes(f'No endpoint found for path "{ctx.scope["path"]}".', "utf-8")),
            )
            return

        ctx.scope["proxy"] = endpoint.get_proxy_scope(ctx.scope)

        pprint.pprint(ctx.scope)

        logger.info(f"◀ {ctx.scope['proxy']['method']} {ctx.scope['proxy']['path']}")

        scope_filters = ()
        for scope_filter in scope_filters:
            await scope_filter(ctx.scope)

        response: httpx.Response

        with self.storage.store(
            Transaction(endpoint=endpoint), mode="ignore" if endpoint.name == "ui" else "save"
        ) as transaction:
            ## REQUEST (from client)
            request_headers = tuple(((k, v) for k, v in ctx.scope["headers"] if k.lower() not in (b"host",)))
            transaction.request = Request(
                ctx.scope["proxy"]["method"],
                urljoin(ctx.scope["proxy"]["target"], ctx.scope["proxy"]["path"])
                + (f"?{ctx.scope['query_string'].decode('utf-8')}" if ctx.scope["query_string"] else ""),
                headers=request_headers,
                body=None,
                endpoint=endpoint,
            )

            try:
                messages = []
                more_body = True
                while more_body:
                    message = await ctx.receive()
                    more_body = message.get("more_body", False)
                    if len(message["body"]):
                        messages.append(message["body"])

                content = b"".join(messages) if len(messages) else None
                logger.info(
                    f"▶▶ {transaction.request.method} {transaction.request.url}", **transaction.request.asdict()
                )
                request = client.build_request(
                    transaction.request.method,
                    transaction.request.url,
                    headers=transaction.request.headers,
                    content=content,
                )
                ### SEND REQUEST (to remote endpoint)
                response = await client.send(request)

                logger.info(f"◀◀ {response.status_code} {response.reason_phrase}")
            except Exception as exc:
                logger.info(f"▶ 503 {codes.get_reason_phrase(503)}")
                tb = "\n".join(traceback.format_exception(exc))
                return await ctx.send_all(
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

            ### SEND RESPONSE (to client)
            await ctx.send(asgi.http.response.start(status=response.status_code, headers=headers))
            transaction.response = Response(response.status_code, headers, response.content)

            await ctx.send(asgi.http.response.body(body=response.content))


class ProxyFactory:
    ProxyType = Proxy

    def __init__(self, *, settings=None, port=4000, ui=True, ui_port=4080):
        self.config = create_config(settings)
        self.container = create_container(self.config)
        self.ports = {}
        self._next_available_port = port

        if ui:
            endpoint = ProxyEndpoint("http://localhost:4999/", name="ui")
            self.ports[ui_port or self.next_available_port()] = endpoint

    def next_available_port(self):
        while self._next_available_port in self.ports:
            self._next_available_port += 1
        try:
            return self._next_available_port
        finally:
            self._next_available_port += 1

    def add(self, target, *, port=auto, name=None):
        if port is auto:
            port = self.next_available_port()

        self.ports[port] = ProxyEndpoint(target, name=name)
        return self.ports[port]

    def create(self):
        # Make it has hard as possible to modify configuration at runtime, outside the factory. Of course, if you really
        # want to write a # shitload of crappy code, you can.
        return self.ProxyType(ports=MappingProxyType(deepcopy(self.ports)), container=self.container)

    def run(self):
        proxy = self.create()

        import logging as python_logging

        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        config = Config()
        config.bind = [f"0.0.0.0:{port}" for port in proxy.ports]
        config.accesslog = python_logging.getLogger("hypercorn.access")
        config.errorlog = python_logging.getLogger("hypercorn.error")

        import anyio

        anyio.run(serve, proxy, config, backend="asyncio", backend_options={"use_uvloop": True})
