#!/bin/bash
#
# Runs the http-tests/cache-tests RFC 9111 compliance suite against HARP and compares the result to a
# recorded baseline.
#
# Every step that can stop the run reports it and exits non-zero. This script used to exit 0 whatever
# happened, including runs where HARP never started, which is what #990 was about.
#
# Environment:
#   CACHE_TESTS_DATABASE_URL   storage DSN. Unset means a file-backed SQLite database under results/.
#   CACHE_TESTS_PROXY_PORT     port HARP listens on (default 4000)
#   CACHE_TESTS_ORIGIN_PORT    port the suite's own origin server listens on (default 8000)

set -euo pipefail

# Job control, so each background job becomes its own process group. `npm run` spawns the real server
# as a child, and killing npm alone leaves it listening: the next run then fails on a port that is
# still held by the previous one.
set -m

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SUITE_DIR="$SCRIPT_DIR/cache-tests"
RESULTS_DIR="$SCRIPT_DIR/results"
BASELINES_DIR="$SCRIPT_DIR/baselines"

PROXY_PORT="${CACHE_TESTS_PROXY_PORT:-4000}"
ORIGIN_PORT="${CACHE_TESTS_ORIGIN_PORT:-8000}"

SERVER_PID=""
HARP_PID=""

fail() {
    echo ""
    echo "FAILED: $*" >&2
    exit 1
}

# Kills only the process groups this script started, by pid. Never by pattern: a pattern matches
# other people's proxies, and has killed them on shared machines.
cleanup() {
    local code=$?
    for pid in "$HARP_PID" "$SERVER_PID"; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
        fi
    done
    exit $code
}
trap cleanup EXIT INT TERM

wait_for_port() {
    local port=$1 service=$2 logfile=$3 waited=0
    while ! nc -z localhost "$port" 2>/dev/null; do
        if [ $waited -ge 30 ]; then
            echo "--- last lines of $logfile ---" >&2
            tail -n 30 "$logfile" >&2 || true
            fail "$service did not listen on port $port within 30s"
        fi
        sleep 1
        waited=$((waited + 1))
    done
}

require_free_port() {
    local port=$1 service=$2
    if nc -z localhost "$port" 2>/dev/null; then
        fail "port $port is already in use, so $service cannot start there. Stop it, or set ${3}."
    fi
}

# --- the suite itself -------------------------------------------------------------------------

[ -f "$SUITE_DIR/package.json" ] || fail "the cache-tests submodule is not initialised. Run:
    git submodule update --init --recursive misc/cache-tests/cache-tests"

SUITE_COMMIT="$(git -C "$SUITE_DIR" rev-parse HEAD)"
HARP_COMMIT="$(git -C "$REPO_DIR" rev-parse HEAD)"

# --- storage ----------------------------------------------------------------------------------

mkdir -p "$RESULTS_DIR"

if [ -n "${CACHE_TESTS_DATABASE_URL:-}" ]; then
    DATABASE_URL="$CACHE_TESTS_DATABASE_URL"
else
    # A file, not HARP's `:memory:` default: on the in-memory default the cache mostly does not
    # cache, and the suite scores 40% instead of 57%. Removed before each run so every run is cold.
    rm -f "$RESULTS_DIR/storage.db"
    DATABASE_URL="sqlite+aiosqlite:///$RESULTS_DIR/storage.db"
fi

# The backend label is derived from the DSN rather than declared separately, so the label and the
# thing it describes cannot disagree.
BACKEND="$(echo "$DATABASE_URL" | sed -E 's/[+:].*//')"
BASELINE="$BASELINES_DIR/$BACKEND.json"

echo "=== RFC 9111 compliance suite"
echo "    storage backend  $BACKEND"
echo "    suite            $SUITE_COMMIT"
echo "    harp             $HARP_COMMIT"
echo ""

require_free_port "$ORIGIN_PORT" "the cache-tests origin server" "CACHE_TESTS_ORIGIN_PORT"
require_free_port "$PROXY_PORT" "HARP" "CACHE_TESTS_PROXY_PORT"

# --- origin server ----------------------------------------------------------------------------

echo "Installing suite dependencies..."
(cd "$SUITE_DIR" && npm install --silent) || fail "npm install failed in $SUITE_DIR"

echo "Starting the origin server on :$ORIGIN_PORT..."
(cd "$SUITE_DIR" && npm run server --port="$ORIGIN_PORT") > "$RESULTS_DIR/origin.log" 2>&1 &
SERVER_PID=$!
wait_for_port "$ORIGIN_PORT" "the origin server" "$RESULTS_DIR/origin.log"

# --- harp -------------------------------------------------------------------------------------

echo "Starting HARP on :$PROXY_PORT..."
(cd "$SCRIPT_DIR" && uv run --project "$REPO_DIR" harp-proxy server \
    --file config.yml \
    --applications http_client,http_cache,proxy,storage \
    --endpoint "cache-tests=$PROXY_PORT:http://localhost:$ORIGIN_PORT/" \
    --set "storage.url=$DATABASE_URL") > "$RESULTS_DIR/harp.log" 2>&1 &
