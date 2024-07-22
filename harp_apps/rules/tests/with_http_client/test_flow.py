from unittest.mock import ANY, Mock

from httpx import AsyncClient

from harp import Config
from harp.config.factories.kernel_factory import KernelFactory
from harp_apps.rules.models.rulesets import RuleSet


async def test_http_client_flow(httpbin):
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

    mock = Mock()

    rules: RuleSet = config["rules"].settings.rules
    rules.add(
        {
            "*": {
                "*": {
                    "*": [
                        mock,
                    ]
                }
            }
        }
    )

    # build our services (!!!badly named)
    factory = KernelFactory(config)
    await factory.build()

    # make a request
    http_client = factory.provider.get(AsyncClient)
    response = await http_client.get(httpbin)
    assert response.status_code == 200

    assert mock.call_count == 2

    assert mock.call_args_list[0].kwargs["rule"] == "on_remote_request"
    assert mock.call_args_list[0].kwargs["response"] is None

    assert mock.call_args_list[1].kwargs["rule"] == "on_remote_response"
    assert mock.call_args_list[1].kwargs["response"] is not response
