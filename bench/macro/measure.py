"""Pure logic of the macro harness: parsing, core assignment, arithmetic, result assembly. No process, no I/O."""

import re
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
        "sent": completed + sum(report["errorDistribution"].values()),
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


# --- load steps ------------------------------------------------------------------------------------------------------

SATURATION_P99_FACTOR = 2
BACKLOG_SERIES = re.compile(r"^async_worker_queue_backlog\{[^}]*\}\s+(\S+)$", re.MULTILINE)
VM_HWM = re.compile(r"^VmHWM:\s+(\d+) kB$", re.MULTILINE)


def step_valid(step: dict, *, base_p99: float) -> bool:
    """A step holds if it had no error and its p99 stayed below twice the p99 of the lowest step."""
    return not step["errors"] and step["latency_ms"]["p99"] < SATURATION_P99_FACTOR * base_p99


def saturation_rate(steps: list[dict]) -> int | None:
    """Highest rate of the valid steps, in order, before the first invalid one. None if the lowest step is invalid."""
    if not steps:
        return None
    base_p99 = steps[0]["latency_ms"]["p99"]
    saturation = None
    for step in steps:
        if not step_valid(step, base_p99=base_p99):
            break
        saturation = step["rate"]
    return saturation


def rerun_rates(saturation: int) -> dict[str, int]:
    return {label: max(1, round(saturation * share)) for label, share in (("50%", 0.5), ("80%", 0.8))}


def parse_backlog(exposition: str) -> int | None:
    """Largest ``async_worker_queue_backlog`` series of a prometheus text exposition, None if absent."""
    values = [float(value) for value in BACKLOG_SERIES.findall(exposition)]
    return int(max(values)) if values else None


def parse_vm_hwm_kib(status: str) -> int:
    """Peak resident set size, in KiB, from the content of ``/proc/<pid>/status``."""
    return int(VM_HWM.search(status).group(1))


def drain_seconds(samples: list[tuple[float, int]], *, t_end: float) -> float:
    """Seconds between the end of the load and the last growth of a (time, recorded rows) series."""
    last_growth = t_end
    for (_, before), (when, after) in zip(samples, samples[1:]):
        if after > before and when > last_growth:
            last_growth = when
    return last_growth - t_end


def shedding_shares(*, sent: int, counts: dict[str, int]) -> dict[str, float]:
    """Share of what should have been recorded (a transaction, a request and a response message, each with headers and
    a body, per request sent) that is missing from ``counts``."""
    expected = {"transactions": sent, "messages": 2 * sent, "headers": 2 * sent, "bodies": 2 * sent}
    return {name: max(0.0, 1 - counts[name] / total) for name, total in expected.items()}


def url_pattern(base: str, *, cache_share: float) -> str:
    """Regex url for ``oha --rand-regex-url``: ``cache_share`` (in tenths) of the requests hit ten cacheable paths of the
    origin (``/cache/``), the others get a unique path (``/miss/``)."""
    cached = round(cache_share * 10)
    branches = ["cache/[0-9]"] * cached + ["miss/[0-9]{9}"] * (10 - cached)
    return f"{base}/({'|'.join(branches)})"
