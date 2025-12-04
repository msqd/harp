#!/usr/bin/env bash

# Script to show API service status
# Usage: ./status.sh

echo "API Service Status"
echo "=================="
echo ""

for service in api1 api2 api3 api4; do
    status=$(docker compose ps --format "{{.Status}}" "$service" 2>/dev/null | head -1)
    if [ -z "$status" ]; then
        status="not created"
    fi

    # Determine emoji based on status
    if [[ "$status" == *"Up"* ]]; then
        emoji="[UP]"
    else
        emoji="[--]"
    fi

    printf "%-6s %s %s\n" "$service:" "$emoji" "$status"
done

echo ""
echo "Commands:"
echo "  ./up.sh api1 api2    - Start specific services"
echo "  ./down.sh api1       - Stop specific services"
