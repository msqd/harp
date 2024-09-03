from pathlib import Path

import pytest
from hishel import AsyncCacheTransport
from rodi import CannotResolveTypeException
from whistle import AsyncEventDispatcher, IAsyncEventDispatcher

from harp import ROOT_DIR
from harp.services import Container
from harp.utils.testing.config import BaseConfigurableTest
from harp_apps.http_client.settings import CacheSettings, HttpClientSettings


class MyCustomTransport(AsyncCacheTransport):
    pass


class TestCacheSettings(BaseConfigurableTest):
    type = CacheSettings
    expected_verbose = {
        "controller": {
            "allow_heuristics": False,
            "allow_stale": False,
            "cacheable_methods": ["GET", "HEAD"],
            "cacheable_status_codes": [
                200,
                203,
                204,
                206,
                300,
                301,
                308,
                404,
                405,
                410,
                414,
                501,
            ],
            "type": "hishel.Controller",
        },
        "enabled": True,
        "storage": {
            "base": "hishel.AsyncBaseStorage",
            "check_ttl_every": 60.0,
            "ttl": None,
            "type": "harp_apps.http_client.contrib.hishel.storages.AsyncStorage",
        },
        "transport": {"type": "hishel.AsyncCacheTransport"},
    }

    def test_service_override(self):
        settings = HttpClientSettings(
            cache=self.create(
                transport={
                    "type": MyCustomTransport.__module__ + "." + MyCustomTransport.__qualname__,
                },
            )
        )

        container = Container()
        container.add_instance(AsyncEventDispatcher(), IAsyncEventDispatcher)
        container.load(
            Path(ROOT_DIR) / "harp_apps" / "http_client" / "services.yml",
            bind_settings=settings,
        )

        provider = container.build_provider()

        cache = provider.get("http_client.cache.transport")
        assert isinstance(cache, MyCustomTransport)

    def test_cache_disabled(self):
        settings = HttpClientSettings(cache=self.create(enabled=False))

        container = Container()
        container.add_instance(AsyncEventDispatcher(), IAsyncEventDispatcher)
        container.load(
            Path(ROOT_DIR) / "harp_apps" / "http_client" / "services.yml",
            bind_settings=settings,
        )

        provider = container.build_provider()

        with pytest.raises(CannotResolveTypeException):
            provider.get("http_client.cache.transport")
