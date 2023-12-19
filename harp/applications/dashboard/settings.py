from typing import Literal, Optional

from harp.core.settings import settings_dataclass
from harp.errors import ProxyConfigurationError


@settings_dataclass
class FromFileSetting:
    from_file: str


@settings_dataclass
class DashboardAuthBasicSettings:
    type = "basic"
    passwd: Optional[FromFileSetting | dict[str, str]] = None


@settings_dataclass
class DashboardAuthSettings:
    type: Optional[Literal["basic"] | None] = None

    def __new__(cls, **kwargs):
        _type = kwargs.pop("type", None)
        available_types = ("basic",)

        if _type is None or not _type:
            if len(kwargs) > 0:
                raise ProxyConfigurationError(
                    "Invalid configuration for dashboard auth. There should not be additional arguments if no auth "
                    f"type is provided. Available types: {', '.join(available_types)}."
                )
            return None

        if _type == "basic":
            return DashboardAuthBasicSettings(**kwargs)

        raise ProxyConfigurationError(
            f"Invalid dashboard auth type: {_type}. Available types: {', '.join(available_types)}."
        )


@settings_dataclass
class DisabledSettings:
    enabled = False

    def __repr__(self):
        return "disabled"


@settings_dataclass
class DashboardSettings:
    enabled = True
    port: int | str = 4080
    auth: str | None = None

    def __new__(cls, **kwargs):
        # todo generic management of disablable settings
        _enabled = kwargs.pop("enabled", True)
        if isinstance(_enabled, str) and _enabled.lower() in {"no", "false", "0"}:
            _enabled = False
        if not _enabled:
            return DisabledSettings()

        return super().__new__(cls)


if __name__ == "__main__":
    s = DashboardAuthSettings()
    print(s)

    s = DashboardAuthSettings(type="")
    print(s)

    s = DashboardAuthSettings(type=None)
    print(s)

    s = DashboardAuthSettings(type="basic", passwd={"foo": "bar"})
    print(s)
