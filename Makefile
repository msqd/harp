PRE_COMMIT ?= $(shell which pre-commit || echo "pre-commit")

.PHONY: format

format:
	$(PRE_COMMIT)
