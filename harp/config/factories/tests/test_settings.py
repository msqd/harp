from tempfile import NamedTemporaryFile

from harp import Config


class TestSettings:
    async def factory(self, settings=None):
        config = Config(settings)
        config.add_application("sqlalchemy_storage")
        config.add_application("dashboard")
        config.validate()
        return config.settings

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
