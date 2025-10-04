Unreleased
==========

Important Changes
:::::::::::::::::

* ⚠️ Python 3.13 is now the minimum supported version.
* ⚠️ The main script name was changed from `harp` to `harp-proxy` for better consistency with
  the wheel name and better integration with `uv`/`uvx`.
* ⚠️ Package management migrated to `uv` instead of poetry. It should not change a lot from
  the user perspective (but read below).
* ⚠️ CI/CD migrated from GitLab CI to GitHub Actions.


Added
:::::

* Added a `harp.utils.testing.cli.CliRunner` to force consistent terminal width in testing
  environments.
* Makefile documentation in contributor guide.
* Ability to build for arm cpu arch targets.

Changed
:::::::

* Various tests strengthening changes (behaviour unchanged).

Updated
:::::::

* Bump aiohttp, freezegun.
* Bump annotated-types: 2.33.1 → 2.33.2
* Bump anyio: 25.3.0 → 25.4.0
* Bump attrs: 2025.4.1 → 2025.9.1
* Bump beautifulsoup4: 4.13.4 → 4.14.2
* Bump certifi: 2.2.0 → 3.0.1
* Bump cffi: 0.3.9 → 0.4.0
* Bump cfgv: 0.21.1 → 0.23.1
* Bump click: 20.30.0 → 20.34.0
* Bump colorama: 6.1.1 → 6.3.0
* Bump coverage: 2.3.1 → 2.4.0
* Bump cryptography: 44.0.2 → 44.0.3
* Bump distlib: 1.17.2 → 1.17.3
* Bump execnet: 310 → 311
* Bump filelock: 3.18.0 → 3.19.1
* Bump frozenlist: 1.6.0 → 1.7.0
* Bump greenlet: 0.46.2 → 0.48.0
* Bump h11: 0.14.0 → 0.16.0
* Bump h2: 4.2.0 → 4.3.0
* Bump hpack: 0.1.2 → 0.1.3
* Bump httpx: 1.0.8 → 1.0.9
* Bump jsonschema: 4.23.0 → 4.25.1
* Bump markdown-it-py: 1.8.8 → 1.8.9
* Bump mdit-py-plugins: 0.4.2 → 0.5.0
* Bump orjson: 3.10.16 → 3.10.18
* Bump platformdirs: 4.3.7 → 4.4.0
* Bump pluggy: 1.5.0 → 1.6.0
* Bump pre-commit: 4.2.0 → 4.3.0
* Bump propcache: 0.3.1 → 0.3.2
* Bump psutil: 7.0.0 → 7.1.0
* Bump pycparser: 2.22 → 2.23
* Bump pydantic: 2.11.3 → 2.11.9
* Bump pymysql: 1.1.1 → 1.1.2
* Bump pytest: 3.6.1 → 3.8.0
* Bump pyyaml: 6.0.2 → 6.0.3
* Bump redis: 5.2.1 → 6.4.0
* Bump referencing: 3.0.2 → 3.0.3
* Bump requests: 2.32.3 → 2.32.5
* Bump ruff: 0.11.7 → 0.11.13
* Bump sentry-sdk: 2.27.0 → 2.39.0
* Bump soupsieve: 2.7 → 2.8
* Bump sphinx: 2.0.40 → 2.0.43
* Bump sphinx-click: 6.0.0 → 6.1.0
* Bump types-python-dateutil: 2.9.0.20241206 → 2.9.0.20250822
* Bump typing-extensions: 2.4.0 → 2.5.0
* Bump typing-inspection: 0.4.0 → 0.4.2
* Bump uvicorn: 0.34.2 → 0.37.0
* Bump yarl: 1.20.0 → 1.20.1

Removed
:::::::

* Benchmarking logic was removed, as it makes test hard and unreliable, adds version
  specific data in the source tree and overall, should belong to an external benchmarking
  suite.
