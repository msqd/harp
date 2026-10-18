"""Every example shown on the rules documentation pages must load and match as documented."""

import os
import re

import pytest

import harp
from harp.http import HttpRequest
from harp_apps.http_client.events import HttpClientFilterEvent
from harp_apps.proxy.events import ProxyFilterEvent
from harp_apps.rules.settings import RulesSettings

EXAMPLES_DIR = os.path.join(harp.ROOT_DIR, "docs/apps/rules/examples")


def ruleset(name):
    settings = RulesSettings()
    settings.load(os.path.join(EXAMPLES_DIR, name))
    return settings.ruleset


def sources(rules, *criteria):
    return [script.source.strip() for script in rules.match(*criteria)]


def proxy_event(name, endpoint, method="GET", path="/"):
    event = ProxyFilterEvent(endpoint, request=HttpRequest(method=method, path=path))
    event.name = name
    return event


def test_example_includes_resolve():
    """The snippet is included by pages of the rules directory, which the literalinclude paths are relative to."""
    pages_dir = os.path.dirname(EXAMPLES_DIR)
    with open(os.path.join(EXAMPLES_DIR, "rules.inc")) as f:
        paths = re.findall(r"literalinclude:: (\S+)", f.read())
    assert paths
    for path in paths:
        assert os.path.exists(os.path.join(pages_dir, path)), path


def test_quickstart_toml_and_yaml_are_the_same_rules():
    from_toml = ruleset("rules.toml")._asdict()
    from_yaml = ruleset("rules.yml")._asdict()
    assert from_toml == from_yaml


class TestEndpointLevel:
    rules = ruleset("patterns-endpoint.toml")

    def test_wildcard(self):
        assert len(sources(self.rules, "httpbin-eu", "GET /", "on_request")) == 1
        assert len(sources(self.rules, "httpbin-", "GET /", "on_request")) == 1

    def test_exact(self):
        assert len(sources(self.rules, "api", "GET /", "on_request")) == 1
        assert sources(self.rules, "api2", "GET /", "on_request") == []
        assert sources(self.rules, "my-api", "GET /", "on_request") == []

    def test_case_sensitive(self):
        assert sources(self.rules, "API", "GET /", "on_request") == []


class TestRequestLevel:
    rules = ruleset("patterns-request.toml")

    def test_proxy_fingerprint_is_method_and_path(self):
        event = proxy_event("proxy.filter.request", "api", "GET", "/users/42")
        assert event.criteria[1] == "GET /users/42"
        assert len(list(self.rules.match(*event.criteria))) == 1

    def test_wildcard_crosses_slashes(self):
        assert len(sources(self.rules, "api", "GET /users/42/orders", "on_request")) == 1

    def test_method_must_match(self):
        assert sources(self.rules, "api", "POST /users/42", "on_request") == []

    def test_exact(self):
        assert len(sources(self.rules, "api", "POST /orders", "on_request")) == 1
        assert sources(self.rules, "api", "POST /orders/1", "on_request") == []

    def test_any_method(self):
        for method in ("GET", "DELETE"):
            assert len(sources(self.rules, "api", f"{method} /health", "on_request")) == 1

    def test_remote_fingerprint_includes_query_string(self):
        import httpx

        request = httpx.Request("GET", "https://example.com/users/42?page=2")
        event = HttpClientFilterEvent(request)
        assert event.fingerprint == "GET /users/42?page=2"
        assert len(sources(self.rules, event.endpoint, event.fingerprint, "on_request")) == 1


class TestStageLevel:
    rules = ruleset("patterns-stage.toml")

    @pytest.mark.parametrize(
        "event_name, stage",
        [
            ("proxy.filter.request", "on_request"),
            ("http_client.filter.request", "on_remote_request"),
            ("http_client.filter.response", "on_remote_response"),
            ("proxy.filter.response", "on_response"),
        ],
    )
    def test_stage_names(self, event_name, stage):
        if event_name.startswith("proxy"):
            event = proxy_event(event_name, "api")
        else:
            import httpx

            event = HttpClientFilterEvent(httpx.Request("GET", "https://example.com/"))
            event.name = event_name
        assert event.criteria[2] == stage

    def test_exact_stage(self):
        assert len(sources(self.rules, "api", "POST /", "on_response")) == 1
        assert sources(self.rules, "api", "POST /", "on_request") == []

    def test_wildcard_stage(self):
        assert len(sources(self.rules, "api", "GET /", "on_remote_request")) == 1
        assert len(sources(self.rules, "api", "GET /", "on_remote_response")) == 1
        assert sources(self.rules, "api", "GET /", "on_request") == []


class TestPrecedence:
    rules = ruleset("patterns-order.toml")

    def test_every_matching_rule_runs_in_written_order(self):
        event = proxy_event("proxy.filter.request", "api", "GET", "/x")
        for script in self.rules.match(*event.criteria):
            event.execute_script(script)
        assert event.request.headers["X-Trail"] == "general,specific"

    def test_only_matching_rules_run(self):
        event = proxy_event("proxy.filter.request", "web", "GET", "/x")
        for script in self.rules.match(*event.criteria):
            event.execute_script(script)
        assert event.request.headers["X-Trail"] == "general"
