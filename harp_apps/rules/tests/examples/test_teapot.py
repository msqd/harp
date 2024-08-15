from harp.http import HttpRequest
from harp_apps.proxy.events import ProxyFilterEvent
from harp_apps.rules import examples
from harp_apps.rules.settings import RulesSettings


class TestTeapotExample:
    source = examples.load("teapot.yml").get("rules")

    def create_request(self, **kwargs):
        return HttpRequest(**kwargs)

    def create_proxy_filter_event(self, event_name, /, *, endpoint, **kwargs):
        event = ProxyFilterEvent(endpoint, **kwargs)
        event.name = event_name
        return event

    def get_rules(self):
        settings = RulesSettings(**self.source)
        return settings.ruleset

    def test_on_proxy_filter_request(self):
        rules = self.get_rules()
        event = self.create_proxy_filter_event("proxy.filter.request", endpoint="acme1", request=self.create_request())

        scripts = list(rules.match(*event.criteria))
        assert len(scripts) == 1

        event.execute_script(scripts[0])
        assert event.response.status == 418
