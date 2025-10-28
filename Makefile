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
PYTHON_VERSION ?= 3.14

# frontend
PNPM ?= $(shell which pnpm || echo "pnpm")

# misc.
SED ?= $(shell which gsed || which sed || echo "sed")
TEST_SKIP_FRONT ?=

# constants
FRONTEND_DIR = harp_apps/dashboard/frontend

# harp
#
# todo: options vs more options should be clarified
HARP_OPTIONS ?= --example sqlite --example proxy:httpbin
HARP_MORE_OPTIONS ?=
HARP_SERVICES ?= server dashboard

.PHONY: start-dev start-dev-frontend
start-dev: install-dev  ## Starts a development instance with reasonable defaults.
	$(UV_RUN) $(NAME) start $(HARP_SERVICES) $(HARP_OPTIONS) $(HARP_MORE_OPTIONS)

start-dev-frontend: install-dev  ## Starts a frontend development instance (dashboard only on port 12121).
	HARP_SERVICES=dashboard HARP_MORE_OPTIONS="--set dashboard.devserver.port=12121" $(MAKE) start-dev


########################################################################################################################
# Dependencies
########################################################################################################################

.PHONY: install install-dev install-frontend install-backend install-backend-dev

install: install-frontend install-backend  ## Installs harp dependencies (backend, dashboard) without development tools.

install-dev: install-backend-dev  ## Installs harp dependencies (backend, dashboard) with development tools.

install-frontend:  ## Installs harp dashboard dependencies (frontend).
	cd $(FRONTEND_DIR); $(PNPM) install

install-backend:  ## Installs harp dependencides (backend).
	$(if $(UV),$(UV) sync $(UV_SYNC_OPTIONS),pip install -e .)

install-backend-dev:  ## Installs harp dependencies (backend) with development tools.
	UV_SYNC_OPTIONS="--extra dev" $(MAKE) install-backend


########################################################################################################################
# Documentation
########################################################################################################################

.PHONY: reference docs docs-dev

reference: harp  ## Generates API reference documentation as ReST files (docs).
	rm -rf docs/reference/core docs/reference/apps
	mkdir -p docs/reference/core docs/reference/apps
	$(UV_RUN) bin/generate_apidoc
	git add docs/reference/

docs:  ## Build html documentation
	$(UV_RUN) $(MAKE) -C docs html

docs-dev:  ## Spin up a livereload documentation server
	$(UV_RUN) $(MAKE) -C docs dev


########################################################################################################################
# Dashboard application
########################################################################################################################

.PHONY: build-frontend

build-frontend: install-frontend  ## Builds the harp dashboard frontend (compiles typescript and other sources into bundled version).
	cd $(FRONTEND_DIR); $(PNPM) build


########################################################################################################################
# QA, tests and other CI/CD related stuff
########################################################################################################################

.PHONY: preqa qa qa-full types format format-backend format-frontend optimize-images
.PHONY: test test-backend test-frontend test-frontend-update test-frontend-ui-update
.PHONY: lint-frontend coverage cloc

preqa: types format reference  ## Runs pre-qa checks (types generation, formatting, api reference).
	-$(UV_RUN) pre-commit

qa: preqa test  ## Runs all QA checks, with most common databases.

qa-full:  ## Runs all QA checks, including all supported databases.
	TEST_ALL_DATABASES=true $(MAKE) qa

qa-nofront:  ## Runs all QA checks without frontend tests.
	TEST_SKIP_FRONT=1 $(MAKE) qa

types:  ## Generates frontend types from the python code.
	$(UV_RUN) bin/generate_types # old school
	$(UV_RUN) bin/generate_ts_types # new school

format:  ## Formats the full codebase (backend and frontend).
	$(MAKE) format-backend
	test -z "$(TEST_SKIP_FRONT)" && $(MAKE) format-frontend || (cd $(FRONTEND_DIR); $(PNPM) prettier -w src/Models)

format-backend:  ## Formats the backend codebase.
	$(UV_RUN) ruff check --fix harp harp_apps tests
	$(UV_RUN) ruff format

format-frontend: install-frontend  ## Formats the frontend codebase.
	(cd $(FRONTEND_DIR); $(PNPM) lint:fix)
	(cd $(FRONTEND_DIR); $(PNPM) prettier -w src)

optimize-images:  ## Optimizes PNG images in documentation.
	find docs -name \*.png | xargs optimizt

test:  ## Runs all tests.
	$(MAKE) test-backend
	test -z "$(TEST_SKIP_FRONT)" && $(MAKE) test-frontend || echo "Skipped."

test-backend: install-backend-dev  ## Runs backend tests.
	$(PYTEST) $(PYTEST_TARGETS) \
	          $(PYTEST_COMMON_OPTIONS) \
	          $(PYTEST_OPTIONS)

test-backend-update:  ## Runs backend tests while updating snapshots.
	PYTEST_OPTIONS="$(PYTEST_OPTIONS) --snapshot-update" $(MAKE) test-backend

test-frontend: install-frontend lint-frontend  ## Runs frontend tests.
	cd $(FRONTEND_DIR); $(PNPM) test:unit
	cd $(FRONTEND_DIR); $(PNPM) test:browser
	bin/runc_visualtests pnpm test:ui:dev

test-frontend-update: install-frontend lint-frontend  ## Runs frontend tests while updating snapshots.
	cd $(FRONTEND_DIR); $(PNPM) test:unit:update

