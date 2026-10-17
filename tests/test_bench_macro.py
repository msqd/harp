"""Tests for the pure logic of the macro benchmark harness (see `bench/macro/`)."""

import pytest

from bench.macro import measure


class TestParseCpuList:
    def test_ranges_and_singles(self):
        assert measure.parse_cpu_list("0-5,12") == [0, 1, 2, 3, 4, 5, 12]

    def test_trailing_newline(self):
        assert measure.parse_cpu_list("0-1\n") == [0, 1]

    def test_empty(self):
        assert measure.parse_cpu_list("") == []


class TestFormatCpuList:
    def test_roundtrip(self):
        assert measure.format_cpu_list([0, 1, 2, 12]) == "0,1,2,12"


class TestAssignCores:
    def test_disjoint_cores_in_order(self):
        cores = measure.assign_cores([0, 1, 2, 3, 4, 5], harp=2, origin=1, loadgen=1)
        assert cores == {"harp": [0, 1], "origin": [2], "loadgen": [3]}

    def test_not_enough_cores(self):
        with pytest.raises(ValueError, match="cores"):
            measure.assign_cores([0, 1], harp=2, origin=1, loadgen=1)


class TestParseOha:
    SAMPLE = {
        "summary": {"requestsPerSec": 199.5},
        "latencyPercentiles": {"p50": 0.001, "p90": 0.002, "p99": 0.004},
        "statusCodeDistribution": {"200": 1000},
        "errorDistribution": {},
    }

    def test_latencies_in_milliseconds(self):
        parsed = measure.parse_oha(self.SAMPLE)
        assert parsed["latency_ms"] == {"p50": 1.0, "p90": 2.0, "p99": 4.0}

    def test_requests_and_no_errors(self):
        parsed = measure.parse_oha(self.SAMPLE)
        assert parsed["requests"] == 1000
        assert parsed["errors"] == 0

    def test_errors_count_non_200_and_failures(self):
        sample = {**self.SAMPLE, "statusCodeDistribution": {"200": 990, "502": 8}, "errorDistribution": {"timeout": 2}}
        parsed = measure.parse_oha(sample)
        assert parsed["requests"] == 998
        assert parsed["errors"] == 10


class TestCpuPerRequest:
    def test_microseconds_per_request(self):
        # 200 ticks at 100 Hz = 2 s of cpu over 1000 requests
        assert measure.cpu_us_per_request(ticks=200, clock_ticks_per_second=100, requests=1000) == 2000.0

    def test_no_requests(self):
        with pytest.raises(ValueError):
            measure.cpu_us_per_request(ticks=1, clock_ticks_per_second=100, requests=0)


class TestParseProcStatTicks:
    def test_utime_plus_stime_even_with_spaces_in_comm(self):
        stat = "123 (harp proxy) S 1 2 3 4 5 6 7 8 9 10 40 25 0 0 20 0 1 0 100 0 0"
        assert measure.parse_proc_stat_ticks(stat) == 65


class TestOverhead:
    def test_difference_per_percentile(self):
        direct = {"p50": 0.3, "p90": 0.5, "p99": 1.0}
        proxied = {"p50": 2.3, "p90": 3.5, "p99": 9.0}
        assert measure.overhead_ms(direct, proxied) == pytest.approx({"p50": 2.0, "p90": 3.0, "p99": 8.0})


class TestMedianSpread:
    def test_median_min_max(self):
        assert measure.median_spread([3.0, 1.0, 2.0]) == {"median": 2.0, "min": 1.0, "max": 3.0, "n": 3}


class TestAssembleResult:
    def test_invalid_when_errors(self):
        direct = {"latency_ms": {"p50": 1, "p90": 1, "p99": 1}, "requests": 10, "errors": 0}
        proxied = {"latency_ms": {"p50": 2, "p90": 2, "p99": 2}, "requests": 10, "errors": 1}
        with pytest.raises(ValueError, match="errors"):
            measure.assemble_overhead(direct, proxied, cpu_us_per_request=10.0)

    def test_assembled(self):
        direct = {"latency_ms": {"p50": 1, "p90": 1, "p99": 1}, "requests": 10, "errors": 0}
        proxied = {"latency_ms": {"p50": 3, "p90": 4, "p99": 6}, "requests": 10, "errors": 0}
        result = measure.assemble_overhead(direct, proxied, cpu_us_per_request=10.0)
        assert result["overhead_ms"] == {"p50": 2, "p90": 3, "p99": 5}
        assert result["direct"] is direct
        assert result["proxied"] is proxied
        assert result["harp_cpu_us_per_request"] == 10.0
