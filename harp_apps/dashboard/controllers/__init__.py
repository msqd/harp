import asyncio
import os
from typing import Optional
from urllib.parse import urlsplit

from asgi_middleware_static_file import ASGIMiddlewareStaticFile
from asgiref.typing import ASGISendCallable
from http_router import NotFoundError, Router
from httpx import AsyncClient

from harp import get_logger
from harp.asgi.events import ViewEvent
from harp.controllers import RoutingController
from harp.errors import ConfigurationError
from harp.http import AlreadyHandledHttpResponse, HttpRequest, HttpResponse, JsonHttpResponse
from harp.http.responses import RedirectHttpResponse
from harp.security.actor import Actor, set_actor
from harp.views.json import on_json_response
from harp_apps import dashboard
from harp_apps.auth.actors import ActorResolver
from harp_apps.auth.setup import SetupLink
from harp_apps.auth.signin import Authenticator, Busy, Throttled
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.settings.remote import Remote
from harp_apps.storage.types import IStorage

from ..security.cookies import is_secure, read_session_secret
from ..settings import DashboardSettings
from ..security.addresses import client_address
from .auth import PublicAuthRoutes, busy, problem, too_many
from .metrics import METRICS_PATH, metrics_controller

logger = get_logger(__name__)

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

#: Values of Sec-Fetch-Site for a request the dashboard itself initiated (or a user typing the URL).
SAME_ORIGIN_FETCH_SITES = frozenset({"same-origin", "none"})

#: Sent on every dashboard response: never sniff a type, never render the dashboard in a frame, never leak a
#: dashboard URL to another site.
BASE_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
}

#: What the built dashboard needs, nothing more. Emotion injects <style> elements, hence 'unsafe-inline' for styles
#: only; message bodies render images through blob: URLs.
DASHBOARD_CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    )
)


def _send_with_headers(asgi_send: ASGISendCallable, headers: dict) -> ASGISendCallable:
    """Wraps an ASGI send callable to add the given headers to responses written directly to it (static assets),
    leaving any header the response already carries untouched."""

    async def send(message):
        if message["type"] == "http.response.start":
            present = {name.lower() for name, _ in message.get("headers", ())}
            extra = [(name.lower().encode(), value.encode()) for name, value in headers.items()]
            message = {
                **message,
                "headers": [*message.get("headers", ()), *(h for h in extra if h[0] not in present)],
            }
        await asgi_send(message)

    return send


class Declined(Exception):
    """A request that was not even looked at, and the response to give: the sign-in limits said no."""

    def __init__(self, response: HttpResponse):
        self.response = response


