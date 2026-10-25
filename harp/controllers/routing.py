import traceback
from typing import Optional

from http_router import NotFoundError, Router
from http_router.types import TMethodsArg, TPath
import orjson

import harp
from harp import get_logger
from harp.http import HttpRequest, HttpResponse
from harp.meta import get_meta, has_meta, set_meta
from harp.security.actor import Role, get_actor
from harp.utils.arguments import Arguments

from harp.utils.signatures import resolve_arguments


logger = get_logger(__name__)


class RoutingController:
    RouterType = Router
    RouterArguments = Arguments(trim_last_slash=True)

    prefix = None

    #: Whether a handler that declares no role is Admin only, instead of open (see :meth:`refuse_actor`).
    roles_required = False

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
        return self.RouterType(*self.RouterArguments.args, **self.RouterArguments.kwargs)

    async def __call__(self, request: HttpRequest):
        try:
            match = self.router(request.path, method=request.method)
            if refusal := self.refuse_actor(request, match.target):
                return refusal
            args = resolve_arguments(match.target, **{**(match.params or {}), "request": request})
            return await match.target(*args)
        except NotFoundError as exc:
            if not self.handle_errors:
                raise
            return self.handle_error(exc, status=404)
        except Exception as exc:
            if not self.handle_errors:
                raise
            return self.handle_error(exc)

    def refuse_actor(self, request: HttpRequest, handler) -> Optional[HttpResponse]:
        """
        A refusal (401, 403) when the actor of the request may not run ``handler``, else None.

        The role a handler requires is declared on the route (``GetHandler("/x", role=Role.ADMIN)``). A handler that
        declares none is open, unless the controller sets ``roles_required``: then it is an Admin one, so that a route
        added without thinking about who may call it fails closed.
        """
        required = get_meta(handler, "role")
        if required is None:
            if not self.roles_required:
                return None
            required = Role.ADMIN
        actor = get_actor(request)
        if actor is None:
            return self._refusal(401, "Unauthorized")
        if not actor.can(required):
            return self._refusal(403, "Forbidden")
        return None

    @staticmethod
    def _refusal(status: int, error: str) -> HttpResponse:
        return HttpResponse(
            orjson.dumps({"error": error, "status": status}), status=status, content_type="application/json"
        )

    def handle_error(self, exc, *, status=500):
        if status >= 500:
            logger.exception("Unhandled error in controller.", exc_info=exc)
        body = {"error": type(exc).__name__, "status": status}
        if harp.DEBUG:
            body["traceback"] = "".join(traceback.format_exception(exc))
        return HttpResponse(orjson.dumps(body), status=status, content_type="application/json")


def RouterPrefix(prefix):
    def _configurator(Controller: RoutingController):
        Controller.prefix = prefix
        return Controller

    return _configurator


def RouteHandler(*paths: TPath, methods: Optional[TMethodsArg] = None, role: Optional[Role] = None, **opts):
    """Declares a route. ``role`` is the lowest role of the actor that may call it."""

    def _configurator(handler):
        nonlocal paths, methods, opts
        if has_meta(handler, "route"):
            raise Exception("Handler already has route metadata.")
        set_meta(handler, "route", (paths, methods, opts))
        if role is not None:
            set_meta(handler, "role", role)
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
