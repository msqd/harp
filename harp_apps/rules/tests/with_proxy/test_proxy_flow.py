from unittest.mock import Mock

from harp.utils.testing.communicators import ASGICommunicator

from .._base import BaseRulesFlowTest


class TestProxyRulesFlow(BaseRulesFlowTest):
    applications = ["http_client", "proxy", "rules"]

    async def test_proxy_flow(self, httpbin):
        mock = Mock()
        system = await self.create_system(
            {"proxy": {"endpoints": [{"name": "httpbin", "port": 80, "url": httpbin}]}},
            mock=mock,
        )

        client = ASGICommunicator(system.kernel)
        await client.asgi_lifespan_startup()

        await client.http_get("/")

        assert mock.call_count == 4

        assert mock.call_args_list[0].args[0]["rule"] == "on_request"
        assert mock.call_args_list[0].args[0]["response"] is None

        assert mock.call_args_list[1].args[0]["rule"] == "on_remote_request"
        assert mock.call_args_list[1].args[0]["response"] is None

        assert mock.call_args_list[2].args[0]["rule"] == "on_remote_response"
        assert mock.call_args_list[2].args[0]["response"].status_code == 200

        assert mock.call_args_list[3].args[0]["rule"] == "on_response"
        assert mock.call_args_list[3].args[0]["response"].status == 200
