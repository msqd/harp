.PHONY: start stop scale

HTTPBIN_1_REPLICAS ?= 2
HTTPBIN_2_REPLICAS ?= 2

start:  ## Start docker compose services and run harp-proxy server with auto-reload
	@echo "Stopping any existing Docker Compose services..."
	@docker compose down 2>/dev/null || true
	@echo "Starting Docker Compose services with httpbin-1=$(HTTPBIN_1_REPLICAS) httpbin-2=$(HTTPBIN_2_REPLICAS) replicas..."
	@docker compose up -d --scale httpbin-1=$(HTTPBIN_1_REPLICAS) --scale httpbin-2=$(HTTPBIN_2_REPLICAS)
	@trap 'docker compose stop' EXIT; \
		CONFIG_FILES=$$(ls etc/*.yml | sed 's/^/-f /' | tr '\n' ' '); \
		echo "Starting harp-proxy server with config files: $$CONFIG_FILES"; \
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
		fi

scale:  ## Scale httpbin services (usage: make scale HTTPBIN_1_REPLICAS=3 HTTPBIN_2_REPLICAS=4)
	@docker compose up -d --scale httpbin-1=$(HTTPBIN_1_REPLICAS) --scale httpbin-2=$(HTTPBIN_2_REPLICAS) --no-recreate

stop:  ## Stop docker compose services
	@docker compose down
