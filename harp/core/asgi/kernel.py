from asgiref.typing import ASGIReceiveCallable, ASGISendCallable, Scope
from whistle import Event

from harp import get_logger
from harp.core.asgi.events import (
    EVENT_CORE_CONTROLLER,
    EVENT_CORE_REQUEST,
    EVENT_CORE_RESPONSE,
    EVENT_CORE_STARTED,
    EVENT_CORE_VIEW,
)
from harp.core.asgi.events.controller import ControllerEvent
from harp.core.asgi.events.request import RequestEvent
from harp.core.asgi.events.response import ResponseEvent
from harp.core.asgi.events.view import ViewEvent
from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.core.asgi.resolvers import ControllerResolver
from harp.core.event_dispatcher import AsyncEventDispatcher

logger = get_logger(__name__)


async def kernel_not_started_controller(request, response: ASGIResponse):
    await response.start(status=500, headers={"content-type": "text/plain"})
    await response.body(
        b"Unhandled server error: Cannot access service provider, the lifespan.startup asgi event probably never went "
        b"through."
    )


class ASGIKernel:
    RequestType = ASGIRequest
    ResponseType = ASGIResponse

    def __init__(self, *, dispatcher=None, resolver=None):
        self.dispatcher: AsyncEventDispatcher = dispatcher or AsyncEventDispatcher()
        self.resolver = resolver or ControllerResolver()
        self.started = False

    async def __call__(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable):
        await self.handle(self.RequestType(scope, receive), send)

    async def handle(self, request: ASGIRequest, send: ASGISendCallable):
        if request.type == "http":
            response = self.ResponseType(request, send)
            if not self.started:
                await kernel_not_started_controller(request, response)
                return response
            return await self.handle_http(request, response)

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

    async def _execute_controller(self, controller, request: ASGIRequest, response: ASGIResponse):
        retval = await controller(request, response)

        if retval is not None:
            if response.started:
                raise RuntimeError("cannot both use the response api and return value in controller")
            await self.dispatcher.dispatch(EVENT_CORE_VIEW, ViewEvent(request, response, retval))

        if not response.started:
            raise RuntimeError("response did not start despite the efforts made")

        await self.dispatcher.dispatch(EVENT_CORE_RESPONSE, ResponseEvent(request, response))
        return response

    async def handle_http(self, request: ASGIRequest, response: ASGIResponse):
        event = await self.dispatcher.dispatch(EVENT_CORE_REQUEST, RequestEvent(request))

        if event.controller:
            return await self._execute_controller(event.controller, request, response)
        controller = await self._resolve_controller(request)

        return await self._execute_controller(controller, request, response)
