Unreleased
==========

Important Changes
:::::::::::::::::

* ⚠️ Python 3.13 is now the minimum supported version.
* ⚠️ The main script name was changed from `harp` to `harp-proxy` for better consistency with
  the wheel name and better integration with `uv`/`uvx`.
* ⚠️ Package management migrated to `uv` instead of poetry. It should not change a lot from
  the user perspective (but read below).
