from string import Template

import pytest

from harp.utils.testing.benchmarking import AbstractProxyBenchmark


@pytest.mark.benchmark(group="postgresql")
@pytest.mark.subprocess
class TestPostgresHttpbinBenchmark(AbstractProxyBenchmark):
    config = Template(
        """
        proxy:
          endpoints:
            - port: "$port"
              url: "$httpbin"
              name: test
        storage:
          url: "$database"
        """
    )


@pytest.mark.benchmark(group="sqlite")
@pytest.mark.subprocess
class TestSqliteHttpbinBenchmark(AbstractProxyBenchmark):
    config = Template(
        """
        proxy:
          endpoints:
            - port: "$port"
              url: "$httpbin"
              name: test
        """
    )
