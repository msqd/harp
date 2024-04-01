import asyncio
import os

from asgi_middleware_static_file import ASGIMiddlewareStaticFile
from asgiref.typing import ASGISendCallable
from http_router import NotFoundError
from httpx import AsyncClient

from harp import ROOT_DIR, get_logger
from harp.controllers import RoutingController
from harp.errors import ConfigurationError
from harp.http import AlreadyHandledHttpResponse, HttpRequest, HttpResponse
from harp.typing.global_settings import GlobalSettings
from harp.typing.storage import Storage
from harp_apps.proxy.controllers import HttpProxyController

from ..settings import DashboardAuthBasicSetting, DashboardSettings
from .blobs import BlobsController
from .overview import OverviewController
from .system import SystemController
from .transactions import TransactionsController

logger = get_logger(__name__)

# Static directories to look for pre-built assets, in order of priority.
STATIC_BUILD_PATHS = [
    os.path.realpath(os.path.join(ROOT_DIR, "harp_apps/dashboard/frontend/dist")),
    os.path.realpath(os.path.join(ROOT_DIR, "harp_apps/dashboard/web")),
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

        # create users if they don't exist
        if isinstance(self.settings.auth, DashboardAuthBasicSetting):
            asyncio.create_task(self.storage.create_users_once_ready(self.settings.auth.users))

        # controllers for delegating requests
        if self.settings.devserver_port:
            self._ui_devserver_proxy_controller = self._create_ui_devserver_proxy_controller(
                port=self.settings.devserver_port
            )

        # register the subcontrollers, aka the api handlers
        self._internal_api_controller = self._create_internal_api_controller()

        # if no devserver is configured, we may need to serve static files
        if not self._ui_devserver_proxy_controller:
            for _path in STATIC_BUILD_PATHS:
                if os.path.exists(_path):
                    self._ui_static_middleware = ASGIMiddlewareStaticFile(None, "", [_path])
                    break

        # if no devserver is configured and no static files are found, we can't serve the dashboard
        if not self._ui_static_middleware and not self._ui_devserver_proxy_controller:
            raise ConfigurationError(
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

    def _create_internal_api_controller(self):
        root = RoutingController(handle_errors=False)

        self.children = [
            BlobsController(storage=self.storage, router=root.router),
            SystemController(storage=self.storage, settings=self.global_settings, router=root.router),
            TransactionsController(storage=self.storage, router=root.router),
            OverviewController(storage=self.storage, router=root.router),
        ]

        return root

    async def __call__(self, request: HttpRequest, asgi_send: ASGISendCallable, *, transaction_id=None):
        request.context.setdefault("user", None)

        if self.settings.auth:
            current_auth = request.basic_auth

            if current_auth:
                request.context["user"] = self.settings.auth.check(current_auth[0], current_auth[1])

            if not request.context["user"]:
                return HttpResponse(
                    b"Unauthorized",
                    status=401,
                    headers={"WWW-Authenticate": 'Basic realm="Harp Dashboard"'},
                    content_type="text/plain",
                )

        # Is this a prebuilt static asset?
        if self._ui_static_middleware and not request.path.startswith("/api/"):
            # XXX todo fix
            await self._ui_static_middleware(
                {
                    "type": "http",
                    "path": request.path if "." in request.path else "/index.html",
                    "method": request.method,
                },
                request._impl.asgi_receive,
                asgi_send,
            )
            return AlreadyHandledHttpResponse()

        try:
            return await self._internal_api_controller(request)
        except NotFoundError:
            if self._ui_devserver_proxy_controller:
                return await self._ui_devserver_proxy_controller(request)

        return HttpResponse("Not found.", status=404, content_type="text/plain")
