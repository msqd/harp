Makefile Tasks Reference
=========================

This guide documents all available Makefile tasks for development, testing, building, and CI operations.

Quick Start
-----------

To see all available commands with brief descriptions:

.. code-block:: shell

    make help

Development Tasks
-----------------

Starting Development Servers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

    # Start development instance with backend and dashboard
    make start-dev

    # Start only frontend development server (requires separate backend)
    make start-dev-frontend

These commands install dependencies first if needed and start HARP with reasonable defaults.

To customize services or options:

.. code-block:: shell

    # Override services to start
    make start-dev HARP_SERVICES="server dashboard"

    # Add extra options
    make start-dev HARP_MORE_OPTIONS="--verbose"

    # Customize examples
    make start-dev HARP_OPTIONS="--example sqlite --example proxy:httpbin"

Dependency Installation
-----------------------

.. code-block:: shell

    # Install all dependencies (backend + frontend) without dev tools
    make install

    # Install all dependencies including dev tools (recommended)
    make install-dev

    # Install only backend dependencies
    make install-backend

    # Install only frontend dependencies
    make install-frontend

Backend uses ``uv`` for Python package management, frontend uses ``pnpm``.

Testing
-------

Running Tests Locally
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

    # Run all tests (backend + frontend)
    make test

    # Run backend tests only
    make test-backend

    # Run frontend tests only (unit + browser + visual)
    make test-frontend

    # Skip frontend tests
    make test TEST_SKIP_FRONT=1

Backend Test Options
^^^^^^^^^^^^^^^^^^^^

The backend test system is highly configurable through environment variables:

.. code-block:: shell

    # Run specific test targets
    make test-backend PYTEST_TARGETS="tests/features/test_http_proxy.py"

    # Add pytest options
    make test-backend PYTEST_OPTIONS="-v -s -k test_specific_function"

    # Control parallel execution
    make test-backend PYTEST_CPUS=4  # Use 4 CPUs
    make test-backend PYTEST_CPUS=1  # Run serially

    # Combine options
    make test-backend PYTEST_TARGETS="harp" PYTEST_OPTIONS="-v" PYTEST_CPUS=2

Available environment variables:

* ``PYTEST``: Path to pytest executable (default: ``uv run pytest``)
* ``PYTEST_TARGETS``: Test paths to run (default: ``harp harp_apps tests``)
* ``PYTEST_CPUS``: Number of parallel workers (default: ``auto``)
* ``PYTEST_OPTIONS``: Additional pytest arguments

Frontend Test Options
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

    # Run unit tests only
    cd harp_apps/dashboard/frontend && pnpm test:unit

    # Run browser tests
    cd harp_apps/dashboard/frontend && pnpm test:browser

    # Update unit test snapshots
    make test-frontend-update

    # Update visual UI snapshots
    make test-frontend-ui-update

Coverage Reports
^^^^^^^^^^^^^^^^

.. code-block:: shell

    # Generate coverage report for backend
    make coverage

This generates an HTML coverage report in ``docs/_build/html/coverage/``.

Running Tests in Docker
^^^^^^^^^^^^^^^^^^^^^^^

These tasks run tests inside Docker containers, simulating the CI environment:

.. code-block:: shell

    # Run backend tests in dev container with Docker-in-Docker
    make testc-backend

    # Run frontend tests in dev container
    make testc-frontend

    # Open a shell in test environment
    make testc-shell

The ``testc-*`` tasks are useful for:

* Testing the exact CI environment locally
* Debugging CI-specific issues
* Verifying Docker-related functionality (like testcontainers)

CI-Specific Test Tasks
^^^^^^^^^^^^^^^^^^^^^^

These tasks are designed for CI environments and match the GitHub Actions workflow. They run tests
in the development Docker image using the host's Docker socket for testcontainers support.

**Testing CI Tasks Locally**

**Prerequisites**

First, build the development image with the appropriate platform:

.. code-block:: shell

    # On Linux or Intel Macs (AMD64):
    make buildc-dev VERSION=ci-test

    # On Apple Silicon Macs (ARM64) - for better performance:
    make buildc-dev VERSION=ci-test DOCKER_PLATFORM=linux/arm64

**Running CI Test Tasks**

The ``ci-test-*`` tasks mount the host Docker socket to allow testcontainers to work:

