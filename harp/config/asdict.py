import copy
import dataclasses
import re
from functools import partial
from typing import Literal

from pydantic import RedisDsn
from pydantic.networks import _BaseMultiHostUrl, _BaseUrl
from pydantic.types import _SecretBase
from pydantic_core import MultiHostUrl, Url

from .secrets import MASK, REVEAL_SECRETS

# The authority of a URL, from `scheme://` up to the first `/`, `?` or `#`. A multi-host DSN holds one `userinfo@host`
# per comma-separated entry, and each one has its own credentials.
_authority_re = re.compile(r"(?P<scheme>[A-Za-z][A-Za-z0-9+.-]*)(?P<sep>://)(?P<authority>[^/?#\s]*)")

# Over HTTP, a username without a password is still a credential: it is sent as the Basic auth username, which is where
# API tokens go. Other schemes (a database user) keep it.
_TOKEN_USERNAME_SCHEMES = frozenset({"http", "https"})

# Query parameters that carry a secret by convention (asyncpg reads the password of a DSN from `?password=`).
_SECRET_QUERY_PARAMETERS = "password|passwd|pwd|sslpassword|sslkey|key|api[_-]?key|token|access[_-]?token|auth|secret|client[_-]?secret|signature|sig"  # pragma: allowlist secret
mask_query_password_re = re.compile(rf"([?&](?:{_SECRET_QUERY_PARAMETERS})=)[^&#\s'\"]*", re.IGNORECASE)

# Dictionary keys whose string value is a secret by name, whatever the algorithm that protects it: credential headers,
# and any name that says it holds a token, a secret, a password or a key.
secret_key_re = re.compile(
    r"^(authorization|proxy-authorization|cookie|cookie2|set-cookie|cookies)$|(^|[-_])auth$"
    r"|token|secret|password|passwd|pwd|signature|api[-_]?key|private[-_]?key|[-_]key$",
    re.IGNORECASE,
)


def _mask_userinfo(host: str, scheme: str) -> str:
    userinfo, at, rest = host.rpartition("@")
    if not at:
        return host
    username, colon, _ = userinfo.partition(":")
    if colon:
        return f"{username}:{MASK}@{rest}"
    if username and scheme.lower() in _TOKEN_USERNAME_SCHEMES:
        return f"{MASK}@{rest}"
    return host


def _mask_authority(match: re.Match) -> str:
    scheme = match["scheme"]
    hosts = ",".join(_mask_userinfo(host, scheme) for host in match["authority"].split(","))
    return f"{scheme}{match['sep']}{hosts}"


def mask_credentials(value: str) -> str:
    """Hide the credentials of any URL found in ``value``: the password of every ``scheme://user:password@host``, the
    token used as the username of an HTTP URL, and the query parameters that carry a secret."""
    value = _authority_re.sub(_mask_authority, value)
    return mask_query_password_re.sub(rf"\1{MASK}", value)


def url_serializer(dsn, secure=True, **kwargs):
    if secure:
        return mask_credentials(str(dsn))
    return str(dsn)


# Pydantic wraps its URL types (``HttpUrl``, ``PostgresDsn``...) in classes that do not inherit from the
# ``pydantic_core`` ones, so masking is keyed on the bases of every one of them, not on an exact type.
URL_TYPES = (Url, MultiHostUrl, _BaseUrl, _BaseMultiHostUrl, RedisDsn)


def is_secret_key(key):
    return isinstance(key, str) and secret_key_re.search(key) is not None


def mask_secret_value(key, value, secure):
    if not secure:
        return value
    if isinstance(value, str) and is_secret_key(key):
        return MASK
    # Cookie names are arbitrary, so every string held under `cookies` is a credential.
    if isinstance(key, str) and key.lower() == "cookies" and isinstance(value, dict):
        return {k: MASK if isinstance(v, str) else v for k, v in value.items()}
    return value


def _mask_header_pair(items, secure):
    """A ``[name, value]`` pair is a header whose name says whether its value is a credential. Two header names in a row
    are a list of names (``redact: [authorization, x-api-key]``), not a pair."""
    if (
        secure
        and len(items) == 2
        and is_secret_key(items[0])
        and isinstance(items[1], str)
        and not is_secret_key(items[1])
    ):
        return type(items)((items[0], MASK))
    return items


def asdict(
    obj,
    /,
    *,
    secure=True,
    verbose=False,
    mode: Literal["json", "python"] | str = "json",
):
    """Dump ``obj`` to plain data. With ``secure``, secrets are masked: first by type (``Secret`` settings and URL
    types), then by shape as a fallback (credentials found in any string, values of ``password`` keys)."""
    if isinstance(obj, URL_TYPES):
        return url_serializer(obj, secure=secure, verbose=verbose)

    if isinstance(obj, _SecretBase):
        return MASK if secure else obj.get_secret_value()

    # namedtuples have an ``_asdict`` too, without ``secure``: they are dumped field by field below
    if hasattr(obj, "_asdict") and not isinstance(obj, tuple):
        return obj._asdict(secure=secure)

    _asdict = partial(asdict, secure=secure, verbose=verbose, mode=mode)

    if hasattr(obj, "model_dump"):
        return _asdict(
            obj.model_dump(
                mode=mode,
                exclude_unset=not verbose,
                exclude_defaults=not verbose,
                context={REVEAL_SECRETS: not secure},
            )
        )

    # A DSN only keeps its own type as far as the nearest `model_dump`: in "json" mode pydantic
    # renders it to a plain string on the way out, and the serializers above never see it. Masking
    # the string itself is what makes `secure` mean the same thing in either mode, and it also
    # reaches credentials embedded in settings that were never typed as URLs in the first place.
    if secure and isinstance(obj, str):
        return mask_credentials(obj)

    if type(obj) in dataclasses._ATOMIC_TYPES:
        return obj

    if dataclasses._is_dataclass_instance(obj):
        # fast path for the common case
        return {f.name: _asdict(getattr(obj, f.name)) for f in dataclasses.fields(obj)}

    if isinstance(obj, tuple) and hasattr(obj, "_fields"):
        return type(obj)(*[_asdict(v) for v in obj])

    if isinstance(obj, (list, tuple)):
        return _mask_header_pair(type(obj)(_asdict(v) for v in obj), secure)

    if isinstance(obj, dict):
        if hasattr(type(obj), "default_factory"):
            # obj is a defaultdict, which has a different constructor from
            # dict as it requires the default_factory as its first arg.
            result = type(obj)(getattr(obj, "default_factory"))
            for k, v in obj.items():
                result[_asdict(k)] = mask_secret_value(k, _asdict(v), secure)
            return result
        return type(obj)((_asdict(k), mask_secret_value(k, _asdict(v), secure)) for k, v in obj.items())

    return copy.deepcopy(obj)
