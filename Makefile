# package
NAME ?= harp-proxy
VERSION ?= $(shell git describe 2>/dev/null || git rev-parse --short HEAD)

# pre commit
PRE_COMMIT ?= $(shell which pre-commit || echo "pre-commit")

# poetry
POETRY ?= $(shell which poetry || echo "poetry")
POETRY_INSTALL_OPTIONS ?=
RUN ?= $(if $(VIRTUAL_ENV),,$(POETRY) run)

# pytest
PYTEST ?= $(RUN) $(shell which pytest || echo "pytest")
PYTEST_TARGETS ?= harp harp_apps tests
PYTEST_COMMON_OPTIONS ?= -n auto
PYTEST_COVERAGE_OPTIONS ?= --cov=harp --cov=harp_apps --cov-report html:docs/_build/html/coverage
PYTEST_OPTIONS ?=


# docker
DOCKER ?= $(shell which docker || echo "docker")
DOCKER_IMAGE ?= $(NAME)
DOCKER_IMAGE_DEV ?= $(NAME)-dev
DOCKER_TAGS ?=
DOCKER_TAGS_SUFFIX ?=
DOCKER_BUILD_OPTIONS ?=
DOCKER_BUILD_TARGET ?= runtime
DOCKER_NETWORK ?= harp_default
DOCKER_RUN_COMMAND ?=

# misc.
SED ?= $(shell which gsed || which sed || echo "sed")


########################################################################################################################
# Dependencies
########################################################################################################################

.PHONY: install install-dev install-frontend install-backend install-backend-dev

install: install-frontend install-backend  ## Installs harp dependencies (backend, dashboard) without development tools.

install-dev:  ## Installs harp dependencies (backend, dashboard) with development tools.
	POETRY_INSTALL_OPTIONS="-E dev" $(MAKE) install

install-frontend:  ## Installs harp dashboard dependencies (frontend).
	cd harp_apps/dashboard/frontend; pnpm install

install-backend:  ## Installs harp dependencides (backend).
	poetry install $(POETRY_INSTALL_OPTIONS)

install-backend-dev:  ## Installs harp dependencies (backend) with development tools.
	POETRY_INSTALL_OPTIONS="-E dev" $(MAKE) install


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

.PHONY: frontend-build

frontend-build:  ## Builds the harp dashboard frontend (compiles typescript and other sources into bundled version).
	cd harp_apps/dashboard/frontend; pnpm build


########################################################################################################################
# QA, tests and other CI/CD related stuff
########################################################################################################################

.PHONY: preqa qa qa-full types format format-backend format-frontend
.PHONY: test test-backend test-frontend test-frontend-update
.PHONY: lint-frontend coverage

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

format-frontend: install-frontend  ## Formats the frontend codebase.
	(cd harp_apps/dashboard/frontend; pnpm lint:fix)
	(cd harp_apps/dashboard/frontend; pnpm prettier -w src)

test:  ## Runs all tests.
	$(MAKE) test-backend
	$(MAKE) test-frontend

test-backend: install-backend-dev  ## Runs backend tests.
	$(PYTEST) $(PYTEST_TARGETS) \
	          --benchmark-disable \
	          $(PYTEST_COMMON_OPTIONS) \
	          $(PYTEST_OPTIONS)

test-frontend: install-frontend lint-frontend  ## Runs frontend tests.
	cd harp_apps/dashboard/frontend; pnpm test

test-frontend-update: install-frontend lint-frontend  ## Runs frontend tests while updating snapshots.
	cd harp_apps/dashboard/frontend; pnpm test:unit:update

lint-frontend: install-frontend  ## Lints the frontend codebase.
	cd harp_apps/dashboard/frontend; pnpm build

coverage:  ## Generates coverage report.
	$(PYTEST) $(PYTEST_TARGETS) tests \
	          -m 'not subprocess' \
	          $(PYTEST_COVERAGE_OPTIONS) \
	          $(PYTEST_COMMON_OPTIONS) \
	          $(PYTEST_OPTIONS)


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

.PHONY: build build-dev push push-dev run run-shell run-example-repositories run-dev run-dev-shell

build:  ## Builds the docker image.
	# TODO: rm in trap ?
	# TODO: document --progress=plain ?
	echo $(VERSION) > version.txt
	$(DOCKER) build --target=$(DOCKER_BUILD_TARGET) $(DOCKER_BUILD_OPTIONS) -t $(DOCKER_IMAGE) $(foreach tag,$(VERSION) $(DOCKER_TAGS),-t $(DOCKER_IMAGE):$(tag)$(DOCKER_TAGS_SUFFIX)) .
	-rm -f version.txt

build-dev:  ## Builds the development docker image.
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) DOCKER_BUILD_TARGET=development $(MAKE) build

push:  ## Pushes the docker image to the registry.
	for tag in $(VERSION) $(DOCKER_TAGS); do \
		$(DOCKER) image push $(DOCKER_IMAGE):$$tag$(DOCKER_TAGS_SUFFIX); \
	done

push-dev:  ## Pushes the development docker image to the registry.
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) $(MAKE) push

run:  ## Runs the docker image.
	$(DOCKER) run -it --network $(DOCKER_NETWORK) -p 4000-4999:4000-4999 --rm $(DOCKER_IMAGE) $(DOCKER_RUN_COMMAND)

run-shell:  ## Runs a shell within the docker image.
	$(DOCKER) run -it --network $(DOCKER_NETWORK) -p 4080:4080 --rm --entrypoint=/bin/ash $(DOCKER_IMAGE) -l

run-example-repositories:  ## Runs harp with the "repositories" example within the docker image.
	$(DOCKER) run -it --network $(DOCKER_NETWORK) -p 4080:4080 -p 9001-9012:9001-9012 --rm $(DOCKER_IMAGE) --file examples/repositories.yml --set storage.url postgresql+asyncpg://harp:harp@harp-postgres-1/repositories

run-dev:  ## Runs the development docker image.
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) $(MAKE) run

run-dev-shell:  ## Runs a shell within the development docker image.
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) $(MAKE) run-shell


########################################################################################################################
# Misc. utilities
########################################################################################################################

.PHONY: help clean

help:   ## Shows available commands.
	@echo "Available commands:"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?##[\s]?.*$$' --no-filename $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?##"}; {printf "    make \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo


clean:  ## Cleans up the project directory.
	(cd docs; $(MAKE) clean)
	-rm -rf harp_apps/dashboard/frontend/dist
	-rm -f benchmark_*.svg

