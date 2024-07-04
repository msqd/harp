from unittest.mock import ANY

from harp import Config
from harp.config.factories.kernel_factory import KernelFactory
from harp.utils.testing.communicators import ASGICommunicator
from harp_apps.storage.types import IBlobStorage


async def test_defaults_with_no_storage():
    config = Config(applications=["http_client"])
    assert config.validate() == {
        "applications": ["harp_apps.http_client"],
        "http_client": {
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
        },
    }

    factory = KernelFactory(config)
    kernel, binds = await factory.build()
    client = ASGICommunicator(kernel)
    await client.asgi_lifespan_startup()

    assert type(factory.provider.get(IBlobStorage)).__name__ == "NullBlobStorage"
