NAME ?= harp
VERSION ?= $(shell git describe 2>/dev/null || git rev-parse --short HEAD)
HONCHO ?= $(shell which honcho || echo "honcho")
PRE_COMMIT ?= $(shell which pre-commit || echo "pre-commit")
PYTEST ?= $(shell which pytest || echo "pytest")

DOCKER ?= $(shell which docker || echo "docker")
DOCKER_IMAGE = $(NAME)
DOCKER_TAGS = $(VERSION)


.PHONY: format test test-ui test-ui-update test-back test-front test-full qa start build

########################################################################################################################
# Local development
########################################################################################################################

start:
	$(HONCHO) start

########################################################################################################################
# QA, tests and other CI/CD related stuff
########################################################################################################################

qa: format test-full

format:
	cd frontend; pnpm prettier -w src
	$(PRE_COMMIT)

test: test-back test-front

test-full: test test-ui

test-ui:
	cd vendors/mkui; pnpm test:prod

test-ui-update:
	cd vendors/mkui; pnpm test:update

test-back:
	$(PYTEST) harp

test-front:
	cd frontend; pnpm test; pnpm build

########################################################################################################################
# Docker builds
########################################################################################################################

build:
	$(DOCKER) build -t $(DOCKER_IMAGE) $(foreach tag,$(DOCKER_TAGS),-t $(DOCKER_IMAGE):$(tag)) .
