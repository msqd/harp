"""Macro benchmark orchestration: overhead at a fixed open-loop rate, startup time, and load steps.

Run from the repo root through the Makefile (`make bench-macro`, `make bench-startup`, `make bench-load`), or:
`uv run --group bench python -m bench.macro.run overhead --profile bare`.

Processes (origin, HARP, oha) are native and pinned on disjoint cores. Nothing here needs docker.
"""

import argparse
import contextlib
import http.client
import json
import os
import shlex
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from bench import metadata
from bench.macro import measure
from harp.config.adapters import SERVERS as adapter_servers

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
RESULTS = ROOT / "bench" / "results"
ORIGIN_DIR = HERE / "origin"
ORIGIN_BIN = ORIGIN_DIR / "target" / "release" / "harp-bench-origin"
DEFAULT_ORIGIN_CMD = f"{ORIGIN_BIN} {{port}} {{size}}"
HARP_BIN = Path(sys.executable).parent / "harp-proxy"
PROFILES = {"bare", "default", "loaded"}
STORAGE_PROFILES = {"default", "loaded"}
CACHE_MIX_PROFILES = {"loaded"}
# The server comes from `harp server --server`; the client is httpx for now (more choices land with #1172).
SERVERS = adapter_servers
CLIENTS = ("httpx",)
HOST = "127.0.0.1"
METRICS_PATH = "/.prometheus/metrics"
BODY_BYTES = {"loaded": 16384}
DEFAULT_BODY_BYTES = 1024


# --- environment -----------------------------------------------------------------------------------------------------


def available_cores() -> tuple[list[int], bool]:
    """Performance cores of a hybrid cpu if the kernel exposes them, else every online cpu."""
    for path, hybrid in (("/sys/devices/cpu_core/cpus", True), ("/sys/devices/system/cpu/online", False)):
        with contextlib.suppress(OSError):
            return measure.parse_cpu_list(Path(path).read_text()), hybrid
    return list(range(os.cpu_count() or 1)), False


