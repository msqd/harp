from typing import Optional

from .base import BaseSetting, settings_dataclass


@settings_dataclass
class DisabledSettings(BaseSetting):
    enabled: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.enabled is True:
            raise ValueError("Cannot set enabled to True in DisabledSettings")

    def __setattr__(self, name, value):
        if name == "enabled" and value is True:
            raise ValueError("Cannot set enabled to True in DisabledSettings")
        super().__setattr__(name, value)

    def __repr__(self):
        return "disabled"


@settings_dataclass
class DisableableBaseSettings(BaseSetting):
    enabled: Optional[bool] = True

    def __new__(cls, **kwargs):
        _enabled = kwargs.pop("enabled", True)

        # todo better parsing of falsy values
        if isinstance(_enabled, str) and _enabled.lower() in {"no", "false", "0"}:
            _enabled = False

        if not _enabled:
            return DisabledSettings()

        return super().__new__(cls)
