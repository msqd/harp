# kbox per-project config — sourced by kbox over its defaults. Everything is
# optional; PROJECT auto-derives from the repo directory name. See the kbox repo
# (examples/config.sh) for the full list of variables.

# harp is a light Python service: 2G is plenty (idle ~0.5G). Applied on the next
# `kbox up` (host-side `multipass set`); resize a RUNNING VM with stop+set+start.
VM_MEMORY="2G"

# Kongo (company mail) wiring, forwarded to the provision hook so it can register
# the kongo MCP against the canonical LAN Kongo. Empty on the host = MCP skipped.
# (These are also exported in the VM's login shells.)
PROVISION_ENV="KONGO_CANONICAL_URL KONGO_API_URL KONGO_REPO_URL"

# Files local to the host checkout (outside git — .env, secrets) copied into the
# VM's clone after cloning. Missing on the host = skipped.
#SEED_PROJECT_FILES=".env"
