from harp.utils.testing.databases import parametrize_with_database_urls

from ..controllers import SystemController
from ._mixins import SystemControllerTestFixtureMixin, parametrize_with_settings


class TestSystemControllerProxy(SystemControllerTestFixtureMixin):
    @parametrize_with_settings({})
    @parametrize_with_database_urls("sqlite")
    async def test_get_proxy_without_config(self, controller: SystemController):
        response = await controller.get_proxy()
        assert response == {"endpoints": []}

    @parametrize_with_settings(
        {
            "applications": ["proxy", "http_client"],
            "proxy": {
                "endpoints": [
                    {"name": "api", "port": 4000, "url": "http://example.com"},
                ],
            },
        }
    )
    @parametrize_with_database_urls("sqlite")
    async def test_get_proxy(self, controller: SystemController):
        response = await controller.get_proxy()
        assert response == {
            "endpoints": [
                {
                    "description": None,
                    "name": "api",
                    "port": 4000,
                    "remote": {
                        "break_on": ["network_error", "unhandled_exception"],
                        "check_after": 10.0,
                        "endpoints": [
                            {
                                "failure_threshold": 1,
                                "pools": ["default"],
                                "success_threshold": 1,
                                "url": "http://example.com/",
                            }
                        ],
                        "min_pool_size": 1,
                        "probe": None,
                    },
                    "url": None,
                }
            ]
        }
