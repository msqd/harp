from functools import cached_property
from typing import Literal, Optional

from harp.core.settings import BaseSetting, DisabledSettings, FromFileSetting, settings_dataclass
from harp.errors import ProxyConfigurationError


def _plain(actual, expected):
    return actual == expected


@settings_dataclass
class DashboardAuthBasicSetting(BaseSetting):
    type: str = "basic"
    algorithm: str = "pbkdf2_sha256"
    users: Optional[FromFileSetting | dict[str, str]] = None

    def __post_init__(self):
        FromFileSetting.may_override(self, "users")

    @cached_property
    def algorithm_impl(self):
        if self.algorithm == "plain":
            return _plain
        # todo check we do not import anything else than a valid algorithm implementation
        impl = __import__("passlib.hash", fromlist=[self.algorithm])
        return getattr(impl, self.algorithm).verify

    def check(self, username, password):
        if not self.users:
            return False

        if isinstance(self.users, dict):
            user = self.users.get(username)
            if not user:
                return False
            if "password" not in user:
                return False
            if not self.algorithm_impl(password, user["password"]):
                return False
            return username
        else:
            raise NotImplementedError("Only dict is supported for now")


@settings_dataclass
class DashboardAuthSetting(BaseSetting):
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
            return DashboardAuthBasicSetting(**kwargs)

        raise ProxyConfigurationError(
            f"Invalid dashboard auth type: {_type}. Available types: {', '.join(available_types)}."
        )

    def check(self, username, password):
        raise NotImplementedError()


@settings_dataclass
class DashboardSettings(BaseSetting):
    enabled: bool = True
    port: int | str = 4080
    auth: Optional[DashboardAuthSetting] = None
    devserver_port: Optional[int | str] = None

    def __new__(cls, **kwargs):
        # todo generic management of disablable settings
        _enabled = kwargs.pop("enabled", True)
        # todo better parsing of falsy values
        if isinstance(_enabled, str) and _enabled.lower() in {"no", "false", "0"}:
            _enabled = False

        if not _enabled:
            return DisabledSettings()

        return super().__new__(cls)

    def __post_init__(self):
        if not self.enabled:
            raise RuntimeError("DashboardSettings should never be instanciated if disabled.")

        if isinstance(self.auth, str):
            raise ProxyConfigurationError(
                "Invalid configuration for dashboard auth: string configuration is not supported anymore."
            )

        if isinstance(self.auth, dict):
            object.__setattr__(self, "auth", DashboardAuthSetting(**self.auth))