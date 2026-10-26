"""Signing in and out of the dashboard.

Two groups of routes. The **public** ones (the sign-in and setup pages and the requests they make) are answered before
the dashboard looks for a session, since they are how one gets a session: :class:`PublicAuthRoutes`. The others
(sign out, sign out everywhere, change the password) are ordinary routes of the dashboard, behind a session:
:class:`AuthController`. The CSRF guard of the dashboard covers both, since every one of them is a ``POST``.
"""

import math
from importlib.resources import files
from typing import Optional, TypeVar

from pydantic import BaseModel, ValidationError

from harp.controllers import PostHandler, RouterPrefix, RoutingController
from harp.http import HttpRequest, HttpResponse, JsonHttpResponse
from harp.security.actor import Role, get_actor
from harp_apps.auth.passwords import PasswordPolicyError
from harp_apps.auth.sessions import SessionsService
from harp_apps.auth.models import UsernameRefused
from harp_apps.auth.setup import SetupLink, SetupLinkRefused
from harp_apps.auth.passwords import HasherBusy
from harp_apps.auth.signin import Authenticator, Busy, Refused, Signed, Throttled
from harp_apps.dashboard.security.addresses import client_address
from harp_apps.dashboard.security.cookies import clear_session_cookie, is_secure, set_session_cookie
from harp_apps.dashboard.settings import DashboardSettings

from .models.auth import ChangePasswordInput, NoInput, SetupInput, SignInInput

#: Nobody signs in or sets a password with more than this in the body.
MAX_BODY = 16 * 1024

T = TypeVar("T", bound=BaseModel)


def _page(name: str) -> bytes:
    return files("harp_apps.dashboard").joinpath("pages", name).read_bytes()


def problem(status: int, message: str, *, error: str, headers: Optional[dict] = None) -> JsonHttpResponse:
    return JsonHttpResponse(
        {"error": error, "status": status, "message": message},
        status=status,
        headers={"Cache-Control": "no-store", **(headers or {})},
    )


def ok(body: Optional[dict] = None) -> JsonHttpResponse:
    return JsonHttpResponse({"ok": True, **(body or {})}, headers={"Cache-Control": "no-store"})


async def read_input(request: HttpRequest, model: type[T]) -> T | JsonHttpResponse:
    """The JSON body as ``model``, or the 400 to answer."""
    # The sign-in routes are reachable by anyone: stop reading at the limit, whatever the request says it will send.
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BODY:
        return problem(413, "The request is too large.", error="Payload Too Large")
    parts, size = [], 0
    async for part in request.stream:
        size += len(part)
        if size > MAX_BODY:
            return problem(413, "The request is too large.", error="Payload Too Large")
        parts.append(part)
    body = b"".join(parts)
    try:
        return model.model_validate_json(body)
    except ValidationError:
        return problem(400, "The request is malformed.", error="Bad Request")


def _address(request: HttpRequest, settings: DashboardSettings) -> str:
    # The address of the connection, or the client's when a trusted proxy says so: a header says whatever its sender
    # wants, and the limits per address go with it.
    return client_address(request, settings.trusted_proxies)


def busy(retry_after: float = 1.0) -> JsonHttpResponse:
    seconds = max(1, math.ceil(retry_after))
    return problem(
        503,
        "Too many sign-ins at once. Try again in a moment.",
        error="Service Unavailable",
        headers={"Retry-After": str(seconds)},
    )


def too_many(retry_after: float) -> JsonHttpResponse:
    seconds = max(1, math.ceil(retry_after))
    return problem(
        429,
        f"Too many attempts. Try again in {seconds} seconds.",
        error="Too Many Requests",
        headers={"Retry-After": str(seconds)},
    )


def _start_session(response: HttpResponse, request: HttpRequest, settings: DashboardSettings, signed: Signed, max_age):
    set_session_cookie(
        response, signed.secret, secure=is_secure(request, public_url=settings.public_url), max_age=max_age
    )
    return response


