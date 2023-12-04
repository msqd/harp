import time

from asgiref.typing import ASGIReceiveCallable, ASGISendCallable, Scope
from httpx import codes
from whistle import Event

from harp import get_logger
from harp.contrib.sqlite_storage.events import on_startup, on_transaction_ended, on_transaction_started
from harp.core.asgi.events import (
    AsyncEventDispatcher,
    ControllerEvent,
    LoggingAsyncEventDispatcher,
    RequestEvent,
    ResponseEvent,
    TransactionMessageEvent,
)
from harp.core.asgi.requests import ASGIRequest
from harp.core.asgi.resolvers import ControllerResolver
from harp.core.asgi.responders import ASGIResponder
from harp.utils.guids import generate_transaction_id_ksuid

EVENT_CORE_CONTROLLER = "core.controller"
EVENT_CORE_REQUEST = "core.request"
EVENT_CORE_RESPONSE = "core.response"
EVENT_CORE_STARTED = "core.startup"
EVENT_TRANSACTION_ENDED = "transaction.ended"
EVENT_TRANSACTION_STARTED = "transaction.started"


logger = get_logger(__name__)


async def on_http_request(event):
    event.request.transaction_id = generate_transaction_id_ksuid()
    event.request.transaction_started_at = time.time()
    logger.info(
        f"▶ {event.request.method} {event.request.path}", transaction_id=getattr(event.request, "transaction_id", None)
    )
    # we don't really want to await this, should run in background ? or use an async queue ?
    await event.dispatcher.dispatch(
        EVENT_TRANSACTION_STARTED, TransactionMessageEvent(event.request.transaction_id, "request", event.request)
    )


async def on_http_response(event):
    status = event.response.status
    reason = codes.get_reason_phrase(status)
    spent = time.time() - event.request.transaction_started_at
    logger.info(f"◀ {status} {reason} ({spent}s)", transaction_id=getattr(event.request, "transaction_id", None))
    await event.dispatcher.dispatch(
        EVENT_TRANSACTION_ENDED, TransactionMessageEvent(event.request.transaction_id, "response", event.response)
    )


async def kernel_not_started_controller(request, responder: ASGIResponder):
    await responder.start(status=500, headers={"content-type": "text/plain"})
    await responder.body(
        b"Unhandled server error: Cannot access service provider, the lifespan.startup asgi event probably never went "
        b"through."
    )


class ASGIKernel:
    RequestType = ASGIRequest
    ResponderType = ASGIResponder

    def __init__(self, *, dispatcher=None, resolver=None, responder_kwargs=None):
        self.dispatcher: AsyncEventDispatcher = dispatcher or AsyncEventDispatcher()
        self.dispatcher.add_listener(EVENT_CORE_REQUEST, on_http_request, priority=-20)
        self.dispatcher.add_listener(EVENT_CORE_RESPONSE, on_http_response, priority=-20)
        self.resolver = resolver or ControllerResolver()
        self.started = False
        self.responder_kwargs = responder_kwargs or {}

    async def __call__(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable):
        await self.handle(self.RequestType(scope, receive), send)

    async def handle(self, request: ASGIRequest, send: ASGISendCallable):
        if request.type == "http":
            responder = self.ResponderType(request, send, **self.responder_kwargs)
            if not self.started:
                await kernel_not_started_controller(request, responder)
                return responder
            return await self.handle_http(request, responder)

        if request.type == "lifespan":
            await request.receive()
            await self.dispatcher.dispatch(EVENT_CORE_STARTED, Event())
            self.started = True
            return

        if request.type == "websocket":
            # NOT IMPLEMENTED YET!
            # This is here to avoid huge errors in the console.
            return

        raise RuntimeError(f'Unable to handle request, invalid type "{request.type}".')

    async def _resolve_controller(self, request):
        controller = await self.resolver.resolve(request)
        if not controller:
            raise RuntimeError("Unable to find request controller using resolver.")
        event = await self.dispatcher.dispatch(EVENT_CORE_CONTROLLER, ControllerEvent(request, controller))
        if not event.controller:
            raise RuntimeError("Unable to find request controller after controller event dispatch.")
        return event.controller

    async def _execute_controller(self, controller, request: ASGIRequest, responder: ASGIResponder):
        await controller(request, responder)
        await self.dispatcher.dispatch(EVENT_CORE_RESPONSE, ResponseEvent(request, responder))
        return responder

    async def handle_http(self, request: ASGIRequest, responder: ASGIResponder):
        event = await self.dispatcher.dispatch(EVENT_CORE_REQUEST, RequestEvent(request))

        if event.controller:
            return await self._execute_controller(event.controller, request, responder)

        controller = await self._resolve_controller(request)

        return await self._execute_controller(controller, request, responder)


if __name__ == "__main__":
    import asyncio

    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    from harp.applications.proxy.controllers.http_proxy import HttpProxyController
    from harp.core.asgi.resolvers import ProxyControllerResolver, dump_request_controller
    from harp.services.storage.in_memory import InMemoryStorage

    storage = InMemoryStorage()

    resolver = ProxyControllerResolver(default_controller=dump_request_controller)
    resolver.add(8080, HttpProxyController("https://v2.jokeapi.dev/"))
    resolver.add(8081, HttpProxyController("http://localhost:4999/"))

    dispatcher = LoggingAsyncEventDispatcher()
    dispatcher.add_listener(EVENT_CORE_STARTED, on_startup)
    dispatcher.add_listener(EVENT_TRANSACTION_STARTED, on_transaction_started)
    dispatcher.add_listener(EVENT_TRANSACTION_ENDED, on_transaction_ended)

    kernel = ASGIKernel(dispatcher=dispatcher, resolver=resolver)

    config = Config()
    config.bind = ["localhost:8080", "localhost:8081"]

    asyncio.run(serve(kernel, config))
