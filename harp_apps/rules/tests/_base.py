from harp.config import ConfigurationBuilder, SystemBuilder


class BaseRulesFlowTest:
    applications = []

    async def create_system(self, settings, /, *, mock):
        config = ConfigurationBuilder(
            (settings or {}) | {"applications": self.applications},
            use_default_applications=False,
        )
        system = await SystemBuilder(config).abuild()
        system.config["rules"].ruleset.add({"*": {"*": {"*": [mock]}}})
        return system
