"""Tests for the pure logic of the macro benchmark harness (see `bench/macro/`)."""

import argparse
from pathlib import Path

import pytest

from bench.macro import measure, run
from harp_apps.http_client.clients import CLIENTS


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

    def test_sent_counts_failures_too(self):
        sample = {**self.SAMPLE, "statusCodeDistribution": {"200": 990}, "errorDistribution": {"timeout": 10}}
        assert measure.parse_oha(sample)["sent"] == 1000

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


def step(rate, p99, errors=0):
    return {"rate": rate, "latency_ms": {"p50": 1.0, "p90": 2.0, "p99": p99}, "errors": errors}


class TestStepValidity:
    def test_valid_below_twice_the_base_p99(self):
        assert measure.step_valid(step(100, 3.9), base_p99=2.0)

    def test_invalid_at_twice_the_base_p99(self):
        assert not measure.step_valid(step(100, 4.0), base_p99=2.0)

    def test_invalid_with_errors(self):
        assert not measure.step_valid(step(100, 1.0, errors=1), base_p99=2.0)


class TestSaturation:
    def test_highest_valid_step(self):
        steps = [step(25, 2.0), step(50, 2.5), step(100, 3.0), step(200, 40.0)]
        assert measure.saturation_rate(steps) == 100

    def test_stops_at_first_invalid_step(self):
        steps = [step(25, 2.0), step(50, 9.0), step(100, 2.0)]
        assert measure.saturation_rate(steps) == 25

    def test_lowest_step_invalid(self):
        assert measure.saturation_rate([step(25, 2.0, errors=3)]) is None

    def test_no_steps(self):
        assert measure.saturation_rate([]) is None


class TestRerunRates:
    def test_half_and_eighty_percent(self):
        assert measure.rerun_rates(200) == {"50%": 100, "80%": 160}

    def test_rounded_and_at_least_one(self):
        assert measure.rerun_rates(3) == {"50%": 2, "80%": 2}
        assert measure.rerun_rates(1) == {"50%": 1, "80%": 1}


class TestParseBacklog:
    EXPOSITION = (
        "# HELP async_worker_queue_backlog Number of items in the async worker queue.\n"
        "# TYPE async_worker_queue_backlog gauge\n"
        'async_worker_queue_backlog{queue_id="1"} 12.0\n'
        'async_worker_queue_backlog{queue_id="2"} 340.0\n'
        "other_metric 5\n"
    )

    def test_max_over_queues(self):
        assert measure.parse_backlog(self.EXPOSITION) == 340

    def test_gauge_absent(self):
        assert measure.parse_backlog("other_metric 5\n") is None


class TestParseVmHwm:
    def test_kib(self):
        status = "Name:\tharp\nVmPeak:\t  900 kB\nVmHWM:\t  123456 kB\nVmRSS:\t  100000 kB\n"
        assert measure.parse_vm_hwm_kib(status) == 123456


class TestDrainSeconds:
    def test_time_of_last_growth_after_the_end_of_load(self):
        samples = [(10.0, 100), (10.5, 150), (11.0, 180), (11.5, 180), (12.0, 180)]
        assert measure.drain_seconds(samples, t_end=10.0) == 1.0

    def test_already_drained(self):
        assert measure.drain_seconds([(10.0, 100), (10.5, 100)], t_end=10.0) == 0.0

    def test_growth_before_the_end_is_ignored(self):
        assert measure.drain_seconds([(8.0, 10), (9.0, 20), (10.0, 20), (11.0, 20)], t_end=10.0) == 0.0


class TestSheddingShares:
    def test_nothing_shed(self):
        counts = {"transactions": 100, "messages": 200, "headers": 200, "bodies": 200}
        shares = measure.shedding_shares(sent=100, counts=counts)
        assert shares == {"transactions": 0.0, "messages": 0.0, "headers": 0.0, "bodies": 0.0}

    def test_share_of_what_was_sent(self):
        counts = {"transactions": 80, "messages": 100, "headers": 60, "bodies": 20}
        shares = measure.shedding_shares(sent=100, counts=counts)
        assert shares == pytest.approx({"transactions": 0.2, "messages": 0.5, "headers": 0.7, "bodies": 0.9})

    def test_never_negative(self):
        counts = {"transactions": 101, "messages": 202, "headers": 202, "bodies": 202}
        assert measure.shedding_shares(sent=100, counts=counts)["transactions"] == 0.0


class TestUrlPattern:
    def test_mix_of_cacheable_and_unique_paths(self):
        pattern = measure.url_pattern("http://h:1", cache_share=0.3)
        branches = pattern.removeprefix("http://h:1/(").removesuffix(")").split("|")
        assert len(branches) == 10
        assert sum(b.startswith("cache/") for b in branches) == 3
        assert sum(b.startswith("miss/") for b in branches) == 7

    def test_no_cache(self):
        assert "cache/" not in measure.url_pattern("http://h:1", cache_share=0)


class TestShedMarkers:
    def test_marked_and_observed_agree(self):
        counts = {
            "marked_messages": 3,
            "marked_headers": 5,
            "marked_bodies": 9,
            "missing_messages": 3,
            "missing_headers": 5,
            "missing_bodies": 9,
        }
        report = measure.shed_marker_report(counts)
        assert report["headers"] == {"marked": 5, "missing": 5, "agree": True}
        assert all(entry["agree"] for entry in report.values())

    def test_disagreement(self):
        counts = {
            "marked_messages": 0,
            "marked_headers": 4,
            "marked_bodies": 0,
            "missing_messages": 0,
            "missing_headers": 5,
            "missing_bodies": 0,
        }
        report = measure.shed_marker_report(counts)
        assert report["headers"]["agree"] is False
        assert report["bodies"]["agree"] is True


class TestHarpCommand:
    def command(self, client="httpx"):
        args = argparse.Namespace(profile="bare", harp_port=4000, origin_port=4100, client=client)
        return run.harp_command(args, {"harp": [0]}, Path("/tmp"), Path("/tmp/h.db"))

    def test_default_client_is_not_passed(self):
        assert "--client" not in self.command()

    def test_client_is_passed(self):
        command = self.command("aiohttp")
        assert command[command.index("--client") + 1] == "aiohttp"

    def test_clients_are_the_ones_harp_knows(self):
        assert run.CLIENTS == CLIENTS
