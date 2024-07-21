from harp.http import HttpRequest
from harp.http.tests.stubs import HttpRequestStubBridge
from harp_apps.proxy.events import ProxyFilterEvent
from harp_apps.rules import examples
from harp_apps.rules.settings import RulesSettings


class TestTeapotExample:
    source = examples.load("teapot.yml").get("rules")

    def create_request(self, **kwargs):
        return HttpRequest(HttpRequestStubBridge(**kwargs))

    def create_proxy_filter_event(self, event_name, /, *, endpoint, **kwargs):
        event = ProxyFilterEvent(endpoint, **kwargs)
        event.name = event_name
        return event

    def get_rules(self):
        settings = RulesSettings(**self.source)
        return settings.rules

    def test_on_proxy_filter_request(self):
        rules = self.get_rules()
        event = self.create_proxy_filter_event("proxy.filter.request", endpoint="acme1", request=self.create_request())

        scripts = list(rules.match(*event.criteria))
        assert len(scripts) == 1

        scripts[0].execute(event.locals, globals=event.globals)
        assert event.response.status == 418
