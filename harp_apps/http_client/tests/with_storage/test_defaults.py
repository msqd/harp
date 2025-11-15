from unittest.mock import ANY

import pytest

from harp.config.asdict import asdict
from harp_apps.http_client.tests._base import BaseTestDefaultsWith
from harp_apps.storage.types import IBlobStorage


class TestDefaultsWithStorage(BaseTestDefaultsWith):
    @pytest.mark.parametrize(
        "applications",
        [
            ["http_client", "storage"],
            ["storage", "http_client"],
        ],
    )
    async def test_defaults_with_storage(self, applications):
        system = await self.create_system(applications=applications)
        assert set(system.config["applications"]) == {
            "harp_apps.http_client",
            "harp_apps.storage",
        }
        assert asdict(system.config["http_client"]) == {}
        assert asdict(system.config["http_client"], verbose=True) == {
            "cache": {
                "enabled": True,
                # hishel 1.0: Controller → SpecificationPolicy (CacheOptions configured in services.yml)
                "policy": {
                    "type": "hishel.SpecificationPolicy",
                },
                "storage": {
                    "base": "hishel.AsyncBaseStorage",
                    "check_ttl_every": 60.0,
                    "ttl": None,
                    "type": "harp_apps.http_client.contrib.hishel.storages.AsyncStorage",
                },
                # hishel 1.0: AsyncCacheTransport moved to _async_httpx module
                "transport": {"type": "hishel._async_httpx.AsyncCacheTransport"},
            },
            "enabled": True,
            "proxy_transport": {"type": "harp_apps.http_client.transport.AsyncFilterableTransport"},
            "timeout": 30.0,
            "transport": {
                "retries": 0,
                "type": "httpx.AsyncHTTPTransport",
                "verify": True,
            },
            "type": "httpx.AsyncClient",
        }
        assert asdict(system.config["storage"], verbose=True) == {
            "blobs": {"type": "sql"},
            "enabled": True,
            "migrate": ANY,
            "url": ANY,
            "redis": None,
        }

        assert type(system.provider.get(IBlobStorage)).__name__ == "SqlBlobStorage"
