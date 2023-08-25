PRE_COMMIT ?= $(shell which pre-commit || echo "pre-commit")

.PHONY: format

format:
	cd frontend; pnpm prettier -w src
	$(PRE_COMMIT)
