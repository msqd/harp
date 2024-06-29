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
          type: sqlalchemy
          url: "$database"
        """
    )

    def test_noproxy_get(self, benchmark, httpbin):
        super().test_noproxy_get(benchmark, httpbin)

    def test_httpbin_get(self, benchmark, proxy):
        super().test_httpbin_get(benchmark, proxy)


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

    def test_noproxy_get(self, benchmark, httpbin):
        super().test_noproxy_get(benchmark, httpbin)

    def test_httpbin_get(self, benchmark, proxy):
        super().test_httpbin_get(benchmark, proxy)
