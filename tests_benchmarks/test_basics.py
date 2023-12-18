from string import Template

import pytest

from harp.utils.testing.benchmarking import AbstractProxyBenchmark


@pytest.mark.benchmark(group="postgresql")
class TestPostgresHttpbinBenchmark(AbstractProxyBenchmark):
    config = Template(
        """
        dashboard:
            enabled: false
        proxy:
            endpoints:
                $port:
                    url: http://localhost:8080/
                    name: test
        storage:
            type: sqlalchemy
            url: postgresql://harp:harp@localhost:5432/benchmarks
    """
    )


@pytest.mark.benchmark(group="sqlite")
class TestSqliteHttpbinBenchmark(AbstractProxyBenchmark):
    config = Template(
        """
        dashboard:
            enabled: false
        proxy:
            endpoints:
                $port:
                    url: http://localhost:8080/
                    name: test
    """
    )
