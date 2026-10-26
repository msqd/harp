"""The dashboard session cookie.

Over HTTPS it is ``__Host-harp_session``: the prefix makes a browser refuse it unless it is Secure, set from a secure
origin, without a Domain and with Path=/, so a sibling subdomain cannot plant one. Over plain HTTP, where the prefix
cannot be used, it is ``harp_session``. Names are in :mod:`harp.security.credentials`, which the proxy relies on to never
let this cookie reach an origin.

Whether a request is secure cannot be seen from the request alone behind a reverse proxy that terminates TLS: it is when
the proxy says so (``X-Forwarded-Proto``) or when the dashboard is configured with an ``https`` public URL.
"""

from typing import Optional

from harp.http import HttpRequest, HttpResponse
from harp.security.credentials import SECURE_SESSION_COOKIE_NAME, SESSION_COOKIE_NAME


def is_secure(request: HttpRequest, *, public_url: Optional[str]) -> bool:
    if public_url and public_url.lower().startswith("https://"):
        return True
    return request.headers.get("x-forwarded-proto", "").strip().lower() == "https"


def _name(secure: bool) -> str:
    return SECURE_SESSION_COOKIE_NAME if secure else SESSION_COOKIE_NAME


def read_session_secret(request: HttpRequest, *, secure: bool) -> Optional[str]:
    """The secret in the session cookie. Only the name this deployment sets is read, so over HTTPS a cookie planted
    under the plain name (from a plain HTTP origin of the same site) opens nothing."""
    return request.cookies.get(_name(secure))


def _attributes(secure: bool, max_age: int) -> str:
    return f"Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}" + ("; Secure" if secure else "")


def set_session_cookie(response: HttpResponse, secret: str, *, secure: bool, max_age: int) -> None:
    response.headers.add("Set-Cookie", f"{_name(secure)}={secret}; {_attributes(secure, max_age)}")


def clear_session_cookie(response: HttpResponse, *, secure: bool) -> None:
    response.headers.add("Set-Cookie", f"{_name(secure)}=; {_attributes(secure, 0)}")
