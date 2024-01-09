from .base import BaseSetting, settings_dataclass


@settings_dataclass
class DisabledSettings(BaseSetting):
    # todo we should not be able to set enabled = True for this class
    enabled: bool = False

    def __repr__(self):
        return "disabled"
