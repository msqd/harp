from harp_apps.sqlalchemy_storage.utils.testing.database import run_cli_migrate_command


async def test_migrations(database_url):
    result = await run_cli_migrate_command(database_url)
    if result.exit_code != 0:
        print(result.output)
    assert result.exit_code == 0
