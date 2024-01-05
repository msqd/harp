import traceback

from asgiref.typing import ASGIReceiveCallable, ASGISendCallable, Scope
from whistle import AsyncEventDispatcher, Event, IAsyncEventDispatcher

from harp import get_logger

from .events import (
    EVENT_CORE_CONTROLLER,
    EVENT_CORE_REQUEST,
    EVENT_CORE_RESPONSE,
    EVENT_CORE_STARTED,
    EVENT_CORE_VIEW,
    ControllerEvent,
    RequestEvent,
    ResponseEvent,
    ViewEvent,
)
from .messages import ASGIRequest, ASGIResponse
from .resolvers import ControllerResolver

logger = get_logger(__name__)


async def kernel_not_started_controller(request, response: ASGIResponse):
    response.headers["content-type"] = "text/plain"
    await response.start(status=500)
    await response.body(
        b"Unhandled server error: Cannot access service provider, the lifespan.startup asgi event probably never went "
        b"through."
    )


class ASGIKernel:
    RequestType = ASGIRequest
    ResponseType = ASGIResponse

    dispatcher: IAsyncEventDispatcher

    def __init__(self, *, dispatcher=None, resolver=None, debug=False):
        self.dispatcher = dispatcher or AsyncEventDispatcher()
        # TODO IControllerResolver ? What contract do we expect ?
        self.resolver = resolver or ControllerResolver()
        self.started = False
        self.debug = debug

    async def __call__(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable):
        await self.handle(self.RequestType(scope, receive), send)

    async def handle(self, request: ASGIRequest, send: ASGISendCallable):
        if request.type == "http":
            response = self.ResponseType(request, send)
            if not self.started:
                await kernel_not_started_controller(request, response)
                return response
            try:
                return await self.handle_http(request, response)
            except Exception as exc:
                # todo refactor this
                logger.exception()
                if self.debug:
                    traceback_message = traceback.format_exc()
                    response.headers["content-type"] = "text/html"
                    await response.start(status=500)
                    await response.body(
                        f"<h1>Internal Server Error</h1><h2>{type(exc).__name__}: {exc}</h2> "
                        f"<pre>{traceback_message}</pre>"
                    )

                else:
                    response.headers["content-type"] = "text/plain"
                    await response.start(status=500)
                    await response.body(b"Internal Server Error")
                return response

        if request.type == "lifespan":
            await request.receive()
            await self.dispatcher.adispatch(EVENT_CORE_STARTED, Event())
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

        event = ControllerEvent(request, controller)
        await self.dispatcher.adispatch(EVENT_CORE_CONTROLLER, event)

        if not event.controller:
            raise RuntimeError("Unable to find request controller after controller event dispatch.")

        return event.controller

    async def _execute_controller(self, controller, request: ASGIRequest, response: ASGIResponse):
        retval = await controller(request, response)

        if retval is not None:
            if response.started:
                raise RuntimeError("Cannot both use the response api and return value in controller.")
            event = ViewEvent(request, response, retval)
            await self.dispatcher.adispatch(EVENT_CORE_VIEW, event)

        if not response.started:
            raise RuntimeError(
                f"Response did not start despite the efforts made (controller return value is {type(retval).__name__})."
            )

        await self.dispatcher.adispatch(EVENT_CORE_RESPONSE, ResponseEvent(request, response))
        return response

    async def handle_http(self, request: ASGIRequest, response: ASGIResponse):
        event = RequestEvent(request)
        await self.dispatcher.adispatch(EVENT_CORE_REQUEST, event)

        if event.controller:
            return await self._execute_controller(event.controller, request, response)

        controller = await self._resolve_controller(request)
        return await self._execute_controller(controller, request, response)
