from time import sleep

import pytest
import respx
from httpx import Response

from harp_apps.proxy.models.remotes import HttpProbe, HttpRemote


def test_remote_round_robin():
    remote = HttpRemote("api", base_urls=("http://api0.example.com/", "http://api1.example.com/"))

    assert remote.name == "api"
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://api1.example.com/"
    assert remote.get_url() == "http://api0.example.com/"

    remote.set_down("http://api1.example.com/")
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://api0.example.com/"

    remote.set_up("http://api1.example.com/")
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://api1.example.com/"


def test_remote_fallback():
    remote = HttpRemote(
        "api",
        base_urls=("http://api0.example.com/", "http://api1.example.com/"),
        fallback_urls=("http://fallback.example.com",),
        min_pool_size=2,
    )

    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://api1.example.com/"
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://api1.example.com/"

    remote.set_down("http://api1.example.com/")
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://fallback.example.com/"
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://fallback.example.com/"

    remote.set_up("http://api1.example.com/")
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://api1.example.com/"
    assert remote.get_url() == "http://api0.example.com/"
    assert remote.get_url() == "http://api1.example.com/"


def test_empty_pool():
    remote = HttpRemote("test")
    with pytest.raises(IndexError):
        remote.get_url()


def test_empty_pool_after_set_down():
    remote = HttpRemote("api", base_urls=["http://example.com"])
    assert remote.get_url() == "http://example.com/"
    remote.set_down("http://example.com")
    with pytest.raises(IndexError):
        remote.get_url()
    remote.set_up("http://example.com")
    assert remote.get_url() == "http://example.com/"


@respx.mock
async def test_basic_probe():
    remote = HttpRemote("api", base_urls=["https://example.com"], probe=HttpProbe("GET", "/health"))
    healthcheck = respx.get("https://example.com/health")
    url = remote["https://example.com"]

    # initial status is "checking"
    assert url.status == 0

    # service up :)
    healthcheck.mock(return_value=Response(200))

    # first check is performed, then the status should be up, (success threshold is 1)
    await remote.check()
    assert url.status > 0

    # subsequent checks call the health endpoint, and keep the status up
    await remote.check()
    assert url.status > 0

    # service down :(
    healthcheck.mock(return_value=Response(418))

    # if the health endpoint returns a 4xx or 5xx status, we start counting failures
    await remote.check()
    assert url.status == 0
    await remote.check()
    assert url.status == 0
    await remote.check()
    assert url.status < 0

    # service up again (what a relief) :)
    healthcheck.mock(return_value=Response(200))
    await remote.check()
    assert url.status > 0


@respx.mock
async def test_probe_errors():
    remote = HttpRemote("api", base_urls=["https://example.com"], probe=HttpProbe("GET", "/health"))
    healthcheck = respx.get("https://example.com/health")
    url = remote["https://example.com"]

    # initial status is "checking"
    assert url.status == 0

    # service in error ...
    healthcheck.mock(side_effect=TimeoutError)

    await remote.check()
    await remote.check()
    assert url.status == 0
    assert url.failure_reasons == {"TIMEOUT_ERROR"}

    await remote.check()
    assert url.status < 0
    assert url.failure_reasons == {"TIMEOUT_ERROR"}

    healthcheck.mock(return_value=Response(200))
    await remote.check()
    assert url.status > 0
    assert url.failure_reasons is None

    healthcheck.mock(return_value=Response(418))
    await remote.check()
    await remote.check()
    assert url.status == 0
    assert url.failure_reasons == {"HTTP_418"}

    await remote.check()
    assert url.status < 0
    assert url.failure_reasons == {"HTTP_418"}

    healthcheck.mock(return_value=Response(200))
    await remote.check()
    assert url.status > 0
    assert url.failure_reasons is None


async def test_probe_timeout():
    remote = HttpRemote("api", base_urls=["https://example.com"], probe=HttpProbe("GET", "/health", timeout=0.1))
    healthcheck = respx.get("https://example.com/health")
    url = remote["https://example.com"]

    healthcheck.mock(side_effect=lambda x: sleep(0.2))

    await remote.check()
    assert url.status == 0
    assert url.failure_reasons == {"CONNECT_TIMEOUT"}
