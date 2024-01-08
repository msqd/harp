import os

from asgi_middleware_static_file import ASGIMiddlewareStaticFile
from http_router import NotFoundError
from httpx import AsyncClient

from harp import ROOT_DIR, get_logger
from harp.apps.dashboard.settings import DashboardSettings
from harp.apps.proxy.controllers import HttpProxyController
from harp.core.asgi import ASGIRequest, ASGIResponse
from harp.core.controllers import RoutingController
from harp.errors import ProxyConfigurationError
from harp.protocols.storage import Storage
from harp.typing.global_settings import GlobalSettings

from .overview import OverviewController
from .system import SystemController
from .transactions import TransactionsController

logger = get_logger(__name__)

# Static directories to look for pre-built assets, in order of priority.
STATIC_BUILD_PATHS = [
    os.path.realpath(os.path.join(ROOT_DIR, "frontend/dist")),
    "/opt/harp/public",
]


class DashboardController:
    name = "ui"

    storage: Storage
    settings: DashboardSettings
    global_settings: GlobalSettings
    http_client: AsyncClient

    _ui_static_middleware = None
    _ui_devserver_proxy_controller = None

    def __init__(
        self,
        storage: Storage,
        all_settings: GlobalSettings,
        local_settings: DashboardSettings,
        http_client: AsyncClient,
    ):
        # context for usage in handlers
        self.http_client = http_client
        self.storage = storage
        self.global_settings = all_settings
        self.settings = local_settings

        # controllers for delegating requests
        if self.settings.devserver_port:
            self._ui_devserver_proxy_controller = self._create_ui_devserver_proxy_controller(
                port=self.settings.devserver_port
            )

        # register the subcontrollers, aka the api handlers
        self._internal_api_controller = self._create_routing_controller()

        # if no devserver is configured, we may need to serve static files
        if not self._ui_devserver_proxy_controller:
            for _path in STATIC_BUILD_PATHS:
                if os.path.exists(_path):
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
        return HttpProxyController(f"http://localhost:{port}/", http_client=self.http_client)

    def _create_routing_controller(self):
        controller = RoutingController(handle_errors=False)
        router = controller.router
        router.route("/api/blobs/{blob}")(self.get_blob)

        # subcontrollers
        for _controller in (
            OverviewController(self.storage),
            TransactionsController(self.storage),
            SystemController(self.global_settings),
        ):
            _controller.register(controller.router)

        return controller

    async def __call__(self, request: ASGIRequest, response: ASGIResponse, *, transaction_id=None):
        request.context.setdefault("user", None)

        if self.settings.auth:
            current_auth = request.basic_auth

            if current_auth:
                request.context["user"] = self.settings.auth.check(current_auth[0], current_auth[1])

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
