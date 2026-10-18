from pathlib import Path

import pytest

from harp.config import ConfigurationBuilder

DOCS_APPS = Path(__file__).parent.parent / "docs" / "apps"
#: need a live database server, covered by the storage tests.
NEEDS_DATABASE_SERVER = {"storage/mysql-aiomysql.yml", "storage/postgres-asyncpg.yml"}
EXAMPLES = [
    path
    for path in sorted(DOCS_APPS.glob("*/examples/*.yml"))
    if f"{path.parent.parent.name}/{path.name}" not in NEEDS_DATABASE_SERVER
]


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: f"{path.parent.parent.name}/{path.name}")
async def test_example_loads_and_binds(example):
    builder = ConfigurationBuilder()
    builder.add_file(str(example))

    system = await builder.abuild_system()
    await system.dispose()
