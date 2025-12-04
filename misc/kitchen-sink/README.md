# Kitchen Sink - HARP Demo Environment

A simplified demonstration environment for HARP's failover, health checks, and multi-endpoint routing capabilities.

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │              Load Testing                   │
                    │           Locust (:8089)                    │
                    └─────────────┬───────────────────────────────┘
                                  │
          ┌───────────────────────┴───────────────────────┐
          ▼                                               ▼
┌──────────────────────┐                    ┌──────────────────────┐
│  proxy1 (:4000)      │                    │  proxy2 (:4001)      │
│  Primary: api1, api2 │                    │  Primary: api3, api4 │
│  Fallback: api3, api4│                    │  Fallback: api1, api2│
└─────────┬────────────┘                    └────────────┬─────────┘
          │                                              │
          └──────────────────┬───────────────────────────┘
                             │
     ┌───────────┬───────────┼───────────┬───────────┐
     ▼           ▼           ▼           ▼           │
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│  api1   │ │  api2   │ │  api3   │ │  api4   │      │
│ :8001   │ │ :8002   │ │ :8003   │ │ :8004   │      │
│ httpbin │ │ httpbin │ │ httpbin │ │ httpbin │      │
└─────────┘ └─────────┘ └─────────┘ └─────────┘      │
```

### Backend Services
- **api1, api2, api3, api4**: Four httpbin services (ports 8001-8004)

### HARP Proxy Endpoints
- **proxy1** (port 4000): Primary pool → api1, api2 | Fallback pool → api3, api4
- **proxy2** (port 4001): Primary pool → api3, api4 | Fallback pool → api1, api2

HARP continuously probes all backends and automatically fails over to fallback pools when primary endpoints are unavailable.

## Quick Start

```bash
# Start the demo environment (local development mode)
make start

# Test it works
curl http://localhost:4000/get

# Check which services are running
./status.sh
```

## Running Modes

### 1. Local Development Mode (Default)

Runs harp-proxy using `uv run` from the local codebase with auto-reload on config changes.

```bash
make start
```

**Features:**
- Auto-reload on config file changes (requires `fswatch`)
- Uses local codebase
- Best for development

### 2. UVX Mode

Runs harp-proxy using `uvx` with a specific version from PyPI.

```bash
# Uses version from pyproject.toml by default
make start-uvx

# Or specify a version explicitly
make start-uvx VERSION=0.9.0
```

**Features:**
- Tests specific PyPI releases
- No local installation needed
- Good for testing published versions

### 3. Docker Mode

Runs harp-proxy as a Docker container from GHCR.

```bash
# Uses version from pyproject.toml by default
make start-docker

# Or specify a version explicitly
make start-docker VERSION=0.9.0

# With custom docker tag
make start-docker DOCKER_TAG=latest

# With custom platform
make start-docker DOCKER_PLATFORM=linux/arm64
```

**Features:**
- Fully containerized
- Good for production-like testing

## Control Scripts

### Start Services

```bash
./up.sh api1 api2      # Start specific services
./up.sh api1           # Start just api1
```

### Stop Services

```bash
./down.sh api1 api2    # Stop specific services
./down.sh api1         # Stop just api1
```

### Check Status

```bash
./status.sh            # Show all service status
```

### Stop Everything

```bash
make stop              # Stop all docker compose services
```

## Testing Failover

```bash
# 1. Start the environment
make start

# 2. Verify requests go to primary pool (api1 or api2)
curl http://localhost:4000/get

# 3. Stop primary pool
./down.sh api1 api2

# 4. Requests now failover to api3/api4
curl http://localhost:4000/get

# 5. Restart primary pool
./up.sh api1 api2

# 6. HARP automatically routes back to primary
curl http://localhost:4000/get
```

## Load Testing

Run Locust load tests against the proxy:

```bash
# Start locust with default settings (50 users)
./start_locust.sh

# Custom settings
USERS=100 SPAWN_RATE=20 ./start_locust.sh
```

Access the Locust UI at http://localhost:8089

## Configuration Files

- `etc/proxy.yml` - HARP configuration for local/uvx modes (uses localhost:8001-8004)
- `etc/proxy.docker.yml` - HARP configuration for Docker mode (uses Docker DNS: api1, api2, etc.)
- `etc/rules.yml` - Proxy rules engine configuration
- `etc/http_client.yml` - HTTP client settings

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| proxy1 | http://localhost:4000 | Primary: api1, api2 / Fallback: api3, api4 |
| proxy2 | http://localhost:4001 | Primary: api3, api4 / Fallback: api1, api2 |
| Dashboard | http://localhost:4080 | HARP Dashboard (if enabled) |
| api1 | http://localhost:8001 | Backend httpbin service |
| api2 | http://localhost:8002 | Backend httpbin service |
| api3 | http://localhost:8003 | Backend httpbin service |
| api4 | http://localhost:8004 | Backend httpbin service |
| Locust | http://localhost:8089 | Load testing UI |

## Requirements

- **Docker & Docker Compose** (required)
- **UV** (for local and uvx modes)
- **fswatch** (optional, for auto-reload in local mode)
