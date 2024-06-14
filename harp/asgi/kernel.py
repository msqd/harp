import traceback
from inspect import signature

from asgiref.typing import ASGIReceiveCallable, ASGISendCallable, Scope
from hypercorn.utils import LifespanFailureError
from whistle import AsyncEventDispatcher, Event, IAsyncEventDispatcher

from harp import get_logger
from harp.controllers import DefaultControllerResolver
from harp.http import AlreadyHandledHttpResponse, HttpRequest, HttpResponse

from .bridge.requests import HttpRequestAsgiBridge
from .bridge.responses import HttpResponseAsgiBridge
from .events import (
    EVENT_CONTROLLER_VIEW,
    EVENT_CORE_CONTROLLER,
    EVENT_CORE_REQUEST,
    EVENT_CORE_RESPONSE,
    EVENT_CORE_STARTED,
    ControllerEvent,
    ControllerViewEvent,
    RequestEvent,
    ResponseEvent,
)

logger = get_logger(__name__)


class ASGIKernel:
    dispatcher: IAsyncEventDispatcher

    def __init__(self, *, dispatcher=None, resolver=None, debug=False, handle_errors=True):
        self.dispatcher = dispatcher or AsyncEventDispatcher()
        # TODO IControllerResolver ? What contract do we expect ?
        self.resolver = resolver or DefaultControllerResolver()
        self.started = False
        self.debug = debug
        self.handle_errors = handle_errors

    async def __call__(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable):
        asgi_type = scope.get("type", None)

        if asgi_type == "http":
            response = await self.handle_http(scope, receive, send)
            if isinstance(response, AlreadyHandledHttpResponse):
                return
            return await HttpResponseAsgiBridge(response, send).send()

        if asgi_type == "lifespan":
            await receive()
            try:
                await self.dispatcher.adispatch(EVENT_CORE_STARTED, Event())
            except Exception as exc:
                raise LifespanFailureError(EVENT_CORE_STARTED, repr(exc)) from exc

            self.started = True
            return

        if asgi_type == "websocket":
            # NOT IMPLEMENTED YET!
            # This is ignored here to avoid huge errors in the console.
            return

        raise RuntimeError(f'Unable to handle request, invalid type "{asgi_type}".')

    def _resolve_arguments(self, subject, **candidates):
        """
        Dynamicaly resolve arguments by names in prototype, looking at a "candidates" dictionary that
        contains the possible arguments used.
        """

        while hasattr(subject, "_mock_wraps"):
            subject = subject._mock_wraps

        try:
            return [
                candidates[name] if name in candidates or param.default is param.empty else param.default
                for name, param in signature(subject).parameters.items()
                if param.kind is not param.KEYWORD_ONLY
            ], {}
        except KeyError as exc:
            raise TypeError(f"Unable to resolve arguments: {exc}")

    async def _resolve_http_controller(self, request: HttpRequest):
        """
        Resolves the controller for the given request, aka the callable that will handle the request. If we fail to do
        so, we will have hard time building a response for the user, and thus we raise an error.

        Resolving the controller involves two steps:
        - first, we use `self.resolver` to find a controller for the request.
          See `harp.controllers.ControllerResolver`

        :param request:
        :return:
        """
        controller = await self.resolver.resolve(request)
        if not controller:
            raise RuntimeError("Unable to find request controller using resolver.")

        event = ControllerEvent(request, controller)
        await self.dispatcher.adispatch(EVENT_CORE_CONTROLLER, event)

        if not event.controller:
            raise RuntimeError("Unable to find request controller after controller event dispatch.")

        return event.controller

    async def _execute_http_controller(self, controller, request: HttpRequest, send: ASGISendCallable):
        """Executes the given controller and make all efforts to build a http response."""
        args, kwargs = self._resolve_arguments(controller, request=request, asgi_send=send)
        response = await controller(*args, **kwargs)

        # if the controller returned anything that is not a response, maybe some view listener can create one from this
        # value (for example for json data, etc.).
        if not isinstance(response, HttpResponse):
            event = ControllerViewEvent(request, response)
            await self.dispatcher.adispatch(EVENT_CONTROLLER_VIEW, event)
            response = event.response

        # if after the view event has been dispatched we still don't have a response, we have to raise an error.
        if not isinstance(response, HttpResponse):
            raise RuntimeError(
                f"Response did not start despite the efforts made (controller return value is "
                f"{type(response).__name__} after controller view event was dispatched)."
            )

        # the core response event may want to filter the response, for example to add some headers, etc.
        await self.dispatcher.adispatch(EVENT_CORE_RESPONSE, ResponseEvent(request, response))

        return response

    async def handle_http(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable):
        request = HttpRequest(HttpRequestAsgiBridge(scope, receive))

        if not self.started:
            return HttpResponse(
                "Unhandled server error: Cannot access service provider, the lifespan.startup asgi event "
                "probably never went through.",
                status=500,
                content_type="text/plain",
            )

        try:
            return await self.do_handle_http(request, send)

        except Exception as exc:
            if not self.handle_errors:
                raise

            # todo refactor this
            logger.exception()
            if self.debug:
                return HttpResponse(
                    f"<h1>Internal Server Error</h1><h2>{type(exc).__name__}: {exc}</h2> "
                    f"<pre>{traceback.format_exc()}</pre>",
                    status=500,
                    content_type="text/html",
                )
            return HttpResponse("Internal Server Error", status=500, content_type="text/plain")

    async def do_handle_http(self, request: HttpRequest, send: ASGISendCallable):
        event = RequestEvent(request)
        await self.dispatcher.adispatch(EVENT_CORE_REQUEST, event)

        if event.controller:
            return await self._execute_http_controller(event.controller, request, send)

        controller = await self._resolve_http_controller(request)
        return await self._execute_http_controller(controller, request, send)