.. code-block:: shell

    # Run backend core tests (tests in harp/ directory)
    make ci-test-backend-core VERSION=ci-test

    # Run backend apps tests (tests in harp_apps/ directory)
    make ci-test-backend-apps VERSION=ci-test

    # Run backend e2e tests (tests in tests/ directory)
    make ci-test-backend-e2e VERSION=ci-test

    # Run frontend unit tests
    make ci-test-frontend-unit VERSION=ci-test

.. note::

   The CI tasks automatically detect and configure Docker socket permissions for both
   Linux (GNU stat) and macOS (BSD stat). If you encounter permission issues, ensure
   Docker Desktop is running and your user has access to ``/var/run/docker.sock``.

**Alternative: Using Docker-in-Docker**

If Docker socket mounting doesn't work, use the ``testc-*`` tasks which use Docker-in-Docker:

.. code-block:: shell

    # Run backend tests (all backend tests)
    make testc-backend

    # Run frontend tests
    make testc-frontend

    # Open interactive shell for debugging
    make testc-shell

**CI Task Behavior**

All ``ci-test-backend-*`` tasks:

* Use the development image (``DOCKER_IMAGE_DEV:VERSION``)
* Mount the host Docker socket for testcontainers
* Handle Docker socket permissions automatically (GID detection)
* Skip subprocess-marked tests (``-m 'not subprocess'``)
* Set ``UV_CACHE_DIR`` for reproducible builds
* Disable testcontainers Ryuk for faster cleanup (``TESTCONTAINERS_RYUK_DISABLED=true``)

Task-specific differences:

* ``ci-test-backend-core``: Tests ``harp/`` directory with parallel execution (no testcontainers)
* ``ci-test-backend-apps``: Tests ``harp_apps/`` directory with serial execution (``PYTEST_CPUS=1``, uses testcontainers)
* ``ci-test-backend-e2e``: Tests ``tests/`` directory with serial execution (``PYTEST_CPUS=1``, uses testcontainers)
* ``ci-test-frontend-unit``: Runs frontend unit tests with timezone set to ``America/Havana``

.. warning::

   The ``ci-test-backend-apps`` and ``ci-test-backend-e2e`` tasks use testcontainers which
   creates containers that need network connectivity. These tasks work in GitHub Actions
   Linux runners but may have networking issues on macOS/Windows Docker Desktop. For local
   testing with full testcontainers support, use ``make testc-backend`` instead.

**Required Variables**

When testing locally, you must specify:

* ``VERSION``: The image tag to use (e.g., ``ci-test``, ``latest``, or git commit)

**Optional Variables**

* ``DOCKER_IMAGE_DEV``: Dev image name (default: ``harp-proxy-dev``)
* ``CI_PYTEST_OPTIONS``: Override pytest options (default: ``-m 'not subprocess'``)
* ``CI_PYTEST_CPUS``: Override CPU count for specific tests

Code Quality
------------

Formatting
^^^^^^^^^^

.. code-block:: shell

    # Format everything (backend + frontend)
    make format

    # Format backend only (isort, black, ruff)
    make format-backend

    # Format frontend only (eslint, prettier)
    make format-frontend

Type Checking and QA
^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

    # Generate TypeScript types from Python models
    make types

    # Run pre-QA checks (types, format, reference docs)
    make preqa

    # Run full QA suite (preqa + tests)
    make qa

    # Run QA with all database backends (slower)
    make qa-full

    # Run QA without frontend tests
    make qa-nofront TEST_SKIP_FRONT=1

Frontend Linting
^^^^^^^^^^^^^^^^

.. code-block:: shell

    # Lint and build frontend (type checking)
    make lint-frontend

Frontend Development
--------------------

Building Frontend Assets
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

    # Build production frontend assets
    make build-frontend

This compiles TypeScript and bundles the frontend into ``harp_apps/dashboard/web/``.

Frontend Development Server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Frontend development is typically done with the dev server started by ``make start-dev-frontend``,
but you can also use the frontend tools directly:

.. code-block:: shell

    cd harp_apps/dashboard/frontend

    # Start dev server
    pnpm dev

    # Build for production
    pnpm build

    # Run Storybook component explorer
    pnpm ui:serve

Documentation
-------------

.. code-block:: shell

    # Generate API reference documentation
    make reference

    # Build HTML documentation
    make docs

    # Start live-reload documentation server
    make docs-dev

The documentation is built with Sphinx and placed in ``docs/_build/html/``.

