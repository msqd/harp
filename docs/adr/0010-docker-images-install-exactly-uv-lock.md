# ADR-0010: Docker images install exactly `uv.lock`

- **Status**: accepted
- **Date**: 2026-10-24
- **Decided in**: [#1014](https://github.com/msqd/harp/issues/1014)

The Docker image installs the CI wheel with `pip install -c constraints.txt`, where `constraints.txt` is
`uv export --locked --no-dev --no-emit-project --no-hashes` for the extras the image installs
(`postgresql`, `mysql`, `sentry`). Every runtime dependency, direct or transitive, is the version CI
tested. CI then lists the packages installed in the built image and fails if they differ from the same
export.

## What was actually being decided

A wheel carries the `pyproject.toml` ranges, not the lock. An image built with a plain `pip install`
resolved each dependency to the newest version in range at build time: tested was not shipped, and two
builds of one tag could differ.

## Rejected

- **`uv sync --frozen` in the image.** Installs the project from source, not the wheel CI tested and
  PyPI ships, and puts uv in the build stage for no gain over a constraints file.
- **Hashes (`--require-hashes`).** The wheel is installed from a file with its own dependencies
  resolved from the index: pinning versions is the decision, hash pinning is a separate one.
- **Check with `pip freeze`.** The runtime image has no pip (#1434); the check lists packages with
  `importlib.metadata` in the image instead.

## Lock refresh routine

The lock moves only through `uv lock` commits. Dependabot's `uv` ecosystem opens those pull requests,
CI tests them, and the next image ships whatever `main` locks. A security fix in a dependency reaches
the image when its lock bump merges, not before. `pip install harp-proxy` users still get the ranges.

## Consequences

- The Dockerfile reads `dist/constraints.txt` next to the wheel; `make buildc` and CI generate it with
  `bin/check_docker_lock.py export`.
- Adding an extra to the image means adding it to `EXTRAS` in `bin/check_docker_lock.py` too; a test
  fails if the two disagree.
