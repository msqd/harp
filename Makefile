########################################################################################################################
# Makefile - This is the main entry point for all development related tasks.
#
# It contains wrappers for everything one may need to work with the codebase (install, test, format, lint, build,
# container related stuff, releasing, etc...).
#
# To have an overview, just run `make help`.
#
# Documentation is available in the `docs/contribute/makefile.rst` and should be kept in sync with this file.
#
# The continuous integration process (and basically all automated processes) uses this file as well, so be careful when
# changing things.
########################################################################################################################

# package
NAME ?= harp-proxy
VERSION ?= $(shell git describe 2>/dev/null || git rev-parse --short HEAD)
DEBUG ?=

# uv
UV ?= $(shell which uv || echo "")
UVX ?= $(shell which uvx || echo "uvx")
UV_RUN ?= $(if $(UV),$(UV) run,)
UV_SYNC_OPTIONS ?=

# pytest
PYTEST ?= $(UV_RUN) pytest
PYTEST_TARGETS ?= harp harp_apps tests
PYTEST_CPUS ?= auto
PYTEST_COMMON_OPTIONS ?= -n $(PYTEST_CPUS)
PYTEST_COVERAGE_OPTIONS ?= --cov=harp --cov=harp_apps --cov-report html:docs/_build/html/coverage
PYTEST_OPTIONS ?=

# docker
DOCKER_PLATFORM ?= $(shell uname -m | sed -E 's/^x86_64$$/linux\/amd64/;s/^(aarch64|arm64)$$/linux\/arm64/')
DOCKER ?= $(shell which docker || echo "docker")
DOCKER_TTY ?= $(shell [ -t 0 ] && echo "-t" || echo "")
DOCKER_INTERACTIVE ?= $(shell [ -t 0 ] && echo "-it" || echo "-t")
DOCKER_OPTIONS ?=
DOCKER_IMAGE ?= $(NAME)
DOCKER_TAGS ?=
DOCKER_TAGS_SUFFIX ?=
DOCKER_BUILD_OPTIONS ?= --platform=$(DOCKER_PLATFORM)
DOCKER_NETWORK ?= harp
DOCKER_RUN_COMMAND ?=
DOCKER_RUN_OPTIONS ?=
PYTHON_VERSION ?= 3.13

# frontend
PNPM ?= $(shell which pnpm || echo "pnpm")

# misc.
SED ?= $(shell which gsed || which sed || echo "sed")
TEST_SKIP_FRONT ?=
COMMA := ,

# constants
FRONTEND_DIR = harp_apps/dashboard/frontend

# helpers
define execute
@echo "⚙️ \033[36m$@\033[0m: \033[2m$(1)\033[0m"
@$(1)
endef

# harp
#
# todo: options vs more options should be clarified
HARP_OPTIONS ?= --example sqlite --example proxy:httpbin
HARP_MORE_OPTIONS ?=
HARP_SERVICES ?= server dashboard

.PHONY: start-dev start-dev-frontend kitchen-sink
start-dev: install-dev  ## Starts a development instance with reasonable defaults.
	$(UV_RUN) $(NAME) start $(HARP_SERVICES) $(HARP_OPTIONS) $(HARP_MORE_OPTIONS)

start-dev-frontend: install-dev  ## Starts a frontend development instance (dashboard only on port 12121).
	HARP_SERVICES=dashboard HARP_MORE_OPTIONS="--set dashboard.devserver.port=12121" $(MAKE) start-dev

kitchen-sink:  ## Starts the kitchen-sink demo environment (docker compose + harp-proxy with auto-reload).
	$(MAKE) -C misc/kitchen-sink start


########################################################################################################################
# Dependencies
########################################################################################################################

.PHONY: install install-dev install-frontend install-backend install-backend-dev

install: install-frontend install-backend  ## Installs harp dependencies (backend, dashboard) without development tools.

install-dev: install-backend-dev  ## Installs harp dependencies (backend, dashboard) with development tools.

install-frontend:  ## Installs harp dashboard dependencies (frontend).
	@mkdir -p harp_apps/dashboard/web
	$(call execute,cd $(FRONTEND_DIR); $(PNPM) install $(if $(DEBUG),,--silent))

install-backend:  ## Installs harp dependencides (backend).
	@mkdir -p harp_apps/dashboard/web
	$(call execute,$(if $(UV),$(UV) sync $(if $(DEBUG),,--quiet) $(UV_SYNC_OPTIONS),pip install -e .))

install-backend-dev:  ## Installs harp dependencies (backend) with development tools.
	$(call execute,UV_SYNC_OPTIONS="--group dev" $(MAKE) install-backend)


########################################################################################################################
# Documentation
########################################################################################################################

.PHONY: reference docs docs-dev

reference: harp  ## Generates API reference documentation as ReST files (docs).
	rm -rf docs/reference/core docs/reference/apps
	mkdir -p docs/reference/core docs/reference/apps
	$(UV_RUN) bin/generate_apidoc
	-git add docs/reference/

docs:  ## Build html documentation
	$(call execute,$(UV_RUN) $(MAKE) -C docs html)

