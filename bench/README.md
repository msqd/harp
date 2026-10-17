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
