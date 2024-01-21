NAME ?= harp-proxy
VERSION ?= $(shell git describe 2>/dev/null || git rev-parse --short HEAD)
PRE_COMMIT ?= $(shell which pre-commit || echo "pre-commit")
PYTEST ?= $(shell which pytest || echo "pytest")
PYTEST_OPTIONS ?=

DOCKER ?= $(shell which docker || echo "docker")
DOCKER_IMAGE ?= $(NAME)
DOCKER_IMAGE_DEV ?= $(NAME)-dev
DOCKER_TAGS ?=
DOCKER_TAGS_SUFFIX ?=
DOCKER_BUILD_OPTIONS ?=
DOCKER_BUILD_TARGET ?= runtime
DOCKER_NETWORK ?= harp_default

SED ?= $(shell which gsed || which sed || echo "sed")


########################################################################################################################
# Local development
########################################################################################################################
.PHONY: install install-frontend install-backend install-ui reference frontend

install: install-frontend install-backend

install-frontend: install-ui
	cd frontend; pnpm install

install-backend:
	poetry install

install-ui:
	cd vendors/mkui; pnpm install

reference: harp
	rm -rf docs/reference/python
	mkdir -p docs/reference/python
	sphinx-apidoc --tocfile index --separate -f -o docs/reference/python -t docs/_api_templates harp '**/tests'
	$(SED) -i "1s/.*/Reference/" docs/reference/python/index.rst
	git add docs/reference/

frontend:
	cd frontend; pnpm build


########################################################################################################################
# QA, tests and other CI/CD related stuff
########################################################################################################################

.PHONY: clean preqa qa types format format-backend format-frontend test test-backend coverage test-frontend lint-frontend test-ui test-ui-update test-ui-build

clean:
	(cd docs; $(MAKE) clean)
	-rm -rf frontend/dist
	-rm -f benchmark_*.svg

preqa: types format reference

qa: preqa test test-ui

types:
	bin/generate_types

format: format-backend format-frontend

format-frontend: install-frontend
	(cd frontend; pnpm lint:fix)
	(cd frontend; pnpm prettier -w src)

format-backend:
	isort harp tests
	black harp tests
	ruff check --fix harp tests

test:
	$(MAKE) test-backend
	$(MAKE) test-frontend

test-backend:
	$(PYTEST) harp tests \
	          --benchmark-disable \
	          -n auto \
	          $(PYTEST_OPTIONS)

coverage:
	$(PYTEST) harp tests \
	          -m 'not subprocess' \
	          --cov=harp \
	          --cov-report html:docs/_build/html/coverage \
	          -n auto \
	          $(PYTEST_OPTIONS)

test-frontend: install-frontend lint-frontend
	cd frontend; pnpm test

lint-frontend: install-frontend
	cd frontend; pnpm build

test-ui-build: install-ui
	cd vendors/mkui; pnpm build

test-ui: test-ui-build
	cd vendors/mkui; pnpm test:prod

test-ui-update: test-ui-build
	cd vendors/mkui; pnpm test:update

########################################################################################################################
# Benchmarks
########################################################################################################################

.PHONY: benchmark benchmark-save

BENCHMARK_OPTIONS ?=
BENCHMARK_MIN_ROUNDS ?= 100

benchmark:
	$(PYTEST) harp tests \
	          $(BENCHMARK_OPTIONS) \
	          --benchmark-enable \
	          --benchmark-only \
	          --benchmark-disable-gc \
	          --benchmark-min-rounds=$(BENCHMARK_MIN_ROUNDS) \
	          --benchmark-group-by=group \
	          --benchmark-compare="0006" \
	          --benchmark-histogram \
	          $(PYTEST_OPTIONS)

benchmark-save:
	BENCHMARK_OPTIONS='--benchmark-warmup=on --benchmark-warmup-iterations=50 --benchmark-save="$(shell git describe --tags --always --dirty)"' \
	BENCHMARK_MIN_ROUNDS=500 \
	$(MAKE) benchmark


########################################################################################################################
# Docker builds
########################################################################################################################

.PHONY: build build-dev push push-dev run run-shell run-example-repositories run-dev run-dev-shell

build:
	echo $(VERSION) > version.txt
	$(DOCKER) build --progress=plain --target=$(DOCKER_BUILD_TARGET) $(DOCKER_BUILD_OPTIONS) -t $(DOCKER_IMAGE) $(foreach tag,$(VERSION) $(DOCKER_TAGS),-t $(DOCKER_IMAGE):$(tag)$(DOCKER_TAGS_SUFFIX)) .
	-rm -f version.txt

build-dev:
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) DOCKER_BUILD_TARGET=development $(MAKE) build

push:
	for tag in $(VERSION) $(DOCKER_TAGS); do \
		$(DOCKER) image push $(DOCKER_IMAGE):$$tag$(DOCKER_TAGS_SUFFIX); \
	done

push-dev:
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) $(MAKE) push

run:
	$(DOCKER) run -it --network $(DOCKER_NETWORK) -p 4080:4080 --rm $(DOCKER_IMAGE)

run-shell:
	$(DOCKER) run -it --network $(DOCKER_NETWORK) -p 4080:4080 --rm --entrypoint=/bin/ash $(DOCKER_IMAGE) -l

run-example-repositories:
	$(DOCKER) run -it --network $(DOCKER_NETWORK) -p 4080:4080 -p 9001-9012:9001-9012 --rm $(DOCKER_IMAGE) --file examples/repositories.yml --set storage.url postgresql+asyncpg://harp:harp@harp-postgres-1/repositories

run-dev:
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) $(MAKE) run

run-dev-shell:
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) $(MAKE) run-shell
