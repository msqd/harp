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

## Macro harness (overhead, startup, load)

End-to-end: HARP runs as a real server process between a load generator and an origin, all native and pinned on
disjoint P-cores with `taskset`. No docker needed.

```shell
make bench-macro PROFILE=bare|default|loaded       # bench/results/macro-<profile>-<sha>-<ts>.json
make bench-startup PROFILE=bare|default|loaded     # startup-<profile>-...json + raw -X importtime capture
make bench-load PROFILE=bare|default|loaded        # load-<profile>-<sha>-<ts>.json
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
temp dir, no rules; `loaded` = `default` + a ruleset (five patterns on the `bench` endpoint, two with a small script),
a mix of cache hits and misses and a 16 KiB body (`--size`). Endpoint and storage url are passed on the command line so ports stay parametric.

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

### Load steps (`bench-load`)

Open-loop rate steps through HARP (`--rates 25,50,100,200,400,800,1600`, `--step-duration`, `--step-warmup`, 32
connections), in one HARP process, stopping after the first invalid step. Per step: p50/p90/p99, errors, achieved
rate, peak RSS (`VmHWM` of the HARP pid at the end of the step), backlog and shedding.

- **Saturation rate**: highest step before the first one with an error or a p99 of at least twice the p99 of the lowest
  step. `saturated: false` in the result means no step failed, so the rate is only a lower bound.
- **Overhead at 50% and 80% of saturation**: once the steps and the drain are done, direct then proxied runs at
  those two rates (`--duration`/`--warmup`, as in `bench-macro`), after the storage has settled.
- **Backlog**: the `metrics` application is enabled (`--no-metrics` to disable), and `async_worker_queue_backlog` is
  scraped from `/.prometheus/metrics` twice a second; `backlog_peak` is the highest value of the step. The gauge is
  only refreshed by the worker every 5 s and not at all while the queue is idle, and the metrics middleware adds a
  little latency of its own (recorded as `metrics_scraped`): treat it as an indication, the database is the reference.
- **Drain**: seconds from the end of the last step until the rows of `transactions` and `messages` stop growing
  (unchanged for 2 s), read from the sqlite file.
- **Shedding share**: per step and after the drain (`drain`, also after each rerun), what the database holds against
  what was sent (readiness probes excluded): transactions against requests, messages, headers and bodies against two per
  request. The per-step figure is read at the end of the step, with the queue not yet drained, so it overestimates;
  the figure after the drain is the reliable one. Headers and bodies are counted per message (column set), never per
  distinct blob: empty bodies all share one blob id. The `shed-messages`/`shed-headers`/`shed-bodies` transaction markers
  set by the worker are counted too (`shed_markers`: marked against really missing, on recorded transactions, they must
  agree); transactions shed entirely leave no row and only show in the missing-vs-sent share. `cache_hits` counts transactions flagged `x_cached`, to check the
  hit share of `loaded`.
- **Mixed hits/misses** (`loaded`): the origin answers `/cache/*` with `Cache-Control: max-age=60`; `oha
  --rand-regex-url` picks ten cacheable paths for `--cache-share` (default 0.5, in tenths) of the requests and a unique
  `/miss/*` path for the others.
- **Server / client**: `--server hypercorn` and `--client httpx` are recorded in the result. HARP has no switch for
  either today (the server adapter is hardcoded in `harp/__init__.py`), so these are the only accepted values until the
  adapters of #1171/#1172 land.
