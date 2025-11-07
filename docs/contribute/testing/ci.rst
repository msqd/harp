Continuous integration
======================

This guide explains how HARP's GitHub Actions CI/CD pipeline works and how to troubleshoot failures.

Overview
--------

HARP uses GitHub Actions for continuous integration. The CI pipeline is defined in ``.github/workflows/cicd.yml`` and runs automatically on:

* Every push to any branch
* Every pull request
* Semantic version tags (e.g., ``0.9.0``, ``0.9.0-rc1``)

The pipeline consists of multiple jobs that run in parallel to provide fast feedback.

CI jobs
-------

Test jobs
^^^^^^^^^

All test jobs run directly on the runner using ``uv`` (no Docker containers):

**test-backend-core**
  Tests the core ``harp/`` directory

  * Runs ``uv run pytest harp -n auto -m 'not subprocess'``
  * Uses parallel execution (``-n auto``)
  * Skips subprocess-marked tests
  * Python 3.13

**test-backend-apps**
  Tests the ``harp_apps/`` directory

  * Runs ``uv run pytest harp_apps -n 1 -m 'not subprocess'``
  * Single worker (``-n 1``) due to testcontainers
  * Includes tests for dashboard, proxy, storage, etc.
  * Python 3.13

**test-backend-e2e**
  Tests the ``tests/`` directory (end-to-end tests)

  * Runs ``uv run pytest tests -n 1 -m 'not subprocess'``
  * Single worker (``-n 1``)
  * Tests complete workflows
  * Python 3.13

**test-frontend-unit**
  Runs frontend unit tests with Vitest

  * Uses pnpm and Node.js 24
  * Runs ``pnpm test:unit`` in ``harp_apps/dashboard/frontend``

Documentation and UI jobs
^^^^^^^^^^^^^^^^^^^^^^^^^^

