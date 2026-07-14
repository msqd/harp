# kbox per-project config — sourced by kbox over its defaults. Everything is
# optional; PROJECT auto-derives from the repo directory name. See the kbox repo
# (examples/config.sh) for the full list of variables.

# Kongo (company mail) wiring, forwarded to the provision hook so it can register
# the kongo MCP against the canonical LAN Kongo. Empty on the host = MCP skipped.
# (These are also exported in the VM's login shells.)
PROVISION_ENV="KONGO_CANONICAL_URL KONGO_API_URL KONGO_REPO_URL"

# Files local to the host checkout (outside git — .env, secrets) copied into the
# VM's clone after cloning. Missing on the host = skipped.
#SEED_PROJECT_FILES=".env"
