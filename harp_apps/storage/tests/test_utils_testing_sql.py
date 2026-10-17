import pytest

from harp_apps.storage.utils.testing.sql import with_driver


@pytest.mark.parametrize(
    "container_url",
    [
        "mysql+pymysql://test:test@localhost:3306/test",  # testcontainers < 4.10
        "mysql://test:test@localhost:3306/test",  # testcontainers >= 4.10
    ],
)
def test_with_driver_mysql(container_url):
    assert with_driver(container_url, "mysql", "aiomysql") == "mysql+aiomysql://test:test@localhost:3306/test"
