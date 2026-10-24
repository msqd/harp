import copy
import dataclasses
import re
from functools import partial
from typing import Literal

from pydantic import RedisDsn
from pydantic.networks import _BaseMultiHostUrl, _BaseUrl
from pydantic_core import MultiHostUrl, Url

MASK = "***"

# Only the userinfo of the authority is touched (up to the first `/`, `?` or `#`). The username may be empty:
# `redis://:password@host` is the usual Redis form.
mask_password_re = re.compile(r"(://[^:/?#@\s]*:)([^/?#\s]+)(@)")

# asyncpg also reads the password from a `?password=` query parameter.
mask_query_password_re = re.compile(r"([?&]password=)[^&#\s'\"]*", re.IGNORECASE)

# Dictionary keys whose string value is a secret by name, whatever the algorithm that protects it.
SECRET_KEYS = frozenset({"password"})


def mask_credentials(value: str) -> str:
    """Replace the password of any ``scheme://user:password@host`` or ``?password=`` found in ``value``."""
    value = mask_password_re.sub(rf"\1{MASK}\3", value)
    return mask_query_password_re.sub(rf"\1{MASK}", value)


def url_serializer(dsn, secure=True, **kwargs):
    if secure:
        return mask_credentials(str(dsn))
    return str(dsn)


# Pydantic wraps its URL types (``HttpUrl``, ``PostgresDsn``...) in classes that do not inherit from the
# ``pydantic_core`` ones, so masking is keyed on the bases of every one of them, not on an exact type.
URL_TYPES = (Url, MultiHostUrl, _BaseUrl, _BaseMultiHostUrl, RedisDsn)


def _mask_secret_value(key, value, secure):
    if secure and key in SECRET_KEYS and isinstance(value, str):
        return MASK
    return value


def asdict(
    obj,
    /,
    *,
    secure=True,
    verbose=False,
    mode: Literal["json", "python"] | str = "json",
):
    if isinstance(obj, URL_TYPES):
        return url_serializer(obj, secure=secure, verbose=verbose)

    if hasattr(obj, "_asdict"):
        return obj._asdict(secure=secure)

    _asdict = partial(asdict, secure=secure, verbose=verbose, mode=mode)

    if hasattr(obj, "model_dump"):
        return _asdict(obj.model_dump(mode=mode, exclude_unset=not verbose, exclude_defaults=not verbose))

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
        return type(obj)(_asdict(v) for v in obj)

    if isinstance(obj, dict):
        if hasattr(type(obj), "default_factory"):
            # obj is a defaultdict, which has a different constructor from
            # dict as it requires the default_factory as its first arg.
            result = type(obj)(getattr(obj, "default_factory"))
            for k, v in obj.items():
                result[_asdict(k)] = asdict(v, secure=secure)
            return result
        return type(obj)((_asdict(k), _mask_secret_value(k, _asdict(v), secure)) for k, v in obj.items())

    return copy.deepcopy(obj)
