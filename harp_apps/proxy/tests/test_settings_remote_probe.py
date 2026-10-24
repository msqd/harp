import logging
from base64 import b64encode

import httpx

from harp.utils.testing.config import BaseConfigurableTest
from harp_apps.proxy.settings.remote.endpoint import RemoteEndpoint, RemoteEndpointSettings
from harp_apps.proxy.settings.remote.probe import RemoteProbe, RemoteProbeSettings


class TestRemoteProbeSettings(BaseConfigurableTest):
    type = RemoteProbeSettings
    initial = {}
    expected = {}
    expected_verbose = {
        "headers": {},
        "interval": 10.0,
        "method": "GET",
        "path": "/",
        "timeout": 10.0,
        "verify": True,
    }


class TestRemoteProbeStateful(BaseConfigurableTest):
    type = RemoteProbe
    initial = {"settings": TestRemoteProbeSettings.initial}
    expected = {"settings": TestRemoteProbeSettings.expected_verbose}
    expected_verbose = {"settings": TestRemoteProbeSettings.expected_verbose}


class TestRemoteProbeCredentials:
    PASSWORD = "P00lPw"
    BASIC = "Basic " + b64encode(f"puser:{PASSWORD}".encode()).decode()

    def _endpoint(self):
        return RemoteEndpoint(
            settings=RemoteEndpointSettings(
                url=f"http://puser:{self.PASSWORD}@probe.test:8080/", liveness={"type": "ignore"}
            )
        )

    def _client(self, handler):
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def test_authenticates_with_basic_header_and_clean_url(self, caplog):
        seen = []

        def handler(request):
            seen.append(request)
            ok = request.headers.get("authorization") == self.BASIC
            return httpx.Response(200 if ok else 401)

        caplog.set_level(logging.DEBUG)
        async with self._client(handler) as client:
            await RemoteProbe(settings=RemoteProbeSettings()).check(client, self._endpoint())

        assert seen[0].headers["authorization"] == self.BASIC
        assert seen[0].url.userinfo == b""
        assert self.PASSWORD not in caplog.text

    async def test_probe_own_authorization_wins(self):
        seen = []

        def handler(request):
            seen.append(request.headers["authorization"])
            return httpx.Response(200)

        probe = RemoteProbe(settings=RemoteProbeSettings(headers={"Authorization": "Bearer abc"}))
        async with self._client(handler) as client:
            await probe.check(client, self._endpoint())

        assert seen == ["Bearer abc"]

    async def test_failing_probe_logs_no_password(self, caplog):
        def handler(request):
            raise httpx.ConnectError("refused")

        caplog.set_level(logging.DEBUG)
        async with self._client(handler) as client:
            await RemoteProbe(settings=RemoteProbeSettings()).check(client, self._endpoint())

        assert "PROBE_CONNECT_ERROR" in caplog.text
        assert self.PASSWORD not in caplog.text

    async def test_http_failure_logs_no_password(self, caplog):
        caplog.set_level(logging.DEBUG)
        async with self._client(lambda request: httpx.Response(500)) as client:
            await RemoteProbe(settings=RemoteProbeSettings()).check(client, self._endpoint())

        assert "PROBE_HTTP_500" in caplog.text
        assert self.PASSWORD not in caplog.text
