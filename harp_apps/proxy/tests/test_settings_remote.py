from time import sleep

import httpx
import pytest
import respx

from harp.config import asdict
from harp_apps.proxy.settings.remote import Remote, RemoteSettings
from harp_apps.proxy.tests._base import BaseModelTest


class TestRemoteSettings(BaseModelTest):
    type = RemoteSettings
    expected_verbose = {
        "break_on": ["network_error", "unhandled_exception"],
        "check_after": 10.0,
        "endpoints": None,
        "min_pool_size": 1,
        "probe": None,
    }

    def test_validate_break_on(self):
        obj = self.create(break_on={"http_5xx", "network_error"})
        assert asdict(obj) == {"break_on": ["http_5xx", "network_error"]}

    def test_validate_break_on_invalid(self):
        with pytest.raises(ValueError):
            self.create(break_on={"invalid_value"})

    def test_getitem(self):
        obj = self.create(endpoints=[{"url": "http://example.com"}])
        assert obj["http://example.com"] == obj.endpoints[0]
        assert obj["http://example.com/"] == obj.endpoints[0]
        with pytest.raises(KeyError):
            _ = obj["http://invalid.com"]

    def test_asdict(self):
        remote = self.create(endpoints=[{"url": "http://example.com"}])
        assert asdict(remote) == {"endpoints": [{"url": "http://example.com/"}]}

    def test_asdict_with_nondefault_poolsize_and_thresholds(self):
        remote = self.create(endpoints=[{"url": "http://example.com"}], min_pool_size=2)
        remote["http://example.com"].success_threshold = 2
        remote["http://example.com"].failure_threshold = 4
        assert asdict(remote) == {
            "endpoints": [
                {
                    "url": "http://example.com/",
                    "success_threshold": 2,
                    "failure_threshold": 4,
                },
            ],
            "min_pool_size": 2,
        }

        assert asdict(RemoteSettings(**asdict(remote))) == asdict(remote)


class TestRemoteStateful(BaseModelTest):
    type = Remote
    initial = {"settings": TestRemoteSettings.initial}
    expected = {
        "current_pool": [],
        "endpoints": [],
        "settings": {"break_on": ["network_error", "unhandled_exception"], "check_after": 10.0, "min_pool_size": 1},
    }

    expected_verbose = {
        "current_pool": [],
        "current_pool_name": "default",
        "endpoints": [],
        "probe": None,
        "settings": {"break_on": ["network_error", "unhandled_exception"], "check_after": 10.0, "min_pool_size": 1},
    }

    def test_remote_round_robin(self):
        remote = self.create(
            settings={
                "endpoints": [
                    {"url": "http://api0.example.com/"},
                    {"url": "http://api1.example.com/"},
                ]
            }
        )

        assert remote.get_url() == "http://api0.example.com/"
        assert remote.get_url() == "http://api1.example.com/"
        assert remote.get_url() == "http://api0.example.com/"

        remote.set_down("http://api1.example.com/")
        assert remote.get_url() == "http://api0.example.com/"
        assert remote.get_url() == "http://api0.example.com/"

        remote.set_up("http://api1.example.com/")
        assert remote.get_url() == "http://api0.example.com/"
        assert remote.get_url() == "http://api1.example.com/"

    def test_remote_fallback(self):
        remote = self.create(
            settings={
                "endpoints": [
                    {"url": "http://api0.example.com/"},
                    {"url": "http://api1.example.com/"},
                    {"url": "http://fallback.example.com/", "pools": ["fallback"]},
                ],
                "min_pool_size": 2,
            }
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

    def test_empty_pool(self):
        remote = self.create(settings={})
        with pytest.raises(IndexError):
            remote.get_url()

    def test_empty_pool_after_set_down(self):
        remote = self.create(settings={"endpoints": [{"url": "http://example.com"}]})
        assert remote.get_url() == "http://example.com/"
        remote.set_down("http://example.com")
        with pytest.raises(IndexError):
            remote.get_url()
        remote.set_up("http://example.com")
        assert remote.get_url() == "http://example.com/"

    @respx.mock
    async def test_basic_probe(self):
        remote = self.create(
            settings={
                "endpoints": [{"url": "https://example.com", "failure_threshold": 3}],
                "probe": {"method": "GET", "path": "/health"},
            }
        )
        healthcheck = respx.get("https://example.com/health")
        url = remote["https://example.com"]

        # initial status is "checking"
        assert url.status == 0

        # service up :)
        healthcheck.mock(return_value=httpx.Response(200))

        # first check is performed, then the status should be up, (success threshold is 1)
        await remote.check()
        assert url.status > 0

        # subsequent checks call the health endpoint, and keep the status up
        await remote.check()
        assert url.status > 0

        # service down :(
        healthcheck.mock(return_value=httpx.Response(418))

        # if the health endpoint returns a 4xx or 5xx status, we start counting failures
        await remote.check()
        assert url.status == 0
        await remote.check()
        assert url.status == 0
        await remote.check()
        assert url.status < 0

        # service up again (what a relief) :)
        healthcheck.mock(return_value=httpx.Response(200))
        await remote.check()
        assert url.status > 0

    @respx.mock
    async def test_probe_errors(self):
        remote = self.create(
            settings={
                "endpoints": [{"url": "https://example.com", "failure_threshold": 3}],
                "probe": {"method": "GET", "path": "/health"},
            }
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

        healthcheck.mock(return_value=httpx.Response(200))
        await remote.check()
        assert url.status > 0
        assert url.failure_reasons is None

        healthcheck.mock(return_value=httpx.Response(418))
        await remote.check()
        await remote.check()
        assert url.status == 0
        assert url.failure_reasons == {"HTTP_418"}

        await remote.check()
        assert url.status < 0
        assert url.failure_reasons == {"HTTP_418"}

        healthcheck.mock(return_value=httpx.Response(200))
        await remote.check()
        assert url.status > 0
        assert url.failure_reasons is None

    async def test_probe_timeout(self):
        remote = self.create(
            settings={
                "endpoints": [{"url": "https://example.com", "failure_threshold": 3}],
                "probe": {"method": "GET", "path": "/health", "timeout": 0.1},
            }
        )
        healthcheck = respx.get("https://example.com/health")
        url = remote["https://example.com"]

        healthcheck.mock(side_effect=lambda x: sleep(0.2))

        await remote.check()
        assert url.status == 0
        assert url.failure_reasons == {"CONNECT_TIMEOUT"}