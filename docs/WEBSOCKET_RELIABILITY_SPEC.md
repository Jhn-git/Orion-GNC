# Specification: WebSocket Reliability Enhancements

## 1. Introduction

This document outlines the specifications for improving the reliability and resilience of the WebSocket communication between the GNC Flight Control service and its clients. The proposed changes address handshake failures, connection instability, and error handling deficiencies.

The implementation will be divided into four main areas:
-   **A. Enhanced WebSocket Server Error Handling**
-   **B. Connection Resilience Improvements**
-   **C. Docker Resource & Network Optimization**
-   **D. Client Connection Robustness**

All pseudocode includes TDD (Test-Driven Development) anchors to guide the creation of corresponding tests.

---

## A. Enhanced WebSocket Server Error Handling

**Applies to:** [`gnc-flight-control/main.py`](gnc-flight-control/main.py:1)

### 1. Functional Requirements

-   The server must catch all common WebSocket connection exceptions from the `websockets` library.
-   Clean client disconnections (`ConnectionClosedOK`) should be logged as INFO.
-   Unexpected disconnections (`ConnectionClosedError`) should be logged as WARNING.
-   The server must gracefully handle client disconnections without impacting other connected clients.

### 2. Pseudocode: `websocket_handler`

```python
# TDD_ANCHOR: test_websocket_handler_graceful_disconnect
# TDD_ANCHOR: test_websocket_handler_unexpected_disconnect
# TDD_ANCHOR: test_websocket_handler_multiple_clients_unaffected

import websockets

async def websocket_handler(websocket, path):
    """
    Handles WebSocket connections with enhanced error handling and logging.
    """
    await register_client(websocket)
    try:
        # The handler will now primarily wait for the connection to close,
        # as pings and other control frames are handled by the library automatically.
        await websocket.wait_closed()
    except websockets.exceptions.ConnectionClosedOK:
        logger.info(f"Client {websocket.remote_address} disconnected gracefully.")
    except websockets.exceptions.ConnectionClosedError as e:
        logger.warning(f"Client {websocket.remote_address} disconnected unexpectedly: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred with client {websocket.remote_address}: {e}", exc_info=True)
    finally:
        await unregister_client(websocket)

# In main():
# Update the server factory to include the new handler and keep-alive settings.
# See Section B for details on keep-alive.
```

---

## B. Connection Resilience Improvements

**Applies to:** [`gnc-flight-control/main.py`](gnc-flight-control/main.py:1)

### 1. Functional Requirements

-   The server must send periodic "ping" frames to clients to keep the connection alive.
-   The server must automatically close connections if a "pong" response is not received within a timeout period.
-   These settings should be configurable via environment variables.

### 2. Pseudocode: Server Initialization

```python
# TDD_ANCHOR: test_server_sends_pings
# TDD_ANCHOR: test_server_disconnects_on_ping_timeout

# --- Configuration ---
WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", 8765))
PING_INTERVAL_SECONDS = int(os.getenv("PING_INTERVAL_SECONDS", 20))
PING_TIMEOUT_SECONDS = int(os.getenv("PING_TIMEOUT_SECONDS", 20))

# --- Main Application ---
async def main():
    """Main application entry point."""
    await initialize_krpc()

    # Add ping_interval and ping_timeout to the server configuration.
    # This enables the automatic keep-alive mechanism.
    websocket_server = await websockets.serve(
        websocket_handler, 
        "0.0.0.0", 
        WEBSOCKET_PORT,
        ping_interval=PING_INTERVAL_SECONDS,
        ping_timeout=PING_TIMEOUT_SECONDS
    )
    logger.info(f"WebSocket server started on port {WEBSOCKET_PORT} with a {PING_INTERVAL_SECONDS}s ping interval.")

    # ... rest of the main function
```

---

## C. Docker Resource & Network Optimization

**Applies to:** [`docker-compose.yml`](docker-compose.yml:1), `gnc-flight-control/`

