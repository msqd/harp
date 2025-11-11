#!/bin/bash
# E2E cache testing script using cache-tests suite
# Tests HARP proxy against RFC 9111 HTTP caching compliance

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Cleanup function to ensure all processes are killed
cleanup() {
    echo ""
    echo "Cleaning up processes..."

    # Kill HARP proxy
    if [ ! -z "$HARP_PID" ]; then
        echo "Stopping HARP proxy (PID: $HARP_PID)..."
        kill $HARP_PID 2>/dev/null || true
        sleep 1
        # Force kill if still running
        kill -9 $HARP_PID 2>/dev/null || true
    fi

    # Kill cache-tests origin server
    if [ ! -z "$SERVER_PID" ]; then
        echo "Stopping origin server (PID: $SERVER_PID)..."
        kill $SERVER_PID 2>/dev/null || true
        sleep 1
        # Force kill if still running
        kill -9 $SERVER_PID 2>/dev/null || true
    fi

    # Kill any remaining node/harp processes on our ports (safety net)
    lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
    lsof -ti:4000 2>/dev/null | xargs kill -9 2>/dev/null || true

    echo "Cleanup complete."
}

# Register cleanup on all exit conditions
trap cleanup EXIT INT TERM ERR

# Helper function to wait for port to be listening
wait_for_port() {
    local port=$1
    local service=$2
    local max_wait=30
    local waited=0

    echo "Waiting for $service to listen on port $port..."
    while ! nc -z localhost $port 2>/dev/null; do
        if [ $waited -ge $max_wait ]; then
            echo "ERROR: $service failed to start within ${max_wait}s"
            return 1
        fi
        sleep 1
        waited=$((waited + 1))
    done
    echo "$service is ready on port $port"
    return 0
}

echo "=== Starting cache-tests E2E Testing ==="
echo ""

# Start cache-tests origin server (Node.js)
echo "Starting cache-tests origin server..."
cd cache-tests
npm install --silent
npm run server > /dev/null 2>&1 &
SERVER_PID=$!
echo "Origin server started (PID: $SERVER_PID)"

# Wait for origin server to be ready
wait_for_port 8000 "Origin server" || exit 1

# Start HARP proxy
echo ""
echo "Starting HARP proxy..."
cd "$SCRIPT_DIR"
uv run harp-proxy server --file config.yml > /dev/null 2>&1 &
HARP_PID=$!
echo "HARP proxy started (PID: $HARP_PID)"

# Wait for HARP to be ready
wait_for_port 4000 "HARP proxy" || exit 1

# Run cache-tests against HARP
echo ""
echo "Running cache-tests suite against HARP..."
echo "Testing endpoint: http://localhost:4000"
echo ""
cd cache-tests

# Run tests and save results to JSON
npm run --silent cli --base=http://localhost:4000 > results/harp.json

# Display summary
echo ""
echo "=== Cache Tests Complete ==="
echo ""
echo "Results saved to: cache-tests/results/harp.json"
echo ""
echo "To view HTML results:"
echo "  ./open-results.sh"
echo ""
