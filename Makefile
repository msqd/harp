# package
NAME ?= harp-proxy
VERSION ?= $(shell git describe 2>/dev/null || git rev-parse --short HEAD)

# pre commit
PRE_COMMIT ?= $(shell which pre-commit || echo "pre-commit")

# poetry
POETRY ?= $(shell which poetry || echo "poetry")
POETRY_INSTALL_OPTIONS ?=
RUN ?= $(if $(VIRTUAL_ENV),,$(POETRY) run)
PLATFORM ?= linux/amd64

# pytest
PYTEST ?= $(RUN) pytest
PYTEST_TARGETS ?= harp harp_apps tests
PYTEST_CPUS ?= auto
PYTEST_COMMON_OPTIONS ?= -n $(PYTEST_CPUS)
PYTEST_COVERAGE_OPTIONS ?= --cov=harp --cov=harp_apps --cov-report html:docs/_build/html/coverage
PYTEST_OPTIONS ?=

# docker
DOCKER ?= $(shell which docker || echo "docker")
DOCKER_OPTIONS ?=
DOCKER_IMAGE ?= $(NAME)
DOCKER_IMAGE_DEV ?= $(NAME)-dev
DOCKER_TAGS ?=
DOCKER_TAGS_SUFFIX ?=
DOCKER_BUILD_OPTIONS ?= --platform=$(PLATFORM)
DOCKER_BUILD_TARGET ?= runtime
DOCKER_NETWORK ?= bridge
DOCKER_RUN_COMMAND ?=
DOCKER_RUN_OPTIONS ?=

# frontend
PNPM ?= $(shell which pnpm || echo "pnpm")

# misc.
SED ?= $(shell which gsed || which sed || echo "sed")
TESTC_COMMAND ?= poetry shell

# constants
FRONTEND_DIR = harp_apps/dashboard/frontend

# default run options
HARP_OPTIONS ?= --file examples/sqlite.yml --file examples/httpbin.yml

.PHONY: start-dev
start-dev:  # Starts a development instance with reasonable defaults (tune HARP_OPTIONS to replace).
	$(POETRY) run harp start $(HARP_OPTIONS)


########################################################################################################################
# Dependencies
########################################################################################################################

.PHONY: install install-dev install-frontend install-backend install-backend-dev wheel

install: install-frontend install-backend  ## Installs harp dependencies (backend, dashboard) without development tools.

install-dev:  ## Installs harp dependencies (backend, dashboard) with development tools.
	POETRY_INSTALL_OPTIONS="-E dev" $(MAKE) install
	cd $(FRONTEND_DIR); $(PNPM) exec playwright install

install-frontend:  ## Installs harp dashboard dependencies (frontend).
	cd $(FRONTEND_DIR); $(PNPM) install

install-backend:  ## Installs harp dependencides (backend).
	$(POETRY) install $(POETRY_INSTALL_OPTIONS)

install-backend-dev:  ## Installs harp dependencies (backend) with development tools.
	POETRY_INSTALL_OPTIONS="-E dev" $(MAKE) install

wheel:
	mkdir -p dist
	bin/sandbox "$(MAKE) install-dev build-frontend; mv harp_apps/dashboard/frontend/dist harp_apps/dashboard/web; rm -rf harp_apps/dashboard/frontend; $(POETRY) build; cp dist/* $(PWD)/dist"

########################################################################################################################
# Documentation
########################################################################################################################

.PHONY: reference

reference: harp  ## Generates API reference documentation as ReST files (docs).
	rm -rf docs/reference/core docs/reference/apps
	mkdir -p docs/reference/core docs/reference/apps
	$(RUN) bin/generate_apidoc
	git add docs/reference/


########################################################################################################################
# Dashboard application
########################################################################################################################

.PHONY: build-frontend

build-frontend:  ## Builds the harp dashboard frontend (compiles typescript and other sources into bundled version).
	cd $(FRONTEND_DIR); $(PNPM) build


########################################################################################################################
# QA, tests and other CI/CD related stuff
########################################################################################################################

.PHONY: preqa qa qa-full types format format-backend format-frontend
.PHONY: test test-backend test-frontend test-frontend-update test-frontend-ui-update
.PHONY: lint-frontend coverage cloc

preqa: types format reference  ## Runs pre-qa checks (types generation, formatting, api reference).

qa: preqa test  ## Runs all QA checks, with most common databases.

qa-full:  ## Runs all QA checks, including all supported databases.
	TEST_ALL_DATABASES=true $(MAKE) qa

types:  ## Generates frontend types from the python code.
	$(RUN) bin/generate_types

format: format-backend format-frontend  ## Formats the full codebase (backend and frontend).

format-backend:  ## Formats the backend codebase.
	$(RUN) isort harp harp_apps tests
	$(RUN) black harp harp_apps tests
	$(RUN) ruff check --fix harp harp_apps tests
	$(RUN) ruff format

format-frontend: install-frontend  ## Formats the frontend codebase.
	(cd $(FRONTEND_DIR); $(PNPM) lint:fix)
	(cd $(FRONTEND_DIR); $(PNPM) prettier -w src)

test:  ## Runs all tests.
	$(MAKE) test-backend
	$(MAKE) test-frontend

test-backend: install-backend-dev  ## Runs backend tests.
	$(PYTEST) $(PYTEST_TARGETS) \
	          --benchmark-disable \
	          $(PYTEST_COMMON_OPTIONS) \
	          $(PYTEST_OPTIONS)

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
# Benchmarks
########################################################################################################################

