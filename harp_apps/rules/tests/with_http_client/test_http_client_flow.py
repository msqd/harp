from unittest.mock import Mock

from httpx import AsyncClient

from harp.config.factories.kernel_factory import KernelFactory

from .._base import BaseRulesFlowTest


class TestHttpClientRulesFlow(BaseRulesFlowTest):
    applications = ["http_client", "rules"]

    async def test_http_client_flow(self, httpbin):
        mock = Mock()
        config = self.create_config({}, mock=mock)

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
        assert mock.call_args_list[1].kwargs["response"].status_code == 200
