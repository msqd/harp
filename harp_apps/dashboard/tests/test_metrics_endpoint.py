from typing import cast
from unittest.mock import AsyncMock, Mock

from httpx import AsyncClient

from harp.config import ConfigurationBuilder
from harp.config.asdict import asdict
from harp.controllers import ProxyControllerResolver
from harp.http import HttpRequest
from harp_apps.dashboard.controllers import DashboardController
from harp_apps.dashboard.settings import BasicAuthSettings, DashboardSettings
from harp_apps.dashboard.settings.auth import User
from harp_apps.storage import worker as _worker  # noqa: F401  (registers the `dropped` counter)
from harp_apps.storage.types import IStorage


def create_controller(settings: DashboardSettings | None = None) -> DashboardController:
    controller = DashboardController(
        storage=cast(IStorage, Mock(spec=IStorage)),
        settings=settings or DashboardSettings(auth={"type": "none"}, devserver={"enabled": True, "port": 5173}),
        http_client=Mock(spec=AsyncClient),
    )
    controller._ui_devserver_proxy_controller = None
    return controller


def metrics_request(**kwargs) -> HttpRequest:
    request = HttpRequest(**kwargs)
    request.path = "/metrics"
    return request


async def test_dashboard_port_serves_metrics():
    controller = create_controller()

    response = await controller(metrics_request(), AsyncMock())

    body = response.body.decode()
    assert response.status == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "async_worker_queue_backlog" in body
    assert "dropped" in body


async def test_dashboard_metrics_follow_dashboard_auth():
    controller = create_controller(
        DashboardSettings(
            auth=BasicAuthSettings(type="basic", algorithm="plaintext", users={"admin": User(password="admin")}),
            devserver={"enabled": True, "port": 5173},
        )
    )

    response = await controller(metrics_request(), AsyncMock())

    assert response.status == 401


async def _build(dashboard_settings: dict):
    return await ConfigurationBuilder(
        {
            "applications": ["http_client", "storage", "harp_apps.dashboard"],
            "dashboard": {
                **asdict(DashboardSettings(auth={"type": "none"}, devserver={"enabled": True, "port": 5173})),
                **dashboard_settings,
            },
        },
        use_default_applications=False,
    ).abuild_system(validate_dependencies=False)


async def test_metrics_port_is_off_by_default():
    system = await _build({})

    assert system.provider.get(ProxyControllerResolver).ports == (4080,)


async def test_metrics_port_serves_metrics_on_its_own_port():
    system = await _build({"metrics_port": 9100})
    resolver = system.provider.get(ProxyControllerResolver)

    assert 9100 in resolver.ports
    response = await resolver.resolve_by_port(9100)(metrics_request())
    assert response.status == 200
    assert "async_worker_queue_backlog" in response.body.decode()


async def test_dropped_series_exist_before_any_drop():
    # alerting and rate() need the series to exist at 0 from startup
    response = await create_controller()(metrics_request(), AsyncMock())

    body = response.body.decode()
    for kind in ("transactions", "messages", "headers", "bodies"):
        assert f'dropped_total{{kind="{kind}"}}' in body