Benchmarks
----------

.. code-block:: shell

    # Run benchmarks
    make benchmark

    # Run and save benchmark results
    make benchmark-save

    # Customize benchmark runs
    make benchmark BENCHMARK_MIN_ROUNDS=500 BENCHMARK_OPTIONS="--verbose"

Benchmarks use pytest-benchmark to measure performance. Results are saved in ``.benchmarks/``
and can be compared across runs. The ``benchmark-save`` target runs more iterations for
stable results.

Available benchmark variables:

* ``BENCHMARK_OPTIONS``: Additional benchmark options
* ``BENCHMARK_MIN_ROUNDS``: Minimum benchmark iterations (default: 100, 500 for save)

Docker Image Tasks
------------------

Building Images
^^^^^^^^^^^^^^^

.. code-block:: shell

    # Build runtime image (production)
    make buildc

    # Build development image
    make buildc-dev

    # Specify platform (useful for ARM64 Macs)
    make buildc PLATFORM=linux/arm64

    # Build with custom tag
    make buildc DOCKER_TAGS="1.0.0 latest"

Image Management
^^^^^^^^^^^^^^^^

.. code-block:: shell

    # Push runtime image
    make pushc

    # Push development image
    make pushc-dev

Running Containers
^^^^^^^^^^^^^^^^^^

.. code-block:: shell

    # Run runtime container interactively
    make runc

    # Run with custom command
    make runc DOCKER_RUN_COMMAND="server --help"

    # Open shell in runtime container
    make runc-shell

    # Run development container
    make runc-dev

    # Open shell in development container
    make runc-dev-shell

Available Docker environment variables:

* ``DOCKER_IMAGE``: Image name (default: ``harp-proxy``)
* ``DOCKER_IMAGE_DEV``: Dev image name (default: ``harp-proxy-dev``)
* ``DOCKER_TAGS``: Additional tags to apply
* ``DOCKER_BUILD_TARGET``: Build stage target (default: ``runtime``)
* ``DOCKER_OPTIONS``: Additional Docker options
* ``DOCKER_RUN_OPTIONS``: Additional run options
* ``DOCKER_RUN_COMMAND``: Command to run in container
* ``PLATFORM``: Target platform (default: ``linux/amd64``)

Cleanup
-------

.. code-block:: shell

    # Clean everything
    make clean

    # Clean frontend node_modules only
    make clean-frontend-modules

    # Clean distribution files
    make clean-dist

    # Clean documentation builds
    make clean-docs

Building Python Wheels
----------------------

.. code-block:: shell

    # Build distributable Python wheel
    make wheel

This creates a sandboxed environment, builds the frontend, packages everything,
and validates the wheel with ``twine``.

Miscellaneous
-------------

.. code-block:: shell

    # Count lines of code
    make cloc

    # Optimize images in documentation
    make optimize-images

Common Workflows
----------------

Starting a New Feature
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

    # 1. Install dependencies
    make install-dev

    # 2. Start development environment
    make start-dev

    # 3. Run tests as you develop
    make test-backend PYTEST_OPTIONS="-v -s"

    # 4. Format code before committing
    make format

    # 5. Run full QA suite
    make qa

Debugging CI Failures Locally
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

    # 1. Build the dev image locally
    make buildc-dev VERSION=debug

    # 2. Run the specific failing test suite
    # If core tests are failing:
    make ci-test-backend-core VERSION=debug

    # If apps tests are failing:
    make ci-test-backend-apps VERSION=debug

    # If e2e tests are failing:
    make ci-test-backend-e2e VERSION=debug

    # If frontend tests are failing:
    make ci-test-frontend-unit VERSION=debug

    # 3. Or open a shell to investigate interactively
    make runc-dev-shell VERSION=debug

    # 4. Inside the container, run tests manually with full control
    cd /opt/harp/src

    # Run specific test file
    uv run pytest tests/specific_test.py -v

    # Run with testcontainers (requires Docker socket access)
    DOCKER_HOST=unix:///var/run/docker.sock uv run pytest tests/storage/ -v

Working with Frontend
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

    # 1. Install frontend dependencies
    make install-frontend

    # 2. Start frontend dev server (needs backend separately)
    make start-dev-frontend

    # 3. In another terminal, run frontend tests
    cd harp_apps/dashboard/frontend
    pnpm test:unit

    # 4. Build production assets when ready
    make build-frontend

