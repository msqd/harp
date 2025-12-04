.PHONY: help start start-uvx start-docker stop _start

# Run mode: local (default), uvx, or docker
MODE ?= local

# Version handling:
# - For local mode: use git describe (current development version)
# - For uvx/docker modes: use version from pyproject.toml (last published version)
GIT_VERSION := $(shell git describe 2>/dev/null || git rev-parse --short HEAD)
PYPROJECT_VERSION := $(shell grep '^version = ' ../../pyproject.toml | cut -d'"' -f2)

DOCKER_PLATFORM ?= linux/amd64
DOCKER_COMMAND ?= server -f /etc/harp/proxy.docker.yml -f /etc/harp/rules.yml
UVX_OPTIONS ?= --refresh-package harp-proxy

start:  ## Start services with harp-proxy in local mode (default, with auto-reload)
	@$(MAKE) _start MODE=local VERSION=$(GIT_VERSION)

start-uvx:  ## Start services with harp-proxy via uvx (defaults to VERSION from pyproject.toml)
	@$(eval VERSION ?= $(PYPROJECT_VERSION))
	@echo "Using VERSION=$(VERSION) for uvx mode"
	@$(MAKE) _start MODE=uvx VERSION=$(VERSION)

start-docker:  ## Start services with harp-proxy as docker container (defaults to VERSION from pyproject.toml)
	@$(eval VERSION ?= $(PYPROJECT_VERSION))
	@$(eval DOCKER_TAG ?= $(VERSION))
	@echo "Using VERSION=$(VERSION) and DOCKER_TAG=$(DOCKER_TAG) for docker mode"
	@$(MAKE) _start MODE=docker VERSION=$(VERSION) DOCKER_TAG=$(DOCKER_TAG)

_start:
	@echo "Stopping any existing Docker Compose services..."
	@docker compose down --remove-orphans 2>/dev/null || true
	@echo "Starting Docker Compose services..."
	@docker compose up -d
	@CONFIG_FILES=$$(ls etc/*.yml | grep -v '\.docker\.yml$$' | sed 's/^/-f /' | tr '\n' ' '); \
	if [ "$(MODE)" = "local" ]; then \
		echo "🚀 Starting harp-proxy in LOCAL mode (uv run) with auto-reload..."; \
		trap 'docker compose stop' EXIT; \
		if command -v fswatch >/dev/null 2>&1; then \
			echo "Watching etc/*.yml for changes (will restart after 1s of inactivity)..."; \
			trap 'kill $$PID 2>/dev/null; exit 0' INT TERM; \
			WATCH_FILES=$$(ls etc/*.yml | grep -v '\.docker\.yml$$' | tr '\n' ' '); \
			while true; do \
				uv run harp-proxy server $$CONFIG_FILES & \
				PID=$$!; \
				fswatch -1 -l 1 $$WATCH_FILES >/dev/null 2>&1 || break; \
				sleep 1; \
				echo "Config changed, restarting harp-proxy..."; \
				kill $$PID 2>/dev/null || true; \
				wait $$PID 2>/dev/null || true; \
			done; \
		else \
			echo "fswatch not available, running without auto-reload..."; \
			uv run harp-proxy server $$CONFIG_FILES; \
		fi; \
	elif [ "$(MODE)" = "uvx" ]; then \
		echo "🚀 Starting harp-proxy in UVX mode (version: $(VERSION))..."; \
		trap 'docker compose stop' EXIT; \
		uvx $(UVX_OPTIONS) harp-proxy@$(VERSION) server $$CONFIG_FILES; \
	elif [ "$(MODE)" = "docker" ]; then \
		echo "🚀 Starting harp-proxy in DOCKER mode (tag: $(DOCKER_TAG), platform: $(DOCKER_PLATFORM))..."; \
		TAG=$(DOCKER_TAG) PLATFORM=$(DOCKER_PLATFORM) COMMAND="$(DOCKER_COMMAND)" docker compose -f compose.yml -f compose.harp-docker.yml up --remove-orphans; \
	else \
		echo "❌ ERROR: Invalid MODE=$(MODE). Must be: local, uvx, or docker"; \
		exit 1; \
	fi

stop:  ## Stop all docker compose services
	@docker compose down

etc/http_client.yml: ../../harp_apps/http_client/docs/examples/reference.yml
	cp $< $@

help:  ## Show available commands
	@echo "Kitchen Sink - HARP Demo Environment"
	@echo
	@echo "\033[1mRunning Modes\033[0m"
	@grep -E '^(start|start-uvx|start-docker):.*?##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?##"}; {printf "    make \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "\033[1mManagement\033[0m"
	@grep -E '^(stop):.*?##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?##"}; {printf "    make \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "\033[1mControl Scripts\033[0m"
	@echo "    \033[36m./up.sh api1 api2     \033[0m Start specific services"
	@echo "    \033[36m./down.sh api1        \033[0m Stop specific services"
	@echo "    \033[36m./status.sh           \033[0m Show service status"
	@echo "    \033[36m./start_locust.sh     \033[0m Run load tests"
	@echo