class DashboardController(RoutingController):
    name = "ui"

    #: A route that declares no role is Admin only: forgetting to think about it must not open anything.
    roles_required = True

    storage: IStorage
    settings: DashboardSettings
    http_client: AsyncClient

    _ui_static_middleware = None
    _ui_devserver_proxy_controller = None
    _create_users_task = None

    #: Static directory to look for pre-built assets.
    static_build_path = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(dashboard.__file__)), "web"))

    def __init__(
        self,
        storage: IStorage,
        settings: DashboardSettings,
        http_client: AsyncClient,
        router: Router = None,
        actors: Optional[ActorResolver] = None,
        authenticator: Optional[Authenticator] = None,
        setup: Optional[SetupLink] = None,
    ):
        super().__init__(router=router, handle_errors=False)

        # context for usage in handlers
        self.http_client = http_client
        self.storage = storage
        self.settings = settings

        # There is no open mode: every request is resolved to an actor by the resolver of the auth application.
        if actors is None:
            raise ConfigurationError("The dashboard authenticates its users, it needs the actor resolver of auth.")
        self.actors = actors

        # the sign-in and setup pages and the requests they make; without the services, only Basic gets in
        self._public = None
        self._authenticator = authenticator
        if authenticator is not None and setup is not None:
            self._public = PublicAuthRoutes(authenticator, setup, settings)

        # Basic is deprecated (#1525): it stays for the users declared in the configuration, whose passwords are
        # still verified from there.
        self._auth = self.settings.auth

        # import the configured users once; keep a strong reference to the task, as the event loop
        # only holds a weak one and would let it be garbage-collected before completion.
        if self._auth:
            self._create_users_task = asyncio.create_task(self.storage.import_users_once_ready(self._auth.users))

        # UI is always initialized when the dashboard app is enabled
        # (the `enabled` setting controls whether the entire app loads)
        self._initialize_ui()

    def _initialize_ui(self):
        # controllers for delegating requests
        if self.settings.devserver.enabled and self.settings.devserver.port:
            self._ui_devserver_proxy_controller = self._create_ui_devserver_proxy_controller(
                port=self.settings.devserver.port
            )

        # if no devserver is configured, we may need to serve static files
        if not self._ui_devserver_proxy_controller:
            if os.path.exists(self.static_build_path):
                self._ui_static_middleware = ASGIMiddlewareStaticFile(None, "", [self.static_build_path])

        # if no devserver is configured and no static files are found, we can't serve the dashboard
        if not self._ui_static_middleware and not self._ui_devserver_proxy_controller:
            raise ConfigurationError(
                "Dashboard controller could not initiate because it got neither compiled assets nor a devserver "
                "configuration. If you're using an editable install, make sure to run `make build-frontend` in the "
                "target working copy, or start a frontend development server."
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
            Remote.from_settings_dict(
                {
                    "endpoints": [{"url": f"http://localhost:{port}/"}],
                    "liveness": {"type": "ignore"},
                }
            ),
            http_client=self.http_client,
            logging=False,
            name="dashboard-devserver",
        )

    async def __call__(self, request: HttpRequest, asgi_send: ASGISendCallable, *, transaction_id=None) -> HttpResponse:
        headers = self._security_headers()
        response = await self._handle(request, _send_with_headers(asgi_send, headers))
        if not isinstance(response, HttpResponse):
            # sub-controllers return view values (json); render them here so they get the headers too
            event = ViewEvent(request, response)
            await on_json_response(event)
            response = event.response or response
        if isinstance(response, HttpResponse):
            for name, value in headers.items():
                response.headers.setdefault(name, value)
        return response

    def _security_headers(self) -> dict:
        # the vite devserver relies on inline scripts, so only the built dashboard gets the content security policy
        if self._ui_devserver_proxy_controller:
            return BASE_SECURITY_HEADERS
        return {**BASE_SECURITY_HEADERS, "Content-Security-Policy": DASHBOARD_CONTENT_SECURITY_POLICY}

    def _refuse_forged_request(self, request: HttpRequest) -> JsonHttpResponse | None:
        """State-changing requests must come from the dashboard itself: JSON (which a cross-site form cannot send
        without a preflight) and never flagged cross-site by the browser."""
        if request.method in SAFE_METHODS:
            return None
        if request.headers.get("Sec-Fetch-Site", "same-origin") not in SAME_ORIGIN_FETCH_SITES:
            return JsonHttpResponse({"error": "Cross-site request refused", "status": 403}, status=403)
        origin = request.headers.get("Origin")
        if origin is not None and urlsplit(origin).netloc != request.headers.get("Host"):
            return JsonHttpResponse({"error": "Cross-site request refused", "status": 403}, status=403)
        if request.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            return JsonHttpResponse({"error": "Content-Type must be application/json", "status": 415}, status=415)
        return None

    async def _authenticate(self, request: HttpRequest) -> Optional[Actor]:
        """The actor of the request, or None if it is not authenticated or its account may not act."""
        secret = read_session_secret(request, secure=is_secure(request, public_url=self.settings.public_url))
        if secret and (actor := await self.actors.session(secret)):
            return actor

        credentials = request.basic_auth if self._auth else None
        if not credentials:
            return None

        async def right() -> bool:
            return bool(await self._auth.acheck(credentials[0], credentials[1]))

        if self._authenticator is None:
            username = await self._auth.acheck(credentials[0], credentials[1])
        else:
            # Basic is slowed down like the password method: a request is an attempt, whatever the cache says
            address = client_address(request, self.settings.trusted_proxies)
            checked = await self._authenticator.guarded(credentials[0].casefold()[:255], address, right)
            if isinstance(checked, Throttled):
                raise Declined(too_many(checked.retry_after))
            if isinstance(checked, Busy):
                raise Declined(busy(checked.retry_after))
            username = credentials[0] if checked.value else False
        return await self.actors.basic(username) if username else None

    def _unauthorized(self, request: HttpRequest) -> HttpResponse:
        """
        What a request that is not signed in gets.

        With Basic configured (deprecated), the challenge is kept for whoever shows no session cookie. A request that
        has one is a session that ended: no challenge, or the browser would ask for a Basic password in the middle of
        the dashboard. The dashboard's own requests (``/api``) get a 401, a browser fetching a page is sent to sign in.
        """
        challenge = {}
        if (
            self._auth
            and read_session_secret(request, secure=is_secure(request, public_url=self.settings.public_url)) is None
        ):
            challenge = {"WWW-Authenticate": 'Basic realm="Harp Dashboard"'}

        if request.path.startswith("/api/") or request.method not in ("GET", "HEAD"):
            return problem(401, "Sign in to use the dashboard.", error="Unauthorized", headers=challenge)
        if challenge or self._public is None or request.path == METRICS_PATH:
            return HttpResponse(b"Unauthorized", status=401, headers=challenge, content_type="text/plain")
        return RedirectHttpResponse("/signin")

    async def _handle(self, request: HttpRequest, asgi_send: ASGISendCallable) -> HttpResponse:
        if self._public is not None and self._public.matches(request):
            return self._refuse_forged_request(request) or await self._public(request)

        try:
            actor = await self._authenticate(request)
        except Declined as declined:
            return declined.response
        if actor is None:
            return self._unauthorized(request)
        set_actor(request, actor)

        if refusal := self._refuse_forged_request(request):
            return refusal

        if request.path == METRICS_PATH:
            return await metrics_controller()

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
