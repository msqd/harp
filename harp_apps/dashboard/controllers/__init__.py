import asyncio
import os

from asgi_middleware_static_file import ASGIMiddlewareStaticFile
from asgiref.typing import ASGISendCallable
from http_router import NotFoundError, Router
from httpx import AsyncClient

from harp import ROOT_DIR, get_logger
from harp.controllers import RoutingController
from harp.errors import ConfigurationError
from harp.http import AlreadyHandledHttpResponse, HttpRequest, HttpResponse
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.settings.remote import Remote
from harp_apps.storage.types import IStorage

from ..settings import DashboardSettings
from ..settings.auth import BasicAuthSettings

logger = get_logger(__name__)

# Static directories to look for pre-built assets, in order of priority.
STATIC_BUILD_PATHS = [
    os.path.realpath(os.path.join(ROOT_DIR, "harp_apps/dashboard/frontend/dist")),
    os.path.realpath(os.path.join(ROOT_DIR, "harp_apps/dashboard/web")),
    "/opt/harp/public",
]


class DashboardController(RoutingController):
    name = "ui"

    storage: IStorage
    settings: DashboardSettings
    http_client: AsyncClient

    _ui_static_middleware = None
    _ui_devserver_proxy_controller = None

    def __init__(
        self,
        storage: IStorage,
        settings: DashboardSettings,
        http_client: AsyncClient,
        router: Router = None,
    ):
        super().__init__(router=router, handle_errors=False)

        # context for usage in handlers
        self.http_client = http_client
        self.storage = storage
        self.settings = settings

        # create users if they don't exist
        if isinstance(self.settings.auth, BasicAuthSettings):
            asyncio.create_task(self.storage.create_users_once_ready(self.settings.auth.users))

        if self.settings.enable_ui:
            self._initialize_ui()

    def _initialize_ui(self):
        # controllers for delegating requests
        if self.settings.devserver.enabled and self.settings.devserver.port:
            self._ui_devserver_proxy_controller = self._create_ui_devserver_proxy_controller(
                port=self.settings.devserver.port
            )

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
            "api": True,
            "devserver": bool(self._ui_devserver_proxy_controller),
            "static": bool(self._ui_static_middleware),
        }
        return f"{type(self).__name__}({'+'.join(f for f in features if features[f])})"

    def _create_ui_devserver_proxy_controller(self, *, port):
        return HttpProxyController(
            Remote.from_settings_dict({"endpoints": [{"url": f"http://localhost:{port}/"}]}),
            http_client=self.http_client,
            logging=False,
            name="dashboard-devserver",
        )

    async def __call__(self, request: HttpRequest, asgi_send: ASGISendCallable, *, transaction_id=None) -> HttpResponse:
        request.extensions.setdefault("user", None)

        if self.settings.auth:
            current_auth = request.basic_auth

            if current_auth:
                request.extensions["user"] = self.settings.auth.check(current_auth[0], current_auth[1])

            if not request.extensions["user"]:
                return HttpResponse(
                    b"Unauthorized",
                    status=401,
                    headers={"WWW-Authenticate": 'Basic realm="Harp Dashboard"'},
                    content_type="text/plain",
                )

        # Is this a prebuilt static asset? Can we serve it using our middleware? This wil need refactoring, as it ties
        # the controller implementation to the underlying webserver protocol implementation, but for now, it works.
        if (
            self._ui_static_middleware
            and not request.path.startswith("/api/")
            and hasattr(request._impl, "asgi_receive")
        ):
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
            return await super().__call__(request)
        except NotFoundError:
            if self._ui_devserver_proxy_controller:
                return await self._ui_devserver_proxy_controller(request)

        return HttpResponse("Not found.", status=404, content_type="text/plain")
