import traceback
from copy import deepcopy
from functools import cached_property
from types import MappingProxyType

import httpx
from httpx._status_codes import codes

from harp import get_logger
from harp.apis.asgi import ManagementApplication
from harp.asgi import AsgiContext, asgi
from harp.errors import EndpointNotFound, ProxyError
from harp.models.message import Request, Response
from harp.models.proxy_endpoint import ProxyEndpoint
from harp.models.transaction import Transaction
from harp.services import create_config, create_container
from harp.services.http import client
from harp.services.storage.base import Storage

auto = object()


logger = get_logger(__name__)


class Proxy:
    def __init__(self, *, endpoints, container):
        self._endpoints = endpoints
        self.app = ManagementApplication(container=container)

    async def __call__(self, scope, receive, send):
        with AsgiContext(scope, receive, send) as ctx:
            try:
                if ctx.type == "lifespan":
                    return await self.app(ctx.scope, ctx.receive, ctx.send)
                elif ctx.type == "http":
                    return await self.handle_http_request(ctx)
                else:
                    raise ProxyError(f"Unsupported scope type: {ctx.type}")
            except EndpointNotFound:
                return await self.not_found(ctx, f"No endpoint found for port {ctx.server_port}.")
            except Exception as exc:
                logger.exception(exc)
                return await self.server_error(ctx, f"Unhandled server error: {str(exc)}")

    @cached_property
    def storage(self):
        return self.app.service_provider.get(Storage)

    async def not_found(self, ctx: AsgiContext, message="Not found."):
        """
        Build and send a 404 response to the given asgi context.

        """
        return await ctx.send_all(
            asgi.http.response.start(status=404),
            asgi.http.response.body(body=bytes(message, "utf-8")),
        )

    async def server_error(self, ctx: AsgiContext, message="Server error."):
        """
        Build and send a 500 response to the given asgi context.

        """
        return await ctx.send_all(
            asgi.http.response.start(status=500),
            asgi.http.response.body(body=bytes(message, "utf-8")),
        )

    async def get_proxy_endpoint_from_asgi_context(self, ctx: AsgiContext) -> ProxyEndpoint:
        try:
            return self._endpoints[ctx.server_port]
        except KeyError as exc:
            raise EndpointNotFound() from exc

    async def handle_http_request(self, ctx: AsgiContext):
        endpoint = await self.get_proxy_endpoint_from_asgi_context(ctx)

        # special case for ui endpoint, should become something more generic at some point but does the job for now
        # 2 cases: either the ui is served from the static build, or it's proxied to dev server. The later will use
        # the standard proxy code while the former delegates frontend app assets to the blacksheep static file handler.
        if endpoint.name == "ui" and (self.app.has_static_build or ctx.scope["path"].startswith("/api/")):
            return await self.app(ctx.scope, ctx.receive, ctx.send)

        # retrieve the proxy target for this request, a.k.a. where and what to forward
        proxy_target = endpoint.get_target(ctx.scope)
        logger.info(f"◀ {proxy_target.method} {proxy_target.path}")

        with self.storage.store(
            Transaction(endpoint=endpoint), mode="ignore" if endpoint.name == "ui" else "save"
        ) as transaction:
            ## REQUEST (from client)
            transaction.request = Request.from_proxy_target(proxy_target)
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
                request: httpx.Request = client.build_request(
                    transaction.request.method,
                    transaction.request.url,
                    headers=transaction.request.headers,
                    content=content,
                )
                ### SEND REQUEST (to remote endpoint)
                response: httpx.Response = await client.send(request)

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
        return self.ProxyType(endpoints=MappingProxyType(deepcopy(self.ports)), container=self.container)

    def run(self):
        proxy = self.create()

        import logging

        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        config = Config()
        config.bind = [f"0.0.0.0:{port}" for port in proxy._endpoints]
        config.accesslog = logging.getLogger("hypercorn.access")
        config.errorlog = logging.getLogger("hypercorn.error")

        import anyio

        anyio.run(serve, proxy, config, backend="asyncio", backend_options={"use_uvloop": True})
