from unittest.mock import Mock

from harp.config.factories.kernel_factory import KernelFactory
from harp.utils.testing.communicators import ASGICommunicator

from .._base import BaseRulesFlowTest


class TestProxyRulesFlow(BaseRulesFlowTest):
    applications = ["http_client", "proxy", "rules"]

    async def test_proxy_flow(self, httpbin):
        mock = Mock()
        config = self.create_config(
            {"proxy": {"endpoints": [{"name": "httpbin", "port": 80, "url": httpbin}]}}, mock=mock
        )

        # build our services (!!!badly named)
        factory = KernelFactory(config)
        kernel, binds = await factory.build()

        client = ASGICommunicator(kernel)
        await client.asgi_lifespan_startup()

        await client.http_get("/")

        assert mock.call_count == 4

        assert mock.call_args_list[0].kwargs["rule"] == "on_request"
        assert mock.call_args_list[0].kwargs["response"] is None

        assert mock.call_args_list[1].kwargs["rule"] == "on_remote_request"
        assert mock.call_args_list[1].kwargs["response"] is None

        assert mock.call_args_list[2].kwargs["rule"] == "on_remote_response"
        assert mock.call_args_list[2].kwargs["response"].status_code == 200

        assert mock.call_args_list[3].kwargs["rule"] == "on_response"
        assert mock.call_args_list[3].kwargs["response"].status == 200
