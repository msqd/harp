import os

from asgi_middleware_static_file import ASGIMiddlewareStaticFile
from config.common import Configuration
from http_router import NotFoundError

from harp import ROOT_DIR, get_logger
from harp.applications.dashboard.controllers.system import SystemController
from harp.applications.dashboard.controllers.transactions import TransactionsController
from harp.applications.proxy.controllers import HttpProxyController
from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.core.controllers.routing import RoutingController
from harp.core.views.json import json
from harp.errors import ProxyConfigurationError
from harp.protocols.storage import IStorage

logger = get_logger(__name__)

# Static directories to look for pre-built assets, in order of priority.
STATIC_BUILD_PATHS = [
    os.path.realpath(os.path.join(ROOT_DIR, "frontend/dist")),
    "/opt/harp/public",
]


class DashboardController:
    name = "ui"
    storage: IStorage
    settings: Configuration

    _ui_static_middleware = None
    _ui_devserver_proxy_controller = None

    def __init__(self, storage: IStorage, settings: Configuration):
        # context for usage in handlers
        self.storage = storage
        self.settings = settings

        # auth (naive first implementation)
        self.auth = self.settings.dashboard.auth

        # controllers for delegating requests
        if self.settings.dashboard.devserver_port:
            self._ui_devserver_proxy_controller = self._create_ui_devserver_proxy_controller(
                port=self.settings.dashboard.devserver_port
            )

        # register the subcontrollers, aka the api handlers
        self._internal_api_controller = self._create_routing_controller()

        # if no devserver is configured, we may need to serve static files
        if not self._ui_devserver_proxy_controller:
            for _path in STATIC_BUILD_PATHS:
                logger.info("Checking for static files in %s", _path)
                if os.path.exists(_path):
                    logger.info("Serving static files from %s", _path)
                    self._ui_static_middleware = ASGIMiddlewareStaticFile(None, "", [_path])
                    break

        # if no devserver is configured and no static files are found, we can't serve the dashboard
        if not self._ui_static_middleware and not self._ui_devserver_proxy_controller:
            raise ProxyConfigurationError(
                "Dashboard controller could not initiate because it got neither compiled assets nor a devserver "
                "configuration."
            )

    def __repr__(self):
        features = {
            "api": bool(self._internal_api_controller),
            "devserver": bool(self._ui_devserver_proxy_controller),
            "static": bool(self._ui_static_middleware),
        }
        return f"{type(self).__name__}({'+'.join(f for f in features if features[f])})"

    def _create_ui_devserver_proxy_controller(self, *, port):
        return HttpProxyController(f"http://localhost:{port}/")

    def _create_routing_controller(self):
        controller = RoutingController(handle_errors=False)
        router = controller.router
        router.route("/api/blobs/{blob}")(self.get_blob)
        router.route("/api/dashboard")(self.get_dashboard_data)
        router.route("/api/dashboard/{endpoint}")(self.get_dashboard_data_for_endpoint)

        # subcontrollers
        for _controller in (
            TransactionsController(self.storage),
            SystemController(self.settings),
        ):
            _controller.register(controller.router)

        return controller

    async def __call__(self, request: ASGIRequest, response: ASGIResponse, *, transaction_id=None):
        request.context.setdefault("user", None)

        if self.auth:
            current_auth = request.basic_auth

            if current_auth:
                request.context["user"] = self.auth.check(current_auth[0], current_auth[1])

            if not request.context["user"]:
                response.headers["content-type"] = "text/plain"
                response.headers["WWW-Authenticate"] = 'Basic realm="Harp Dashboard"'
                await response.start(401)
                await response.body(b"Unauthorized")
                return

        # Is this a prebuilt static asset?
        if self._ui_static_middleware and not request.path.startswith("/api/"):
            try:
                return await self._ui_static_middleware(
                    {
                        "type": request._scope["type"],
                        "path": request._scope["path"] if "." in request._scope["path"] else "/index.html",
                        "method": request._scope["method"],
                    },
                    request._receive,
                    response._send,
                )
            finally:
                response.started = True

        try:
            return await self._internal_api_controller(request, response)
        except NotFoundError:
            if self._ui_devserver_proxy_controller:
                return await self._ui_devserver_proxy_controller(request, response)

        await response.start(status=404)
        await response.body("Not found.")

    async def get_blob(self, request: ASGIRequest, response: ASGIResponse, blob):
        blob = await self.storage.get_blob(blob)

        if not blob:
            response.headers["content-type"] = "text/plain"
            await response.start(status=404)
            await response.body(b"Blob not found.")
            return

        response.headers["content-type"] = blob.content_type or "application/octet-stream"
        await response.start(status=200)

        if blob.content_type == "application/json":
            await response.body(blob.prettify())
        else:
            await response.body(blob.data)

    async def get_dashboard_data(self, request: ASGIRequest, response: ASGIResponse):
        data = [
            {"date": "2022-01-01", "requests": 120, "errors": 20},
            {"date": "2022-01-02", "requests": 160, "errors": 30},
            {"date": "2022-01-03", "requests": 200, "errors": 40},
            {"date": "2022-01-04", "requests": 100, "errors": 50},
            {"date": "2022-01-05", "requests": 280, "errors": 60},
            {"date": "2022-01-06", "requests": 320, "errors": 70},
            {"date": "2022-01-07", "requests": 300, "errors": 50},
            {"date": "2022-01-08", "requests": 400, "errors": 90},
            {"date": "2022-01-09", "requests": 440, "errors": 50},
            {"date": "2022-01-10", "requests": 480, "errors": 50},
            {"date": "2022-01-11", "requests": 300, "errors": 120},
            {"date": "2022-01-12", "requests": 560, "errors": 130},
            {"date": "2022-01-13", "requests": 600, "errors": 10},
            {"date": "2022-01-14", "requests": 640, "errors": 150},
            {"date": "2022-01-15", "requests": 680, "errors": 50},
            {"date": "2022-01-16", "requests": 500, "errors": 170},
            {"date": "2022-01-17", "requests": 760, "errors": 180},
            {"date": "2022-01-18", "requests": 800, "errors": 190},
            {"date": "2022-01-19", "requests": 400, "errors": 50},
            {"date": "2022-01-20", "requests": 880, "errors": 210},
            {"date": "2022-01-21", "requests": 300, "errors": 50},
            {"date": "2022-01-22", "requests": 300, "errors": 50},
            {"date": "2022-01-23", "requests": 1000, "errors": 50},
            {"date": "2022-01-24", "requests": 500, "errors": 50},
            {"date": "2022-01-25", "requests": 300, "errors": 50},
            {"date": "2022-01-26", "requests": 300, "errors": 100},
        ]
        return json({"data": data})

    async def get_dashboard_data_for_endpoint(self, request: ASGIRequest, response: ASGIResponse, endpoint: str):
        data_foo = [
            {"date": "2022-01-01", "requests": 120, "errors": 100},
            {"date": "2022-01-02", "requests": 160, "errors": 30},
            {"date": "2022-01-03", "requests": 200, "errors": 40},
            {"date": "2022-01-04", "requests": 100, "errors": 50},
            {"date": "2022-01-05", "requests": 280, "errors": 60},
            {"date": "2022-01-06", "requests": 320, "errors": 70},
            {"date": "2022-01-07", "requests": 300, "errors": 50},
            {"date": "2022-01-08", "requests": 400, "errors": 90},
            {"date": "2022-01-09", "requests": 440, "errors": 50},
        ]
        data_bar = [
            {"date": "2022-01-01", "requests": 120, "errors": 20},
            {"date": "2022-01-02", "requests": 160, "errors": 30},
            {"date": "2022-01-03", "requests": 200, "errors": 80},
            {"date": "2022-01-04", "requests": 100, "errors": 50},
            {"date": "2022-01-05", "requests": 280, "errors": 30},
            {"date": "2022-01-06", "requests": 320, "errors": 10},
            {"date": "2022-01-07", "requests": 300, "errors": 50},
            {"date": "2022-01-08", "requests": 400, "errors": 50},
            {"date": "2022-01-09", "requests": 440, "errors": 50},
        ]

        endpoints_data = {
            "foo": data_foo,
            "bar": data_bar,
        }

        return json({"data": endpoints_data[endpoint]})
