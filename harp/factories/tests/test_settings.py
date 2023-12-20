from tempfile import NamedTemporaryFile

import pytest

from harp import ProxyFactory
from harp.applications.dashboard.settings import DashboardAuthBasicSettings
from harp.core.settings import DisabledSettings, FromFileSetting


class TestSettings:
    async def factory(self, settings=None):
        factory = ProxyFactory(settings=settings)
        await factory.create()
        return factory.settings

    @pytest.mark.parametrize("false_value", ["no", "false", "0", 0, None])
    async def test_disabled_dashboard(self, false_value):
        settings = await self.factory({"dashboard": {"enabled": false_value}})

        assert settings.dashboard.enabled is False
        assert isinstance(settings.dashboard, DisabledSettings)

    async def test_dashboard_auth_basic(self):
        passwd = {"foo": "bar"}
        settings = await self.factory({"dashboard": {"auth": {"type": "basic", "passwd": passwd}}})
        assert settings.dashboard.auth.type == "basic"
        assert isinstance(settings.dashboard.auth, DashboardAuthBasicSettings)
        assert settings.dashboard.auth.passwd == passwd
        assert settings.dashboard.auth.to_dict() == {"type": "basic", "passwd": passwd}

    async def test_dashboard_auth_basic_from_file(self):
        with NamedTemporaryFile("w") as f:
            f.write("foo:bar")
            f.close()
            settings = await self.factory({"dashboard": {"auth": {"type": "basic", "passwd": {"fromFile": f.name}}}})
            assert settings.dashboard.auth.type == "basic"
            assert isinstance(settings.dashboard.auth, DashboardAuthBasicSettings)
            assert isinstance(settings.dashboard.auth.passwd, FromFileSetting)
