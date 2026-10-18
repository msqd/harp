from harp.config import ConfigurationBuilder


class BaseRulesFlowTest:
    applications = []

    async def create_system(self, settings, /, *, mock):
        # respx mocks the httpx transports only.
        http_client = {"http_client": {"transport": {"type": "httpx.AsyncHTTPTransport"}}}
        system = await ConfigurationBuilder(
            http_client | (settings or {}) | {"applications": self.applications},
            use_default_applications=False,
        ).abuild_system(validate_dependencies=False)
        system.config["rules"].ruleset.add({"*": {"*": {"*": [mock]}}})
        return system
