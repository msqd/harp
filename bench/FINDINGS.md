# Findings

Rules (milestone explore/extensions): each candidate declares its target metric up front; native code must gain ≥15%
on it, net of the best adopt-native option, against the best reasonable Python, median of ≥5 runs outside the spread,
with no regression elsewhere. Laptop numbers validate tooling only; verdicts need the external runner (#1168). Recording profiles (`default`, `loaded`) use PostgreSQL.

## Status

| Candidate | Option | Verdict | Why |
|---|---|---|---|
| ASGI kernel | own Rust | **rejected** | ~100 µs of `await` glue; every hop calls back into Python controllers and listeners |
| Config parsing | own Rust | **rejected** | startup only, already pydantic-core + libyaml; dwarfed by imports and migrations |
| Rules, headers, path regex, cache key, dashboard | own Rust | **rejected** | microseconds of C-backed work, or DB-bound |
| Blob ID | own Rust | **no perf case** | toolchain spike only: 1.2–1.5× on small bodies (call overhead), slower than OpenSSL at 5 MB |
| Cache entry (de)serialisation | Python fix | **done** | libyaml (#1176, #1186) |
| Blob hashing on the request path | Python fix | **done** | no copy, off-loop above 64 KiB (#1177, #1187) |
| Dispatch logging | Python fix | **done** | `debug` (#1184, #1188) |
| SQLite storage | Python fix | **done** | WAL + busy_timeout (#1152, #1206) |
| ASGI server (hypercorn) | adopt | **keep hypercorn, uvloop by default** | verdict run: best on `default` is uvicorn -11% CPU, under the bar (and no h2c); hypercorn+uvloop -7%, default with aiohttp (#1362) |
| Upstream client (httpx transport) | adopt | **aiohttp by default** | verdict run on `bare`: aiohttp -16% CPU, pyreqwest ceiling -18 to -19%. No own Rust: the ceiling is 3% under aiohttp. Default with uvloop (#1362), compatibility review #1363 |
| Storage write pipeline | Python design | **write once: done (-48.9 % CPU)**, batching next | 55.6% of `default` CPU; ADR-0006, #1365 merged, #1366, #1367 |

## Verdict runs

Remote dedicated VM: 4 physical cores, SMT off (Xeon Platinum 8488C), HARP on 2 cores, origin and load generator sharing
the third, PostgreSQL 17 alone on the fourth. `explore/extensions` at `b240b57b`, 50 req/s open loop, 30 s measured
after 5 s warmup, 0 errors (any non-200 counts as one) in every run below.

### Noise gate

Same build, 5 runs per profile, on two machines.

| Profile | Machine A: CPU/req (spread) | Machine B: CPU/req (spread) | A vs B |
|---|---|---|---|
| `bare` | 1467 µs (1.8 %) | 1300 µs (2.6 %) | -11 % |
| `default` | 7460 µs (1.6 %) | 6607 µs (1.6 %) | -11 % |

- Within a machine, CPU/request, p90 and p99 stay within 2–4 %: a 15 % bar is unambiguous.
- Across machines of the same type there is a ~11 % offset. **A verdict only compares variants interleaved on one
  machine** (round-robin, 5 rounds); a campaign is never compared with another.
- `default` and `loaded` p50 can be bimodal on some machines (12–19 % spread, p90 stable): judge them on CPU and
  p90/p99.
- Micro (`bench-noise`, blob id): ≤ 2 % across 5 runs.

### Baseline

| Profile | CPU/req | Overhead p50 / p90 / p99 (ms) | Cold startup |
|---|---|---|---|
| `bare` | 1280 µs | 1.08 / 1.10 / 1.56 | 0.55 s |
| `default` | 6547 µs | 2.54 / 2.63 / 3.05 | 0.64 s |
| `loaded` | 7033 µs | 3.89 / 4.07 / 4.95 | 0.64 s |

`default` rate steps: p99 3.5–4.7 ms and storage backlog ≤ 7 up to 100 req/s; at 200 req/s p99 20 ms, backlog 3631,
1880 messages shed (all marked), drained in 3.2 s. Saturation sits between 100 and 200 req/s and is storage-bound:
recording costs ~5× the proxying itself.

### ASGI servers (interleaved)

| Server | `bare` CPU/req | `default` CPU/req | `default` p50 / p99 (ms) |
|---|---|---|---|
| hypercorn | 1280 µs | 6620 µs | 2.55 / 3.09 |
| hypercorn+uvloop | -4.7 % | -7.2 % | 2.50 / 3.00 |
| uvicorn | -21.9 % | -11.1 % | 2.41 / 2.93 |
| granian | -17.7 % | -1.1 % | 2.60 / 3.37 |

Ranges do not overlap, but nothing clears 15 % on `default`, the verdict profile. hypercorn stays. uvicorn is rejected
(under the bar, no h2c, two workarounds). hypercorn+uvloop is the one alternative worth carrying.

### HTTP transports (interleaved, `bare`)

| Transport | 50 req/s CPU/req | 200 req/s CPU/req | p50 / p99 at 50 req/s (ms) |
|---|---|---|---|
| httpx | 1287 µs | 1247 µs | 1.08 / 1.56 |
| aiohttp | -15.5 % | -16.3 % | 0.88 / 1.42 |
| pyreqwest (ceiling, non-conforming) | -18.1 % | -19.0 % | 0.85 / 1.35 |

aiohttp saves ~200 µs and ~0.2 ms of p50 per request, conforming (no divergence in the suite). On `default` that is
~3 % of 6.6 ms: under the bar on the verdict profile, worth it as an opt-in for proxy-only deployments. The Rust ceiling
beats aiohttp by 3 %, far from the 15 % that would justify an own hyper transport: **no own Rust on the client**.

### Default stack (interleaved, 5 rounds)

| Stack | `default` CPU/req | `default` p99 overhead | `bare` CPU/req |
|---|---|---|---|
| hypercorn + httpx | 7713 µs | 3.98 ms | 1500 µs |
| hypercorn+uvloop + httpx | -7.0 % | 3.78 ms | -5.8 % |
| hypercorn + aiohttp | -5.1 % | 3.39 ms | -13.8 % |
| hypercorn+uvloop + aiohttp | **-10.3 %** | **3.33 ms** | **-18.2 %** |

The gains add up only in part (about -12 % expected, -10.3 % measured). Under the bar on `default`, but both are
adoptions with no code to own: they become the defaults (#1362). Absolute numbers differ from the baseline table
because this ran on another VM; only the interleaved ratios compare.

### Where `default` CPU goes (py-spy, 90 s at 50 req/s, hypercorn + httpx)

| Part | Share of HARP samples |
|---|---|
| Recording (storage worker, SQLAlchemy, asyncpg) | 55.6 % |
| Event loop and socket I/O | 20.0 % |
| Kernel and proxy controller | 6.9 % |
| HTTP cache (hishel) | 5.2 % |
| Imports at startup | 4.8 % |
| hypercorn and h11 | 3.9 % |
| Upstream client | 3.5 % |

Inside recording, 58 % of samples end in SQLAlchemy Python code (cache keys, compilation, ORM unit of work,
greenlets), 17 % in asyncpg, 12 % in asyncio. Each transaction costs about eight committed round trips:
transaction insert, two message inserts, four blob puts, transaction update. With uvloop, 28 % of samples land in
the loop's compiled code, which py-spy cannot split; recording stays the largest part.

### Saturation on `default` (rates 50 to 250 req/s, 20 s steps, 2 rounds each)

| Stack | Records everything up to | Bodies shed from | p99 latency at 250 req/s | Peak RSS |
|---|---|---|---|---|
| hypercorn + httpx | 50 req/s | 100 req/s | 21 to 31 ms | 113 to 126 MiB |
| hypercorn+uvloop + aiohttp | 100 req/s | 125 req/s | 28 to 37 ms | 120 to 126 MiB |

The proxy serves 250 req/s with no error and a flat p50 on both stacks: recording sets the limit. Shedding bounds
the backlog, so RSS stays flat. In some steps one message is missing without its marker (#1367 checks it).

### Write once per transaction (#1365, interleaved, 5 rounds)

Two commits on one VM, alternating: `explore/extensions` at `b2d39dd4` (base) and #1365 at `717dd7ad`. Both sides ran
hypercorn on the asyncio loop with the aiohttp transport (the harness labels it httpx, #1374).

| | base | write once |
|---|---|---|
| `default` CPU/req at 50 req/s | 6487 µs | **3313 µs (-48.9 %)** |
| overhead p50 / p99 at 50 req/s | 2.35 / 3.09 ms | 2.32 / 3.11 ms |
| records everything up to | 100 req/s | **250 req/s** |
| proxy p99 at 200 req/s | 9.92 ms | 3.22 ms |
| peak RSS under load | 116 to 121 MiB | 116 to 120 MiB |

Recording drops from about eight committed round trips per transaction to one database transaction. At 300 req/s it
sheds bodies again (backlog 669, p99 29 ms): batching (#1366) is the next step.

### What this leaves

With storage on, the proxy path is no longer where the cost is: what `default` adds over `bare` (recording to PostgreSQL first) is ~80 % of CPU/request on
`default` and sets saturation. The next candidate is the storage write pipeline (batching, fewer round trips), in
Python first: ADR-0006.

## Upstream client matrix (#1172)

Target metric: HARP CPU per request on `bare` (all of the process, tokio threads included). The layer profile of #1171
puts the client stack at ~35% of it. HARP pinned on cpus 0-1, origin 2, loadgen 3, 20 s runs, alternating transports,
laptop with other tenants (load average 3-17): ranges overlap, read as ±10%. Verdicts wait for #1168.

The seam is the httpx `AsyncBaseTransport` (`http_client.transport.type`, full class path, `--transport` in the
harness); the httpx client, `Request` and `Response` stay, so hishel and the filters are untouched. Transports:
httpx's own (httpcore + h11), aiohttp, pyreqwest (reqwest/hyper in Rust). All three run the same conformance suite
(`harp_apps/http_client/tests/test_transport_conformance.py`).

CPU per request, median of 5 alternating runs (3 for `default` and `loaded`), overhead rate 50 req/s unless noted:

| Profile | httpx | aiohttp | pyreqwest |
|---|---|---|---|
| `bare` | 2900 µs | 2870 µs (-1%) | 2710 µs (-7%) |
| `bare`, 200 req/s | 2430 µs | 2230 µs (-8%) | 2265 µs (-7%) |
| `default` | 13730 µs | 13060 µs (-5%) | 12500 µs (-9%) |
| `loaded` | 15350 µs | 15310 µs | 15180 µs |

Overhead p50/p90/p99 are the same within noise (`bare` 50 req/s: 2.6-3.4 ms p50 for all three). The ranges overlap on
every row but `bare` at 200 req/s (httpx 2300-2780, aiohttp 2150-2425, pyreqwest 2145-2362).

Transport alone, in-process against the origin (3000 sequential requests, CPU of the whole process, 3 runs): httpx
~215 µs, aiohttp ~93 µs, pyreqwest ~85 µs. Swapping the transport can therefore save ~0.12-0.13 ms per request, about
5% of `bare`; the rest of the client cost sits above the transport, in `httpx.Client` itself (request building,
response objects, event hooks), which no transport reaches.

Correction: an earlier ceiling measurement (pyreqwest at -23% vs aiohttp) was void. The throwaway transport raised on
every request (a float where reqwest wants a `timedelta`), HARP answered 500s quickly, and the script did not check
statuses. The harness above invalidates a run on any non-200.

What the transports change or break (the suite lists these as declared divergences, strict xfail):
- aiohttp: none found. `retries` > 0, `limits.max_keepalive_connections` and a non-bool, non-`SSLContext` `verify` are
  refused at startup; it keeps its own DNS cache.
- pyreqwest: hyper's header map groups values by name and changes case (request names are title-cased, response names
  lower-cased): order across names, interleaving of duplicates and casing are lost; it adds `Accept: */*` and a
  `User-Agent` when absent; a timeout waiting for the response head surfaces as a connect timeout; a peer hanging up
  without answering is recognised by message. `retries` > 0 and a non-bool `verify` are refused. One reqwest client per
  distinct timeout triple, since httpx timeouts are per request and reqwest's per client.
- a startup flake (`no 200 after 60 s`) hit 3 of 30 early harness runs on httpx, not reproducible, unrelated.

Reading against the rule (≥15% net of the best adopt-native option, on the declared metric): no transport gets near
it. aiohttp is the adopt-native option and gives 1-8% on `bare`; the Rust client is no better than aiohttp (85 vs
93 µs of transport CPU, -7% vs -1/-8% end to end), costs header fidelity, and needs an extra and an unstable API. There
is no case for own Rust on this seam.

Strict header fidelity is required, so pyreqwest fails the contract and stays a measurement ceiling only (non-conforming,
benchmark use, never to ship). An own Rust transport (hyper with `preserve_header_case` and an ordered header map) is
the only native path for the client, and it is not started: it is built only if the verdict run on the external runner
(#1168) shows the pyreqwest ceiling still beating aiohttp by ≥15% CPU/request on `bare`, since an own hyper transport
cannot beat that ceiling by much. On the laptop it does not (-7% vs aiohttp's -1 to -8%).

Provisional recommendation, pending #1168: keep httpx the default; aiohttp is a safe opt-in (already a dependency, no
divergence, ~5-8% on the proxy path); pyreqwest only as the ceiling. If client cost still matters, the lever is the
httpx client layer above the transport, not the transport. `default` and `loaded` do not move: storage dominates.

## SQLite lock contention (#1169)

With cache + storage on a file-backed SQLite database in rollback-journal mode, the cache's blob reads waited on
locks held by the storage writers. The event loop was idle (~60% in `select`), and the time was spent in aiosqlite
threads. On `default` at 50 req/s, overhead p90 was 1.1–2.2 s and storage recorded ~13% of transactions under load.
With WAL: overhead p90 6.6–7.8 ms and 100% recorded (laptop, 3 alternating runs each). Until this fix, the `default`
profile measured lock contention, not HARP. Any baseline recorded before the fix is void.

## Next lead: storage cost per transaction

After WAL, `default` costs ~11 ms of HARP CPU per transaction vs ~4 ms on `bare`, saturates around 100 req/s, and sheds
bodies from that rate on (laptop). The difference is the storage pipeline: SQLAlchemy ORM writes through one consumer
queue. That is ORM and database work, not Rust material; batching writes or more than one consumer are the levers to
measure first.

## Toolchain spike: blob ID

Issue #1174. Rust `blob_id(data: bytes, content_type: str | None) -> str` (hex sha1 of `content_type`, `\n`, `data`),
PyO3 0.30 abi3-py313, `sha1` 0.11 crate. **No performance claim**: hashlib is already OpenSSL. Laptop numbers validate the
tooling only (#1168 for verdicts). Wheels built with maturin 1.15, cargo 1.97, Linux x86_64, warm cargo registry.

### Implementation

- Boundary: Python does the `;` split and `ensure_bytes`, Rust only hashes. `&[u8]` is borrowed from the `bytes` object
  (no copy); `py.detach` (GIL released) from 64 KiB, below which the release costs more than the hash.
- `Blob.from_data` resolves `select("blob_id", blob_id_python)` once at import. `HARP_NATIVE=blob_id` without the
  extension still fails hard (`NativeUnavailableError`).
- **sha1 crate over `ring`**: pure Rust, no C compiler or perlasm, so the zig/musl/windows/macOS cross builds below need
  nothing but rustup targets; uses SHA-NI/ARMv8 when the CPU has them (`cpufeatures`). `ring` ships its own asm (needs
  `cc`), and flags SHA-1 "legacy use only". Cost: on x86 the 5 MB case is slower than OpenSSL (see micro).
- Shim looks up `harp._native._core` then `harp_native` (`CORE_MODULES`).
- Parity tests (random sizes 0..5 MB, None/""/str/unicode content types, 64 KiB threshold edges, lone surrogate raising
  `UnicodeEncodeError` like Python) skip when no extension is built.
- Mutants killed by the parity tests (each rebuilt and run): dropped `\n`; content type not hashed; data hashed before
  content type; `None` hashed as `"none"`; uppercase hex; large-body (GIL-released) path hashing `data[..len-1]`;
  large-body path ignoring the content type. 7/7 killed.

### Layouts

| | A: `harp-proxy-native` in `native/` | B: harp-proxy built by maturin |
|---|---|---|
| Module | **`harp_native`** (top level). `harp._native._core` injected from another distribution works for installed wheels but is invisible to editable harp-proxy (`uv sync`): the editable path wins, `site-packages/harp/` has no `__init__.py`. Verified: `ModuleNotFoundError` | `harp._native._core` (in tree, `maturin develop`/editable writes the `.so` into `harp/_native/`) |
| Build | `cd native && maturin build --release` | `maturin build --release` at the root (`build-backend = "maturin"`) |
| Clean wheel build | 7.5 s (19 s with cold crate download) | 4.9 s (hatch wheel: 0.4 s) |
| Wheel size | 184 KB (.so 346 KB) | 431 KB (hatch wheel: 247 KB, `py3-none-any`) |
| sdist | 3 KB (Cargo + src) | 2.5 MB, 965 files (hatch sdist: 316 KB); no `harp_apps/dashboard/frontend` or tests exclusion parity |
| sdist install, no cargo, PATH without Rust | needs a compile only where no wheel exists; only for users who asked for `[native]` | **every** harp-proxy install without a matching wheel compiles. Tried with PATH stripped and a fake `$HOME`: maturin bootstraps rustup itself, 31 s, works online, fails offline |
| Python surface | unchanged `py3-none-any` harp-proxy | harp-proxy becomes `cp313-abi3-<platform>`: no universal wheel; Docker images and the `ls dist/*.whl` in `bin/build_wheel` become per-arch |
| Contributors, `uv sync` | unchanged (0.7 s). `uv sync --extra native` builds it: +6 s with cargo | every `uv sync` and every CI job (9 `uv sync`) builds Rust: +6 s with cargo; without cargo, 43 s bootstrap (venv + rustup) |
| Lock | extra needs `[tool.uv.sources] harp-proxy-native = { path = "native" }`, else `uv lock` fails until the dist is on PyPI. Source ignored by pip | none |
| Existing build | hatchling untouched | `[tool.hatch.*]` include/exclude/force-include rewritten in maturin globs; cookiecutter `tests/` re-include (hatch `!` negation) **not reproducible**: 2 files lost from the wheel; 7 tests fail (`tests/test_wheel_packaging.py`, `tests/test_declared_dependencies.py` call hatchling's builder) |
| Dockerfile / Dockerfile.pypi | `pip install "harp-proxy[...,native]"`: manylinux/musllinux wheel, no toolchain; `COPY dist/*.whl` unchanged for the pure wheel (native wheel copied alongside) | `python:slim` gets a platform wheel (fine) but a local build needs Rust in `bin/sandbox`, and multi-arch `dist/*.whl` breaks the glob |
| Release | two dists to publish and keep in lock step (`harp-proxy-native==<same version>` pinned in the extra) | one dist |
| Version skew | possible (private API, hence the `==` pin) | impossible |

### CI wheel matrix (either layout; A: `native/` only, B: whole project)

abi3 means one wheel per platform, not per Python. `PyO3/maturin-action` (or `cibuildwheel`) matrix:

- Linux manylinux x86_64, aarch64; musllinux x86_64, aarch64
- macOS x86_64 (`macos-13`), arm64 (`macos-14`)
- Windows x64 (arm64 optional)
- plus an sdist job.

Locally validated by cross-building with `uvx --with ziglang maturin build --release --zig --target <t>` (no docker
needed): aarch64 manylinux_2_17 28 s, aarch64 musllinux_1_2 25 s, x86_64 musllinux_1_2 26 s, each ~190 KB. Not
executed (no aarch64 or musl host here). macOS and Windows not built (no host); expect 2-4 min per job in CI. Release
critical path is the slowest job. For B the same matrix runs per release of harp-proxy itself, and the frontend build
(`make wheel`) has to feed every platform job.

### Micro (laptop, `--fast`, tooling validation only)

`make bench-micro BENCH_OUTPUT=bench/results/micro-py.json` and the same with `HARP_NATIVE=blob_id` into
`micro-rs.json`, then `make bench-compare BASE=... CAND=...`. `blob_id[...]` is `Blob.from_data` end to end,
`digest[...]` the digest function alone.

| Benchmark | python (hashlib) | native | |
|---|---|---|---|
| blob_id[64B] | 871 ns | 758 ns | 1.15x faster |
| digest[64B] | 542 ns | 425 ns | 1.27x faster |
| blob_id[1KB] | 1.97 us | 1.36 us | 1.45x faster |
| digest[1KB] | 1.65 us | 1.11 us | 1.48x faster |
| blob_id[100KB] / digest[100KB] | | | not significant |
| blob_id[5MB] | 2.55 ms | 2.98 ms | 1.17x slower |
| digest[5MB] | 2.70 ms | 3.89 ms | 1.44x slower |

Reading: the boundary is cheap (one call vs hashlib's object + 3 calls); small bodies gain from that, not from the
hash. Large bodies are bound by the hash itself, where OpenSSL's assembly beats the crate on this CPU. Spread on
`--fast` is wide (5 MB shows 0.5 ms std dev): rerun on the external runner before quoting any of it.

### Recommendation

**A, with a top-level `harp_native` module.**

- B turns every harp-proxy install and every contributor/CI `uv sync` into a Rust build, loses the universal wheel
  (Docker, `bin/build_wheel`), breaks 7 tests tied to hatchling and cannot express the cookiecutter re-include. For one
  function with no perf win.
- A costs nothing to those who do not opt in, keeps hatchling and the sandboxed `make wheel` untouched, and builds in
  seconds. Its price is two dists released in lock step and an `==` pin.
- Do not inject `harp._native._core` from a second distribution: it breaks editable installs.
- The layout B diff is kept as `native/layout-b.patch` (applies on the spike commit, `git apply`).
- Open point for the ADR: if native components multiply and become mandatory, B's single dist becomes attractive again;
  it is a packaging move, the shim (`CORE_MODULES`) already supports both.

## ASGI server matrix

Issue #1171. `harp server --server <name>` (or `HARP_SERVER`) picks the server; `hypercorn` stays the default. Everything
but the default needs the `servers` extra. `make bench-macro|bench-load|bench-startup` take `--server`.

**Indicative only.** Laptop (Core Ultra 7 255H, `powersave` governor, hybrid), shared with other jobs: load average was
2 to 40 during the runs. HARP on P-cores 4,5, origin 3, load generator 2. 3 runs per cell, order rotated each round,
50 req/s, 30 s measured + 5 s warmup, `oha` 1.16.0, HTTP/1.1 keep-alive, 1 KiB body. Verdict waits for the external
runner (#1168). Cells show the median of 3 runs, `[min-max]` where useful.

### Overhead (proxied minus direct, ms) and CPU per request

| profile | server | p50 | p90 | p99 | CPU us/req | peak RSS MiB |
|---|---|---|---|---|---|---|
| bare | hypercorn | 2.44 [2.27-2.53] | 2.49 | 3.24 [2.7-7.3] | 2693 | 104 |
| bare | hypercorn+uvloop | 2.32 [2.24-2.40] | 2.77 | 3.52 [3.1-4.5] | 2680 | 106 |
| bare | uvicorn | 2.38 [2.26-2.47] | 2.87 | 3.62 [3.3-7.5] | 2340 | 106 |
| bare | granian | 2.80 [2.80-2.92] | 3.33 | 5.03 [3.2-16.8] | 2433 | 110 |
| default | hypercorn | 6.10 [5.34-6.22] | 6.72 | 7.63 [7.6-15.2] | 11587 | 111 |
| default | hypercorn+uvloop | 5.93 [5.57-6.00] | 6.94 | 8.91 [7.9-14.3] | 10327 | 114 |
| default | uvicorn | 5.61 [5.44-5.79] | 6.38 | 6.86 [6.8-12.6] | 10067 | 113 |
| default | granian | 6.38 [6.29-6.51] | 9.41 | 22.48 [13.3-55.8] | 10427 | 121 |

Reading:

- The server is a small part of the overhead: about 2.4 ms bare, and `default` adds the storage and cache work (about
  3.5 ms more). The three Python-loop options differ by less than the spread between runs on p50 and p90.
- **CPU per request is the steadiest signal**: uvicorn -13% (bare and default), hypercorn+uvloop -11% on `default` (equal
  on `bare`), granian -10% on `default`, -10% on `bare`. Bare CPU is the h11 vs httptools parsing plus loop cost; on
  `default` the storage work, identical for all, dilutes it.
- granian is slower at p50 (+0.4 ms bare, +0.3 default) and clearly worse at p99: HARP still runs on a Python asyncio
  loop, so every request crosses the Rust/Python boundary and a thread hop on top of the same Python work. It gains
  nothing while the handler stays in Python.
- Peak RSS: granian +5 to +10 MiB (Rust runtime), others equal.

### Saturation (`bench-load`, steps 25..1600 req/s, 32 connections)

Saturation rate per run (3 runs, sorted) and, in brackets, the best one. Spread is huge because the machine was shared:
the same option moved from 25 to 400 between runs. Do not read a ranking beyond the order of magnitude.

| profile | hypercorn | hypercorn+uvloop | uvicorn | granian |
|---|---|---|---|---|
| bare | 25, 200, 400 | 25, 50, 400 | 50, 800, 800 | 50, 50, 200 |
| default | 25, 25, 25 | 25, 100, 200 | 50, 50, 200 | 25, 50, 100 |

On `bare`, uvicorn is the only one reaching 800 req/s (twice); hypercorn and hypercorn+uvloop reach 400; granian 200 at
best. On `default` storage dominates (transactions and bodies were shed from 50-200 req/s) and every server lands
between 25 and 200.

### Startup (exec to first proxied 200, `default`, warm)

Bimodal on this machine (about 0.5 s when quiet, 0.9 to 1.3 s when it is not), independent of the server. Best warm run
per server: hypercorn 0.51 s, hypercorn+uvloop 0.49 s, uvicorn 0.53 s, granian 0.52 s. No measurable difference.

### What each option breaks

| | hypercorn (default) | hypercorn+uvloop | uvicorn | granian |
|---|---|---|---|---|
| HTTP/2 (h2c prior knowledge, checked with curl) | yes | yes | **no**, HTTP/1.1 only | yes |
| lifespan | yes | yes | yes, but needs `interface="asgi3"`: its auto detection takes the metrics middleware (plain `__call__`) for ASGI 2 and fails startup | yes, once only: see below |
| several binds (proxy ports + dashboard) | one lifespan, all binds | same | same (sockets passed to one `Server`) | embed serves **one address per server**: one server per bind, first carries the lifespan, the others run without it, so they can answer 500 for a few ms before startup completes |
| server port in scope | int | int | int | **string** (spec says int): controllers are resolved by port, every request was a 404 until the adapter coerced it |
| logging | `hypercorn.access/error` through HARP's logging | same | `uvicorn.access/error` through HARP's logging | **none**: disabled by the adapter (embed would configure logging on its own); no access log |
| signals (SIGTERM, exit code) | graceful, 0 | graceful, 0 | graceful, 0 after the adapter replaces `capture_signals`; stock uvicorn re-raises the signal and kills the process before `system.dispose()` (143) | graceful, 0 (handlers installed by the adapter, embed installs none) |
| reload | not used by HARP | same | same | embed refuses reload |
| TLS / acme | HARP's adapter never configured TLS: nothing lost | same | same | same |
| Windows | yes | **no** (uvloop) | **no** (the adapter requires uvloop) | yes, not tried |
| new deps | none | `uvloop` | `uvicorn[standard]`, `uvloop` | `granian` (Rust wheel) |
| other | | needs `asyncio.run(loop_factory=...)`, no policy change | | embed API is experimental (it logs so at startup) |

Not tested: HTTP/2 under load, slow clients, request body streaming limits, websockets (HARP ignores them), Windows.

### Provisional recommendation

Keep **hypercorn** as default. If one alternative is worth carrying, it is **hypercorn+uvloop**: same server, same HTTP/2,
logging and signal behaviour, 11% less CPU per request on `default`, one optional dependency, no code path of its own.
**uvicorn** has the best CPU and the best saturation here but drops HTTP/2 and needed two workarounds (ASGI 3 detection,
signals). **granian** loses on latency and p99, loses logging and carries the embed caveats: do not pursue while the
handlers are Python. Decide on the external runner (#1168): rerun `bare` and `default` with the same options, pinned
and quiet; the CPU per request column is the one to trust first.
