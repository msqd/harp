import pytest

from harp import ProxyFactory
from harp.applications.dashboard.settings import DisabledSettings


@pytest.mark.parametrize("false_value", ["no", "false", "0", 0, None])
async def test_disabled_dashboard(false_value):
    proxy = ProxyFactory(settings={"dashboard": {"enabled": false_value}})
    await proxy.create()
    assert isinstance(proxy.settings.dashboard, DisabledSettings)
    assert proxy.settings.dashboard.enabled is False
