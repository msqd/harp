#!/usr/bin/env bash

# Script to watch API service replica counts
# Uses watch command to refresh every 2 seconds
# Usage: ./watch.sh

if ! command -v watch &> /dev/null; then
    echo "Error: 'watch' command not found"
    echo "Install it with: brew install watch (macOS) or apt install procps (Linux)"
    exit 1
fi

watch -n 2 '
echo "API Service Replica Counts"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━"
for service in api1 api2 api3 api4; do
    running=$(docker compose ps --filter "status=running" "$service" 2>/dev/null | tail -n +2 | wc -l | tr -d " ")
    echo "$service: $running replica(s) running"
done
'
