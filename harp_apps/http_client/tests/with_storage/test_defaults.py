from unittest.mock import ANY

import pytest

from harp.config import asdict
from harp_apps.storage.types import IBlobStorage

from .._base import BaseTestDefaultsWith


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
        assert set(system.config["applications"]) == {"harp_apps.http_client", "harp_apps.storage"}
        assert asdict(system.config["http_client"]) == {
            "cache": {
                "enabled": True,
                "controller": ANY,
                "storage": ANY,
                "transport": {"@type": ANY},
                "ttl": ANY,
                "check_ttl_every": ANY,
            },
            "timeout": 30.0,
            "transport": {"@type": "httpx:AsyncHTTPTransport"},
        }
        assert asdict(system.config["storage"]) == {
            "blobs": {"type": "sql"},
            "migrate": ANY,
            "url": ANY,
        }

        assert type(system.provider.get(IBlobStorage)).__name__ == "SqlBlobStorage"
