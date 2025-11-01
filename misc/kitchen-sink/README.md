# Kitchen Sink - HARP Demo Environment

This is a demonstration environment for testing HARP with multiple backends, load balancing, and failover configurations.

## Architecture

### Backend Services
- **api1, api2, api3, api4**: Four scalable httpbin services (default: 2 replicas each)
- **api1-lb, api2-lb, api3-lb, api4-lb**: Nginx load balancers (ports 8001-8004)

### HARP Proxy Endpoints
- **proxy1** (port 4000): Primary pool → api1, api2 | Fallback pool → api3, api4
- **proxy2** (port 4001): Primary pool → api3, api4 | Fallback pool → api1, api2

HARP continuously probes all backends and automatically fails over to fallback pools when primary endpoints are unavailable.

## Running Modes

### 1. Local Development Mode (Default)

Runs harp-proxy using `uv run` from the local codebase with auto-reload on config changes.

```bash
make start

# With custom replica counts
make start API1_REPLICAS=3 API2_REPLICAS=4
```

**Features:**
- ✅ Auto-reload on config file changes (requires `fswatch`)
- ✅ Uses local codebase
- ✅ Best for development

### 2. UVX Mode

Runs harp-proxy using `uvx` with a specific version from PyPI.

```bash
# Uses version from pyproject.toml by default (last published version)
make start-uvx

# Or specify a version explicitly
make start-uvx VERSION=0.9.0-rc11

# With custom replica counts
make start-uvx VERSION=0.9.0-rc11 API1_REPLICAS=3 API2_REPLICAS=4
```

**Features:**
- ✅ Tests specific PyPI releases
- ✅ No local installation needed
- ✅ Good for testing published versions
- ✅ VERSION defaults to version from `../../pyproject.toml`

### 3. Docker Mode

Runs harp-proxy as a Docker container from GHCR.

```bash
# Uses version from pyproject.toml by default (last published version)
make start-docker

# Or specify a version explicitly
make start-docker VERSION=0.9.0-rc11

# With custom docker tag (defaults to VERSION if not specified)
make start-docker VERSION=0.9.0-rc11 DOCKER_TAG=0.9-git

# With custom platform (defaults to linux/amd64)
make start-docker DOCKER_PLATFORM=linux/arm64

# With custom command (defaults to: server -f /etc/harp/proxy.docker.yml -f /etc/harp/rules.yml)
make start-docker DOCKER_COMMAND="server -f /etc/harp/custom.yml"

# With custom replica counts
make start-docker VERSION=0.9.0-rc11 API1_REPLICAS=3 API2_REPLICAS=4
```

**Features:**
- ✅ Tests Docker images
- ✅ Fully containerized
- ✅ Good for production-like testing
- ✅ VERSION defaults to version from `../../pyproject.toml`
- ✅ DOCKER_TAG defaults to VERSION if not specified
- ✅ DOCKER_PLATFORM defaults to `linux/amd64` for better compatibility
- ✅ DOCKER_COMMAND allows customizing the harp-proxy command
- ✅ Exposes port range 4000-4999 for flexibility

## Management Commands

### Scale Individual Services

Use the `scale.sh` script to scale a specific API service:

```bash
./scale.sh api1 5    # Scale api1 to 5 replicas
./scale.sh api2 3    # Scale api2 to 3 replicas
./scale.sh api3 1    # Scale api3 to 1 replica
./scale.sh api4 0    # Scale api4 to 0 replicas (stop)
```

### Scale All Services (via Makefile)

```bash
make scale API1_REPLICAS=5 API2_REPLICAS=3 API3_REPLICAS=2 API4_REPLICAS=4
```

### Watch Service Status

Use the `watch.sh` script to monitor replica counts in real-time (refreshes every 2 seconds):

```bash
./watch.sh
```

Press `Ctrl+C` to exit.

### Stop All Services

```bash
make stop
```

## Configuration Files

Configuration files are in the `etc/` directory:

### HARP Proxy Configuration
- `proxy.yml` - Proxy endpoints for local/uvx modes (uses localhost:8001-8004)
- `proxy.docker.yml` - Proxy endpoints for Docker mode (uses Docker DNS: api1-lb, api2-lb, api3-lb, api4-lb)
- `rules.yml` - Proxy rules engine configuration

### Nginx Load Balancer Configuration
- `nginx/api1-lb.conf` - Load balancer for api1 service
- `nginx/api2-lb.conf` - Load balancer for api2 service
- `nginx/api3-lb.conf` - Load balancer for api3 service
- `nginx/api4-lb.conf` - Load balancer for api4 service

## Testing the Setup

### Access Points

Once started, HARP proxies are available at:
- **http://localhost:4000** - proxy1 (primary: api1, api2 | fallback: api3, api4)
- **http://localhost:4001** - proxy2 (primary: api3, api4 | fallback: api1, api2)
- **http://localhost:4080** - Dashboard (if enabled)

Backend load balancers (direct access):
- http://localhost:8001 - api1-lb
- http://localhost:8002 - api2-lb
- http://localhost:8003 - api3-lb
- http://localhost:8004 - api4-lb

### Example Requests

```bash
# Via proxy1 (routes to api1 or api2)
curl http://localhost:4000/get

# Via proxy2 (routes to api3 or api4)
curl http://localhost:4001/get

# Check which backend replica handled the request
curl http://localhost:4000/hostname

# Test JSON response
curl http://localhost:4000/json

# Test with delay
curl http://localhost:4000/delay/2
```

### Testing Failover

```bash
# Stop api1 and api2 to test fallback to api3/api4
./scale.sh api1 0
./scale.sh api2 0

# proxy1 should now route to api3 or api4
curl http://localhost:4000/get

# Watch the service status in another terminal
./watch.sh
```

## Requirements

- **Docker & Docker Compose** (required)
- **UV** (for local and uvx modes)
- **fswatch** (optional, for auto-reload in local mode)
- **watch** (optional, for `watch.sh` script)
