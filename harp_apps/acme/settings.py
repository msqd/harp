from harp.config import ApplicationSettingsMixin, Configurable


class AcmeSettings(ApplicationSettingsMixin, Configurable):
    owner: str = "Joe"