docs-dev:  ## Spin up a livereload documentation server
	$(call execute,$(UV_RUN) $(MAKE) -C docs dev)


########################################################################################################################
# Dashboard application
########################################################################################################################

.PHONY: build-frontend

build-frontend: install-frontend  ## Builds the harp dashboard frontend (compiles typescript and other sources into bundled version).
	$(call execute,cd $(FRONTEND_DIR); $(PNPM) build)


########################################################################################################################
# QA, tests and other CI/CD related stuff
########################################################################################################################

.PHONY: preqa qa qa-full types format format-backend format-frontend optimize-images
.PHONY: test test-backend test-frontend test-frontend-update test-frontend-ui-update test-e2e-cache
.PHONY: lint-frontend coverage cloc

preqa: types format reference  ## Runs pre-qa checks (types generation, formatting, api reference).
	$(call execute,-$(UV_RUN) pre-commit)

qa: preqa test  ## Runs all QA checks, with most common databases.

qa-full:  ## Runs all QA checks, including all supported databases.
	$(call execute,TEST_ALL_DATABASES=true $(MAKE) qa)

qa-nofront:  ## Runs all QA checks without frontend tests.
	$(call execute,TEST_SKIP_FRONT=1 $(MAKE) qa)

types: install-frontend  ## Generates frontend types from the python code.
	$(call execute,$(UV_RUN) bin/generate_types)
	$(call execute,$(UV_RUN) bin/generate_ts_types)

format:  ## Formats the full codebase (backend and frontend).
	$(call execute,$(MAKE) format-backend)
	$(call execute,test -z "$(TEST_SKIP_FRONT)" && $(MAKE) format-frontend || (cd $(FRONTEND_DIR); $(PNPM) prettier -w src/Models))

format-backend:  ## Formats the backend codebase.
	$(call execute,$(UV_RUN) ruff check --fix harp harp_apps tests)
	$(call execute,$(UV_RUN) ruff format)

format-frontend: install-frontend  ## Formats the frontend codebase.
	$(call execute,(cd $(FRONTEND_DIR); $(PNPM) lint:fix $(if $(DEBUG),,--quiet)))
	$(call execute,(cd $(FRONTEND_DIR); $(PNPM) prettier -w src $(if $(DEBUG),,--log-level=warn)))

optimize-images:  ## Optimizes PNG images in documentation.
	find docs -name \*.png | xargs optimizt

test:  ## Runs all tests.
	@# Both suites run even if the first one fails, and the target's exit status reflects what
	@# actually happened. A suite skipped on request is not a suite that failed, so the two are
	@# reported differently and only the second one is an error.
	@echo "⚙️ \033[36m$@\033[0m: \033[2m$(MAKE) test-backend, then test-frontend unless TEST_SKIP_FRONT\033[0m"
	@rc=0; \
	$(MAKE) test-backend || rc=1; \
	if [ -z "$(TEST_SKIP_FRONT)" ]; then \
		$(MAKE) test-frontend || rc=1; \
	else \
		echo "⚙️ \033[36m$@\033[0m: \033[2mfrontend tests skipped on request (TEST_SKIP_FRONT is set).\033[0m"; \
	fi; \
	if [ $$rc -ne 0 ]; then \
		echo "❌ \033[31m$@\033[0m: \033[2mat least one suite failed, see above.\033[0m"; \
	fi; \
	exit $$rc

test-backend: install-backend-dev  ## Runs backend tests.
	$(call execute,$(PYTEST) $(PYTEST_TARGETS) $(PYTEST_COMMON_OPTIONS) $(PYTEST_OPTIONS))

test-backend-update:  ## Runs backend tests while updating snapshots.
	$(call execute,PYTEST_OPTIONS="$(PYTEST_OPTIONS) --snapshot-update" $(MAKE) test-backend)

test-frontend: install-frontend lint-frontend  ## Runs frontend tests.
	$(call execute,cd $(FRONTEND_DIR); $(PNPM) test:unit)
	$(call execute,cd $(FRONTEND_DIR); $(PNPM) test:browser)
	$(call execute,bin/runc_visualtests pnpm test:ui:dev)

test-frontend-update: install-frontend lint-frontend  ## Runs frontend tests while updating snapshots.
	$(call execute,cd $(FRONTEND_DIR); $(PNPM) test:unit:update)

test-frontend-ui-update: install-frontend lint-frontend  ## Update user interface visual snapshots.
	$(call execute,bin/runc_visualtests pnpm test:ui:update)

test-e2e-cache: install-backend-dev  ## Runs E2E cache tests using cache-tests suite.
	@echo "Initializing cache-tests submodule..."
	@git submodule update --init --recursive misc/cache-tests/cache-tests 2>/dev/null || true
	$(call execute,cd misc/cache-tests && ./run-tests.sh)

lint-frontend: install-frontend  ## Lints the frontend codebase.
	$(call execute,cd $(FRONTEND_DIR); $(PNPM) build)

coverage:  ## Generates coverage report.
	$(call execute,$(PYTEST) $(PYTEST_TARGETS) tests -m 'not subprocess' $(PYTEST_COVERAGE_OPTIONS) $(PYTEST_COMMON_OPTIONS) $(PYTEST_OPTIONS))

