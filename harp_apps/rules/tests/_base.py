from harp import Config


class BaseRulesFlowTest:
    applications = []

    def create_config(self, settings, /, *, mock):
        config = Config(settings, applications=self.applications)
        config.validate()
        config["rules"].settings.rules.add({"*": {"*": {"*": [mock]}}})
        return config
