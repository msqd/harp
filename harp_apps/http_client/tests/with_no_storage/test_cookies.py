import respx
from httpx import AsyncClient, Response

from harp_apps.http_client.tests._base import BaseTestDefaultsWith

URL = "http://www.example.com/"


class TestSharedClientCookies(BaseTestDefaultsWith):
    @respx.mock
    async def test_upstream_cookies_are_not_replayed_to_other_clients(self):
        system = await self.create_system()
        http_client = system.provider.get(AsyncClient)
        route = respx.get(URL).mock(return_value=Response(200, headers={"set-cookie": "session=A; Path=/"}))

        response_a = await http_client.get(URL)
        await http_client.get(URL)  # client B, no cookie of its own

        assert response_a.headers["set-cookie"] == "session=A; Path=/"
        assert "cookie" not in route.calls[1].request.headers
        assert len(http_client.cookies.jar) == 0

    @respx.mock
    async def test_request_cookie_header_is_forwarded(self):
        system = await self.create_system()
        http_client = system.provider.get(AsyncClient)
        route = respx.get(URL).mock(return_value=Response(200))

        await http_client.get(URL, headers={"Cookie": "session=A"})

        assert route.calls[0].request.headers["cookie"] == "session=A"
