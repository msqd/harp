# Cache E2E Testing with cache-tests

This directory contains end-to-end integration tests for HARP's HTTP caching functionality using the [cache-tests](https://github.com/http-tests/cache-tests) RFC 9111 compliance test suite.

## Overview

The cache-tests suite is a comprehensive set of tests that verify HTTP caching behavior against [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html) (HTTP Caching specification). These tests ensure that HARP's caching implementation (via hishel) correctly handles:

- Cache-Control directives (max-age, no-cache, no-store, etc.)
- Vary header handling
- Conditional requests (ETags, Last-Modified)
- Expiration and freshness calculations
- Stale response handling
- Request/response caching rules

## Quick Start

Run the E2E cache tests from the project root:

```bash
make test-e2e-cache
```

This will:
1. Initialize the cache-tests git submodule if needed
2. Start the cache-tests origin server on port 8000
3. Start HARP proxy on port 4000 (configured as reverse proxy to origin)
4. Run the complete cache-tests suite against HARP
5. Report results and cleanup

## Directory Structure

```
misc/cache-tests/
├── cache-tests/          # Git submodule: http-tests/cache-tests suite
│   └── results/
│       ├── harp.json     # Test results (generated)
│       └── index.mjs     # Results registry
├── config.yml            # HARP configuration for testing
├── run-tests.sh          # Test execution script
├── open-results.sh       # HTML viewer launcher script
└── README.md             # This file
```

## Architecture

### Test Flow

```
cache-tests origin (port 8000)
         ↑
         | HTTP
         |
    HARP Proxy (port 4000)
         ↑
         | HTTP
         |
   cache-tests CLI
```

1. **Origin Server**: Node.js server from cache-tests providing test endpoints
2. **HARP Proxy**: Configured as reverse proxy with HTTP client caching enabled
3. **Test CLI**: Sends HTTP requests through HARP, verifies caching behavior

### Configuration

HARP is configured in `config.yml` with:

```yaml
applications:
  - proxy
  - http_client
  - storage

# Uses default in-memory SQLite storage

http_client:
  cache:
    enabled: true
    # Uses default policy: hishel.SpecificationPolicy (RFC 9111 compliant)
    # Uses default options: shared=true, supported_methods=[GET, HEAD], allow_stale=false

proxy:
  endpoints:
    - name: cache-tests
      port: 4000
      url: "http://localhost:8000/"
```

## Manual Execution

To run tests manually with more control:

```bash
# Navigate to this directory
cd misc/cache-tests

# Initialize submodule (first time only)
git submodule update --init --recursive cache-tests

# Run the test script
./run-tests.sh
```

Or run components individually:

```bash
# Start cache-tests origin server
cd cache-tests && npm install && npm run server &

# Start HARP proxy (in separate terminal)
cd misc/cache-tests
uv run harp-proxy server --file config.yml

# Run tests (in separate terminal)
cd misc/cache-tests/cache-tests
npm run --silent cli --base=http://localhost:4000
```

## Test Results

### JSON Output

Test results are saved to `cache-tests/results/harp.json` in JSON format.

### HTML Results Viewer

To view results in a visual HTML interface:

```bash
./open-results.sh
```

This script will:
- Start an HTTP server on port 8080
- Automatically open your browser to http://localhost:8080/
- Keep the server running until you press Ctrl+C

Alternatively, start the server manually:

```bash
cd misc/cache-tests/cache-tests
python3 -m http.server 8080
```

The interface will show:
- Overall pass/fail statistics
- Detailed test results by category
- Comparison with other cache implementations (Chrome, Firefox, Nginx, etc.)
- RFC 9111 compliance analysis

### Result Interpretation

The cache-tests suite shows:

- **Pass** (`true`): Test passed, caching behavior is RFC 9111 compliant
- **Fail** (with message): Test failed with specific assertion details
- **Setup errors**: Issues with test infrastructure

Example JSON output:

```json
{
  "freshness-max-age": true,
  "freshness-expires": true,
  "cc-req-no-cache": [
    "Assertion",
    "Response 2 does not come from cache"
  ]
}
```

## Troubleshooting

### Submodule Not Initialized

```bash
git submodule update --init --recursive misc/cache-tests/cache-tests
```

### Port Conflicts

If ports 4000 or 8000 are already in use, you'll need to:
1. Stop the conflicting services
2. Or modify `config.yml` and `run-tests.sh` to use different ports

### Test Failures

Test failures may indicate:
- **HARP caching bugs**: Issues with HARP's cache configuration or integration
- **hishel bugs**: Issues with the underlying hishel library
- **Configuration issues**: HARP cache not configured as expected

Check the HARP logs for detailed caching behavior during failed tests.

## Related Documentation

- **cache-tests**: https://github.com/http-tests/cache-tests
- **RFC 9111**: https://www.rfc-editor.org/rfc/rfc9111.html
- **hishel**: https://hishel.com/
- **HARP caching docs**: `docs/apps/http_client/`

## Development

### Adding New Test Scenarios

The cache-tests suite is maintained upstream. To add HARP-specific test scenarios:

1. Create a custom test script in this directory
2. Update `run-tests.sh` to run both cache-tests and custom tests
3. Document custom tests in this README

### Updating cache-tests

To update to the latest cache-tests version:

```bash
cd misc/cache-tests/cache-tests
git pull origin main
cd ..
git add cache-tests
git commit -m "chore: update cache-tests submodule"
```

## CI/CD Integration

The `make test-e2e-cache` target can be integrated into CI pipelines:

```yaml
# Example GitHub Actions
- name: Run E2E Cache Tests
  run: make test-e2e-cache
```

**Note**: These tests require Node.js to be available in the CI environment for the cache-tests origin server.
