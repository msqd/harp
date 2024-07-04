from unittest.mock import ANY

import pytest

from harp import Config
from harp.config.factories.kernel_factory import KernelFactory
from harp.utils.testing.communicators import ASGICommunicator
from harp_apps.storage.types import IBlobStorage


@pytest.mark.parametrize(
    "applications",
    [
        ["http_client", "storage"],
        ["storage", "http_client"],
    ],
)
async def test_defaults_with_storage(applications):
    config = Config(applications=applications)
    validated_config = config.validate()
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

    factory = KernelFactory(config)
    kernel, binds = await factory.build()
    client = ASGICommunicator(kernel)
    await client.asgi_lifespan_startup()

    assert type(factory.provider.get(IBlobStorage)).__name__ == "SqlBlobStorage"
