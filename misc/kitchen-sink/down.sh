#!/usr/bin/env bash
set -e

# Script to stop individual API services
# Usage: ./down.sh <service1> [service2] ...
# Example: ./down.sh api1 api2

if [ $# -eq 0 ]; then
    echo "Usage: $0 <service1> [service2] ..."
    echo ""
    echo "Services: api1, api2, api3, api4"
    echo "Example: $0 api1 api2"
    exit 1
fi

# Validate all service names first
for SERVICE in "$@"; do
    if [[ ! "$SERVICE" =~ ^api[1-4]$ ]]; then
        echo "Error: Invalid service name '$SERVICE'"
        echo "Valid services: api1, api2, api3, api4"
        exit 1
    fi
done

# Stop the services
echo "Stopping: $*"
docker compose stop "$@"

echo "Done. Use ./status.sh to check service status."
