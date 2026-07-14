# kbox per-project config — sourced by kbox over its defaults. Everything is
# optional; PROJECT auto-derives from the repo directory name. See the kbox repo
# (examples/config.sh) for the full list of variables.

# Host env var names forwarded into the VM: handed to .kbox/provision.sh AND
# exported in the VM's login shells (/etc/profile.d). Unset host vars are skipped.
#PROVISION_ENV=""

# Files local to the host checkout (outside git — .env, secrets) copied into the
# VM's clone after cloning. Missing on the host = skipped.
#SEED_PROJECT_FILES=".env"
