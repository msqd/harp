# Benchmarks

Micro benchmarks (pyperf) measuring HARP's own code paths, to judge changes to the **overhead** it adds (see
`CONTEXT.md`).

```shell
make bench-micro                                   # bench/results/micro-<sha>.json
make bench-compare BASE=<file> CAND=<file>         # pyperf compare_to --table
make bench-noise                                   # same bench x5, spread between runs
```

Pass `BENCH_OPTIONS=--fast` for a quick check. Each result records git sha, `HARP_NATIVE`, CPU model and Python
build (`bench/metadata.py`). `bench/results/` is gitignored.

## Why outside the tests

Benchmarks were removed from the test suite in 0.9.0 because they made it unreliable
([changelog](../docs/changelogs/0.9.0.rst)). `bench/` is ignored by pytest and only runs on demand.

## Caveat

Laptop numbers validate the tooling only. Verdict runs happen on an external runner (#1168).

## Macro harness (overhead, startup)

End-to-end: HARP runs as a real server process between a load generator and an origin, all native and pinned on
disjoint P-cores with `taskset`. No docker needed.

```shell
make bench-macro PROFILE=bare|default              # bench/results/macro-<profile>-<sha>-<ts>.json
make bench-startup PROFILE=bare|default            # startup-<profile>-...json + raw -X importtime capture
make bench-macro PROFILE=bare BENCH_MACRO_OPTIONS="--rate 50 --duration 30 --warmup 5"
```

`overhead` runs `oha` at the same fixed open-loop rate (`-q`, `--latency-correction`) once against the origin and once
through HARP, and reports p50/p90/p99 for both plus the difference, and HARP's CPU per request
(utime+stime delta of the process over the measured window / requests completed). Any error invalidates the run. Overhead percentiles are differences of percentiles (proxied pN minus direct pN), not percentiles of per-request differences; CPU per request counts all HARP process CPU in the window, background storage work included.
`startup` measures exec to first proxied 200 (polled every 10 ms): `cold` is a fresh database, `warm` an already
migrated one (`default` only, `bare` has no database); median, min, max over `--reps` plus raw samples.

Options: `python -m bench.macro.run --help`. Rate defaults to 50 req/s: on the laptop `default` already queues at 200
req/s on one core, and the point is overhead at low load, not saturation.

Profiles (`bench/macro/profiles/`): `bare` = `proxy` + `http_client`; `default` = default applications, sqlite in a
temp dir, no rules. Endpoint and storage url are passed on the command line so ports stay parametric.

### Tools

- `oha` 1.16.0, `cargo install oha --locked --version 1.16.0`.
- `taskset` (util-linux).
- Origin: `bench/macro/origin/`, a ~40 line std-only Rust server (fixed body, keep-alive, thread per connection),
  built on first run with `cargo build --release`. Chosen because nginx was not installed here, it needs no download
  beyond the toolchain, and it is native and far cheaper than HARP. Body size is `--size` (default 1024 bytes).
  Another origin (nginx, go-httpbin, a container) plugs in through `--origin-cmd` / `BENCH_ORIGIN_CMD`, a command
  template with `{port}` and `{size}`.

### Pinning and metadata

Cores come from `/sys/devices/cpu_core/cpus` (P-cores of a hybrid cpu; all online cpus otherwise), handed out
disjointly: HARP 2 (`--harp-cores`), origin 1, load generator 1. Override with `--harp-cpus/--origin-cpus/--loadgen-cpus`.
Recorded in the result with the cpu governor of those cores (not changed: needs root), oha version, profile, rate,
duration and the origin description, next to `bench.metadata.collect()`.

HARP stdout/stderr are discarded during runs (terminal logging would be measured). CPU time is read from the pid
launched, HARP being a single process.