**build-documentation**
  Builds Sphinx documentation

  * Runs ``make docs``
  * Outputs to ``harp-doc`` artifact (30 day retention)
  * Continues on error (won't fail the build)

**build-storybook**
  Builds Ladle (Storybook) UI component explorer

  * Runs ``pnpm ui:build``
  * Outputs to ``harp-ui`` artifact (30 day retention)
  * Continues on error (won't fail the build)

Build and release jobs
^^^^^^^^^^^^^^^^^^^^^^^

**build-python-package**
  Builds the Python wheel

  * Runs ``make clean-dist wheel``
  * Bundles frontend assets
  * Validates with twine
  * Uploads wheel artifact (7 day retention)

**all-checks-passed**
  Consolidation job ensuring all tests pass

  * Depends on all test jobs and package build
  * Tests wheel installation on Python 3.13
  * Must pass before any releases

**build-docker-image-development**
  Builds Docker image for development branches

  * Only runs for non-tag pushes
  * Uses local wheel from build
  * Pushes to GHCR for all commits
  * Version branches (e.g., ``0.9``) also push to Docker Hub as ``<version>-git``

**publish-to-testpypi**
  Publishes to Test PyPI

  * Only runs for release tags
  * Uses trusted publishing (OIDC)

**publish-to-pypi**
  Publishes to PyPI

  * Runs after TestPyPI succeeds
  * Uses trusted publishing (OIDC)

**build-docker-image-release**
  Builds Docker image from PyPI release

  * Only runs for release tags
  * Uses ``Dockerfile.pypi`` to install from PyPI
  * Mainline releases (``X.Y.Z``) get multiple tags: ``X``, ``X.Y``, ``X.Y.Z``
  * Pre-releases (``X.Y.Z-rc1``) get exact tag only
  * ``0.9.x`` releases also tagged as ``:latest``

**create-github-release**
  Creates GitHub release

  * Converts changelog RST to Markdown
  * Attaches wheel artifact
  * Marks pre-releases appropriately

How tests run in CI
--------------------

Test execution
^^^^^^^^^^^^^^

Tests run directly on the GitHub Actions runner using ``uv``:

.. code-block:: bash

    # Install uv
    uses: astral-sh/setup-uv@v4

    # Create required directories
    mkdir -p harp_apps/dashboard/web

    # Install dependencies
    uv sync

    # Run tests
    uv run pytest harp -n auto -m 'not subprocess'

This approach is simpler and faster than using Docker containers.

Testcontainers support
^^^^^^^^^^^^^^^^^^^^^^^

Tests that use testcontainers (for PostgreSQL, MySQL, etc.) work automatically on GitHub Actions runners because:

* Docker is pre-installed on ubuntu-latest runners
* Tests have access to the Docker socket
* ``TESTCONTAINERS_RYUK_DISABLED=true`` is set for faster cleanup

Environment variables
^^^^^^^^^^^^^^^^^^^^^

Key environment variables set by the CI:

* ``CI``: Automatically set by GitHub Actions
* ``TESTCONTAINERS_RYUK_DISABLED``: Set to ``true`` for faster cleanup
* ``DOCKER_BUILDKIT``: Enables BuildKit for Docker builds

Test parallelization
^^^^^^^^^^^^^^^^^^^^

* **Core tests** (``harp/``): Run with ``-n auto`` for maximum parallelism
* **App tests** (``harp_apps/``): Run with ``-n 1`` due to testcontainers database conflicts
* **E2E tests** (``tests/``): Run with ``-n 1`` for stability

Frontend tests
^^^^^^^^^^^^^^

Frontend tests use pnpm and Node.js 24:

.. code-block:: bash

    cd harp_apps/dashboard/frontend
    pnpm install --ignore-workspace
    pnpm test:unit

Troubleshooting CI failures
----------------------------

Common issues
^^^^^^^^^^^^^

**Test failures with testcontainers**

If database tests fail, check:

* Docker service is running on the runner
* No port conflicts between parallel tests (use ``-n 1`` if needed)
* Testcontainers can access the Docker socket

**Frontend test failures**

If frontend tests fail:

* Check Node.js version matches (24)
* Ensure pnpm version matches (10)
* Verify ``harp_apps/dashboard/web`` directory exists

**Build failures**

If wheel build fails:

* Check that frontend assets are bundled correctly
* Verify version validation passes for tags
* Check twine validation output

Debugging locally
^^^^^^^^^^^^^^^^^

To reproduce CI failures locally:

.. code-block:: shell

    # 1. Ensure web directory exists
    mkdir -p harp_apps/dashboard/web

    # 2. Install dependencies (matches CI)
    uv sync

    # 3. Run tests exactly as CI does
    uv run pytest harp -n auto -m 'not subprocess'
    uv run pytest harp_apps -n 1 -m 'not subprocess'
    uv run pytest tests -n 1 -m 'not subprocess'

    # 4. Frontend tests
    cd harp_apps/dashboard/frontend
    pnpm install --ignore-workspace
    pnpm test:unit

Running specific job tests
^^^^^^^^^^^^^^^^^^^^^^^^^^^

To simulate specific CI jobs:

.. code-block:: shell

    # test-backend-core
    uv run pytest harp -n auto -m 'not subprocess'

    # test-backend-apps
    uv run pytest harp_apps -n 1 -m 'not subprocess'

    # test-backend-e2e
    uv run pytest tests -n 1 -m 'not subprocess'

    # test-frontend-unit
    cd harp_apps/dashboard/frontend && pnpm test:unit

Checking CI logs
^^^^^^^^^^^^^^^^

Use GitHub CLI to view logs:

.. code-block:: shell

    # List recent runs
    gh run list --limit 10

    # View specific run
    gh run view <run-id>

    # View failed job logs
    gh run view <run-id> --log-failed

    # Watch a running build
    gh run watch <run-id>

CI/CD best practices
--------------------

For contributors
^^^^^^^^^^^^^^^^

1. **Run tests locally before pushing**

   .. code-block:: shell

       uv run pytest harp harp_apps tests -n auto -m 'not subprocess'

2. **Run the same commands as CI**

   Match the exact CI commands to catch failures early.

3. **Check CI logs immediately after pushing**

   Failed CI checks block merging, so fix issues quickly.

4. **Ensure ``harp_apps/dashboard/web`` exists**

   Create it with ``mkdir -p harp_apps/dashboard/web`` if missing.

For maintainers
^^^^^^^^^^^^^^^

1. **Keep CI fast**

   * Use parallelism for core tests (``-n auto``)
   * Run sequential tests in parallel jobs
   * Use GitHub Actions caching

2. **Make failures actionable**

   * CI output should clearly show what failed
   * Error messages should suggest fixes
   * Document common issues in this guide

3. **Version compatibility**

   * Currently testing Python 3.13
   * Keep dependencies in sync with ``uv.lock``
   * Test wheel installation before release

CI configuration reference
---------------------------

Key files
^^^^^^^^^

* ``.github/workflows/cicd.yml``: Main CI/CD workflow
* ``Makefile``: Build and test automation
* ``Dockerfile``: Production image (uses local wheel)
* ``Dockerfile.pypi``: Release image (installs from PyPI)
* ``pyproject.toml``: Python dependencies and tool config
* ``uv.lock``: Locked Python dependencies
* ``harp_apps/dashboard/frontend/package.json``: Frontend dependencies
* ``bin/validate_version``: Version validation script for releases

GitHub Actions secrets and variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Required configuration:

* ``GITHUB_TOKEN``: Automatic, used for GHCR push and releases
* ``DOCKERHUB_USERNAME`` (variable): Docker Hub username
* ``DOCKERHUB_TOKEN`` (secret): Docker Hub token
* PyPI trusted publishing configured for ``harp-proxy`` package

Workflow triggers
^^^^^^^^^^^^^^^^^

.. code-block:: yaml

    on:
      push:
        branches: ['**']           # All branches
        tags:
          - '*.*.*'                # Semantic versions (0.9.0)
          - '*.*.*-*'              # Pre-releases (0.9.0-rc1)
      pull_request:                # All PRs

Release conditions
^^^^^^^^^^^^^^^^^^

Different jobs run based on push type:

**Development images** (``build-docker-image-development``):
  * All non-tag pushes
  * Version branches (e.g., ``0.9``) also push to Docker Hub as ``<version>-git``

**PyPI releases** (``publish-to-pypi``):
  * Only semver tags (``0.9.0``, ``0.9.0-rc1``, etc.)

**Release images** (``build-docker-image-release``):
  * Only after PyPI publish succeeds
  * Installs from PyPI, not local wheel

Further reading
---------------

* :doc:`../makefile` - Complete Makefile reference
* `GitHub Actions documentation <https://docs.github.com/en/actions>`_
* `uv documentation <https://docs.astral.sh/uv/>`_
* `pytest documentation <https://docs.pytest.org/>`_
* `Testcontainers for Python <https://testcontainers-python.readthedocs.io/>`_
