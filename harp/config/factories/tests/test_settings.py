from tempfile import NamedTemporaryFile

import pytest

from harp import Config


class TestSettings:
    async def factory(self, settings=None):
        config = Config(settings)
        config.add_application("harp_apps.sqlalchemy_storage")
        config.add_application("harp_apps.dashboard")
        config.validate()
        return config.settings

    @pytest.mark.parametrize("false_value", ["no", "false", "0", 0, None])
    async def test_disabled_dashboard(self, false_value):
        settings = await self.factory({"dashboard": {"enabled": false_value}})
        assert settings["dashboard"] == {"enabled": False}

    async def test_dashboard_auth_basic(self):
        users = {"foo": "bar"}
        settings = await self.factory({"dashboard": {"auth": {"type": "basic", "algorithm": "plain", "users": users}}})
        assert settings["dashboard"]["auth"] == {"algorithm": "plain", "type": "basic", "users": {"foo": "bar"}}

    async def test_dashboard_auth_basic_from_file(self):
        with NamedTemporaryFile("w") as f:
            f.write("foo:bar")
            f.close()
            settings = await self.factory({"dashboard": {"auth": {"type": "basic", "users": {"fromFile": f.name}}}})

        assert settings["dashboard"]["auth"] == {
            "algorithm": "pbkdf2_sha256",
            "type": "basic",
            "users": {"from_file": f.name},
        }
