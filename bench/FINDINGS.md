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
