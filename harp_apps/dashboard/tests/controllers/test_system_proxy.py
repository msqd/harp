from unittest.mock import ANY

import orjson

from harp.http import HttpRequest
from harp.utils.testing.databases import parametrize_with_database_urls
from harp_apps.dashboard.controllers.system import SystemController
from harp_apps.dashboard.tests._mixins import SystemControllerTestFixtureMixin, parametrize_with_settings

PROXY_SETTINGS = {
    "applications": ["proxy", "http_client"],
    "proxy": {
        "endpoints": [
            {"name": "api", "port": 4000, "url": "http://example.com"},
        ],
    },
}


class TestSystemControllerProxy(SystemControllerTestFixtureMixin):
    @parametrize_with_settings({})
    @parametrize_with_database_urls("sqlite")
    async def test_get_proxy_without_config(self, controller: SystemController):
        response = await controller.get_proxy()
        assert response == {"endpoints": []}

    @parametrize_with_settings(PROXY_SETTINGS)
    @parametrize_with_database_urls("sqlite")
    async def test_get_proxy(self, controller: SystemController):
        response = await controller.get_proxy()
        assert response == {
            "endpoints": [
                {
                    "remote": {
                        "current_pool": ["http://example.com/"],
                        "current_pool_name": "default",
                        "endpoints": [
                            {
                                "failure_reasons": None,
                                "settings": {
                                    "liveness": {"type": "inherit"},
                                    "pools": ["default"],
                                    "url": "http://example.com/",
                                },
                                "status": 0,
                            }
                        ],
                        "probe": None,
                        "settings": {
                            "break_on": ["network_error", "unhandled_exception"],
                            "check_after": 10.0,
                            "min_pool_size": 1,
                        },
                    },
                    "settings": {"description": None, "name": "api", "port": 4000},
                }
            ]
        }

    @parametrize_with_settings(PROXY_SETTINGS)
    @parametrize_with_database_urls("sqlite")
    async def test_put_proxy(self, controller: SystemController):
        response = await controller.put_proxy(HttpRequest())
        assert response.status == 400

        response = await controller.put_proxy(
            HttpRequest(
                body=orjson.dumps(
                    {
                        "endpoint": "not-an-api",
                        "action": "up",
                        "url": "http://example.com",
                    }
                )
            )
        )
        assert response.status == 404

        response = await controller.put_proxy(
            HttpRequest(
                body=orjson.dumps(
                    {
                        "endpoint": "api",
                        "action": "up",
                        "url": "http://invalid.com",
                    }
                )
            )
        )
        assert response.status == 404

        response = await controller.put_proxy(
            HttpRequest(
                body=orjson.dumps(
                    {
                        "endpoint": "api",
                        "action": "up",
                        "url": "http://example.com",
                    }
                )
            )
        )
        assert response == {
            "endpoints": [
                {
                    "remote": {
                        "current_pool": ["http://example.com/"],
                        "current_pool_name": "default",
                        "endpoints": [
                            {
                                "failure_reasons": None,
                                "settings": ANY,
                                "status": 1,
                            }
                        ],
                        "probe": None,
                        "settings": ANY,
                    },
                    "settings": ANY,
                }
            ]
        }
