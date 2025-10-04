Continuous Integration
======================

This guide explains how HARP's GitHub Actions CI/CD pipeline works and how to troubleshoot failures.

Overview
--------

HARP uses GitHub Actions for continuous integration. The CI pipeline is defined in ``.github/workflows/ci.yml`` and runs automatically on:

* Every push to any branch
* Every pull request
* Tag creation

The pipeline consists of multiple jobs that run in parallel to provide fast feedback.

CI Jobs
-------

Build Jobs
^^^^^^^^^^

**build-runtime**
  Builds the production Docker image (``runtime`` stage from Dockerfile)

  * Pushes to ``ghcr.io/msqd/harp:<sha>-<run_number>``
  * Uses Docker buildx with layer caching
  * Sets image version from git describe

**build-dev**
  Builds the development Docker image (``development`` stage from Dockerfile)

  * Includes all development tools (pytest, playwright, etc.)
  * Pushes to ``ghcr.io/msqd/harp:<sha>-<run_number>-dev``
  * Used by all test jobs

Test Jobs
^^^^^^^^^

All test jobs depend on ``build-dev`` and run in parallel:

**test-backend-core**
  Tests the core ``harp/`` directory

  * Runs with parallel execution (``auto`` CPUs)
  * Skips subprocess-marked tests (``-m 'not subprocess'``)
  * Uses host Docker socket for testcontainers

**test-backend-apps**
  Tests the ``harp_apps/`` directory

  * Runs serially (``PYTEST_CPUS=1``) due to testcontainers
  * Uses host Docker socket for database containers
  * Includes tests for dashboard, proxy, storage, etc.

**test-backend-e2e**
  Tests the ``tests/`` directory (end-to-end tests)

  * Runs serially (``PYTEST_CPUS=1``)
  * Uses testcontainers for integration testing
  * Tests complete workflows

**test-frontend-unit**
  Runs frontend unit tests with vitest

  * Sets timezone to ``America/Havana`` for consistency
  * Runs inside development container

Documentation & UI Jobs
^^^^^^^^^^^^^^^^^^^^^^^

