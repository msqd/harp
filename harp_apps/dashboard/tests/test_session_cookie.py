import pytest

from harp.http import HttpRequest, HttpResponse
from harp_apps.dashboard.security.cookies import (
    clear_session_cookie,
    is_secure,
    read_session_secret,
    set_session_cookie,
)

SECRET = "s" * 43


def request(**headers):
    return HttpRequest(headers=headers)


def test_a_request_is_secure_when_the_reverse_proxy_says_so():
    assert is_secure(request(**{"x-forwarded-proto": "https"}), public_url=None) is True
    assert is_secure(request(**{"x-forwarded-proto": "http"}), public_url=None) is False
    assert is_secure(request(), public_url=None) is False


def test_a_request_is_secure_when_the_public_url_is_https():
    assert is_secure(request(), public_url="https://harp.example.com") is True
    assert is_secure(request(), public_url="http://harp.example.com") is False


def test_the_cookie_over_https_is_host_prefixed_http_only_same_site_lax_and_secure():
    response = HttpResponse(b"")

    set_session_cookie(response, SECRET, secure=True, max_age=604800)

    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"__Host-harp_session={SECRET};")
    attributes = {a.strip().lower() for a in cookie.split(";")[1:]}
    assert {"path=/", "httponly", "samesite=lax", "secure", "max-age=604800"} <= attributes
    assert not any(a.startswith("domain") for a in attributes)


def test_the_cookie_over_http_is_not_secure_and_has_no_prefix():
    response = HttpResponse(b"")

    set_session_cookie(response, SECRET, secure=False, max_age=60)

    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"harp_session={SECRET};")
    attributes = {a.strip().lower() for a in cookie.split(";")[1:]}
    assert {"path=/", "httponly", "samesite=lax"} <= attributes and "secure" not in attributes


@pytest.mark.parametrize("secure, name", [(True, "__Host-harp_session"), (False, "harp_session")])
def test_clearing_expires_the_cookie_it_set(secure, name):
    response = HttpResponse(b"")

    clear_session_cookie(response, secure=secure)

    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{name}=;") and "max-age=0" in cookie.lower()
    assert ("secure" in cookie.lower()) is secure


def test_over_https_only_the_host_prefixed_cookie_is_read():
    assert read_session_secret(request(cookie=f"__Host-harp_session={SECRET}"), secure=True) == SECRET
    assert read_session_secret(request(cookie=f"harp_session={SECRET}"), secure=True) is None


def test_over_http_only_the_plain_cookie_is_read():
    assert read_session_secret(request(cookie=f"harp_session={SECRET}"), secure=False) == SECRET
    assert read_session_secret(request(cookie=f"__Host-harp_session={SECRET}"), secure=False) is None


def test_the_name_is_case_sensitive_and_other_cookies_are_ignored():
    assert read_session_secret(request(cookie=f"HARP_SESSION={SECRET}; other=1"), secure=False) is None
    assert read_session_secret(request(cookie=f"theme=dark; harp_session={SECRET}"), secure=False) == SECRET
    assert read_session_secret(request(), secure=False) is None
