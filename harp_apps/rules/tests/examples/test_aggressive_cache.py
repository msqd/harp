import httpx
import pytest

from harp_apps.http_client.events import HttpClientFilterEvent
from harp.config.examples import get_example_filename
from harp_apps.rules.settings import RulesSettings


def apply_aggressive_cache(request_headers: dict, response_headers: dict) -> httpx.Response:
    settings = RulesSettings()
    settings.load(get_example_filename("rules:aggressive-cache"))
    rules = settings.ruleset
    event = HttpClientFilterEvent(
        httpx.Request("GET", "http://example.com/", headers=request_headers),
        httpx.Response(200, headers=response_headers),
    )
    event.name = "http_client.filter.response"
    for script in rules.match("acme", "GET /", "on_remote_response"):
        event.execute_script(script)
    return event.response


class TestAggressiveCacheExample:
    def test_anonymous_get_is_cached_for_an_hour_but_not_public(self):
        response = apply_aggressive_cache({}, {})
        assert response.headers["Cache-Control"] == "max-age=3600"

    @pytest.mark.parametrize("header", ["Authorization", "Cookie"])
    def test_request_with_identity_is_left_alone(self, header):
        response = apply_aggressive_cache({header: "secret"}, {"Cache-Control": "max-age=10"})
        assert response.headers["Cache-Control"] == "max-age=10"
        response = apply_aggressive_cache({header: "secret"}, {})
        assert "Cache-Control" not in response.headers

    def test_upstream_private_is_kept(self):
        response = apply_aggressive_cache({}, {"Cache-Control": "Private, max-age=60"})
        assert response.headers["Cache-Control"] == "Private, max-age=60"
