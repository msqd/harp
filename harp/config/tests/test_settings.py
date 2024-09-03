from tempfile import NamedTemporaryFile

from sqlalchemy import make_url

from harp.config import ConfigurationBuilder
from harp.config.asdict import asdict


def create_settings(settings=None):
    config = ConfigurationBuilder(settings)
    config.applications.add("storage")
    config.applications.add("dashboard")
    return asdict(config.build())


class TestSettings:
    async def test_dashboard_auth_basic(self):
        users = {"foo": "bar"}
        settings = create_settings({"dashboard": {"auth": {"type": "basic", "algorithm": "plain", "users": users}}})
        assert settings["dashboard"]["auth"] == {
            "algorithm": "plaintext",
            "type": "basic",
            "users": {"foo": {"password": "bar"}},
        }

    async def test_dashboard_auth_basic_from_file(self):
        with NamedTemporaryFile("w", delete_on_close=False) as f:
            f.write("romain: s3cr3t")
            f.close()
            settings = create_settings({"dashboard": {"auth": {"type": "basic", "users": {"fromFile": f.name}}}})

            assert settings["dashboard"]["auth"] == {
                "type": "basic",
                "users": {"romain": {"password": "s3cr3t"}},
            }

    async def test_sqlalchemy_url_merges(self):
        dburl = "postgresql+asyncpg:///user:pass@localhost:1234/name"

        builder = ConfigurationBuilder()
        builder.applications.add("storage")
        builder.add_values({"storage": {"url": dburl}})
        builder.add_values({"storage": {"url": dburl}})
        config = builder.build()
        assert str(config["storage"].url) == str(make_url(dburl))
        assert asdict(config, secure=False)["storage"]["url"] == dburl
