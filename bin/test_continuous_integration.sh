#!/bin/bash

# Run all the CI test task locally to check the process. "set -e" will make the script stop on the first error.
# Usage: bin/test_continuous_integration.sh

set -e  # stop on non-successful commands

# Change to the project root directory (parent of bin)
cd "$(dirname "$0")/.."



# Function to display colored banner
banner() {
    echo -e "\n\033[1;34m================================================================================\033[0m"
    echo -e "\033[1;33m  $1\033[0m"
    echo -e "\033[1;34m================================================================================\033[0m\n"
}

# Environment variables
export CI=true
export CI_PYTEST_CPUS=1
export VERSION=ci-$(date +%Y%m%d%H%M%S)-$(openssl rand -hex 4)

# detect cpu arch
if [ -z "$DOCKER_PLATFORM" ]; then
    if [ "$(uname -m)" = "arm64" ]; then
        export DOCKER_PLATFORM=linux/arm64
    else
        export DOCKER_PLATFORM=linux/amd64
    fi
fi


# Build image for better performance on Apple Silicon
banner "Building development container"
make buildc-dev

# Run all CI test suites
banner "Running backend core tests"
make ci-test-backend-core

banner "Running backend apps tests"
make ci-test-backend-apps

banner "Running backend e2e tests"
make ci-test-backend-e2e

banner "Running frontend unit tests"
make ci-test-frontend-unit
