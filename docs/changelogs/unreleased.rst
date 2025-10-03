Unreleased
==========

Important Changes
:::::::::::::::::

* ⚠️ Python 3.13 is now the minimum supported version.
* ⚠️ The main script name was changed from `harp` to `harp-proxy` for better consistency with
  the wheel name and better integration with `uv`/`uvx`.
* ⚠️ Package management migrated to `uv` instead of poetry. It should not change a lot from
  the user perspective (but read below).


Added
:::::

* Added a `harp.utils.testing.cli.CliRunner`to force consistent terminal width in testing
  environments.
* Makefile documentation in contributor guide.
* Ability to build for arm cpu arch targets.

Changed
:::::::

* Various tests strenghtening changes (behaviour unchanged).

Updated
:::::::

* Bump aiohttp, freezegun.

Removed
:::::::

* Benchmarking logic was removed, as it makes test hard and unreliable, adds version
  specific data in the source tree and overall, should belong to an external benchmarking
  suite.
