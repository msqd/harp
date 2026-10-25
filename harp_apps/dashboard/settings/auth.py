import asyncio
import hmac
import secrets
from functools import cached_property
from time import monotonic
from typing import Annotated, Any, Literal

import passlib.hash
from pydantic import BeforeValidator, Field, model_validator

from harp import get_logger
from harp.config import Configurable, Secret
from harp.utils.config import yaml
from harp_apps.dashboard.constants import TAlgorithm

logger = get_logger(__name__)

CHECK_CACHE_TTL = 60.0
CHECK_CACHE_MAX_ENTRIES = 1024


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
    password: Secret

    @model_validator(mode="before")
    @classmethod
    def _replace_strings_by_password_dict(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"password": data}
        return data


class BasicAuthSettings(Configurable):
    type: Literal["basic"] = Field(
        None,
        description="Authentication type.",
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
    def _algorithm_module(self):
        return getattr(passlib.hash, self.algorithm)

    @cached_property
    def algorithm_impl(self):
        return self._algorithm_module.verify

    @cached_property
    def _dummy_hash(self):
        """A valid hash for the configured algorithm, verified against when the user is unknown."""
        return self._algorithm_module.hash("harp")

    @cached_property
    def _verified(self) -> dict[bytes, float]:
        return {}

    @cached_property
    def _cache_secret(self) -> bytes:
        """Random key of this process, never logged nor persisted, so cache keys are useless outside of it."""
        return secrets.token_bytes(32)

    def _cache_key(self, username, password) -> bytes:
        # Not password storage (CodeQL py/weak-sensitive-data-hashing, dismissed): the key only lives in memory, under
        # a random per-process secret, for CHECK_CACHE_TTL. Reading it needs process memory, which already exposes the
        # plaintext credentials of live requests.
        return hmac.new(self._cache_secret, f"{len(username)}:{username}:{password}".encode(), "sha256").digest()

    def check(self, username, password):
        """Blocking check (hashing is slow by design), prefer :meth:`acheck` from the event loop."""
        user = self.users.get(username)
        stored = user.password.get_secret_value() if user else self._dummy_hash

        try:
            matches = self.algorithm_impl(password, stored)
        except ValueError:
            logger.error(
                f"Dashboard user «{username}» has a stored password that is not a valid {self.algorithm} hash, "
                "authentication refused. Check dashboard.auth.users."
            )
            return False

        if not user or not matches:
            return False

        return username

    async def acheck(self, username, password):
        """Same as :meth:`check`, without blocking the event loop. Successful checks are remembered for a while."""
        key = self._cache_key(username, password)
        now = monotonic()

        if self._verified.get(key, 0) > now:
            return username

        result = await asyncio.to_thread(self.check, username, password)
        if result:
            for expired in [k for k, v in self._verified.items() if v <= now]:
                del self._verified[expired]
            if len(self._verified) < CHECK_CACHE_MAX_ENTRIES:
                self._verified[key] = now + CHECK_CACHE_TTL
        return result

    @model_validator(mode="before")
    @classmethod
    def model_always_shown_defaults(cls, data):
        """This validator overcomes the behaviour of model_dump(exclude_defaults=True, exclude_unset=True) and forces
        some defaults to be dumped everytime."""
        data.setdefault("type", "basic")
        return data
