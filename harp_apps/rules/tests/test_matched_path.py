"""The rules match the path the proxy forwards: scheme and authority removed, unreserved percent-escapes decoded,
no query string. Requests are built from raw ASGI scopes, as a server delivers them."""

from unittest.mock import AsyncMock

import httpx
import pytest
from whistle import AsyncEventDispatcher

from harp.asgi.bridge.requests import HttpRequestAsgiBridge
from harp.http import HttpRequest
from harp_apps.http_client.events import EVENT_FILTER_HTTP_CLIENT_REQUEST, HttpClientFilterEvent
from harp_apps.proxy.events import EVENT_FILTER_PROXY_REQUEST, ProxyFilterEvent

from ..models.rulesets import RuleSet
from ..subscribers import RulesSubscriber


def _asgi_request(raw_path: str, query: bytes = b"") -> HttpRequest:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": raw_path,
        "raw_path": raw_path.encode(),
        "query_string": query,
        "headers": [],
        "server": ["127.0.0.1", 80],
    }
    receive = AsyncMock(return_value={"type": "http.request", "body": b"", "more_body": False})
    return HttpRequest(HttpRequestAsgiBridge(scope, receive))


def _ruleset(pattern: str) -> RuleSet:
    rules = RuleSet()
    rules.add({"api": {pattern: {"on_request": "context['response'] = 'denied'"}}})
    return rules


def _matches(rules: RuleSet, request: HttpRequest) -> bool:
    event = ProxyFilterEvent("api", request=request)
    event.name = EVENT_FILTER_PROXY_REQUEST
    return len(list(rules.match(*event.criteria))) == 1


@pytest.mark.parametrize(
    "raw_path",
    [
        "/admin",
        "http://example.com/admin",
        "https://user@example.com:8080/admin",
        "//evil.example/admin",
        "/%61dmin",
        "/%61%64%6d%69%6e",
        "/%61dmin?x=1",
    ],
)
def test_proxy_level_matches_the_forwarded_path(raw_path):
    assert _matches(_ruleset("GET /admin"), _asgi_request(raw_path))


def test_reserved_escapes_stay_encoded():
    assert not _matches(_ruleset("GET /a/b"), _asgi_request("/a%2fb"))
    assert _matches(_ruleset("GET /a%2fb"), _asgi_request("/a%2fb"))


def test_query_string_is_not_matched():
    assert _matches(_ruleset("GET /admin"), _asgi_request("/admin", b"x=1"))


def test_unparsable_authority_is_matched_as_received():
    assert _matches(_ruleset("GET //[x/admin"), _asgi_request("//[x/admin"))


def test_empty_path_is_root():
    assert _matches(_ruleset("GET /"), _asgi_request("http://example.com"))


def _remote_ruleset(pattern: str) -> RuleSet:
    rules = RuleSet()
    rules.add({"api": {pattern: {"on_remote_request": "logger.info('ran')"}}})
    return rules


async def _dispatch_remote(rules: RuleSet, url: str):
    dispatcher = AsyncEventDispatcher()
    RulesSubscriber(rules).subscribe(dispatcher)
    event = HttpClientFilterEvent(httpx.Request("GET", url, extensions={"harp": {"endpoint": "api"}}))
    await dispatcher.adispatch(EVENT_FILTER_HTTP_CLIENT_REQUEST, event)
    return event


def _deprecations(caplog):
    return [r.getMessage() for r in caplog.records if "Deprecated" in r.getMessage()]


async def test_remote_level_pattern_relying_on_query_still_matches_and_warns(caplog):
    rules = _remote_ruleset("GET /users?page=2")
    with caplog.at_level("WARNING"):
        event = await _dispatch_remote(rules, "http://example.com/users?page=2")
    assert event.fingerprint == "GET /users?page=2"
    assert len(list(rules.match(*event.criteria))) == 1
    (message,) = _deprecations(caplog)
    assert "GET /users?page=2" in message


async def test_remote_level_path_only_pattern_does_not_warn(caplog):
    with caplog.at_level("WARNING"):
        await _dispatch_remote(_remote_ruleset("GET /users*"), "http://example.com/users?page=2")
    assert not _deprecations(caplog)


async def _is_denied(pattern: str, raw_path: str) -> bool:
    """Whether a deny rule written as ``pattern`` answers a request for ``raw_path``, through the subscriber."""
    rules = RuleSet()
    rules.add({"api": {pattern: {"on_request": "response = {'denied': True}"}}})
    dispatcher = AsyncEventDispatcher()
    RulesSubscriber(rules).subscribe(dispatcher)
    event = ProxyFilterEvent("api", request=_asgi_request(raw_path))
    await dispatcher.adispatch(EVENT_FILTER_PROXY_REQUEST, event)
    return event.response is not None and event.response.status == 200


@pytest.mark.parametrize(
    "raw_path",
    [
        "/admin//users",
        "///admin///users",
        "/admin;x=1/users",
        "/admin/users;jsessionid=1",
        "/;/admin/users",
        "/admin%2Fusers",
        "/admin%2fusers",
        "/admin%2F%2Fusers",
        "/%61dmin%2Fusers",
    ],
)
async def test_deny_rule_holds_for_path_variants_the_upstream_normalises(raw_path):
    assert await _is_denied("GET /admin/users", raw_path)


@pytest.mark.parametrize("raw_path", ["/admin/", "/admin//", "/admin/;x", "/admin/users/", "/admin%2F", "/admin/a;b/"])
async def test_prefix_deny_rule_still_matches_trailing_slash_variants(raw_path):
    assert await _is_denied("GET /admin/*", raw_path)


@pytest.mark.parametrize("raw_path", ["/admin/users/", "/admin/users;a=1/", "/%61dmin%2Fusers/"])
async def test_trailing_slash_is_kept_so_exact_deny_rules_end_with_a_wildcard(raw_path):
    assert not await _is_denied("GET /admin/users", raw_path)
    assert await _is_denied("GET /admin/users*", raw_path)


async def test_other_paths_are_not_denied():
    assert not await _is_denied("GET /admin/users", "/admin/users2")
    assert not await _is_denied("GET /admin/users", "/admin/user;s")
    assert not await _is_denied("GET /admin/users", "/other/admin/users")


def test_fingerprint_collapses_variants_but_keeps_reserved_escapes_encoded():
    event = ProxyFilterEvent("api", request=_asgi_request("/a///b;x=1/c%2Fd/"))
    assert event.fingerprint == "GET /a/b/c%2Fd/"
    assert event.alternate_fingerprints == ["GET /a/b/c/d/"]


def test_root_stays_root():
    assert ProxyFilterEvent("api", request=_asgi_request("/;a=1")).fingerprint == "GET /"
