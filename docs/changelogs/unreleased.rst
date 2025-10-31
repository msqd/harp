Unreleased
==========

Changed
-------

- Simplified version detection mechanism to use ``importlib.metadata`` for installed packages instead of ``version.txt``
- Version now falls back to ``"unknown"`` instead of ``"0.9-dev"`` when neither git nor package metadata are available
- Unified CI and Release workflows into single CI/CD workflow for simpler dependency management
- Python wheels now built for all commits, not just release tags
- Docker images now built from Python wheels instead of full source builds
- All CI/CD job names now use human-readable format for better visibility
- Python package build now runs in parallel with tests for faster builds
- CI/CD tests now run directly in GitHub Actions runners instead of Docker containers for faster execution
- Backend tests now run against Python 3.13 and 3.14 using matrix strategy
- Removed initial Docker image builds from CI/CD workflow (build-runtime-image, build-development-image)
- Updated CI/CD to use Node.js 24 and pnpm 10 for consistent environment between local and CI
- Simplified Dockerfile to single-stage wheel-based build matching CI/CD process
- Local Docker builds (``make buildc``) now build wheel first then install in container, consistent with CI
- Removed development Docker image targets (``buildc-dev``, ``runc-dev-shell``, ``testc-*``) - tests run natively
- Message headers column in storage database is now nullable to support selective header storage
- Add storage markers for granular control over what gets stored:

  - ``skip-request-body-storage`` and ``skip-response-body-storage`` - skip storing message bodies
  - ``skip-request-headers-storage`` and ``skip-response-headers-storage`` - skip storing message headers
  - ``skip-request-storage`` and ``skip-response-storage`` - skip storing entire messages

Added
-----

- Frontend assets are now built and included in release wheels automatically
- Node.js and pnpm setup in release workflow for frontend compilation
- Docker images built from wheels with smart version tagging:

  - Release tags (e.g., ``0.9.0``): tagged as ``0.9.0``, ``0.9``, and ``0`` (installed from PyPI, pushed to registry)
  - Pre-release tags (e.g., ``0.9.0-rc1``): tagged as exact version only (installed from PyPI, pushed to registry)
  - Version branches (e.g., ``0.9``): tagged as ``0.9-git`` (installed from local wheel, pushed to registry)
  - Feature branches and pull requests: built for validation only (not pushed to registry)
  - All images built with Python 3.14 (GIL enabled) and Python 3.14t (GIL disabled, ``-nogil`` suffix)

Fixed
-----

- Made playwright installation non-fatal in ``install-dev`` target to prevent build failures
- Fixed test isolation issues in version detection tests that caused subprocess test failures
- Updated Python version requirement to ``>=3.13,<3.15`` to support Python 3.14

Removed
-------

- Removed ``version.txt`` creation from build process (``bin/sandbox``)
