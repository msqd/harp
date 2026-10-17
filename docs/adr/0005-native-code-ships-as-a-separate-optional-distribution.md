# ADR-0005: Native code ships as a separate, optional distribution

- **Status**: accepted, not yet implemented outside `explore/extensions`
- **Date**: 2026-10-17
- **Decided in**: [#1174](https://github.com/msqd/harp/issues/1174), spike [#1204](https://github.com/msqd/harp/pull/1204)

Rust code we write ourselves lives in `native/` and ships as its own distribution, `harp-proxy-native`
(top-level module `harp_native`), installed through the extra `harp-proxy[native]`. `harp-proxy` stays a
pure-Python `py3-none-any` wheel built by hatchling. Pure Python remains the reference implementation,
and native code is used only when asked for (`HARP_NATIVE`).

## Why not one distribution built by maturin

The obvious shape is one package with the extension inside it. The spike built it and it costs every
user and every contributor, not only those who want native code:

- an install without a matching wheel compiles Rust (maturin even bootstraps rustup, and fails offline);
- the wheel becomes per-platform, which breaks the universal `dist/*.whl` the Docker builds rely on;
- every `uv sync` and every CI job builds Rust;
- hatchling's include rules cannot be carried over: two files drop out of the wheel and seven packaging
  tests fail.

The separate distribution confines all of that to the opt-in. Its cost is two distributions released in
lock step: the extra pins `harp-proxy-native==` the same version, because the boundary is a private API.

## Why `harp_native`, not `harp._native._core`

A submodule injected into the `harp` package from another distribution works for installed wheels but
is invisible to an editable install of `harp-proxy`, which is how every contributor runs it. A
top-level module has no such conflict.

## Consequences

- Until `harp-proxy-native` is on PyPI, the lock needs `[tool.uv.sources] harp-proxy-native = { path = "native" }`.
- Releasing native code needs a wheel matrix (Linux manylinux and musllinux, x86_64 and aarch64; macOS
  x86_64 and arm64; Windows x64; sdist). abi3 keeps it to one wheel per platform.
- Whether any native code ships at all is a separate question, decided per component against the bar
  of the `explore/extensions` milestone. This record only fixes where it lives if it does.
