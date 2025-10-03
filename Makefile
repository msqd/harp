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
DOCKER_INTERACTIVE ?= $(shell [ -t 0 ] && echo "-it" || echo "-t")
DOCKER_OPTIONS ?=
DOCKER_IMAGE ?= $(NAME)
DOCKER_IMAGE_DEV ?= $(NAME)-dev
DOCKER_TAGS ?=
DOCKER_TAGS_SUFFIX ?=
DOCKER_BUILD_OPTIONS ?= --platform=$(DOCKER_PLATFORM)
DOCKER_BUILD_TARGET ?= runtime
DOCKER_NETWORK ?= harp
DOCKER_RUN_COMMAND ?=
DOCKER_RUN_OPTIONS ?=

# frontend
PNPM ?= $(shell which pnpm || echo "pnpm")

# misc.
SED ?= $(shell which gsed || which sed || echo "sed")
TESTC_COMMAND ?= bash
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
start-dev: install-dev  # Starts a development instance with reasonable defaults (tune HARP_OPTIONS to replace).
	$(UV_RUN) $(NAME) start $(HARP_SERVICES) $(HARP_OPTIONS) $(HARP_MORE_OPTIONS)

start-dev-frontend: install-dev  # Starts a frontend development instance with reasonable defaults (you'll have to a backend, useful to use an external debugger for example).
	HARP_SERVICES=dashboard HARP_MORE_OPTIONS="--set dashboard.devserver.port=12121" $(MAKE) start-dev


########################################################################################################################
# Dependencies
########################################################################################################################

.PHONY: install install-dev install-frontend install-backend install-backend-dev

install: install-frontend install-backend  ## Installs harp dependencies (backend, dashboard) without development tools.

install-dev: install-backend-dev  ## Installs harp dependencies (backend, dashboard) with development tools.
	cd $(FRONTEND_DIR); $(PNPM) exec playwright install

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

qa-nofront:
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

optimize-images:
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

cloc:
	cloc harp harp_apps tests  --exclude-dir=node_modules,build,dist


########################################################################################################################
# Docker builds
########################################################################################################################

.PHONY: buildc pushc runc runc-shell runc-example-repositories

buildc:  ## Builds the docker image.
	# Set up cleanup trap to ensure version.txt is removed even on error
	# Use --progress=plain for more detailed build output (useful for CI/debugging)
	trap 'rm -f version.txt' EXIT; \
	echo $(VERSION) > version.txt && \
	$(DOCKER) build --target=$(DOCKER_BUILD_TARGET) $(DOCKER_OPTIONS) $(DOCKER_BUILD_OPTIONS) -t $(DOCKER_IMAGE) $(foreach tag,$(VERSION) $(DOCKER_TAGS),-t $(DOCKER_IMAGE):$(tag)$(DOCKER_TAGS_SUFFIX)) .

pushc:  ## Pushes the docker image to the registry.
	for tag in $(VERSION) $(DOCKER_TAGS); do \
		$(DOCKER) image push $(DOCKER_IMAGE):$$tag$(DOCKER_TAGS_SUFFIX); \
	done

runc:  ## Runs the docker image.
	$(DOCKER) network create $(DOCKER_NETWORK) 2>/dev/null || true
	$(DOCKER) run $(DOCKER_INTERACTIVE) --network $(DOCKER_NETWORK) $(DOCKER_OPTIONS) $(DOCKER_RUN_OPTIONS) -p 4000-4999:4000-4999 --rm $(DOCKER_IMAGE) $(DOCKER_RUN_COMMAND)

runc-shell:  ## Runs a shell within the docker image.
	$(DOCKER) network create $(DOCKER_NETWORK) 2>/dev/null || true
	$(DOCKER) run $(DOCKER_INTERACTIVE) --network $(DOCKER_NETWORK) $(DOCKER_OPTIONS) $(DOCKER_RUN_OPTIONS) -p 4080:4080 --rm --entrypoint=/bin/bash $(DOCKER_IMAGE) $(DOCKER_RUN_COMMAND)


.PHONY: buildc-dev pushc-dev runc-dev runc-dev-shell

buildc-dev:  ## Builds the development docker image.
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) DOCKER_BUILD_TARGET=development $(MAKE) buildc

pushc-dev:  ## Pushes the development docker image to the registry.
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) $(MAKE) pushc

runc-dev:  ## Runs the development docker image.
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) $(MAKE) runc

runc-dev-shell:  ## Runs a shell within the development docker image.
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) $(MAKE) runc-shell


.PHONY: testc-shell testc-backend testc-frontend

# Test container configuration variables
TESTC_TZ ?= America/Havana