Best Practices
--------------

1. **Always use ``make install-dev``** before starting development to ensure all
   dependencies (including playwright browsers) are installed.

2. **Use Makefile tasks instead of direct commands** to ensure consistency with
   CI and avoid configuration drift.

3. **Test in Docker locally** before pushing if you're working on CI-related
   changes or Docker configuration.

4. **Run ``make format``** before committing to avoid formatting issues in CI.

5. **Use ``TEST_SKIP_FRONT=1``** when working on backend-only changes to speed
   up test runs.

6. **Set ``PYTEST_CPUS=1``** when debugging to avoid parallel execution issues.

Environment Variables Reference
-------------------------------

Global
^^^^^^

* ``NAME``: Package name (default: ``harp-proxy``)
* ``VERSION``: Version string from git
* ``UV``: Path to uv executable
* ``PYTEST``: Path to pytest executable
* ``PNPM``: Path to pnpm executable
* ``DOCKER``: Path to docker executable

Backend Testing
^^^^^^^^^^^^^^^

* ``PYTEST``: Path to pytest executable (default: ``uv run pytest``)
* ``PYTEST_TARGETS``: Test paths (default: ``harp harp_apps tests``)
* ``PYTEST_CPUS``: Parallel workers (default: ``auto``)
* ``PYTEST_COMMON_OPTIONS``: Common pytest options (default: ``-n $(PYTEST_CPUS)``)
* ``PYTEST_COVERAGE_OPTIONS``: Coverage reporting options
* ``PYTEST_OPTIONS``: Additional pytest arguments
* ``TEST_SKIP_FRONT``: Skip frontend tests if set
* ``TEST_ALL_DATABASES``: Test all database backends if set

Docker
^^^^^^

* ``DOCKER``: Path to docker executable
* ``DOCKER_IMAGE``: Runtime image name (default: ``harp-proxy``)
* ``DOCKER_IMAGE_DEV``: Development image name (default: ``harp-proxy-dev``)
* ``DOCKER_PLATFORM``: Target platform (default: ``linux/amd64``)
* ``DOCKER_TAGS``: Additional image tags
* ``DOCKER_TAGS_SUFFIX``: Suffix for image tags
* ``DOCKER_BUILD_TARGET``: Dockerfile stage target (default: ``runtime``)
* ``DOCKER_BUILD_OPTIONS``: Docker build options
* ``DOCKER_OPTIONS``: Additional Docker CLI options
* ``DOCKER_RUN_OPTIONS``: Additional docker run options
* ``DOCKER_RUN_COMMAND``: Container command
* ``DOCKER_NETWORK``: Docker network name (default: ``harp``)

CI Testing
^^^^^^^^^^

* ``CI_PYTEST_TARGETS``: Test paths for CI backend tests (used by ``ci-test-*`` targets)
* ``CI_PYTEST_OPTIONS``: Pytest options for CI (default: ``-m 'not subprocess'``)
* ``CI_PYTEST_CPUS``: CPU count for CI tests (set to ``1`` for apps/e2e tests)
* ``CI_PYTEST_FAILFAST``: Enable fail-fast mode (``--maxfail=1``) if set

Test Containers
^^^^^^^^^^^^^^^

* ``TESTC_COMMAND``: Command to run in test container shell (default: ``bash``)
* ``TESTC_TZ``: Timezone for frontend test containers (default: ``America/Havana``)
* ``TESTC_FRONTEND_IMAGE``: Frontend test container image
* ``TESTC_FRONTEND_INTERACTIVE``: Interactive mode for frontend tests

Frontend
^^^^^^^^

* ``PNPM``: Path to pnpm executable
* ``TEST_SKIP_FRONT``: Skip frontend tests if set

Development
^^^^^^^^^^^

* ``HARP_OPTIONS``: Runtime options for start-dev (default: ``--example sqlite --example proxy:httpbin``)
* ``HARP_MORE_OPTIONS``: Additional runtime options
* ``HARP_SERVICES``: Services to start (default: ``server dashboard``)

UV/Build Tools
^^^^^^^^^^^^^^

* ``UV``: Path to uv executable
* ``UVX``: Path to uvx executable
* ``UV_RUN``: UV run command prefix
* ``UV_SYNC_OPTIONS``: Options for uv sync
* ``SED``: Path to sed executable (gsed or sed)
