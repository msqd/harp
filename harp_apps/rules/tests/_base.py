from harp.config import ConfigurationBuilder


class BaseRulesFlowTest:
    applications = []

    async def create_system(self, settings, /, *, mock):
        system = await ConfigurationBuilder(
            (settings or {}) | {"applications": self.applications},
            use_default_applications=False,
        ).abuild_system()
        system.config["rules"].ruleset.add({"*": {"*": {"*": [mock]}}})
        return system
