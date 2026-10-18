"""Pure logic of the macro harness: parsing, core assignment, arithmetic, result assembly. No process, no I/O."""

import re
import statistics
from typing import Iterable, Mapping, Optional

from sqlalchemy import make_url


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


def usable_cores(affinity: Iterable[int], performance_cores: Optional[list[int]]) -> list[int]:
    """The cores the harness may use: its process affinity, narrowed to the performance cores of a hybrid cpu."""
    allowed = sorted(set(affinity))
    if performance_cores:
        narrowed = [cpu for cpu in allowed if cpu in performance_cores]
        if narrowed:
            return narrowed
    return allowed


def assign_harness_cores(available: list[int], *, harp: int) -> dict[str, list[int]]:
    """
    Cores for harp, origin and load generator, in order. With one spare core only, the origin and the load generator
    share it; with more, every role has its own and the extra cores stay unused.
    """
    if len(available) < harp + 1:
        raise ValueError(f"not enough cores: need {harp + 1}, have {len(available)}")
    harp_cores, rest = available[:harp], available[harp:]
    if len(rest) == 1:
        return {"harp": harp_cores, "origin": rest[:1], "loadgen": rest[:1]}
    return {"harp": harp_cores, "origin": rest[:1], "loadgen": rest[1:2]}


def shared_roles(cores: dict[str, list[int]]) -> list[str]:
    """The roles that run on a core another role also uses, in the order of ``cores``."""
    owners: dict[int, list[str]] = {}
    for role, cpus in cores.items():
        for cpu in cpus:
            owners.setdefault(cpu, []).append(role)
    shared = [role for roles in owners.values() if len(roles) > 1 for role in roles]
    return [role for role in cores if role in shared]


DATABASE_URL_ENV = "BENCH_DATABASE_URL"


def require_database_url(env: Mapping[str, str], *, stores: bool) -> Optional[str]:
    """The PostgreSQL url the recording profiles use; refused when unset or not PostgreSQL. None if nothing is stored."""
    if not stores:
        return None
    url = env.get(DATABASE_URL_ENV, "")
    if not url:
        raise ValueError(
            f"{DATABASE_URL_ENV} is not set: profiles that record need a PostgreSQL database, "
            "e.g. postgresql+asyncpg://bench@127.0.0.1:5432/bench"
        )
    if not url.startswith("postgresql"):
        raise ValueError(
            f"{DATABASE_URL_ENV} must be a PostgreSQL url (postgresql+asyncpg://...), got {url.split(':')[0]}"
        )
    return url


def asyncpg_arguments(url: str) -> dict:
    """``asyncpg.connect`` keyword arguments for a SQLAlchemy url (``host`` may be a unix socket directory)."""
    parsed = make_url(url)
    arguments = {"user": parsed.username, "password": parsed.password, "database": parsed.database}
    arguments["host"] = parsed.query.get("host") or parsed.host
    arguments["port"] = parsed.port
    return {key: value for key, value in arguments.items() if value is not None}


def _marked(marker: str) -> str:
    return f"(SELECT count(*) FROM transactions WHERE position(',{marker},' in ',' || markers || ',') > 0)"


# `headers`/`bodies` count messages whose column is set, not distinct blobs: empty bodies all share one blob id.
# `missing_*` count recorded transactions, to compare with the `shed-*` markers set on them.
COUNTS_SQL = f"""
SELECT
  (SELECT count(*) FROM transactions),
  (SELECT count(*) FROM messages),
  (SELECT count(*) FROM messages WHERE headers IS NOT NULL),
  (SELECT count(*) FROM messages WHERE body IS NOT NULL),
  (SELECT count(*) FROM transactions WHERE x_cached = 'true'),
  {_marked("shed-messages")},
  {_marked("shed-headers")},
  {_marked("shed-bodies")},
  (SELECT count(*) FROM transactions t WHERE (SELECT count(*) FROM messages WHERE transaction_id = t.id) < 2),
  (SELECT count(DISTINCT transaction_id) FROM messages WHERE headers IS NULL),
  (SELECT count(DISTINCT transaction_id) FROM messages WHERE body IS NULL)
"""
COUNT_NAMES = (
    "transactions",
    "messages",
    "headers",
    "bodies",
    "cache_hits",
    "marked_messages",
    "marked_headers",
    "marked_bodies",
    "missing_messages",
    "missing_headers",
    "missing_bodies",
)


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


def shed_marker_report(counts: dict[str, int]) -> dict[str, dict]:
    """Recorded transactions flagged ``shed-*`` by the storage worker against recorded transactions that really miss a
    message, headers or body. They must agree; transactions shed entirely appear in neither."""
    return {
        kind: {
            "marked": counts[f"marked_{kind}"],
            "missing": counts[f"missing_{kind}"],
            "agree": counts[f"marked_{kind}"] == counts[f"missing_{kind}"],
        }
        for kind in ("messages", "headers", "bodies")
    }
