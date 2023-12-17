from string import Template

import httpx
import pytest

from harp.utils.testing.benchmarking import AbstractProxyBenchmark


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

    @pytest.mark.benchmark
    def test_postgres_httpbin_get(self, benchmark, proxy):
        @benchmark
        def result():
            return httpx.get(f"http://{proxy}/get")


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

    @pytest.mark.benchmark
    def test_sqlite_httpbin_get(self, benchmark, proxy):
        @benchmark
        def result():
            return httpx.get(f"http://{proxy}/get")
