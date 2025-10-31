.PHONY: start start-uvx start-docker stop scale _start

HTTPBIN_1_REPLICAS ?= 2
HTTPBIN_2_REPLICAS ?= 2

# Version defaults to git describe (same as main Makefile)
VERSION ?= $(shell git describe 2>/dev/null || git rev-parse --short HEAD)

# Run mode: local (default), uvx, or docker
MODE ?= local
DOCKER_TAG ?= $(VERSION)
UVX_OPTIONS ?= --refresh-package harp-proxy

start:  ## Start services with harp-proxy in local mode (default, with auto-reload)
	@$(MAKE) _start MODE=local

start-uvx:  ## Start services with harp-proxy via uvx (defaults to VERSION=$(VERSION) or specify: make start-uvx VERSION=0.9.0-rc11)
	@echo "Using VERSION=$(VERSION) for uvx mode"
	@$(MAKE) _start MODE=uvx VERSION=$(VERSION)

start-docker:  ## Start services with harp-proxy as docker container (defaults to VERSION=$(VERSION) [DOCKER_TAG=$(DOCKER_TAG)])
	@echo "Using VERSION=$(VERSION) and DOCKER_TAG=$(DOCKER_TAG) for docker mode"
	@$(MAKE) _start MODE=docker VERSION=$(VERSION) DOCKER_TAG=$(DOCKER_TAG)

_start:
	@echo "Stopping any existing Docker Compose services..."
	@docker compose down 2>/dev/null || true
	@echo "Starting Docker Compose services with httpbin-1=$(HTTPBIN_1_REPLICAS) httpbin-2=$(HTTPBIN_2_REPLICAS) replicas..."
	@docker compose up -d --scale httpbin-1=$(HTTPBIN_1_REPLICAS) --scale httpbin-2=$(HTTPBIN_2_REPLICAS)
	@CONFIG_FILES=$$(ls etc/*.yml | sed 's/^/-f /' | tr '\n' ' '); \
	if [ "$(MODE)" = "local" ]; then \
		echo "🚀 Starting harp-proxy in LOCAL mode (uv run) with auto-reload..."; \
		trap 'docker compose stop' EXIT; \
		if command -v fswatch >/dev/null 2>&1; then \
			echo "Watching etc/*.yml for changes (will restart after 1s of inactivity)..."; \
			trap 'kill $$PID 2>/dev/null; exit 0' INT TERM; \
			while true; do \
				uv run harp-proxy server $$CONFIG_FILES & \
				PID=$$!; \
				fswatch -1 -l 1 etc/*.yml >/dev/null 2>&1 || break; \
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
		echo "🚀 Starting harp-proxy in DOCKER mode (tag: $(DOCKER_TAG))..."; \
		HARP_DOCKER_TAG=$(DOCKER_TAG) docker compose -f compose.yml -f compose.harp-docker.yml up; \
	else \
		echo "❌ ERROR: Invalid MODE=$(MODE). Must be: local, uvx, or docker"; \
		exit 1; \
	fi

scale:  ## Scale httpbin services (usage: make scale HTTPBIN_1_REPLICAS=3 HTTPBIN_2_REPLICAS=4)
	@docker compose up -d --scale httpbin-1=$(HTTPBIN_1_REPLICAS) --scale httpbin-2=$(HTTPBIN_2_REPLICAS) --no-recreate

stop:  ## Stop docker compose services
	@docker compose down
