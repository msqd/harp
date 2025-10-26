Unreleased
==========

Changed
-------

- Simplified version detection mechanism to use ``importlib.metadata`` for installed packages instead of ``version.txt``
- Version now falls back to ``"unknown"`` instead of ``"0.9-dev"`` when neither git nor package metadata are available
- Unified CI and Release workflows into single CI/CD workflow for simpler dependency management

Added
-----

- Frontend assets are now built and included in release wheels automatically
- Node.js and pnpm setup in release workflow for frontend compilation

Fixed
-----

- Made playwright installation non-fatal in ``install-dev`` target to prevent build failures
- Fixed test isolation issues in version detection tests that caused subprocess test failures

Removed
-------

- Removed ``version.txt`` creation from build process (``bin/sandbox``)