.PHONY: benchmark benchmark-save

BENCHMARK_OPTIONS ?=
BENCHMARK_MIN_ROUNDS ?= 100

benchmark:  ## Runs benchmarks.
	$(PYTEST) tests/benchmarks \
	          $(BENCHMARK_OPTIONS) \
	          --benchmark-enable \
	          --benchmark-only \
	          --benchmark-disable-gc \
	          --benchmark-min-rounds=$(BENCHMARK_MIN_ROUNDS) \
	          --benchmark-group-by=group \
	          --benchmark-compare="0006" \
	          --benchmark-histogram \
	          $(PYTEST_OPTIONS)

benchmark-save:  ## Runs benchmarks and saves the results.
	BENCHMARK_OPTIONS='--benchmark-warmup=on --benchmark-warmup-iterations=50 --benchmark-save="$(shell git describe --tags --always --dirty)"' \
	BENCHMARK_MIN_ROUNDS=500 \
	$(MAKE) benchmark


########################################################################################################################
# Docker builds
########################################################################################################################

.PHONY: buildc pushc runc runc-shell runc-example-repositories

buildc:  ## Builds the docker image.
	# TODO: rm in trap ?
	# TODO: document --progress=plain ?
	echo $(VERSION) > version.txt
	$(DOCKER) build --target=$(DOCKER_BUILD_TARGET) $(DOCKER_OPTIONS) $(DOCKER_BUILD_OPTIONS) -t $(DOCKER_IMAGE) $(foreach tag,$(VERSION) $(DOCKER_TAGS),-t $(DOCKER_IMAGE):$(tag)$(DOCKER_TAGS_SUFFIX)) .
	-rm -f version.txt

pushc:  ## Pushes the docker image to the registry.
	for tag in $(VERSION) $(DOCKER_TAGS); do \
		$(DOCKER) image push $(DOCKER_IMAGE):$$tag$(DOCKER_TAGS_SUFFIX); \
	done

runc:  ## Runs the docker image.
	$(DOCKER) run -it --network $(DOCKER_NETWORK) $(DOCKER_OPTIONS) $(DOCKER_RUN_OPTIONS) -p 4000-4999:4000-4999 --rm $(DOCKER_IMAGE) $(DOCKER_RUN_COMMAND)

runc-shell:  ## Runs a shell within the docker image.
	$(DOCKER) run -it --network $(DOCKER_NETWORK) $(DOCKER_OPTIONS) $(DOCKER_RUN_OPTIONS) -p 4080:4080 --rm --entrypoint=/bin/bash $(DOCKER_IMAGE) $(DOCKER_RUN_COMMAND)

runc-example-repositories:  ## Runs harp with the "repositories" example within the docker image.
	$(DOCKER) run -it --network $(DOCKER_NETWORK) $(DOCKER_OPTIONS) $(DOCKER_RUN_OPTIONS) -p 4080:4080 -p 9001-9012:9001-9012 --rm $(DOCKER_IMAGE) --file examples/repositories.yml --set storage.url postgresql+asyncpg://harp:harp@harp-postgres-1/repositories


.PHONY: buildc-dev pushc-dev runc-dev runc-dev-shell

buildc-dev:  ## Builds the development docker image.
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) DOCKER_BUILD_TARGET=development $(MAKE) buildc

pushc-dev:  ## Pushes the development docker image to the registry.
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) $(MAKE) pushc

runc-dev:  ## Runs the development docker image.
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) $(MAKE) runc

runc-dev-shell:  ## Runs a shell within the development docker image.
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) $(MAKE) runc-shell


.PHONY: testc-shell testc-backend

testc-shell:  ## Runs a shell in the development test suite environment.
	$(DOCKER) rm -f docker || true
	$(DOCKER) run --privileged -d --name docker --network $(DOCKER_NETWORK) --network-alias docker -e DOCKER_TLS_CERTDIR= $(DOCKER_OPTIONS) $(DOCKER_RUN_OPTIONS) docker:24.0.6-dind
	DOCKER_OPTIONS="-e DOCKER_HOST=tcp://docker:2375/" DOCKER_RUN_COMMAND="-c \"bin/wait-until-docker-available && (cd src; docker compose up -d; $(TESTC_COMMAND))\"" $(MAKE) runc-dev-shell
	$(DOCKER) stop docker
	$(DOCKER) rm docker

testc-backend:  ## Runs the backend test suite within the development docker image, with a docker in docker sidecar service.
	DOCKER_OPTIONS="-e DOCKER_HOST=tcp://docker:2375/" TESTC_COMMAND="PYTEST_CPUS=2 make test-backend" $(MAKE) testc-shell


########################################################################################################################
# Misc. utilities
########################################################################################################################

.PHONY: help clean clean-dist clean-docs clean-frontend-modules

help:   ## Shows available commands.
	@echo "Available commands:"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?##[\s]?.*$$' --no-filename $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?##"}; {printf "    make \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo

clean-frontend-modules:  ## Cleans up the frontend node modules directory.
	-rm -rf $(FRONTEND_DIR)/node_modules

clean-dist:  ## Cleans up the distribution files (wheels...)
	-rm -rf dist

clean-docs:  ## Cleanup the documentation builds.
	-rm -rf docs/_build

clean: clean-frontend-modules clean-dist clean-docs  ## Cleans up the project.
	-rm -rf $(FRONTEND_DIR)/dist
	-rm -f benchmark_*.svg
