from unittest.mock import ANY

from harp import Config
from harp.config.factories.kernel_factory import KernelFactory
from harp.utils.testing.communicators import ASGICommunicator


async def test_http_client_flow():
    config = Config(applications=["http_client", "rules"])
    assert config.validate() == {
        "applications": ["harp_apps.http_client", "harp_apps.rules"],
        "http_client": {
            "cache": {
                "enabled": True,
                "check_ttl_every": 60,
                "controller": ANY,
                "storage": ANY,
                "transport": ANY,
                "ttl": ANY,
            },
            "timeout": 30.0,
            "transport": ANY,
        },
        "rules": {},
    }

    factory = KernelFactory(config)
    kernel, binds = await factory.build()
    client = ASGICommunicator(kernel)
    await client.asgi_lifespan_startup()
