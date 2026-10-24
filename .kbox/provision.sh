#!/usr/bin/env bash
# harp provisioning inside a kbox VM: as ubuntu, cwd = the cloned repo, login shell
# (claude on PATH). MUST stay idempotent — kbox re-runs it on every `up` and `sync`.
set -euo pipefail

# --- project deps (harp: uv backend + pnpm dashboard frontend) ---------------
# harp's package build references harp_apps/dashboard/web; it is `make install-backend`
# that does `mkdir -p` on it before `uv sync`, so a bare `uv sync` fails with
# "harp_apps/dashboard/web not found". Drive the deps through the Makefile instead.
command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
# pnpm for the dashboard frontend, honoring the version pinned in package.json.
# COREPACK_ENABLE_DOWNLOAD_PROMPT=0 lets corepack fetch that pinned pnpm without the
# interactive "Do you want to continue? [Y/n]" prompt (which hangs a non-interactive hook).
export COREPACK_ENABLE_DOWNLOAD_PROMPT=0
if command -v corepack >/dev/null 2>&1; then sudo corepack enable
else command -v pnpm >/dev/null 2>&1 || sudo npm install -g pnpm@10.22.0; fi

make install-dev   # uv sync (+ creates the web dir)
# Build the dashboard UI once. Vite/tsc is heap-hungry; give V8 room (needs a 4G VM,
# see .kbox/config.sh) so it doesn't die with "JavaScript heap out of memory".
[ -n "$(ls -A harp_apps/dashboard/web 2>/dev/null)" ] \
  || NODE_OPTIONS=--max-old-space-size=3072 make build-frontend
