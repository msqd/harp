#!/bin/bash
# Opens the cache-tests HTML results viewer in a browser

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/cache-tests"

PORT=8080
URL="http://localhost:$PORT/"

# Check if results file exists
if [ ! -f "results/harp.json" ]; then
    echo "No results found. Please run tests first:"
    echo "  make test-e2e-cache"
    exit 1
fi

# Check if port is already in use
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "Port $PORT is already in use."
    echo "Opening browser to existing server at $URL"
else
    echo "Starting HTTP server on port $PORT..."
    python3 -m http.server $PORT > /dev/null 2>&1 &
    SERVER_PID=$!

    # Wait for server to be ready
    echo "Waiting for server to start..."
    MAX_WAIT=5
    WAITED=0
    while ! nc -z localhost $PORT 2>/dev/null; do
        if [ $WAITED -ge $MAX_WAIT ]; then
            echo "ERROR: Server failed to start within ${MAX_WAIT}s"
            kill $SERVER_PID 2>/dev/null || true
            exit 1
        fi
        sleep 1
        WAITED=$((WAITED + 1))
    done

    echo "Server started (PID: $SERVER_PID)"
    echo ""
    echo "To stop the server later, run:"
    echo "  kill $SERVER_PID"
    echo ""
fi

# Open browser
echo "Opening browser to $URL"

# Try different browser opening commands (cross-platform)
if command -v open >/dev/null 2>&1; then
    # macOS
    open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then
    # Linux
    xdg-open "$URL"
elif command -v start >/dev/null 2>&1; then
    # Windows
    start "$URL"
else
    echo "Could not detect browser opener command."
    echo "Please open manually: $URL"
fi

echo ""
echo "Results viewer is ready!"
echo "Press Ctrl+C to stop."

# Keep script running if we started the server
if [ ! -z "$SERVER_PID" ]; then
    # Trap to cleanup on exit
    trap "echo ''; echo 'Stopping server...'; kill $SERVER_PID 2>/dev/null || true" EXIT INT TERM

    # Wait indefinitely
    wait $SERVER_PID 2>/dev/null || true
fi
