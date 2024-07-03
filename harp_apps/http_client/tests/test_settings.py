from typing import Optional

import hishel
import httpx
from whistle import AsyncEventDispatcher, IAsyncEventDispatcher

from harp.config import DisabledSettings
from harp_apps.http_client.client import AsyncHttpClient
from harp_apps.http_client.settings import CacheSettings, HttpClientSettings


class TestHttpClientSettings:
    def create_http_client(
        self, settings: HttpClientSettings, /, *, dispatcher: Optional[IAsyncEventDispatcher] = None
    ):
        return AsyncHttpClient(settings, dispatcher=dispatcher or AsyncEventDispatcher())

    def test_without_cache(self):
        settings = HttpClientSettings(cache={"enabled": False})

        assert settings.cache.enabled is False
        assert isinstance(settings.cache, DisabledSettings)

        client = self.create_http_client(settings)
        assert isinstance(client._transport._transport, httpx.AsyncHTTPTransport)

    def test_without_cache_with_custom_client(self):
        settings = HttpClientSettings(
            transport={"@type": "httpx._client:BaseClient"},
            cache={"enabled": False},
        )

        assert settings.cache.enabled is False
        assert isinstance(settings.cache, DisabledSettings)

        client = self.create_http_client(settings)
        assert isinstance(client._transport._transport, httpx._client.BaseClient)

    def test_with_default_cache(self):
        settings = HttpClientSettings()

        assert settings.cache.enabled is True
        assert isinstance(settings.cache, CacheSettings)

        client = self.create_http_client(settings)
        assert isinstance(client._transport, hishel.AsyncCacheTransport)
        assert client._transport._controller._allow_heuristics is False
        assert client._transport._controller._allow_stale is False
        assert client._transport._controller._cacheable_methods == ["GET", "HEAD"]
        assert client._transport._controller._cacheable_status_codes == list(
            hishel.HEURISTICALLY_CACHEABLE_STATUS_CODES
        )

    def test_with_custom_cache(self):
        settings = HttpClientSettings(
            cache={
                "enabled": True,
                "controller": {
                    "allow_stale": True,
                    "cacheable_methods": ["GET"],
                    "cacheable_status_codes": [200],
                },
            }
        )

        assert settings.cache.enabled is True
        assert isinstance(settings.cache, CacheSettings)

        client = self.create_http_client(settings)
        assert isinstance(client._transport, hishel.AsyncCacheTransport)

        assert isinstance(client._transport._controller, hishel.Controller)
        assert client._transport._controller._allow_heuristics is False
        assert client._transport._controller._allow_stale is True
        assert client._transport._controller._cacheable_methods == ["GET"]
        assert client._transport._controller._cacheable_status_codes == [200]
