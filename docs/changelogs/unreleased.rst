Unreleased
==========

Important Changes
:::::::::::::::::

* ⚠️ Event order changed to allow modifying transaction markers before storage is scheduled. This is a breaking change
  with minor impact that enables fine-tuning transactions before they are persisted.

Added
-----

* Version validation in release workflow to ensure pyproject.toml matches git tag
* Test matrix for Python 3.13, 3.14, and 3.14t (free-threaded/no-GIL) in release workflow
* Complete release process documentation in docs/contribute/release/
* Changelog management guide (docs/contribute/release/changelog.rst)
* bin/validate_version script for version consistency checks

Changed
-------

* **Release workflow**: Version must now be manually updated in pyproject.toml before tagging (no longer automated during CI)
* **Release workflow**: Replaced single-version wheel testing with matrix testing across Python 3.13, 3.14, and 3.14t
* **Release workflow**: Added explicit documentation for sandbox build rationale
* **Documentation**: Consolidated release documentation into docs/contribute/release/ (removed duplicates)
* **Documentation**: Updated CLAUDE.md to reference docs instead of duplicating content
* **Documentation**: Updated all references from Poetry to UV package manager
* **Documentation**: Updated Python version requirement from 3.12 to 3.13+
* **Documentation**: Fixed command examples throughout (poetry run → uv run)
* Bump alembic: 1.15.2 → 1.17.0
* Bump aiohttp: 3.12.15 → 3.13.1
* Bump asgi-tools: 1.1.0 → 1.3.3
* Bump asgiref: 3.8.1 → 3.10.0
* Bump cryptography: 46.0.2 → 46.0.3
* Bump hatchling: (new) 1.27.0
* Bump multidict: 6.4.4 → 6.7.0
* Bump orjson: 3.10.18 → 3.11.3
* Bump rich-click: 1.8.9 → 1.9.3
* Bump slack-sdk: 3.35.0 → 3.37.0
* Bump sqlalchemy-utils: 0.41.2 → 0.42.0
* Bump testcontainers: 4.13.1 → 4.13.2
* Reorganized dev dependencies from optional-dependencies to dependency-groups

Removed
-------

* Removed duplicate/outdated release documentation (sources.rst, bump.rst)
* Removed anyio dependency
* Removed black (replaced by ruff)
* Removed isort (replaced by ruff)
* Removed pytest-benchmark
* Removed mysql from default dependency groups
