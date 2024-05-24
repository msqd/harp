from _pytest.fixtures import fixture

from harp import Config


class BaseTestForApplications:
    name = None
    config_key = None

    expected_defaults = {}

    @fixture
    def configuration(self):
        config = Config()
        config.add_application(self.name)
        return config

    @fixture
    def ApplicationType(self, configuration):
        return configuration.get_application_type(self.name)

    def test_default_settings_on_none_passed(self, ApplicationType):
        assert ApplicationType.defaults() == self.expected_defaults

    def test_default_settings_on_empty_dict_passed(self, ApplicationType):
        settings = {}
        assert ApplicationType.defaults(settings) == self.expected_defaults

    def test_instanciate_with_default_settings(self, ApplicationType):
        defaults = ApplicationType.defaults()
        application = ApplicationType(defaults)
        assert application.validate() == defaults
