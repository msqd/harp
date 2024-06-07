from typing import Optional

from .base import BaseSetting, settings_dataclass


@settings_dataclass
class DisabledSettings(BaseSetting):
    # todo we should not be able to set enabled = True for this class
    enabled: bool = False

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
