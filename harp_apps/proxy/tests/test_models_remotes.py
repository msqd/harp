from time import sleep

import pytest
import respx
from httpx import Response

from harp.config import asdict
from harp_apps.proxy.models.remotes import HttpEndpoint, HttpProbe, HttpRemote


def test_remote_round_robin():
    remote = HttpRemote([{"url": "http://api0.example.com/"}, {"url": "http://api1.example.com/"}])

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
        [
            {"url": "http://api0.example.com/"},
            {"url": "http://api1.example.com/"},
            {"url": "http://fallback.example.com/", "pools": ["fallback"]},
        ],
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
    remote = HttpRemote()
    with pytest.raises(IndexError):
        remote.get_url()


def test_empty_pool_after_set_down():
    remote = HttpRemote([{"url": "http://example.com"}])
    assert remote.get_url() == "http://example.com/"
    remote.set_down("http://example.com")
    with pytest.raises(IndexError):
        remote.get_url()
    remote.set_up("http://example.com")
    assert remote.get_url() == "http://example.com/"


@respx.mock
async def test_basic_probe():
    remote = HttpRemote(
        [
            HttpEndpoint(url="https://example.com/", failure_threshold=3),
        ],
        probe=HttpProbe("GET", "/health"),
    )
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
    remote = HttpRemote(
        [
            HttpEndpoint("https://example.com", failure_threshold=3),
        ],
        probe=HttpProbe("GET", "/health"),
    )
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
    remote = HttpRemote(
        [
            HttpEndpoint("https://example.com", failure_threshold=3),
        ],
        probe=HttpProbe("GET", "/health", timeout=0.1),
    )
    healthcheck = respx.get("https://example.com/health")
    url = remote["https://example.com"]

    healthcheck.mock(side_effect=lambda x: sleep(0.2))

    await remote.check()
    assert url.status == 0
    assert url.failure_reasons == {"CONNECT_TIMEOUT"}


def test_endpoint_asdict():
    endpoint = HttpEndpoint("http://example.com")
    assert asdict(endpoint) == {
        "url": "http://example.com/",
    }

    # idempotence
    endpoint = HttpEndpoint(**asdict(endpoint))
    assert asdict(endpoint) == {
        "url": "http://example.com/",
    }


def test_endpoint_asdict_with_nondefault_thresholds():
    endpoint = HttpEndpoint("http://example.com", success_threshold=2, failure_threshold=4)
    assert asdict(endpoint) == {
        "url": "http://example.com/",
        "success_threshold": 2,
        "failure_threshold": 4,
    }

    # idempotence
    endpoint = HttpEndpoint(**asdict(endpoint))
    assert asdict(endpoint) == {
        "url": "http://example.com/",
        "success_threshold": 2,
        "failure_threshold": 4,
    }


def test_remote_asdict():
    remote = HttpRemote([{"url": "http://example.com"}])
    assert asdict(remote) == {
        "endpoints": [
            {
                "url": "http://example.com/",
                "pools": ["default"],
            },
        ],
    }


def test_remote_asdict_with_nondefault_poolsize_and_thresholds():
    remote = HttpRemote([{"url": "http://example.com"}], min_pool_size=2)
    remote["http://example.com"].success_threshold = 2
    remote["http://example.com"].failure_threshold = 4
    assert asdict(remote) == {
        "endpoints": [
            {
                "url": "http://example.com/",
                "pools": ["default"],
                "success_threshold": 2,
                "failure_threshold": 4,
            },
        ],
        "min_pool_size": 2,
    }

    assert asdict(HttpRemote(**asdict(remote))) == asdict(remote)