def governor(cpu: int) -> str:
    try:
        return Path(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor").read_text().strip()
    except OSError:
        return "unknown"


def resolve_cores(args) -> dict[str, list[int]]:
    available, hybrid = available_cores()
    explicit = {role: getattr(args, f"{role}_cpus") for role in ("harp", "origin", "loadgen")}
    if all(explicit.values()):
        cores = {role: measure.parse_cpu_list(value) for role, value in explicit.items()}
        used = [cpu for cpus in cores.values() for cpu in cpus]
        if len(used) != len(set(used)):
            sys.exit("pinning error: harp, origin and loadgen cpus must be disjoint")
        return cores
    return measure.assign_cores(available, harp=args.harp_cores, origin=1, loadgen=1)


def pinned(command: list[str], cpus: list[int]) -> list[str]:
    return ["taskset", "-c", measure.format_cpu_list(cpus), *command]


def oha_version() -> str:
    return subprocess.run(["oha", "--version"], capture_output=True, text=True, check=True).stdout.strip()


# --- processes -------------------------------------------------------------------------------------------------------


def ensure_origin_built(origin_cmd: str) -> None:
    if origin_cmd == DEFAULT_ORIGIN_CMD and not ORIGIN_BIN.exists():
        subprocess.run(["cargo", "build", "--release", "--manifest-path", str(ORIGIN_DIR / "Cargo.toml")], check=True)


def wait_port(port: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with contextlib.suppress(OSError), socket.create_connection((HOST, port), timeout=0.2):
            return
        time.sleep(0.01)
    raise TimeoutError(f"nothing listening on port {port}")


def get_ok(port: int) -> bool:
    try:
        conn = http.client.HTTPConnection(HOST, port, timeout=2)
        conn.request("GET", "/")
        response = conn.getresponse()
        response.read()
        conn.close()
        return response.status == 200
    except (OSError, http.client.HTTPException):
        return False


def wait_first_200(port: int, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if get_ok(port):
            return
        time.sleep(0.01)
    raise TimeoutError(f"no 200 from port {port} after {timeout}s")


@contextlib.contextmanager
def running(command: list[str], **kwargs):
    proc = subprocess.Popen(command, start_new_session=True, **kwargs)
    try:
        yield proc
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGINT)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()


def origin_process(args, cores):
    command = shlex.split(args.origin_cmd.format(port=args.origin_port, size=args.size))
    return running(pinned(command, cores["origin"]), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def harp_command(args, cores, workdir: Path, db: Path, importtime: bool = False) -> list[str]:
    python = [sys.executable, "-X", "importtime", str(HARP_BIN)] if importtime else [str(HARP_BIN)]
    command = [
        *python,
        "server",
        "--server",
        args.server,
        "-f",
        str(HERE / "profiles" / f"{args.profile}.yml"),
        "--endpoint",
        f"bench={args.harp_port}:http://{HOST}:{args.origin_port}/",
    ]
    if args.profile in STORAGE_PROFILES:
        command += ["--set", "storage.url", f"sqlite+aiosqlite:///{db}"]
    if getattr(args, "scrape_metrics", False):
        command += ["--enable", "metrics"]
    return pinned(command, cores["harp"])


def harp_process(args, cores, workdir: Path, db: Path, **kwargs):
    return running(
        harp_command(args, cores, workdir, db),
        cwd=workdir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **kwargs,
    )


# --- load ------------------------------------------------------------------------------------------------------------


def oha(args, cores, port: int, rate: int, seconds: float) -> dict:
    """Runs ``oha`` at a fixed open-loop rate against ``port`` and returns the parsed report."""
    command = [
        "oha",
        "--output-format",
        "json",
        "--no-tui",
        "--latency-correction",
        "-w",
        "-c",
        str(args.connections),
        "-q",
        str(rate),
        "-z",
        f"{seconds}s",
    ]
    if args.profile in CACHE_MIX_PROFILES and args.cache_share > 0:
        command += ["--rand-regex-url", measure.url_pattern(f"http://{HOST}:{port}", cache_share=args.cache_share)]
    else:
        command.append(f"http://{HOST}:{port}/")
    out = subprocess.run(pinned(command, cores["loadgen"]), capture_output=True, text=True, check=True).stdout
    return measure.parse_oha(json.loads(out))


def cpu_ticks(pid: int) -> int:
    return measure.parse_proc_stat_ticks(Path(f"/proc/{pid}/stat").read_text())


def peak_rss_kib(pid: int) -> int:
    return measure.parse_vm_hwm_kib(Path(f"/proc/{pid}/status").read_text())


def measured_run(args, cores, port: int, pid: int | None = None, rate=None, duration=None, warmup=None):
    """Warms up, then measures at the fixed rate. Returns the parsed oha report and harp cpu ticks over the window."""
    rate, duration, warmup = rate or args.rate, duration or args.duration, warmup or args.warmup
    warm = oha(args, cores, port, rate, warmup)
    before = cpu_ticks(pid) if pid else None
    report = oha(args, cores, port, rate, duration)
    after = cpu_ticks(pid) if pid else None
    report["sent_with_warmup"] = warm["sent"] + report["sent"]
    return report, None if pid is None else after - before


# --- storage: backlog, drain, shedding -------------------------------------------------------------------------------


def _marked(marker: str) -> str:
    return f"(SELECT count(*) FROM transactions WHERE instr(',' || markers || ',', ',{marker},') > 0)"


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


def db_counts(db: Path) -> dict[str, int] | None:
    """What HARP recorded so far, read from outside. None while the database is not readable yet."""
    try:
        with contextlib.closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)) as conn:
            return dict(zip(COUNT_NAMES, conn.execute(COUNTS_SQL).fetchone()))
    except sqlite3.Error:
        return None


def wait_settled(db: Path, *, quiet: float = 2.0, timeout: float = 120.0) -> tuple[list[tuple[float, int]], bool]:
    """Polls the recorded rows until they stop growing for ``quiet`` seconds. Returns the samples and a settled flag."""
    samples: list[tuple[float, int]] = []
    started = time.monotonic()
    last_change = started
    while time.monotonic() - started < timeout:
        counts = db_counts(db)
        now = time.monotonic()
        if counts is not None:
            total = counts["transactions"] + counts["messages"]
            if samples and total != samples[-1][1]:
                last_change = now
            samples.append((now, total))
        if now - last_change >= quiet and samples:
            return samples, True
        time.sleep(0.25)
    return samples, False


class Ledger:
    """What was sent to HARP against what its database holds (readiness probes excluded through a baseline)."""

    def __init__(self, db: Path):
        self.db = db
        self.sent = 0
        self.baseline = {name: 0 for name in COUNT_NAMES}

    def start(self) -> None:
        wait_settled(self.db)
        self.baseline = db_counts(self.db) or self.baseline

    def snapshot(self) -> dict:
        counts = db_counts(self.db) or {}
        recorded = {name: counts.get(name, 0) - self.baseline[name] for name in COUNT_NAMES}
        return {
            "sent": self.sent,
            "recorded": recorded,
            "shed_share": measure.shedding_shares(sent=self.sent, counts=recorded),
            "shed_markers": measure.shed_marker_report(recorded),
        }


class BacklogScraper:
    """Scrapes the backlog gauge of the metrics app twice a second while a step runs."""

    def __init__(self, port: int):
        self.port = port
        self.samples: list[int] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _scrape(self) -> None:
        try:
            conn = http.client.HTTPConnection(HOST, self.port, timeout=2)
            conn.request("GET", METRICS_PATH)
            backlog = measure.parse_backlog(conn.getresponse().read().decode())
            conn.close()
        except (OSError, http.client.HTTPException):
            return
        if backlog is not None:
            self.samples.append(backlog)

    def _run(self) -> None:
        while not self._stop.wait(0.5):
            self._scrape()

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()

    @property
    def peak(self) -> int | None:
        return max(self.samples) if self.samples else None


# --- commands --------------------------------------------------------------------------------------------------------


def common_metadata(args, cores) -> dict:
    available, hybrid = available_cores()
    used = [cpu for cpus in cores.values() for cpu in cpus]
    return {
        **metadata.collect(),
        "profile": args.profile,
        "cores": cores,
        "cores_source": "hybrid P-cores" if hybrid else "all online cpus (no hybrid topology found)",
        "governor": {str(cpu): governor(cpu) for cpu in used},
        "oha_version": oha_version(),
        "oha_connections": args.connections,
        "server": args.server,
        "client": args.client,
        "origin": {"command": args.origin_cmd, "port": args.origin_port, "body_bytes": args.size},
        "cache_share": args.cache_share if args.profile in CACHE_MIX_PROFILES else 0,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def write_result(name: str, result: dict) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    path = RESULTS / f"{name}-{result['git_sha']}-{stamp}.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return path


def overhead(args) -> int:
    cores = resolve_cores(args)
    ensure_origin_built(args.origin_cmd)
    with tempfile.TemporaryDirectory(prefix="harp-bench-") as tmp, origin_process(args, cores):
        wait_port(args.origin_port)
        direct, _ = measured_run(args, cores, args.origin_port)
        with harp_process(args, cores, Path(tmp), Path(tmp) / "harp.db") as harp:
            wait_first_200(args.harp_port)
            proxied, ticks = measured_run(args, cores, args.harp_port, pid=harp.pid)
    clk = os.sysconf("SC_CLK_TCK")
    cpu = measure.cpu_us_per_request(ticks=ticks, clock_ticks_per_second=clk, requests=proxied["requests"])
    result = {
        **common_metadata(args, cores),
        "rate": args.rate,
        "duration_s": args.duration,
        "warmup_s": args.warmup,
        **measure.assemble_overhead(direct, proxied, cpu_us_per_request=cpu),
    }
    path = write_result(f"macro-{args.profile}", result)
    summarize_overhead(result, path)
    return 0


def summarize_overhead(result: dict, path: Path) -> None:
    print(
        f"profile={result['profile']} rate={result['rate']}/s duration={result['duration_s']}s cores={result['cores']}"
    )
    print(f"{'ms':<10}{'p50':>9}{'p90':>9}{'p99':>9}")
    for label, values in (
        ("direct", result["direct"]["latency_ms"]),
        ("harp", result["proxied"]["latency_ms"]),
        ("overhead", result["overhead_ms"]),
    ):
        print(f"{label:<10}{values['p50']:>9.3f}{values['p90']:>9.3f}{values['p99']:>9.3f}")
    print(f"harp cpu: {result['harp_cpu_us_per_request']:.0f} us/request ({result['proxied']['requests']} requests)")
    print(f"-> {path}")


def startup_once(args, cores, workdir: Path, db: Path, importtime_file: Path | None = None) -> float:
    command = harp_command(args, cores, workdir, db, importtime=importtime_file is not None)
    stderr = importtime_file.open("w") if importtime_file else subprocess.DEVNULL
    started = time.perf_counter()
    with running(command, cwd=workdir, stdout=subprocess.DEVNULL, stderr=stderr):
        wait_first_200(args.harp_port)
        return time.perf_counter() - started


def startup(args) -> int:
    cores = resolve_cores(args)
    ensure_origin_built(args.origin_cmd)
    modes = ["cold", "warm"] if args.profile in STORAGE_PROFILES else ["cold"]  # bare has no database: nothing to warm
    timings: dict[str, list[float]] = {mode: [] for mode in modes}
    with tempfile.TemporaryDirectory(prefix="harp-bench-") as tmp, origin_process(args, cores):
        workdir = Path(tmp)
        wait_port(args.origin_port)
        for mode in modes:
            if mode == "warm":  # database migrated by a first, discarded start
                startup_once(args, cores, workdir, workdir / "warm.db")
            for i in range(args.reps):
                db = workdir / (f"cold-{i}.db" if mode == "cold" else "warm.db")
                timings[mode].append(startup_once(args, cores, workdir, db))
        RESULTS.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        importtime = RESULTS / f"startup-{args.profile}-importtime-{stamp}.txt"
        startup_once(args, cores, workdir, workdir / "importtime.db", importtime_file=importtime)
    result = {
        **common_metadata(args, cores),
        "reps": args.reps,
        "startup_s": {mode: measure.median_spread(values) | {"samples": values} for mode, values in timings.items()},
        "importtime_file": str(importtime.relative_to(ROOT)),
    }
    path = write_result(f"startup-{args.profile}", result)
    print(f"startup profile={args.profile} reps={args.reps} cores={cores}")
    for mode, spread in result["startup_s"].items():
        print(f"{mode:<6} median={spread['median']:.2f}s min={spread['min']:.2f}s max={spread['max']:.2f}s")
    print(f"-> {path}\n-> {importtime}")
    return 0


# --- load steps ------------------------------------------------------------------------------------------------------


def load_step(args, cores, harp_pid: int, ledger: Ledger | None, rate: int) -> dict:
    """One open-loop rate step through HARP: latency, errors, achieved rate, peak rss, backlog and shedding so far."""
    with BacklogScraper(args.harp_port) as scraper:
        warm = oha(args, cores, args.harp_port, rate, args.step_warmup)
        report = oha(args, cores, args.harp_port, rate, args.step_duration)
    step = {"rate": rate, **report, "peak_rss_kib": peak_rss_kib(harp_pid), "backlog_peak": scraper.peak}
    if ledger:
        ledger.sent += warm["sent"] + report["sent"]
        step["storage"] = ledger.snapshot()
    return step


def rerun(args, cores, harp_pid: int, ledger: Ledger | None, rate: int) -> dict:
    """Direct then proxied run at ``rate`` for the overhead there, after the storage queue is empty."""
    if ledger:
        wait_settled(ledger.db)
    direct, _ = measured_run(args, cores, args.origin_port, rate=rate)
    proxied, ticks = measured_run(args, cores, args.harp_port, pid=harp_pid, rate=rate)
    clk = os.sysconf("SC_CLK_TCK")
    result = {"rate": rate, "direct": direct, "proxied": proxied}
    try:
        cpu = measure.cpu_us_per_request(ticks=ticks, clock_ticks_per_second=clk, requests=proxied["requests"])
        result |= measure.assemble_overhead(direct, proxied, cpu_us_per_request=cpu)
    except ValueError as error:
        result["invalid"] = str(error)
    if ledger:
        ledger.sent += proxied["sent_with_warmup"]
        wait_settled(ledger.db)
        result["storage"] = ledger.snapshot()
    return result


def drain(ledger: Ledger) -> dict:
    t_end = time.monotonic()
    samples, settled = wait_settled(ledger.db)
    return {"seconds": measure.drain_seconds(samples, t_end=t_end), "settled": settled, **ledger.snapshot()}


def load(args) -> int:
    cores = resolve_cores(args)
    storage = args.profile in STORAGE_PROFILES
    args.scrape_metrics = storage and args.metrics
    ensure_origin_built(args.origin_cmd)
    steps: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="harp-bench-") as tmp, origin_process(args, cores):
        db = Path(tmp) / "harp.db"
        wait_port(args.origin_port)
        with harp_process(args, cores, Path(tmp), db) as harp:
            wait_first_200(args.harp_port)
            ledger = Ledger(db) if storage else None
            if ledger:
                ledger.start()
            for rate in args.rates:
                steps.append(load_step(args, cores, harp.pid, ledger, rate))
                print(summarize_step(steps[-1]), flush=True)
                if not measure.step_valid(steps[-1], base_p99=steps[0]["latency_ms"]["p99"]):
                    break
            saturation = measure.saturation_rate(steps)
            drained = drain(ledger) if ledger else None
            reruns = {}
            if saturation:
                for label, rate in measure.rerun_rates(saturation).items():
                    reruns[label] = rerun(args, cores, harp.pid, ledger, rate)
    result = {
        **common_metadata(args, cores),
        "rates": args.rates,
        "step_duration_s": args.step_duration,
        "step_warmup_s": args.step_warmup,
        "metrics_scraped": args.scrape_metrics,
        "steps": steps,
        "saturation_rate": saturation,
        "saturated": not measure.step_valid(steps[-1], base_p99=steps[0]["latency_ms"]["p99"]),
        "drain": drained,
        "reruns": reruns,
        "rerun_duration_s": args.duration,
    }
    path = write_result(f"load-{args.profile}", result)
    summarize_load(result, path)
    return 0


def summarize_step(step: dict) -> str:
    latency = step["latency_ms"]
    line = (
        f"rate={step['rate']:>5}/s achieved={step['requests_per_sec']:>7.1f}/s p50={latency['p50']:>8.2f} "
        f"p90={latency['p90']:>8.2f} p99={latency['p99']:>9.2f} errors={step['errors']} "
        f"rss={step['peak_rss_kib'] / 1024:.0f}MiB backlog={step['backlog_peak']}"
    )
    if "storage" in step:
        shed = step["storage"]["shed_share"]
        line += " shed tx/hdr/body=" + "/".join(f"{shed[k]:.0%}" for k in ("transactions", "headers", "bodies"))
    return line


def summarize_load(result: dict, path: Path) -> None:
    print(f"load profile={result['profile']} server={result['server']} client={result['client']} ms")
    for step in result["steps"]:
        print(summarize_step(step))
    saturation = result["saturation_rate"]
    bound = "" if result["saturated"] else " (lower bound: no step saturated)"
    print(f"saturation rate: {saturation}/s{bound}")
    if result["drain"]:
        drain = result["drain"]
        print(
            f"drain: {drain['seconds']:.1f}s settled={drain['settled']} recorded={drain['recorded']} of {drain['sent']}"
        )
    for label, rerun_ in result["reruns"].items():
        if "invalid" in rerun_:
            print(f"{label} of saturation ({rerun_['rate']}/s): invalid, {rerun_['invalid']}")
            continue
        o = rerun_["overhead_ms"]
        print(
            f"{label} of saturation ({rerun_['rate']}/s): overhead p50={o['p50']:.3f} p90={o['p90']:.3f} "
            f"p99={o['p99']:.3f} ms, cpu {rerun_['harp_cpu_us_per_request']:.0f} us/request"
        )
    print(f"-> {path}")


# --- cli -------------------------------------------------------------------------------------------------------------


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("command", choices=["overhead", "startup", "load"])
    p.add_argument("--profile", choices=sorted(PROFILES), default="bare")
    p.add_argument("--rate", type=int, default=50, help="requests per second, open loop (default: %(default)s)")
    p.add_argument("--duration", type=float, default=30, help="measured seconds (default: %(default)s)")
    p.add_argument("--warmup", type=float, default=5, help="warmup seconds, same rate (default: %(default)s)")
    p.add_argument("--connections", type=int, help="oha connections (default: 8, 32 for load)")
    p.add_argument("--size", type=int, help="origin response body bytes (default: 1024, 16384 for loaded)")
    p.add_argument(
        "--rates",
        type=lambda text: [int(rate) for rate in text.split(",")],
        default=[25, 50, 100, 200, 400, 800, 1600],
        help="load: ascending rate steps in req/s, stops after the first saturated one (default: 25,...,1600)",
    )
    p.add_argument(
        "--step-duration", type=float, default=10, help="load: measured seconds per step (default: %(default)s)"
    )
    p.add_argument("--step-warmup", type=float, default=3, help="load: warmup seconds per step (default: %(default)s)")
    p.add_argument(
        "--cache-share",
        type=float,
        default=0.5,
        help="loaded: share of requests on cacheable paths, in tenths (default: %(default)s)",
    )
    p.add_argument(
        "--metrics",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="load, storage profiles: enable the metrics app to scrape the queue backlog gauge (default: on)",
    )
    p.add_argument("--server", choices=SERVERS, default=SERVERS[0], help="HARP server adapter (default: %(default)s)")
    p.add_argument("--client", choices=CLIENTS, default=CLIENTS[0], help="HARP http client (default: %(default)s)")
    p.add_argument("--reps", type=int, default=5, help="startup repetitions (default: %(default)s)")
    p.add_argument("--harp-port", type=int, default=4000)
    p.add_argument("--origin-port", type=int, default=9100)
    p.add_argument(
        "--origin-cmd",
        default=os.environ.get("BENCH_ORIGIN_CMD", DEFAULT_ORIGIN_CMD),
        help="origin command template with {port} and {size} (env BENCH_ORIGIN_CMD)",
    )
    p.add_argument("--harp-cores", type=int, default=2, help="P-cores given to harp when auto-assigning")
    for role in ("harp", "origin", "loadgen"):
        p.add_argument(f"--{role}-cpus", help=f"explicit cpu list for {role}, e.g. 0,1 (all three roles to override)")
    return p


def main() -> int:
    args = parser().parse_args()
    for tool in ("taskset", "oha"):
        if not shutil.which(tool):
            sys.exit(f"missing tool: {tool} (see bench/README.md)")
    args.size = args.size or BODY_BYTES.get(args.profile, DEFAULT_BODY_BYTES)
    args.connections = args.connections or (32 if args.command == "load" else 8)
    return {"overhead": overhead, "startup": startup, "load": load}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
