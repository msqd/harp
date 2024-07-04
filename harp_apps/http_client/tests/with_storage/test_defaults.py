from unittest.mock import ANY

import pytest

from harp_apps.http_client.tests.base import BaseTestDefaultsWith
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
        factory, kernel = await self.build(applications=applications)
        validated_config = factory.configuration.validate()
        assert set(validated_config["applications"]) == {"harp_apps.http_client", "harp_apps.storage"}
        assert validated_config["http_client"] == {
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
        assert validated_config["storage"] == {
            "type": "sqlalchemy",
            "blobs": {"type": "sql"},
            "migrate": ANY,
            "url": ANY,
        }

        assert type(factory.provider.get(IBlobStorage)).__name__ == "SqlBlobStorage"
