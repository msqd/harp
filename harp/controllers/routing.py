from typing import Optional

from http_router import NotFoundError, Router
from http_router.types import TMethodsArg, TPath
from rich.console import Console
from rich.traceback import Traceback

from harp.asgi.messages import ASGIRequest, ASGIResponse
from harp.meta import get_meta, has_meta, set_meta
from harp.utils.arguments import Arguments


def get_exception_traceback_str(exc):
    console = Console(record=True)
    traceback = Traceback.from_exception(type(exc), exc, exc.__traceback__)
    console.print(traceback)
    return console.export_html()


class RoutingController:
    RouterType = Router
    RouterArguments = Arguments(trim_last_slash=True)

    prefix = None

    def __init__(self, *, handle_errors=True, router=None):
        self.router = router or self.create_router()
        self.handle_errors = handle_errors
        self.prefix = self.prefix or ""

        for _name in dir(self):
            _attr = getattr(self, _name)
            if callable(_attr) and (meta := get_meta(_attr, "route")):
                _paths, _methods, _opts = meta
                self.router.route(*tuple(map(lambda x: self.prefix + x, _paths)), methods=_methods, **_opts)(_attr)

        self.configure()

    def configure(self):
        pass

    def create_router(self):
        return self.RouterType(*self.RouterArguments.args, *self.RouterArguments.kwargs)

    async def __call__(self, request: ASGIRequest, response: ASGIResponse):
        try:
            match = self.router(request.path, method=request.method)
            return await match.target(request, response, **(match.params or {}))
        except NotFoundError as exc:
            if not self.handle_errors:
                raise
            await self.handle_error(exc, response, status=404)
        except Exception as exc:
            if not self.handle_errors:
                raise
            await self.handle_error(exc, response)

    async def handle_error(self, exc, response, *, status=500):
        response.headers["content-type"] = "text/html"
        await response.start(status=status)
        await response.body(f"<h1>{type(exc).__name__}</h1><h2>Stack trace</h2>{get_exception_traceback_str(exc)}")


def RouterPrefix(prefix):
    def _configurator(Controller: RoutingController):
        Controller.prefix = prefix
        return Controller

    return _configurator


def RouteHandler(*paths: TPath, methods: Optional[TMethodsArg] = None, **opts):
    def _configurator(handler):
        nonlocal paths, methods, opts
        if has_meta(handler, "route"):
            raise Exception("Handler already has route metadata.")
        set_meta(handler, "route", (paths, methods, opts))
        return handler

    return _configurator


def GetHandler(*paths: TPath, **opts):
    return RouteHandler(*paths, methods=["GET"], **opts)


def PostHandler(*paths: TPath, **opts):
    return RouteHandler(*paths, methods=["POST"], **opts)


def PutHandler(*paths: TPath, **opts):
    return RouteHandler(*paths, methods=["PUT"], **opts)


def DeleteHandler(*paths: TPath, **opts):
    return RouteHandler(*paths, methods=["DELETE"], **opts)


def PatchHandler(*paths: TPath, **opts):
    return RouteHandler(*paths, methods=["PATCH"], **opts)


def OptionsHandler(*paths: TPath, **opts):
    return RouteHandler(*paths, methods=["OPTIONS"], **opts)


def HeadHandler(*paths: TPath, **opts):
    return RouteHandler(*paths, methods=["HEAD"], **opts)


def TraceHandler(*paths: TPath, **opts):
    return RouteHandler(*paths, methods=["TRACE"], **opts)


def ConnectHandler(*paths: TPath, **opts):
    return RouteHandler(*paths, methods=["CONNECT"], **opts)


def AnyMethodHandler(*paths: TPath, **opts):
    return RouteHandler(*paths, methods=None, **opts)