cloc:  ## Counts lines of code in the project.
	$(call execute,cloc harp harp_apps tests --exclude-dir=node_modules$(COMMA)build$(COMMA)dist)


########################################################################################################################
# Docker builds
########################################################################################################################

.PHONY: buildc buildc-pypi pushc runc runc-shell runc-example-repositories

buildc: wheel  ## Builds the docker image from wheel (supports PYTHON_VERSION=3.13 or 3.14).
	$(call execute,$(DOCKER) build $(DOCKER_OPTIONS) $(DOCKER_BUILD_OPTIONS) --build-arg PYTHON_VERSION=$(PYTHON_VERSION) --build-arg INSTALL_FROM=local --build-arg VERSION=$(VERSION) -t $(DOCKER_IMAGE) $(foreach tag,$(VERSION) $(DOCKER_TAGS),-t $(DOCKER_IMAGE):$(tag)$(DOCKER_TAGS_SUFFIX)) .)

buildc-pypi:  ## Builds the docker image from PyPI (requires VERSION, supports PYTHON_VERSION=3.13 or 3.14).
	@if [ -z "$(VERSION)" ]; then \
		echo "ERROR: VERSION is required. Usage: make buildc-pypi VERSION=0.9.0"; \
		exit 1; \
	fi
	$(call execute,$(DOCKER) build $(DOCKER_OPTIONS) $(DOCKER_BUILD_OPTIONS) --build-arg PYTHON_VERSION=$(PYTHON_VERSION) --build-arg VERSION=$(VERSION) -f Dockerfile.pypi -t $(DOCKER_IMAGE) $(foreach tag,$(VERSION) $(DOCKER_TAGS),-t $(DOCKER_IMAGE):$(tag)$(DOCKER_TAGS_SUFFIX)) .)

pushc:  ## Pushes the docker image to the registry.
	$(call execute,for tag in $(VERSION) $(DOCKER_TAGS); do $(DOCKER) image push $(DOCKER_IMAGE):$$tag$(DOCKER_TAGS_SUFFIX); done)

runc:  ## Runs the docker image.
	$(call execute,$(DOCKER) network create $(DOCKER_NETWORK) 2>/dev/null || true)
	$(call execute,$(DOCKER) run $(DOCKER_TTY) --init --network $(DOCKER_NETWORK) $(DOCKER_OPTIONS) $(DOCKER_RUN_OPTIONS) -p 4000-4999:4000-4999 --rm $(DOCKER_IMAGE) $(DOCKER_RUN_COMMAND))

runc-shell:  ## Runs a shell within the docker image.
	$(call execute,$(DOCKER) network create $(DOCKER_NETWORK) 2>/dev/null || true)
	$(call execute,$(DOCKER) run $(DOCKER_INTERACTIVE) --init --network $(DOCKER_NETWORK) $(DOCKER_OPTIONS) $(DOCKER_RUN_OPTIONS) -p 4080:4080 --rm --entrypoint=/bin/bash $(DOCKER_IMAGE) $(DOCKER_RUN_COMMAND))




########################################################################################################################
# Misc. utilities
########################################################################################################################

.PHONY: help clean clean-dist clean-docs clean-frontend-modules wheel

help:   ## Shows available commands.
	@echo "Available commands:"
	@echo
	@echo "\033[1mInstall & Build\033[0m"
	@grep -E '^(install|install-dev|install-frontend|install-backend|install-backend-dev|start-dev|start-dev-frontend|build-frontend|wheel):.*?##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?##"}; {printf "    make \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "\033[1mQuality\033[0m"
	@grep -E '^(preqa|qa|qa-full|qa-nofront|test|test-backend|test-frontend|test-backend-update|test-frontend-update|test-frontend-ui-update|test-e2e-cache|lint-frontend|format|format-backend|format-frontend|types|coverage|cloc|optimize-images):.*?##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?##"}; {printf "    make \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "\033[1mDocumentation\033[0m"
	@grep -E '^(reference|docs|docs-dev):.*?##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?##"}; {printf "    make \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "\033[1mContainers\033[0m"
	@grep -E '^(buildc|buildc-pypi|pushc|runc|runc-shell):.*?##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?##"}; {printf "    make \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "\033[1mMiscellaneous\033[0m"
	@grep -E '^(help|kitchen-sink|clean|clean-dist|clean-docs|clean-frontend-modules):.*?##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?##"}; {printf "    make \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo

wheel:  ## Builds a python wheel (sandboxed)
	@mkdir -p dist
	$(call execute,PWD_ORIG=$(PWD) UV=$(UV) UVX=$(UVX) bin/sandbox bin/build_wheel)

clean-frontend-modules:  ## Cleans up the frontend node modules directory.
	-rm -rf $(FRONTEND_DIR)/node_modules

clean-dist:  ## Cleans up the distribution files (wheels...)
	-rm -rf $(FRONTEND_DIR)/dist
	-rm -rf dist

clean-docs:  ## Cleanup the documentation builds.
	-rm -rf docs/_build

clean: clean-frontend-modules clean-dist clean-docs  ## Cleans up the project.