HARP_PID=$!
wait_for_port "$PROXY_PORT" "HARP" "$RESULTS_DIR/harp.log"

# Listening is not the same as proxying. Without this, a HARP that cannot reach the origin produces
# 365 setup errors and a score of zero, which reads like a compliance collapse rather than a broken
# run.
echo "Checking the proxy actually reaches the origin..."
curl -fsS "http://localhost:$PROXY_PORT/" | grep -q "HTTP Caching Tests" || {
    echo "--- last lines of $RESULTS_DIR/harp.log ---" >&2
    tail -n 30 "$RESULTS_DIR/harp.log" >&2 || true
    fail "HARP is listening on :$PROXY_PORT but did not serve the origin's index page"
}

# --- run --------------------------------------------------------------------------------------

run_suite() {
    local output=$1
    (cd "$SUITE_DIR" && npm run --silent cli --base="http://localhost:$PROXY_PORT") > "$output" \
        || fail "the cache-tests cli exited non-zero, see $output"

    # A server that dies mid-run leaves a full set of verdicts that are all failures, which reads as a
    # compliance collapse and is nothing of the sort. Whatever is in $output describes a broken run,
    # so no score is claimed from it.
    nc -z localhost "$ORIGIN_PORT" 2>/dev/null \
        || fail "the origin server stopped listening on :$ORIGIN_PORT during the run, so $output
    describes a broken run and not HARP's compliance. See $RESULTS_DIR/origin.log"
    nc -z localhost "$PROXY_PORT" 2>/dev/null \
        || fail "HARP stopped listening on :$PROXY_PORT during the run, so $output describes a
    broken run and not HARP's compliance. See $RESULTS_DIR/harp.log"
}

echo "Running the suite (about a minute)..."
run_suite "$RESULTS_DIR/$BACKEND.json"

# Recording a baseline runs the suite exactly the way the gate runs it, so a baseline can never
# describe conditions the gate does not reproduce. It runs it several times, because about one test
# per run changes verdict and it is a different test each time: a baseline taken from a single
# observation records whichever tests happened to flap that day as their unlucky value, and then
# reports them for ever.
if [ -n "${CACHE_TESTS_RECORD_REASON:-}" ]; then
    recorded="$RESULTS_DIR/$BACKEND.json"
    for run in $(seq 2 "${CACHE_TESTS_BASELINE_RUNS:-3}"); do
        echo "Running the suite again, $run of ${CACHE_TESTS_BASELINE_RUNS:-3}..."
        run_suite "$RESULTS_DIR/$BACKEND.record-$run.json"
        recorded="$recorded $RESULTS_DIR/$BACKEND.record-$run.json"
    done

    echo ""
    # shellcheck disable=SC2086  # $recorded is a list of paths this script built
    (cd "$REPO_DIR" && uv run --project "$REPO_DIR" python -m tests.cache_compliance record \
        --baseline "$BASELINE" \
        --backend "$BACKEND" \
        --suite-commit "$SUITE_COMMIT" \
        --harp-commit "$HARP_COMMIT" \
        --recorded-on "$(date +%Y-%m-%d)" \
        --reason "$CACHE_TESTS_RECORD_REASON" \
        $recorded)
    exit $?
fi

[ -f "$BASELINE" ] || fail "no baseline recorded for the $BACKEND backend ($BASELINE).
    Record one deliberately with: make test-e2e-cache-baseline REASON='...'"

check() {
    (cd "$REPO_DIR" && uv run --project "$REPO_DIR" python -m tests.cache_compliance check \
        --baseline "$BASELINE" --backend "$BACKEND" --harp-errors "$(harp_error_count)" "$@")
}

# HARP's own count of requests it failed to proxy. The comparison recognises those failures by
# reading upstream's prose, which is the one thing here that can silently stop matching if the suite
# is updated. This is a second, independent instrument pointed at the same fact: if HARP logged proxy
# errors and the comparison recognised none, the report says the pattern may have gone stale rather
# than quietly reporting a clean run.
harp_error_count() {
    grep -c "◀ HttpError" "$RESULTS_DIR/harp.log" 2>/dev/null || echo 0
}

echo ""
set +e
check "$RESULTS_DIR/$BACKEND.json"
status=$?
set -e

if [ "$status" -eq 0 ]; then
    exit 0
fi

if [ "$status" -ne 1 ]; then
    # The run could not be trusted at all, and running it again will not make it trustworthy.
    exit "$status"
fi

# A regression seen once may be the suite's measured flap: about one test in 365 fails on a transient
# 502, roughly one run in four. A second full run costs a minute and only happens on this path.
echo ""
echo "Candidate regressions above. Re-running the suite once, since a regression seen once may be flap..."
run_suite "$RESULTS_DIR/$BACKEND.2.json"

echo ""
check "$RESULTS_DIR/$BACKEND.json" "$RESULTS_DIR/$BACKEND.2.json"
