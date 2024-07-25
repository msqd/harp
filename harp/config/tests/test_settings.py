from tempfile import NamedTemporaryFile

from sqlalchemy import make_url

from harp.config import ConfigurationBuilder, asdict


def create_settings(settings=None):
    config = ConfigurationBuilder(settings)
    config.applications.add("storage")
    config.applications.add("dashboard")
    return asdict(config.build())


class TestSettings:
    async def test_dashboard_auth_basic(self):
        users = {"foo": "bar"}
        settings = create_settings({"dashboard": {"auth": {"type": "basic", "algorithm": "plain", "users": users}}})
        assert settings["dashboard"]["auth"] == {"algorithm": "plain", "type": "basic", "users": {"foo": "bar"}}

    async def test_dashboard_auth_basic_from_file(self):
        with NamedTemporaryFile("w") as f:
            f.write("foo:bar")
            f.close()
            settings = create_settings({"dashboard": {"auth": {"type": "basic", "users": {"fromFile": f.name}}}})

        assert settings["dashboard"]["auth"] == {
            "algorithm": "pbkdf2_sha256",
            "type": "basic",
            "users": {"from_file": f.name},
        }

    async def test_sqlalchemy_url_merges(self):
        dburl = "proto:///user:pass@localhost:1234/name"

        builder = ConfigurationBuilder()
        builder.applications.add("storage")
        builder.add_values({"storage": {"url": dburl}})
        builder.add_values({"storage": {"url": dburl}})
        config = builder.build()
        assert config["storage"].url == make_url(dburl)
        assert asdict(config)["storage"]["url"] == dburl
