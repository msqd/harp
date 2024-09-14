from functools import cached_property
from typing import Annotated, Any, Literal

from pydantic import BeforeValidator, Field, model_validator

from harp.config import Configurable
from harp.utils.config import yaml
from harp_apps.dashboard.constants import TAlgorithm


def _replace_plain_algorithm_for_bc(value):
    if value == "plain":
        return "plaintext"
    return value


def _load(value):
    if isinstance(value, dict) and "fromFile" in value:
        with open(value["fromFile"]) as f:
            return yaml.safe_load(f)
    return value


class User(Configurable):
    password: str

    @model_validator(mode="before")
    @classmethod
    def _replace_strings_by_password_dict(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"password": data}
        return data


class BasicAuthSettings(Configurable):
    type: Literal["basic"] = Field(
        None,
        description="Authentication type. Only «basic» is supported for now.",
    )

    algorithm: Annotated[
        TAlgorithm,
        BeforeValidator(_replace_plain_algorithm_for_bc),
        Field(
            "pbkdf2_sha256",
            description="Hashing algorithm used for passwords.",
        ),
    ]

    users: Annotated[
        dict[str, User],
        BeforeValidator(_load),
        Field(
            default_factory=dict,
            description="Users list.",
        ),
    ]

    @cached_property
    def algorithm_impl(self):
        impl = __import__("passlib.hash", fromlist=[self.algorithm])
        return getattr(impl, self.algorithm).verify

    def check(self, username, password):
        user = self.users.get(username)

        if not user:
            return False

        if not self.algorithm_impl(password, user.password):
            return False

        return username

    @model_validator(mode="before")
    @classmethod
    def model_always_shown_defaults(cls, data):
        """This validator overcomes the behaviour of model_dump(exclude_defaults=True, exclude_unset=True) and forces
        some defaults to be dumped everytime."""
        data.setdefault("type", "basic")
        return data
