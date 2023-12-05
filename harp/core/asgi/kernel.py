from asgiref.typing import ASGIReceiveCallable, ASGISendCallable, Scope
from whistle import Event

from harp import get_logger
from harp.core.asgi.events import (
    EVENT_CORE_CONTROLLER,
    EVENT_CORE_REQUEST,
    EVENT_CORE_RESPONSE,
    EVENT_CORE_STARTED,
    EVENT_CORE_VIEW,
    AsyncEventDispatcher,
    ControllerEvent,
    LoggingAsyncEventDispatcher,
    RequestEvent,
    ResponderEvent,
    ViewEvent,
)
from harp.core.asgi.requests import ASGIRequest
from harp.core.asgi.resolvers import ControllerResolver
from harp.core.asgi.responders import ASGIResponder

logger = get_logger(__name__)


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
        retval = await controller(request, responder)

        if retval:
            if responder.started:
                raise RuntimeError("cannot both use responder and return value in controller")
            await self.dispatcher.dispatch(EVENT_CORE_VIEW, ViewEvent(request, responder, retval))

        if not responder.started:
            raise RuntimeError("responder did not start despite the efforts made")

        await self.dispatcher.dispatch(EVENT_CORE_RESPONSE, ResponderEvent(request, responder))
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

    from harp.applications.proxy.controllers import HttpProxyController
    from harp.core.asgi.resolvers import ProxyControllerResolver, dump_request_controller
    from harp.services.storage.in_memory import InMemoryStorage

    storage = InMemoryStorage()

    resolver = ProxyControllerResolver(default_controller=dump_request_controller)
    resolver.add(8080, HttpProxyController("https://v2.jokeapi.dev/"))
    resolver.add(8081, HttpProxyController("http://localhost:4999/"))

    dispatcher = LoggingAsyncEventDispatcher()

    kernel = ASGIKernel(dispatcher=dispatcher, resolver=resolver)

    config = Config()
    config.bind = ["localhost:8080", "localhost:8081"]

    asyncio.run(serve(kernel, config))
