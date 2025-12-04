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
        """Test http_client defaults when storage app is loaded."""
        system = await self.create_system(applications=applications)
        assert set(system.config["applications"]) == {
            "harp_apps.http_client",
            "harp_apps.storage",
        }
        assert asdict(system.config["http_client"]) == {}
        assert asdict(system.config["http_client"], verbose=True) == {
            "enabled": True,
            "proxy_transport": {"type": "harp_apps.http_client.transports.AsyncFilterableTransport"},
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
