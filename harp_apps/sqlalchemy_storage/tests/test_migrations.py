from harp_apps.sqlalchemy_storage.utils.testing.database import run_migrations


async def test_migrations(database_url):
    result = await run_migrations(database_url)
    assert result.exit_code == 0
