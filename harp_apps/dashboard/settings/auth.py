import asyncio
import hmac
import secrets
from concurrent.futures import ThreadPoolExecutor
from functools import cached_property
from time import monotonic
from typing import Annotated, Any, Literal

from pydantic import BeforeValidator, Field, model_validator

from harp import get_logger
from harp.config import Configurable, Secret
from harp.utils.config import yaml
from harp_apps.dashboard.passwords import (
    ALGORITHMS,
    TAlgorithm,
    dummy_hash,
    hash_cost,
    pad_verification,
    verify_password,
)

logger = get_logger(__name__)

CHECK_CACHE_TTL = 60.0
CHECK_CACHE_MAX_ENTRIES = 1024

# Password verifications are slow and memory hungry by design, and anyone can trigger them with random credentials. They
# run on their own small pool, so a flood can neither starve the default executor (DNS resolution of upstreams) nor
# exhaust memory. Excess verifications wait in the pool's queue. There is no failure rate limit (known limit).
VERIFY_WORKERS = 4
VERIFY_THREAD_PREFIX = "harp-auth-verify"
_VERIFY_EXECUTOR = ThreadPoolExecutor(max_workers=VERIFY_WORKERS, thread_name_prefix=VERIFY_THREAD_PREFIX)


def _check_algorithm(value):
    if value == "plain":
        return "plaintext"
    if isinstance(value, str) and value not in ALGORITHMS:
        raise ValueError(
            f"Unsupported password algorithm «{value}». Accepted: {', '.join(ALGORITHMS)}. Other passlib "
            "algorithms (bcrypt, md5_crypt, ...) are no longer supported: hash the passwords again with pbkdf2_sha256 "
            "or argon2."
        )
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
        BeforeValidator(_check_algorithm),
        Field(
            "pbkdf2_sha256",
            description="Hashing algorithm used for passwords. «plaintext» is for tests only.",
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

    @model_validator(mode="after")
    def _check_algorithm_is_usable(self):
        if self.algorithm == "plaintext":
            logger.warning(
                "Dashboard passwords are stored in plaintext (dashboard.auth.algorithm=plaintext). "
                "Use it for tests only, hash them with pbkdf2_sha256 or argon2."
            )
        elif self.algorithm == "argon2":
            try:
                import argon2  # noqa: F401
            except ImportError as exc:
                raise ValueError("The argon2 algorithm needs its extra: install harp-proxy[argon2].") from exc
        self._warn_on_mixed_costs()
        return self

    def _warn_on_mixed_costs(self):
        costs = {hash_cost(self.algorithm, user.password.get_secret_value()) for user in self.users.values()}
        if len(costs - {None}) > 1:
            logger.warning(
                "Dashboard passwords are hashed with different costs. Every check costs as much as the costliest, "
                "the cheaper hashes only keep their strength: rehash them (dashboard.auth.users)."
            )

    @cached_property
    def _dummy_hash(self):
        """A hash as costly as the configured users', verified against when the user is unknown."""
        return dummy_hash(self.algorithm, [user.password.get_secret_value() for user in self.users.values()])

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
            matches = verify_password(self.algorithm, password, stored)
        except ValueError:
            logger.error(
                f"Dashboard user «{username}» has a stored password that is not a valid {self.algorithm} hash, "
                "authentication refused. Check dashboard.auth.users."
            )
            # Not faster than an unknown user.
            verify_password(self.algorithm, password, self._dummy_hash)
            return False

        # Hashes made before an upgrade may be cheaper than new ones: every check costs the costliest.
        pad_verification(self.algorithm, password, stored, self._dummy_hash)

        if not user or not matches:
            return False

        return username

    async def acheck(self, username, password):
        """Same as :meth:`check`, without blocking the event loop. Successful checks are remembered for a while."""
        key = self._cache_key(username, password)
        now = monotonic()

        if self._verified.get(key, 0) > now:
            return username

        result = await asyncio.get_running_loop().run_in_executor(_VERIFY_EXECUTOR, self.check, username, password)
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
