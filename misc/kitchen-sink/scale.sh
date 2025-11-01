#!/usr/bin/env bash
set -e

# Script to scale individual API services
# Usage: ./scale.sh <service> <replicas>
# Example: ./scale.sh api1 5

if [ $# -ne 2 ]; then
    echo "Usage: $0 <service> <replicas>"
    echo ""
    echo "Services: api1, api2, api3, api4"
    echo "Example: $0 api1 3"
    exit 1
fi

SERVICE=$1
REPLICAS=$2

# Validate service name
if [[ ! "$SERVICE" =~ ^api[1-4]$ ]]; then
    echo "Error: Invalid service name '$SERVICE'"
    echo "Valid services: api1, api2, api3, api4"
    exit 1
fi

# Validate replicas is a number
if ! [[ "$REPLICAS" =~ ^[0-9]+$ ]]; then
    echo "Error: Replicas must be a positive number"
    exit 1
fi

# Get current replica counts for all API services
# This preserves existing replica counts when scaling one service
API1_COUNT=$(docker compose ps "api1" 2>/dev/null | tail -n +2 | wc -l | tr -d ' ')
API2_COUNT=$(docker compose ps "api2" 2>/dev/null | tail -n +2 | wc -l | tr -d ' ')
API3_COUNT=$(docker compose ps "api3" 2>/dev/null | tail -n +2 | wc -l | tr -d ' ')
API4_COUNT=$(docker compose ps "api4" 2>/dev/null | tail -n +2 | wc -l | tr -d ' ')

# Update the target service's replica count
case "$SERVICE" in
    api1) API1_COUNT=$REPLICAS ;;
    api2) API2_COUNT=$REPLICAS ;;
    api3) API3_COUNT=$REPLICAS ;;
    api4) API4_COUNT=$REPLICAS ;;
esac

echo "Scaling $SERVICE to $REPLICAS replicas..."
docker compose up -d \
    --scale api1=$API1_COUNT \
    --scale api2=$API2_COUNT \
    --scale api3=$API3_COUNT \
    --scale api4=$API4_COUNT \
    --no-recreate

echo "✓ $SERVICE scaled to $REPLICAS replicas"
