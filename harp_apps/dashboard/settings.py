from functools import cached_property
from typing import Literal, Optional

from harp.config import BaseSetting, FromFileSetting, settings_dataclass
from harp.errors import ConfigurationRemovedSettingError, ConfigurationValueError


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
                raise ConfigurationValueError(
                    "Invalid configuration for dashboard auth. There should not be additional arguments if no auth "
                    f"type is provided. Available types: {', '.join(available_types)}."
                )
            return None

        if _type == "basic":
            return DashboardAuthBasicSetting(**kwargs)

        raise ConfigurationValueError(
            f"Invalid dashboard auth type: {_type}. Available types: {', '.join(available_types)}."
        )

    def check(self, username, password):
        raise NotImplementedError()


@settings_dataclass
class DashboardSettings(BaseSetting):
    """Root settings for the dashboard."""

    port: int | str = 4080
    auth: Optional[DashboardAuthSetting] = None
    devserver_port: Optional[int | str] = None

    def __post_init__(self):
        if isinstance(self.auth, str):
            raise ConfigurationRemovedSettingError(
                "Invalid configuration for dashboard auth: string configuration is not supported anymore."
            )

        if isinstance(self.auth, dict):
            object.__setattr__(self, "auth", DashboardAuthSetting(**self.auth))
