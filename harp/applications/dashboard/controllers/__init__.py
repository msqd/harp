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

    def __init__(self, storage: IStorage, settings: Configuration):
        # context for usage in handlers
        self.storage = storage
        self.settings = settings

        # auth (naive first implementation)
        self.auth = self.settings.dashboard.values.get("auth", None)

        # controllers for delegating requests
        self._devserver_proxy_controller = self._create_devserver_proxy_controller()
        self._routing_controller = self._create_routing_controller()

        self.sub_controllers = [
            TransactionsController(self.storage),
            SystemController(self.settings),
        ]

        for _controller in self.sub_controllers:
            _controller.register(self._routing_controller.router)

        for _path in STATIC_BUILD_PATHS:
            logger.info("Checking for static files in %s", _path)
            if os.path.exists(_path):
                logger.info("Serving static files from %s", _path)
                self._ui_static_middleware = ASGIMiddlewareStaticFile(None, "", [_path])
                break

    def _create_devserver_proxy_controller(self):
        return HttpProxyController("http://localhost:4999/")

    def _create_routing_controller(self):
        controller = RoutingController(handle_errors=False)
        router = controller.router
        router.route("/api/blobs/{blob}")(self.get_blob)
        router.route("/api/dashboard")(self.get_dashboard_data)
        router.route("/api/dashboard/{endpoint}")(self.get_dashboard_data_for_endpoint)
        return controller

    async def __call__(self, request: ASGIRequest, response: ASGIResponse, *, transaction_id=None):
        # This is a naive implementation of auth, but it works for now.
        # TODO: This feature won't stay, it will use standard auth mechanisms instead.
        if self.auth:
            _auth = request.cookies.get("harp", None)
            logger.info(f'🔑 {request.method} {request.path} "{_auth}" "{_auth.value if _auth else None}"')
            if not _auth or _auth.value != self.auth:
                response.headers["content-type"] = "text/plain"
                await response.start(401)
                await response.body(b"Unauthorized")
                return

        logger.debug(f"📈 {request.method} {request.path}")

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
            return await self._routing_controller(request, response)
        except NotFoundError:
            return await self._devserver_proxy_controller(request, response)

    async def get_blob(self, request: ASGIRequest, response: ASGIResponse, blob):
        blob = await self.storage.get_blob(blob)

        if not blob:
            response.headers["content-type"] = "text/plain"
            await response.start(status=404)
            await response.body(b"Blob not found.")
            return

        response.headers["content-type"] = "application/octet-stream"
        await response.start(status=200)
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