test-frontend-ui-update: install-frontend lint-frontend  ## Update user interface visual snapshots.
	bin/runc_visualtests pnpm test:ui:update

lint-frontend: install-frontend  ## Lints the frontend codebase.
	cd $(FRONTEND_DIR); $(PNPM) build

coverage:  ## Generates coverage report.
	$(PYTEST) $(PYTEST_TARGETS) tests \
	          -m 'not subprocess' \
	          $(PYTEST_COVERAGE_OPTIONS) \
	          $(PYTEST_COMMON_OPTIONS) \
	          $(PYTEST_OPTIONS)

cloc:  ## Counts lines of code in the project.
	cloc harp harp_apps tests  --exclude-dir=node_modules,build,dist


########################################################################################################################
# Docker builds
########################################################################################################################

.PHONY: buildc buildc-pypi pushc runc runc-shell runc-example-repositories

buildc: wheel  ## Builds the docker image from wheel (supports PYTHON_VERSION=3.13 or 3.14).
	$(DOCKER) build \
		$(DOCKER_OPTIONS) \
		$(DOCKER_BUILD_OPTIONS) \
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
		--build-arg INSTALL_FROM=local \
		--build-arg VERSION=$(VERSION) \
		-t $(DOCKER_IMAGE) \
		$(foreach tag,$(VERSION) $(DOCKER_TAGS),-t $(DOCKER_IMAGE):$(tag)$(DOCKER_TAGS_SUFFIX)) \
		.

buildc-pypi:  ## Builds the docker image from PyPI (requires VERSION, supports PYTHON_VERSION=3.13 or 3.14).
	@if [ -z "$(VERSION)" ]; then \
		echo "ERROR: VERSION is required. Usage: make buildc-pypi VERSION=0.9.0"; \
		exit 1; \
	fi
	$(DOCKER) build \
		$(DOCKER_OPTIONS) \
		$(DOCKER_BUILD_OPTIONS) \
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
		--build-arg VERSION=$(VERSION) \
		-f Dockerfile.pypi \
		-t $(DOCKER_IMAGE) \
		$(foreach tag,$(VERSION) $(DOCKER_TAGS),-t $(DOCKER_IMAGE):$(tag)$(DOCKER_TAGS_SUFFIX)) \
		.

pushc:  ## Pushes the docker image to the registry.
	for tag in $(VERSION) $(DOCKER_TAGS); do \
		$(DOCKER) image push $(DOCKER_IMAGE):$$tag$(DOCKER_TAGS_SUFFIX); \
	done

runc:  ## Runs the docker image.
	$(DOCKER) network create $(DOCKER_NETWORK) 2>/dev/null || true
	$(DOCKER) run $(DOCKER_TTY) --init --network $(DOCKER_NETWORK) $(DOCKER_OPTIONS) $(DOCKER_RUN_OPTIONS) -p 4000-4999:4000-4999 --rm $(DOCKER_IMAGE) $(DOCKER_RUN_COMMAND)

runc-shell:  ## Runs a shell within the docker image.
	$(DOCKER) network create $(DOCKER_NETWORK) 2>/dev/null || true
	$(DOCKER) run $(DOCKER_INTERACTIVE) --init --network $(DOCKER_NETWORK) $(DOCKER_OPTIONS) $(DOCKER_RUN_OPTIONS) -p 4080:4080 --rm --entrypoint=/bin/bash $(DOCKER_IMAGE) $(DOCKER_RUN_COMMAND)




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
	@grep -E '^(preqa|qa|qa-full|qa-nofront|test|test-backend|test-frontend|test-backend-update|test-frontend-update|test-frontend-ui-update|lint-frontend|format|format-backend|format-frontend|types|coverage|cloc|optimize-images):.*?##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?##"}; {printf "    make \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "\033[1mDocumentation\033[0m"
	@grep -E '^(reference|docs|docs-dev):.*?##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?##"}; {printf "    make \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "\033[1mContainers\033[0m"
	@grep -E '^(buildc|buildc-pypi|pushc|runc|runc-shell):.*?##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?##"}; {printf "    make \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "\033[1mMiscellaneous\033[0m"
	@grep -E '^(help|clean|clean-dist|clean-docs|clean-frontend-modules):.*?##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?##"}; {printf "    make \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo

wheel:  ## Builds a python wheel (sandboxed)
	mkdir -p dist
	bin/sandbox "$(MAKE) install-dev build-frontend; \
				 rm -rf harp_apps/dashboard/frontend harp_apps/dashboard/web/src; \
				 sed '/^People & Credits/,$$ d' README.rst > README.rst.tmp; \
				 mv README.rst.tmp README.rst; \
				 $(if $(UV),$(UV) build,python -m build); \
				 cp dist/* $(PWD)/dist; \
				 $(if $(UVX),$(UVX) twine check dist/*,twine check dist/*)"

clean-frontend-modules:  ## Cleans up the frontend node modules directory.
	-rm -rf $(FRONTEND_DIR)/node_modules

clean-dist:  ## Cleans up the distribution files (wheels...)
	-rm -rf $(FRONTEND_DIR)/dist
	-rm -rf dist

clean-docs:  ## Cleanup the documentation builds.
	-rm -rf docs/_build

clean: clean-frontend-modules clean-dist clean-docs  ## Cleans up the project.
