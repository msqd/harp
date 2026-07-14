#!/usr/bin/env bash
# harp provisioning inside a kbox VM: as ubuntu, cwd = the cloned repo, login shell
# (claude on PATH). MUST stay idempotent — kbox re-runs it on every `up` and `sync`.
set -euo pipefail

# --- kongo MCP (company mail), when a canonical Kongo URL is forwarded --------
# Done first so the MCP is registered even if the project deps below hiccup. The
# stdio bin lives in a kongo clone of its own; registered user-scope so Claude sees
# it from anywhere in the VM. Idempotent add-or-replace. Skipped when no URL is set.
KONGO_URL="${KONGO_CANONICAL_URL:-${KONGO_API_URL:-}}"
if [ -n "$KONGO_URL" ]; then
  export GIT_SSH_COMMAND='ssh -o StrictHostKeyChecking=accept-new'
  [ -d "$HOME/kongo/.git" ] || git clone "${KONGO_REPO_URL:-git@github.com:hartym/kongo.git}" "$HOME/kongo"
  (cd "$HOME/kongo" && npm ci)
  claude mcp remove --scope user kongo >/dev/null 2>&1 || true
  claude mcp add --scope user kongo -e KONGO_API_URL="$KONGO_URL" -- npx tsx "$HOME/kongo/src/mcp/bin.ts"
fi

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

make install-dev                                                             # uv sync (+ creates the web dir)
[ -n "$(ls -A harp_apps/dashboard/web 2>/dev/null)" ] || make build-frontend # build the dashboard UI once