testc-shell:  ## Runs a shell in the development test suite environment.
	@_DIND_CONTAINER="dind-$$(date +%s)-$$$$" && \
	_DOCKER_NETWORK="harp-$$(date +%s)-$$$$" && \
	trap "$(DOCKER) stop $$_DIND_CONTAINER 2>/dev/null || true; \
	      $(DOCKER) rm $$_DIND_CONTAINER 2>/dev/null || true; \
	      $(DOCKER) network rm $$_DOCKER_NETWORK 2>/dev/null || true" EXIT && \
	$(DOCKER) network create $$_DOCKER_NETWORK && \
	$(DOCKER) run --privileged -d \
		--name $$_DIND_CONTAINER \
		--network $$_DOCKER_NETWORK \
		--network-alias docker \
		-e DOCKER_TLS_CERTDIR= \
		$(DOCKER_OPTIONS) \
		$(DOCKER_RUN_OPTIONS) \
		docker:24.0.6-dind && \
	DOCKER_OPTIONS="-e DOCKER_HOST=tcp://docker:2375/" \
	DOCKER_RUN_COMMAND="-c \"bin/wait-until-docker-available && (cd src; $(TESTC_COMMAND))\"" \
	DOCKER_NETWORK=$$_DOCKER_NETWORK \
	$(MAKE) runc-dev-shell

testc-backend:  ## Runs the backend test suite within the development docker image, with a docker in docker sidecar service.
	DOCKER_OPTIONS="-e DOCKER_HOST=tcp://docker:2375/" TESTC_COMMAND="PYTEST_OPTIONS=-vv make test-backend" $(MAKE) testc-shell

testc-frontend:  ## Runs the frontend test suite within the development docker image.
	@_DOCKER_NETWORK="harp-$$(date +%s)-$$$$" && \
	trap "$(DOCKER) network rm $$_DOCKER_NETWORK 2>/dev/null || true" EXIT && \
	$(DOCKER) network create $$_DOCKER_NETWORK && \
	$(DOCKER) run $(DOCKER_INTERACTIVE) --rm \
		--network $$_DOCKER_NETWORK \
		-e TZ=$(TESTC_TZ) \
		$(DOCKER_IMAGE_DEV) \
		bash -c "cd /opt/harp/src/harp_apps/dashboard/frontend && \
		         pnpm test:unit"


# CI test configuration variables
CI_PYTEST_TARGETS ?=
CI_PYTEST_OPTIONS ?= -m 'not subprocess'
CI_PYTEST_CPUS ?=
CI_PYTEST_FAILFAST ?=

# Internal target for running backend tests in CI environment
# Parameters: CI_PYTEST_TARGETS (required), CI_PYTEST_OPTIONS, CI_PYTEST_CPUS, CI_PYTEST_FAILFAST
_ci-run-backend-test:
	$(eval DOCKER_GID := $(shell stat -c '%g' /var/run/docker.sock 2>/dev/null || stat -f '%g' /var/run/docker.sock 2>/dev/null || stat -f '%g' ~/.docker/run/docker.sock 2>/dev/null || echo ""))
	$(eval CI_PYTEST_OPTIONS_WITH_FAILFAST := $(CI_PYTEST_OPTIONS)$(if $(CI_PYTEST_FAILFAST), --maxfail=1,))
	$(DOCKER) run --rm \
		--privileged \
		$(if $(DOCKER_GID),--group-add $(DOCKER_GID),) \
		--group-add 0 \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-e PYTEST=/opt/venv/bin/pytest \
		-e PYTEST_OPTIONS="$(CI_PYTEST_OPTIONS_WITH_FAILFAST)" \
		-e PYTEST_TARGETS=$(CI_PYTEST_TARGETS) \
		$(if $(CI_PYTEST_CPUS),-e PYTEST_CPUS=$(CI_PYTEST_CPUS),) \
		-e DOCKER_HOST=unix:///var/run/docker.sock \
		-e UV_CACHE_DIR=/tmp/.uv-cache \
		-e TESTCONTAINERS_RYUK_DISABLED=true \
		$(DOCKER_IMAGE_DEV):$(VERSION) \
		bash -c "cd /opt/harp/src && make test-backend"

.PHONY: ci-test-backend-core ci-test-backend-apps ci-test-backend-e2e ci-test-frontend-unit

# CI test tasks - these run tests in the dev container with CI-specific configuration
ci-test-backend-core:  ## Runs backend core tests in CI environment (requires dev image to be built)
	CI_PYTEST_TARGETS=harp $(MAKE) _ci-run-backend-test

ci-test-backend-apps:  ## Runs backend apps tests in CI environment (requires dev image to be built)
	CI_PYTEST_TARGETS=harp_apps CI_PYTEST_CPUS=1 $(MAKE) _ci-run-backend-test

ci-test-backend-e2e:  ## Runs backend e2e tests in CI environment (requires dev image to be built)
	CI_PYTEST_TARGETS=tests CI_PYTEST_CPUS=1 $(MAKE) _ci-run-backend-test

ci-test-frontend-unit:  ## Runs frontend unit tests in CI environment (requires dev image to be built)
	DOCKER_IMAGE_DEV=$(DOCKER_IMAGE_DEV):$(VERSION) DOCKER_INTERACTIVE="" $(MAKE) testc-frontend


########################################################################################################################
# Misc. utilities
########################################################################################################################

.PHONY: help clean clean-dist clean-docs clean-frontend-modules wheel

help:   ## Shows available commands.
	@echo "Available commands:"
	@echo
	@grep -E '^[a-zA-Z0-9_-]+:.*?##[\s]?.*$$' --no-filename $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?##"}; {printf "    make \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo

wheel:
	mkdir -p dist
	bin/sandbox "$(MAKE) install-dev build-frontend; \
				 rm -rf harp_apps/dashboard/frontend; \
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