class PublicAuthRoutes:
    """What is reachable without a session: the pages, and the requests that make a session."""

    def __init__(
        self,
        authenticator: Authenticator,
        setup: SetupLink,
        settings: DashboardSettings,
    ):
        self.authenticator = authenticator
        self.setup = setup
        self.settings = settings
        # the browser keeps the cookie as long as the server would accept the session
        self.session_max_age = int(authenticator.sessions.settings.session_max_age.total_seconds())
        self._routes = {
            ("GET", "/signin"): self._signin_page,
            ("GET", "/setup"): self._setup_page,
            ("GET", "/auth.js"): self._script,
            ("POST", "/api/auth/signin"): self._signin,
            ("POST", "/api/auth/setup"): self._setup,
        }

    def _handler(self, request: HttpRequest):
        method = "GET" if request.method == "HEAD" else request.method
        return self._routes.get((method, request.path.rstrip("/") or "/"))

    def matches(self, request: HttpRequest) -> bool:
        return self._handler(request) is not None

    async def __call__(self, request: HttpRequest) -> HttpResponse:
        return await self._handler(request)(request)

    @staticmethod
    def _document(name: str, content_type: str) -> HttpResponse:
        return HttpResponse(_page(name), content_type=content_type, headers={"Cache-Control": "no-store"})

    async def _signin_page(self, request):
        return self._document("signin.html", "text/html; charset=utf-8")

    async def _setup_page(self, request):
        return self._document("setup.html", "text/html; charset=utf-8")

    async def _script(self, request):
        return self._document("auth.js", "text/javascript; charset=utf-8")

    async def _signin(self, request: HttpRequest) -> HttpResponse:
        data = await read_input(request, SignInInput)
        if isinstance(data, HttpResponse):
            return data
        result = await self.authenticator.sign_in(
            data.username,
            data.password,
            ip=_address(request, self.settings),
            user_agent=request.headers.get("user-agent"),
        )
        match result:
            case Signed():
                return _start_session(ok(), request, self.settings, result, self.session_max_age)
            case Throttled(retry_after=wait):
                return too_many(wait)
            case Busy(retry_after=wait):
                return busy(wait)
            case Refused():
                return problem(401, "Wrong username or password.", error="Unauthorized")

    async def _setup(self, request: HttpRequest) -> HttpResponse:
        data = await read_input(request, SetupInput)
        if isinstance(data, HttpResponse):
            return data
        try:
            signed = await self.setup.accept(
                data.secret,
                data.username,
                data.password,
                ip=_address(request, self.settings),
                user_agent=request.headers.get("user-agent"),
            )
        except SetupLinkRefused:
            return problem(
                400,
                "This setup link is not valid anymore. Restart HARP to get a new one in its logs.",
                error="Bad Request",
            )
        except (UsernameRefused, PasswordPolicyError) as exc:
            return problem(400, str(exc), error="Bad Request")
        except HasherBusy:
            return busy()
        return _start_session(ok(), request, self.settings, signed, self.session_max_age)


@RouterPrefix("/api/auth")
class AuthController(RoutingController):
    """Ending sessions and changing the password: what an account does once it is signed in."""

    def __init__(
        self,
        *,
        authenticator: Authenticator,
        sessions: SessionsService,
        settings: DashboardSettings,
        router=None,
        handle_errors=True,
    ):
        self.authenticator = authenticator
        self.sessions = sessions
        self.settings = settings
        super().__init__(router=router, handle_errors=handle_errors)

    def _cleared(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        clear_session_cookie(response, secure=is_secure(request, public_url=self.settings.public_url))
        return response

    @PostHandler("/signout", role=Role.VIEWER)
    async def signout(self, request: HttpRequest):
        """Ends the session of the request. The other sessions of the account stay open."""
        data = await read_input(request, NoInput)
        if isinstance(data, HttpResponse):
            return data
        actor = get_actor(request)
        if actor.via != "session":
            return problem(400, "This request did not sign in with a session.", error="Bad Request")
        await self.sessions.revoke(int(actor.via_id))
        return self._cleared(request, ok())

    @PostHandler("/signout-all", role=Role.VIEWER)
    async def signout_all(self, request: HttpRequest):
        """Ends every session of the account, this one included."""
        data = await read_input(request, NoInput)
        if isinstance(data, HttpResponse):
            return data
        revoked = await self.sessions.revoke_all(get_actor(request).account.id)
        return self._cleared(request, ok({"revoked": revoked}))

    @PostHandler("/password", role=Role.VIEWER)
    async def change_password(self, request: HttpRequest):
        """Changes the password and ends the other sessions of the account."""
        data = await read_input(request, ChangePasswordInput)
        if isinstance(data, HttpResponse):
            return data
        actor = get_actor(request)
        if actor.via != "session":
            return problem(400, "Sign in with a session to change the password.", error="Bad Request")
        try:
            changed = await self.authenticator.change_password(
                actor.account.id,
                actor.account.username,
                data.current,
                data.new,
                keep=int(actor.via_id),
                ip=_address(request, self.settings),
            )
        except PasswordPolicyError as exc:
            return problem(400, str(exc), error="Bad Request")
        match changed:
            case Throttled(retry_after=wait):
                return too_many(wait)
            case Busy(retry_after=wait):
                return busy(wait)
            case Refused():
                return problem(403, "The current password is not right.", error="Forbidden")
        return ok()
