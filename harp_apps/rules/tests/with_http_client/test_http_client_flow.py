from unittest.mock import Mock

from httpx import AsyncClient

from .._base import BaseRulesFlowTest


class TestHttpClientRulesFlow(BaseRulesFlowTest):
    applications = ["http_client", "rules"]

    async def test_http_client_flow(self, httpbin):
        mock = Mock()
        system = await self.create_system({}, mock=mock)

        # make a request
        http_client = system.provider.get(AsyncClient)
        response = await http_client.get(httpbin)
        assert response.status_code == 200

        assert mock.call_count == 2

        assert mock.call_args_list[0].args[0]["rule"] == "on_remote_request"
        assert mock.call_args_list[0].args[0]["response"] is None

        assert mock.call_args_list[1].args[0]["rule"] == "on_remote_response"
        assert mock.call_args_list[1].args[0]["response"].status_code == 200
