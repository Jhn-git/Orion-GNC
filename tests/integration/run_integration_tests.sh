#!/bin/bash

# Integration Test Runner Script
# Validates complete system communication flow after SPARC orchestration bug fixes

set -e

echo "🧪 Starting Orion GNC Integration Test Suite"
echo "============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log with timestamp
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Navigate to project root
cd "$(dirname "$0")/../.."

log "Cleaning up any existing containers..."
docker-compose down -v 2>/dev/null || true

log "Installing integration test dependencies..."
pip install -r tests/integration/requirements-test.txt

log "Building and starting all services..."
docker-compose up -d --build

log "Waiting for services to be ready..."
sleep 60

log "Running integration tests..."
echo ""

# Run the integration tests
cd tests/integration
if python -m pytest test_system_integration.py -v --tb=short; then
    log "✅ Integration tests PASSED!"
    log "🎉 SPARC orchestration fixes successfully validated!"
    log ""
    log "Critical bugs resolved:"
    log "  ✓ Mission Control UI Gunicorn worker configuration"
    log "  ✓ GNC Flight Control WebSocket TypeError fix"
    log "  ✓ Complete system startup and communication"
    log "  ✓ Redis Pub/Sub messaging validation"
    log "  ✓ End-to-end mission workflow"
    TEST_RESULT=0
else
    error "❌ Integration tests FAILED!"
    error "Some critical system issues may not be resolved"
    TEST_RESULT=1
fi

log "Cleaning up containers..."
cd ../..
docker-compose down -v

log "Integration test run completed."
exit $TEST_RESULT