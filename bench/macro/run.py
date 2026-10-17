"""Macro benchmark orchestration: overhead at a fixed open-loop rate, and startup time.

Run from the repo root through the Makefile (`make bench-macro`, `make bench-startup`), or:
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
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from bench import metadata
from bench.macro import measure

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
RESULTS = ROOT / "bench" / "results"
ORIGIN_DIR = HERE / "origin"
ORIGIN_BIN = ORIGIN_DIR / "target" / "release" / "harp-bench-origin"
DEFAULT_ORIGIN_CMD = f"{ORIGIN_BIN} {{port}} {{size}}"
HARP_BIN = Path(sys.executable).parent / "harp-proxy"
PROFILES = {"bare", "default"}
HOST = "127.0.0.1"


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
        "-f",
        str(HERE / "profiles" / f"{args.profile}.yml"),
        "--endpoint",
        f"bench={args.harp_port}:http://{HOST}:{args.origin_port}/",
    ]
    if args.profile == "default":
        command += ["--set", "storage.url", f"sqlite+aiosqlite:///{db}"]
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


def oha(args, cores, url: str, seconds: float) -> dict:
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
        str(args.rate),
        "-z",
        f"{seconds}s",
        url,
    ]
    out = subprocess.run(pinned(command, cores["loadgen"]), capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def cpu_ticks(pid: int) -> int:
    return measure.parse_proc_stat_ticks(Path(f"/proc/{pid}/stat").read_text())


def measured_run(args, cores, port: int, pid: int | None = None) -> tuple[dict, int | None]:
    """Warms up, then measures at the fixed rate. Returns the parsed oha report and harp cpu ticks over the window."""
    url = f"http://{HOST}:{port}/"
    oha(args, cores, url, args.warmup)
    before = cpu_ticks(pid) if pid else None
    report = measure.parse_oha(oha(args, cores, url, args.duration))
    after = cpu_ticks(pid) if pid else None
    return report, None if pid is None else after - before


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
        "origin": {"command": args.origin_cmd, "port": args.origin_port, "body_bytes": args.size},
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
    modes = ["cold", "warm"] if args.profile == "default" else ["cold"]  # bare has no database: nothing to warm
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


# --- cli -------------------------------------------------------------------------------------------------------------


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("command", choices=["overhead", "startup"])
    p.add_argument("--profile", choices=sorted(PROFILES), default="bare")
    p.add_argument("--rate", type=int, default=50, help="requests per second, open loop (default: %(default)s)")
    p.add_argument("--duration", type=float, default=30, help="measured seconds (default: %(default)s)")
    p.add_argument("--warmup", type=float, default=5, help="warmup seconds, same rate (default: %(default)s)")
    p.add_argument("--connections", type=int, default=8, help="oha connections (default: %(default)s)")
    p.add_argument("--size", type=int, default=1024, help="origin response body bytes (default: %(default)s)")
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
    return {"overhead": overhead, "startup": startup}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
