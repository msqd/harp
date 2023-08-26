PRE_COMMIT ?= $(shell which pre-commit || echo "pre-commit")
PYTEST ?= $(shell which pytest || echo "pytest")

.PHONY: format test test-ui test-ui-update test-back test-front test-full qa

format:
	cd frontend; pnpm prettier -w src
	$(PRE_COMMIT)

test-ui:
	cd vendors/mkui; pnpm test:prod

test-ui-update:
	cd vendors/mkui; pnpm test:update

test-back:
	$(PYTEST) harp

test-front:

test: test-back test-front

test-full: test test-ui

qa: format test-full
