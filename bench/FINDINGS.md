# Findings

Rules (milestone explore/extensions): each candidate declares its target metric up front; native code must gain ≥15%
on it, net of the best adopt-native option, against the best reasonable Python, median of ≥5 runs outside the spread,
with no regression elsewhere. Laptop numbers validate tooling only; verdicts need the external runner (#1168).

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
| ASGI server (hypercorn, pure h11) | adopt | open | #1171: needs a server switch first, HARP hardcodes `HypercornAdapter` |
| Upstream client (httpx) | adopt | open | #1172 |
| Storage write pipeline | Python design | open lead | see below |

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
