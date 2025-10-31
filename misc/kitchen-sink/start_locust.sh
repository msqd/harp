#!/bin/bash
# Auto-start locust in headless mode targeting both ports 4000 and 4001
# Usage: ./start_locust.sh or bash start_locust.sh

USERS=${USERS:-50}
SPAWN_RATE=${SPAWN_RATE:-10}
HOST=${HOST:-http://localhost:4000}

echo "Starting Locust load testing..."
echo "Target: $HOST (will alternate between :4000 and :4001)"
echo "Users: $USERS"
echo "Spawn rate: $SPAWN_RATE users/second"
echo "Web UI: http://localhost:8089"
echo ""

uvx locust \
  -f locustfile.py \
  --host "$HOST" \
  --users "$USERS" \
  --spawn-rate "$SPAWN_RATE" \
  --autostart
