"""``asdict(secure=True)`` hides credentials, whatever shape they arrive in.

Masking used to be keyed on the type of the value, against ``Url``, ``RedisDsn`` and
``MultiHostUrl``. Those types only survive as far as the nearest ``model_dump``: in ``"json"``
mode, which is this function's default, pydantic renders a DSN to a plain string on the way out,
so the lookup saw a ``str`` and did nothing. ``secure=True`` was therefore a no-op in the mode
most callers use, which is a worse failure than having no masking at all, because it reads as
working.
"""

import pytest

from harp.config.asdict import asdict
from harp_apps.proxy.settings import Endpoint
from harp_apps.storage.settings.redis import RedisSettings

PASSWORD = "hunter2"
DSN = f"redis://svc:{PASSWORD}@cache.internal:6379/0"


@pytest.mark.parametrize("mode", ["json", "python"])
def test_a_dsn_held_by_a_settings_model_is_masked_in_either_mode(mode):
    """The DSN goes through ``model_dump``, which is where its type used to be lost."""
    assert asdict(RedisSettings(url=DSN), mode=mode)["url"] == "redis://svc:***@cache.internal:6379/0"


@pytest.mark.parametrize("mode", ["json", "python"])
def test_unsecure_shows_the_credentials(mode):
    assert asdict(RedisSettings(url=DSN), secure=False, mode=mode)["url"] == DSN


def test_credentials_are_masked_in_a_plain_string_setting():
    """A webhook or callback URL is an ordinary string, and carries credentials just as well."""
    result = asdict({"webhook": f"https://bot:{PASSWORD}@hooks.internal/notify"})

    assert result == {"webhook": "https://bot:***@hooks.internal/notify"}


def test_strings_without_credentials_are_left_alone():
    values = {
        "plain": "just a string",
        "url": "https://upstream.internal/path",
        "port_like": "host:5432",
        "sentence": "user: alice, password: secret",
    }

    assert asdict(values) == values


def test_proxy_endpoints_do_not_expose_upstream_credentials():
    """The shape ``GET /api/system/proxy`` returns, on a dashboard that is unauthenticated by default."""
    endpoint = Endpoint.from_kwargs(settings={"name": "api", "port": 80, "url": f"http://svc:{PASSWORD}@upstream/"})

    assert PASSWORD not in repr(asdict([endpoint], verbose=True))
