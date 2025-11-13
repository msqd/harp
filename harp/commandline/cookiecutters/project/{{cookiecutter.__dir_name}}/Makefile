########################################################################################################################
# Makefile for {{cookiecutter.name}}
########################################################################################################################

# Configuration
DEBUG ?=
HARP_OPTIONS ?=
UV ?= $(shell which uv || echo uv)

# Helper function to execute commands
define execute
@echo "⚙️ \033[36m$@\033[0m: \033[2m$(1)\033[0m"
@$(1)
endef

# Default target
.DEFAULT_GOAL := help

.PHONY: help install start test clean

help:  ## Shows this help message
	@echo "📦 \033[1m{{cookiecutter.name}}\033[0m"
	@echo
	@echo "Available commands:"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo

install:  ## Install dependencies using UV
	$(call execute,$(UV) sync $(if $(DEBUG),,--quiet))

start: install  ## Start the HARP proxy server
	$(call execute,$(UV) run harp-proxy server{% if cookiecutter.create_application %} --enable {{cookiecutter.__pkg_name}}{% endif %}{% if cookiecutter.create_config %} --file config.yml{% endif %} $(HARP_OPTIONS))

test: install  ## Run tests with pytest
	$(call execute,$(UV) run pytest)

clean:  ## Clean up generated files
	$(call execute,rm -rf .venv .pytest_cache __pycache__ .coverage htmlcov)
	$(call execute,find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true)
	$(call execute,find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true)
