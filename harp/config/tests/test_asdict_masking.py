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
from harp_apps.storage.settings import StorageSettings
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


QUERY_DSN = "postgresql+asyncpg://harp@db.internal:5432/harp?password=Top%40Secret&ssl=disable"


@pytest.mark.parametrize("mode", ["json", "python"])
def test_a_query_password_is_masked_in_either_mode(mode):
    """asyncpg reads a ``?password=`` query parameter: the settings and storage APIs must not show it."""
    masked = asdict(StorageSettings(url=QUERY_DSN), secure=True, mode=mode)["url"]

    assert str(masked) == "postgresql+asyncpg://harp@db.internal:5432/harp?password=***&ssl=disable"


def test_unsecure_shows_a_query_password():
    assert asdict({"url": QUERY_DSN}, secure=False) == {"url": QUERY_DSN}


@pytest.mark.parametrize(
    "url, masked",
    [
        ("http://h/p?password=s3cret", "http://h/p?password=***"),
        ("http://h/p?a=1&password=s3cret#top", "http://h/p?a=1&password=***#top"),
        ("http://u:one@h/p?password=two", "http://u:***@h/p?password=***"),
        ("http://h/p?old_password=s3cret", "http://h/p?old_password=s3cret"),
        ("http://h/p?Password=s3cret&PASSWORD=s3cret", "http://h/p?Password=***&PASSWORD=***"),
    ],
)
def test_mask_credentials_masks_the_query_password(url, masked):
    assert mask_credentials(f"see {url} now") == f"see {masked} now"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("http://h:8080/p?email=a@b.com", "http://h:8080/p?email=a@b.com"),
        ("http://h:8080?email=a@b.com", "http://h:8080?email=a@b.com"),
        ("http://h:8080/p#a@b.com", "http://h:8080/p#a@b.com"),
        ("http://h:8080/a@b/c", "http://h:8080/a@b/c"),
        ("http://u:secret@h:8080/p?email=a@b.com", "http://u:***@h:8080/p?email=a@b.com"),
        ("http://:secret@h/", "http://:***@h/"),
    ],
)
def test_url_masking_only_touches_the_userinfo_password(value, expected):
    assert mask_credentials(value) == expected


def test_mask_credentials_leaves_a_host_port_followed_by_free_text_intact():
    message = "could not connect to http://db:5432 as user@host"

    assert mask_credentials(message) == message


def test_a_namedtuple_is_dumped_field_by_field():
    from collections import namedtuple

    Pair = namedtuple("Pair", ["name", "dsn"])

    assert asdict(Pair("db", "postgresql://user:secret@host/db")) == Pair(
        "db", mask_credentials("postgresql://user:secret@host/db")
    )


@pytest.mark.parametrize("mode", ["json", "python"])
@pytest.mark.parametrize(
    "key",
    [
        "Authorization",
        "COOKIE",
        "Proxy-Authorization",
        "X-Auth-Token",
        "client_secret",
        "DB_PASSWORD",
        "X-Api-Key",
        "api_key",
    ],
)
def test_credential_like_keys_are_masked_at_any_depth(mode, key):
    arguments = {"headers": {key: "VALUE", "x-purpose": "health"}, "deep": [{"a": {key: "VALUE"}}]}

    assert asdict({"arguments": arguments}, mode=mode) == {
        "arguments": {"headers": {key: "***", "x-purpose": "health"}, "deep": [{"a": {key: "***"}}]}
    }


def test_unsecure_shows_credential_like_keys():
    values = {"headers": {"Authorization": "Bearer X"}}

    assert asdict(values, secure=False) == values


def test_service_arguments_are_masked():
    from harp_apps.http_client.settings import HttpClientSettings

    settings = HttpClientSettings(arguments={"headers": {"Authorization": "Bearer X"}})

    assert "Bearer X" not in repr(asdict(settings))


@pytest.mark.parametrize("mode", ["json", "python"])
@pytest.mark.parametrize(
    "key",
    [
        "apikey",
        "x-apikey",
        "passwd",
        "pwd",
        "auth",
        "X-Auth",
        "privatekey",
        "private_key",
        "x-amz-signature",
        "Set-Cookie",
        "cookie2",
    ],
)
def test_keys_masked_by_the_query_rule_are_masked_too(mode, key):
    assert asdict({"headers": {key: "VALUE"}}, mode=mode) == {"headers": {key: "***"}}


@pytest.mark.parametrize("mode", ["json", "python"])
def test_every_string_under_cookies_is_masked(mode):
    values = {"Cookies": {"sid": "VALUE", "theme": "dark", "retries": 3}}

    assert asdict(values, mode=mode) == {"Cookies": {"sid": "***", "theme": "***", "retries": 3}}


@pytest.mark.parametrize("mode", ["json", "python"])
@pytest.mark.parametrize("pair", [["Authorization", "Bearer X"], ("x-api-key", "KEY")])
def test_a_header_pair_in_a_list_is_masked(mode, pair):
    result = asdict({"headers": [pair, ["x-purpose", "health"]]}, mode=mode)

    assert result["headers"][0][1] == "***"
    assert result["headers"][1] == ["x-purpose", "health"]


def test_unsecure_shows_header_pairs_and_cookies():
    values = {"headers": [["Authorization", "Bearer X"]], "cookies": {"sid": "VALUE"}}

    assert asdict(values, secure=False) == values


@pytest.mark.parametrize("mode", ["json", "python"])
def test_non_secret_keys_stay_visible(mode):
    values = {
        "key_prefix": "harp",
        "author": "alice",
        "cache_key": ["method", "url"],
        "redact": ["authorization", "x-api-key"],
        "rules": {"authorization": {"allow": ["GET"]}, "token": {"ttl": 60}},
    }

    assert asdict(values, mode=mode) == values


@pytest.mark.parametrize("mode", ["json", "python"])
@pytest.mark.parametrize(
    "pair",
    [
        ["Authorization", "Bearer my-secret-token"],
        ["X-Api-Key", "sk_live_secret_abc"],
        ["X-Api-Key", "dev_key"],
        ("Cookie", "session=abc; csrftoken=x"),
    ],
)
def test_a_header_pair_whose_value_looks_like_a_credential_is_masked(mode, pair):
    assert asdict({"headers": [pair]}, mode=mode)["headers"][0][1] == "***"
