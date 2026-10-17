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
| Upstream client (httpx) | adopt | **provisional** | #1172: aiohttp transport -6 to -15% CPU, Rust client ceiling -23% more, see below |
| Storage write pipeline | Python design | open lead | see below |

## Upstream client matrix (#1172)

Target metric: HARP CPU per request on `bare` (all of the process, tokio threads included), the layer profile of #1171
puts the client stack at ~35% of it. HARP pinned on cpus 0-1, origin 2, loadgen 3, 50 and 200 req/s, alternating runs,
laptop with other tenants (load average 2-20): read as ±10%, verdicts wait for #1168.

`--client httpx|aiohttp` (`HARP_CLIENT`) swaps the transport under the filter and cache transports; httpx
`Request`/`Response` stay, so hishel and the filters are untouched. The Rust client is a throwaway httpx transport on
pyreqwest 0.15 (reqwest/hyper), no error mapping, `bare` only.

CPU per request, median of 5 alternating runs (`bare`):

| Client | 50 req/s | vs httpx | 200 req/s | vs httpx | vs aiohttp |
|---|---|---|---|---|---|
| httpx (httpcore + h11) | 3310 µs | | 2708 µs | | |
| aiohttp transport | 3100 µs | -6% | 2308 µs | -15% | |
| pyreqwest (ceiling) | 2390 µs | -28% | 1778 µs | -34% | **-23%** (both rates) |

Run ranges do not overlap between aiohttp and pyreqwest at either rate. Latency is noise-bound here: overhead p50 at
50 req/s is 2.2 ms for httpx and aiohttp (6 runs each), p90 2.5 ms, p99 3.1 vs 3.9 ms.

| Profile (50 req/s, overhead) | httpx CPU | aiohttp CPU | p50 / p90 / p99 |
|---|---|---|---|
| `bare` | 2750 µs | 2450 µs (-11%) | same within noise |
| `default` | 10610 µs | 10940 µs | same: storage dominates |
| `loaded` | ~12.3 ms | ~12.3 ms | same: storage dominates |

`bench-load` saturation does not separate the clients: rates are noise-bound (`bare` stops at 400 req/s for httpx
twice, at 100 for aiohttp twice, while a fixed 200 req/s overhead run shows aiohttp as good or better; at 32
connections both clients swing from 2 to 80 ms p90 between identical runs; the one-core thread-per-connection origin
is the likely limit). `default` saturates at 100-200 req/s for both, from the storage pipeline.

What the aiohttp transport changes or breaks:
- no `retries` (refused at startup); no HTTP/2 (HARP does not use it);
- aiohttp keeps its own DNS cache; connection limits are matched to httpx's (100, 5 s keep-alive);
- certificate and other connect failures surface as `ConnectError` like with httpx; exception text differs;
- a startup flake (`no 200 after 60 s`) hit 3 of 30 harness runs, all on httpx, not reproducible; unrelated to the client.

Reading against the rule (≥15% net of the best adopt-native option, on the declared metric, ≥5 runs outside the
spread): the aiohttp transport is the adopt-native option and gives 6-15% on `bare`, below the bar on its own. A Rust
client clears the bar over it (-23%, 5 runs, non-overlapping) even before the cost of error mapping and streaming,
which the throwaway ignores. `default` and `loaded` do not move: there the work is storage (see above).

Provisional recommendation, pending #1168: keep httpx the default; ship the aiohttp transport as an opt-in (cheap, pure
Python, ~10% on the proxy path); open the Rust adapter question on the external runner, since the ceiling clears the
bar on `bare` only. The `default` profile gains nothing from either until the storage pipeline is fixed.

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