**doc-html**
  Builds Sphinx documentation

  * Outputs to ``harp-doc`` artifact
  * Uses world-writable mount for permission compatibility
  * Continues on error (won't fail the build)

**storybook**
  Builds Ladle (Storybook) UI component explorer

  * Outputs to ``harp-ui`` artifact
  * Uses world-writable mount for permission compatibility
  * Continues on error (won't fail the build)

Release Job
^^^^^^^^^^^

**release**
  Tags and pushes images to Docker Hub

  * Only runs on version branches (e.g., ``1.0``) or tags
  * Depends on all test jobs passing
  * Tags format:

    * Version branches: ``makersquad/harp-proxy:<version>-git``
    * Semver tags: ``makersquad/harp-proxy:<tag>`` and ``:latest``

How Tests Run in CI
--------------------

The CI environment uses a different approach than local development:

Docker Socket Mounting
^^^^^^^^^^^^^^^^^^^^^^^

In CI, tests run inside containers but need to create other containers (for databases, etc.). This is achieved by mounting the host's Docker socket:

.. code-block:: bash

    docker run --rm \
      --privileged \
      --group-add <docker-gid> \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -e DOCKER_HOST=unix:///var/run/docker.sock \
      ghcr.io/msqd/harp:xxx-dev \
      bash -c "cd /opt/harp/src && make test-backend"

The Makefile's ``testc-backend`` target detects the ``CI`` environment variable and automatically:

1. Detects the Docker socket's group ID (works on both Linux and macOS)
2. Adds that group to the container with ``--group-add``
3. Mounts the socket with ``-v /var/run/docker.sock:/var/run/docker.sock``
4. Sets ``TESTCONTAINERS_RYUK_DISABLED=true`` for faster cleanup

Environment Variables
^^^^^^^^^^^^^^^^^^^^^

The CI environment sets these automatically:

* ``CI``: Set by GitHub Actions, triggers CI-specific behavior
* ``DOCKER_BUILDKIT``: Enables BuildKit for faster builds
* ``DOCKER_IMAGE_DEV``: Full image name including SHA and run number
* ``PYTEST_OPTIONS``: Set per-job (e.g., ``-m 'not subprocess'``)
* ``PYTEST_TARGETS``: Which directories to test
* ``PYTEST_CPUS``: Parallelism level (``auto`` or ``1``)

Artifact Handling
^^^^^^^^^^^^^^^^^

Documentation and UI builds face permission challenges when using Docker volumes:

1. Create output directory on runner: ``mkdir -p harp-doc``
2. Make it world-writable: ``chmod 777 harp-doc``
3. Mount it where the build tool outputs: ``-v $PWD/harp-doc:/opt/harp/src/docs/_build``
4. Build runs inside container, writes to mounted directory
5. Upload artifact action (running on runner) can access the files

This approach avoids:

* Permission denied errors when container tries to write
* Need for ``chown`` commands (which fail on mounted volumes)
* Complex user ID mapping

Troubleshooting CI Failures
----------------------------

Common Issues
^^^^^^^^^^^^^

**Permission Denied Errors**

If you see permission errors in doc-html or storybook jobs:

.. code-block:: text

    Permission denied: '/opt/harp/src/docs/_build/html/_static'

This usually means the mounted directory isn't writable. Check that:

1. The directory is created with ``mkdir -p``
2. Permissions are set with ``chmod 777``
3. The mount point matches where the tool writes output

**Docker Socket Permission Errors**

If tests fail with:

.. code-block:: text

    Cannot connect to the Docker daemon at unix:///var/run/docker.sock

This means the container can't access the Docker socket. The Makefile should handle this automatically in CI, but if not:

1. Check that ``CI`` environment variable is set
2. Verify Docker socket exists and is accessible
3. Check group-add logic is working correctly

**Test Failures with Testcontainers**

Tests that use testcontainers (database tests, integration tests) may fail if:

* Network isolation prevents container-to-container communication
* Docker-in-Docker networking isn't set up correctly
* Port conflicts between test containers

The CI uses host Docker socket mounting to avoid these issues.

Debugging Locally
^^^^^^^^^^^^^^^^^

To reproduce CI failures locally:

.. code-block:: shell

    # 1. Build the dev image (matches CI)
    make buildc-dev

    # 2. Run tests in container (simulates CI)
    make testc-backend

    # With specific options
    PYTEST_OPTIONS="-v -k test_storage" make testc-backend
    PYTEST_TARGETS="harp_apps/storage" make testc-backend

    # 3. Or open an interactive shell
    make testc-shell

    # Inside the container
    cd /opt/harp/src
    uv run pytest tests/storage/test_sqlalchemy.py -v

Running Specific Job Tests
^^^^^^^^^^^^^^^^^^^^^^^^^^^

To simulate a specific CI job:

.. code-block:: shell

    # test-backend-core
    PYTEST_TARGETS=harp PYTEST_OPTIONS="-m 'not subprocess'" make testc-backend

    # test-backend-apps
    PYTEST_TARGETS=harp_apps PYTEST_OPTIONS="-m 'not subprocess'" PYTEST_CPUS=1 make testc-backend

    # test-backend-e2e
    PYTEST_TARGETS=tests PYTEST_OPTIONS="-m 'not subprocess'" PYTEST_CPUS=1 make testc-backend

    # test-frontend-unit
    make testc-frontend

Checking CI Logs
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

CI/CD Best Practices
--------------------

For Contributors
^^^^^^^^^^^^^^^^

1. **Run tests locally before pushing**

   .. code-block:: shell

       make qa  # Runs format, types, and tests

2. **Test in container if changing Docker config**

   .. code-block:: shell

       make testc-backend  # Simulates CI environment

3. **Check CI logs immediately after pushing**

   Failed CI checks block merging, so fix issues quickly.

4. **Don't skip hooks or checks**

   The CI runs the same checks, so skipping locally just delays failure.

For Maintainers
^^^^^^^^^^^^^^^

1. **Keep CI fast**

   * Use parallelism where possible (``test-backend-core``)
   * Cache Docker layers aggressively
   * Split long-running tests into separate jobs

2. **Make failures actionable**

   * CI output should clearly show what failed
   * Error messages should suggest fixes
   * Document common issues in this guide

3. **Version compatibility**

   * Test against multiple Python versions if needed
   * Keep dependencies up to date
   * Use lock files for reproducibility

CI Configuration Reference
---------------------------

Key Files
^^^^^^^^^

* ``.github/workflows/ci.yml``: Main CI workflow
* ``Makefile``: Build and test automation
* ``Dockerfile``: Multi-stage image definition
* ``pyproject.toml``: Python dependencies and tool config
* ``harp_apps/dashboard/frontend/package.json``: Frontend dependencies

GitHub Actions Secrets
^^^^^^^^^^^^^^^^^^^^^^^

Required secrets (configured in repository settings):

* ``GITHUB_TOKEN``: Automatic, used for GHCR push
* ``DOCKERHUB_USERNAME``: Docker Hub username for releases
* ``DOCKERHUB_TOKEN``: Docker Hub token for releases

Workflow Triggers
^^^^^^^^^^^^^^^^^

.. code-block:: yaml

    on:
      push:
        branches: ['**']  # All branches
        tags: ['**']      # All tags
      pull_request:       # All PRs

Release Conditions
^^^^^^^^^^^^^^^^^^

The release job only runs when:

.. code-block:: yaml

    if: |
      (github.ref_type == 'branch' && contains(github.ref_name, '.') && !contains(github.ref_name, '/')) ||
      github.ref_type == 'tag'

This means:

* Version branches: ``1.0``, ``2.1``, etc. (contains dot, no slashes)
* Any tag push

Further Reading
---------------

* :doc:`makefile` - Complete Makefile reference
* `GitHub Actions docs <https://docs.github.com/en/actions>`_
* `Docker buildx <https://docs.docker.com/buildx/working-with-buildx/>`_
* `Testcontainers <https://testcontainers.com/>`_
