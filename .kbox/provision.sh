#!/usr/bin/env bash
# Provisioning run INSIDE the kbox VM after the clone: as ubuntu, cwd = the cloned
# repo, login shell (claude on PATH). MUST stay idempotent — kbox re-runs it on
# every `up` and every `sync`. Put dependency installs, service startup and MCP
# registration here (uncomment/adapt the examples below).
set -euo pipefail

# [ -f package-lock.json ] && npm ci
# [ -f pyproject.toml ]    && uv sync
# docker compose up -d
