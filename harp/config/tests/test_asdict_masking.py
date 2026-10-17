"""``asdict(secure=True)`` hides credentials, whatever shape they arrive in.

Masking used to be keyed on the type of the value, against ``Url``, ``RedisDsn`` and
``MultiHostUrl``. Those types only survive as far as the nearest ``model_dump``: in ``"json"``
mode, which is this function's default, pydantic renders a DSN to a plain string on the way out,
so the lookup saw a ``str`` and did nothing. ``secure=True`` was therefore a no-op in the mode
most callers use, which is a worse failure than having no masking at all, because it reads as
working.
"""

import pytest
from pydantic import HttpUrl, PostgresDsn, TypeAdapter

from harp.config.asdict import asdict, mask_credentials
from harp_apps.proxy.settings.remote.endpoint import RemoteEndpointSettings
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


@pytest.mark.parametrize(
    "url",
    [
        "redis://:s3cret@cache.internal:6379/0",
        "redis://u:s3cret@cache.internal:6379/0",
    ],
)
def test_the_password_is_masked_whatever_the_username(url):
    masked = asdict({"url": url})["url"]

    assert "s3cret" not in masked
    assert masked.endswith("@cache.internal:6379/0")


def test_urls_without_a_password_are_left_alone():
    values = {"none": "redis://cache.internal:6379/0", "user_only": "redis://user@cache.internal:6379/0"}

    assert asdict(values) == values


def test_an_empty_username_is_masked_in_a_settings_model():
    assert (
        asdict(RedisSettings(url="redis://:s3cret@cache.internal:6379/0"))["url"]
        == "redis://:***@cache.internal:6379/0"
    )


@pytest.mark.parametrize("mode", ["json", "python"])
def test_a_password_key_is_masked_whatever_its_value(mode):
    users = {"users": {"alice": {"password": "s3cretAlice"}}}

    assert asdict(users, mode=mode) == {"users": {"alice": {"password": "***"}}}


def test_unsecure_shows_a_password_key():
    values = {"users": {"alice": {"password": "s3cretAlice"}}}

    assert asdict(values, secure=False) == values


@pytest.mark.parametrize("mode", ["json", "python"])
@pytest.mark.parametrize("userinfo", ["user:secret", ":secret"], ids=["with-username", "empty-username"])
def test_an_http_url_field_is_masked_in_either_mode(mode, userinfo):
    """``HttpUrl`` is neither ``Url`` nor a string once ``model_dump(mode="python")`` has run."""
    settings = RemoteEndpointSettings(url=f"http://{userinfo}@127.0.0.1:1/")

    masked = asdict(settings, secure=True, mode=mode, verbose=True)["url"]

    assert "secret" not in str(masked)
    assert str(masked) == f"http://{userinfo.split(':')[0]}:***@127.0.0.1:1/"


@pytest.mark.parametrize("mode", ["json", "python"])
def test_unsecure_shows_an_http_url_field(mode):
    settings = RemoteEndpointSettings(url="http://user:secret@127.0.0.1:1/")

    assert str(asdict(settings, secure=False, mode=mode, verbose=True)["url"]) == "http://user:secret@127.0.0.1:1/"


@pytest.mark.parametrize("mode", ["json", "python"])
def test_a_bare_url_object_is_masked(mode):
    url = TypeAdapter(HttpUrl).validate_python("http://user:secret@127.0.0.1:1/")
    hosts = TypeAdapter(PostgresDsn).validate_python("postgresql://u:secret@h1,h2/db")

    assert asdict(url, mode=mode) == "http://user:***@127.0.0.1:1/"
    assert asdict(hosts, mode=mode) == "postgresql://u:***@h1,h2/db"
    assert asdict(url, secure=False, mode=mode) == "http://user:secret@127.0.0.1:1/"


def test_two_urls_in_one_string_are_masked_separately():
    text = "HttpUrl('http://a:one@x/'), HttpUrl('http://b:two@y/')"

    assert mask_credentials(text) == "HttpUrl('http://a:***@x/'), HttpUrl('http://b:***@y/')"
