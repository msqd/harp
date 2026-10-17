"""Pure logic of the macro harness: parsing, core assignment, arithmetic, result assembly. No process, no I/O."""

import statistics


def parse_cpu_list(text: str) -> list[int]:
    """Parses a kernel cpu list such as ``0-5,12``."""
    cpus: list[int] = []
    for part in text.strip().split(","):
        if not part:
            continue
        low, _, high = part.partition("-")
        cpus.extend(range(int(low), int(high or low) + 1))
    return cpus


def format_cpu_list(cpus: list[int]) -> str:
    return ",".join(str(cpu) for cpu in cpus)


def assign_cores(available: list[int], **counts: int) -> dict[str, list[int]]:
    """Hands out disjoint cores, in order, to each role (``harp=2, origin=1, ...``)."""
    if sum(counts.values()) > len(available):
        raise ValueError(f"not enough cores: need {sum(counts.values())}, have {len(available)}")
    assigned: dict[str, list[int]] = {}
    start = 0
    for role, count in counts.items():
        assigned[role] = available[start : start + count]
        start += count
    return assigned


def parse_oha(report: dict) -> dict:
    """Extracts latency percentiles (ms), completed requests and errors from an ``oha`` json report."""
    percentiles = report["latencyPercentiles"]
    statuses = report["statusCodeDistribution"]
    completed = sum(statuses.values())
    failed = completed - statuses.get("200", 0) + sum(report["errorDistribution"].values())
    return {
        "latency_ms": {name: percentiles[name] * 1000 for name in ("p50", "p90", "p99")},
        "requests": completed,
        "errors": failed,
        "requests_per_sec": report["summary"]["requestsPerSec"],
    }


def parse_proc_stat_ticks(stat: str) -> int:
    """utime + stime, in clock ticks, from the content of ``/proc/<pid>/stat``."""
    fields = stat.rsplit(")", 1)[1].split()  # fields[0] is the state, field 3 of the file
    return int(fields[11]) + int(fields[12])


def cpu_us_per_request(*, ticks: int, clock_ticks_per_second: int, requests: int) -> float:
    if requests <= 0:
        raise ValueError("no completed request to divide cpu time by")
    return ticks / clock_ticks_per_second * 1_000_000 / requests


def overhead_ms(direct: dict[str, float], proxied: dict[str, float]) -> dict[str, float]:
    return {name: proxied[name] - direct[name] for name in direct}


def median_spread(values: list[float]) -> dict:
    return {"median": statistics.median(values), "min": min(values), "max": max(values), "n": len(values)}


def assemble_overhead(direct: dict, proxied: dict, *, cpu_us_per_request: float) -> dict:
    """Combines the two runs; a run with any error is invalid and raises."""
    if direct["errors"] or proxied["errors"]:
        raise ValueError(f"invalid run, errors: direct={direct['errors']} proxied={proxied['errors']}")
    return {
        "direct": direct,
        "proxied": proxied,
        "overhead_ms": overhead_ms(direct["latency_ms"], proxied["latency_ms"]),
        "harp_cpu_us_per_request": cpu_us_per_request,
    }
