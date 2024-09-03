from inspect import signature
from typing import Optional

from http_router import NotFoundError, Router
from http_router.types import TMethodsArg, TPath
from rich.console import Console
from rich.traceback import Traceback

from harp.http import HttpRequest, HttpResponse
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
                self.router.route(
                    *tuple(map(lambda x: self.prefix + x, _paths)),
                    methods=_methods,
                    **_opts,
                )(_attr)

        self.configure()

    def configure(self):
        pass

    def create_router(self):
        return self.RouterType(*self.RouterArguments.args, *self.RouterArguments.kwargs)

    async def __call__(self, request: HttpRequest):
        try:
            match = self.router(request.path, method=request.method)
            sig = signature(match.target)
            args = (
                request if name == "request" else match.params.get(name, param.default)
                for name, param in sig.parameters.items()
            )
            return await match.target(*args)
        except NotFoundError as exc:
            if not self.handle_errors:
                raise
            return self.handle_error(exc, status=404)
        except Exception as exc:
            if not self.handle_errors:
                raise
            return self.handle_error(exc)

    def handle_error(self, exc, *, status=500):
        return HttpResponse(
            f"<h1>{type(exc).__name__}</h1><h2>Stack trace</h2>{get_exception_traceback_str(exc)}",
            status=status,
            content_type="text/html",
        )


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
