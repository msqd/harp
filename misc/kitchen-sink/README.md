# Kitchen Sink - HARP Demo Environment

This is a demonstration environment for testing HARP with multiple backends and configurations.

## Architecture

- **httpbin-1**: Scalable httpbin service (default: 2 replicas)
- **httpbin-2**: Scalable httpbin service (default: 2 replicas)
- **lb-httpbin-1**: Nginx load balancer for httpbin-1 (port 8991)
- **lb-httpbin-2**: Nginx load balancer for httpbin-2 (port 8992)
- **harp-proxy**: HARP proxy server (port 4000) - runs in 3 different modes

## Running Modes

### 1. Local Development Mode (Default)

Runs harp-proxy using `uv run` from the local codebase with auto-reload on config changes.

```bash
make start
# or
make start HTTPBIN_1_REPLICAS=3 HTTPBIN_2_REPLICAS=4
```

**Features:**
- ✅ Auto-reload on config file changes (requires `fswatch`)
- ✅ Uses local codebase
- ✅ Best for development

### 2. UVX Mode

Runs harp-proxy using `uvx` with a specific version from PyPI.

```bash
# Uses current git version by default (git describe)
make start-uvx

# Or specify a version explicitly
make start-uvx VERSION=0.9.0-rc11

# With scaling
make start-uvx VERSION=0.9.0-rc11 HTTPBIN_1_REPLICAS=3
```

**Features:**
- ✅ Tests specific PyPI releases
- ✅ No local installation needed
- ✅ Good for testing published versions
- ✅ VERSION defaults to `git describe` output

### 3. Docker Mode

Runs harp-proxy as a Docker container from GHCR.

```bash
# Uses current git version by default (git describe)
make start-docker

# Or specify a version explicitly
make start-docker VERSION=0.9.0-rc11

# With custom docker tag (defaults to VERSION if not specified)
make start-docker VERSION=0.9.0-rc11 DOCKER_TAG=0.9-git

# With custom platform (defaults to linux/amd64)
make start-docker DOCKER_PLATFORM=linux/arm64

# With scaling
make start-docker VERSION=0.9.0-rc11 HTTPBIN_1_REPLICAS=3
```

**Features:**
- ✅ Tests Docker images
- ✅ Fully containerized
- ✅ Good for production-like testing
- ✅ VERSION defaults to `git describe` output
- ✅ DOCKER_TAG defaults to VERSION if not specified
- ✅ DOCKER_PLATFORM defaults to `linux/amd64` for better compatibility

## Other Commands

### Scale Backend Services

```bash
make scale HTTPBIN_1_REPLICAS=5 HTTPBIN_2_REPLICAS=3
```

### Stop All Services

```bash
make stop
```

## Configuration Files

Configuration files are in the `etc/` directory:
- `harp.yml` - Main HARP configuration
- `endpoints.yml` - Endpoint definitions
- `rules.yml` - Proxy rules

## Testing the Setup

Once started, HARP is available at http://localhost:4000

Example requests:
```bash
# Via httpbin-1 endpoint
curl http://localhost:4000/httpbin-1/get

# Via httpbin-2 endpoint
curl http://localhost:4000/httpbin-2/get

# Check which backend replica handled the request
curl http://localhost:4000/httpbin-1/hostname
```

## Requirements

- Docker & Docker Compose
- UV (for local and uvx modes)
- fswatch (optional, for auto-reload in local mode)
