from harp.config import ConfigurationBuilder, SystemBuilder


class BaseRulesFlowTest:
    applications = []

    async def create_system(self, settings, /, *, mock):
        config = ConfigurationBuilder(
            (settings or {}) | {"applications": self.applications},
            use_default_applications=False,
        )
        config.add_values({"rules": {"*": {"*": {"*": [mock]}}}})
        return await SystemBuilder(config).abuild()