### 1. Functional Requirements

-   The Docker health check for the `gnc_flight_control` service must validate the WebSocket handshake, not just the TCP port.
-   Resource reservations should be reviewed to ensure service stability under load.

### 2. Health Check Refinement

A dedicated health check script should be created.

**File:** `gnc-flight-control/healthcheck.py`

```python
# TDD_ANCHOR: This script is a test itself and does not require a separate test.

import asyncio
import sys
import websockets

async def check_websocket():
    try:
        # Connect to the server with a short timeout.
        async with asyncio.timeout(5):
            async with websockets.connect("ws://localhost:8765") as websocket:
                # The connection was successful if this block is entered.
                print("WebSocket handshake successful.")
                return 0
    except Exception as e:
        print(f"Health check failed: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(check_websocket()))
```

### 3. `docker-compose.yml` Update

```yaml
# TDD_ANCHOR: test_docker_compose_healthcheck_is_valid

# In services: gnc_flight_control:
services:
  gnc_flight_control:
    build:
      context: ./gnc-flight-control
      dockerfile: Dockerfile
      target: production
    # ... other settings
    healthcheck:
      # Use the new Python script for the health check.
      test: ["CMD", "python", "/app/healthcheck.py"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        # Recommendation: Monitor usage and consider increasing reservations 
        # for production stability if CPU/memory usage is consistently high.
        reservations:
          cpus: '0.2'
          memory: 256M
```

---

## D. Client Connection Robustness

**Applies to:** `telemetry-dashboard/static/main.js` (or equivalent client)

### 1. Functional Requirements

-   The client must detect when a WebSocket connection is closed.
-   The client must attempt to reconnect automatically using an exponential backoff strategy.
-   The UI must display the current connection status (e.g., CONNECTING, OPEN, CLOSED, RECONNECTING).
-   The reconnection attempts should be capped to avoid infinite loops.

### 2. Pseudocode: Client-Side WebSocket Manager

```javascript
// TDD_ANCHOR: test_client_initial_connection
// TDD_ANCHOR: test_client_displays_connection_status
// TDD_ANCHOR: test_client_handles_on_close_event
// TDD_ANCHOR: test_client_reconnects_with_exponential_backoff
// TDD_ANCHOR: test_client_stops_reconnecting_after_max_attempts

class WebSocketManager {
    constructor(url) {
        this.url = url;
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000; // Start with 1 second
        
        // This function would update a UI element.
        this.updateStatusUI = (status) => {
            console.log(`WebSocket Status: ${status}`);
            // e.g., document.getElementById('socket-status').textContent = status;
        };
    }

    connect() {
        this.updateStatusUI('CONNECTING');
        this.websocket = new WebSocket(this.url);

        this.websocket.onopen = () => {
            this.updateStatusUI('OPEN');
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000; // Reset delay on successful connection
            console.log('WebSocket connection established.');
        };

        this.websocket.onmessage = (event) => {
            const telemetryData = JSON.parse(event.data);
            // e.g., updateDashboard(telemetryData);
            console.log('Telemetry received:', telemetryData);
        };

        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            // The onclose event will be fired next, which handles reconnection.
        };

        this.websocket.onclose = (event) => {
            this.updateStatusUI(`CLOSED (Code: ${event.code})`);
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                console.log(`WebSocket closed. Attempting reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${this.reconnectDelay}ms.`);
                setTimeout(() => this.connect(), this.reconnectDelay);
                // Exponential backoff
                this.reconnectDelay = Math.min(30000, this.reconnectDelay * 2); // Cap at 30s
            } else {
                this.updateStatusUI('DISCONNECTED (Max retries reached)');
                console.error('WebSocket reconnection failed after max attempts.');
            }
        };
    }
}

// Usage:
// const socketManager = new WebSocketManager('ws://localhost:8765');
// socketManager.connect();