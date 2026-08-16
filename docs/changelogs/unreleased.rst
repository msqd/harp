Unreleased
==========

Important Changes
:::::::::::::::::

Added
:::::

Changed
:::::::

Fixed
:::::

* ``uv.lock`` is now consistent with ``pyproject.toml``: the ``redis`` requirement recorded in the
  lockfile had drifted from the manifest, so every ``uv sync`` on a clean checkout silently rewrote
  ``uv.lock`` and left developers with a dirty working tree they did not create.

Security
::::::::

Removed
:::::::
