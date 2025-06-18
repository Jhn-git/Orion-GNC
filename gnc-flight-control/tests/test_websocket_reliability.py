"""
Comprehensive tests for WebSocket reliability improvements.
Tests cover error handling, connection resilience, ping/pong heartbeat, 
retry logic, and Docker integration scenarios.

Following TDD principles: Write failing tests first that define expected behavior.
"""

import asyncio
import pytest
import websockets
import json
import logging
from unittest.mock import patch, MagicMock, AsyncMock, call
import fakeredis.aioredis
from websockets.exceptions import (
    InvalidHandshake, 
    ConnectionClosedError, 
    ConnectionClosedOK,
    InvalidMessage
)

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
# Import the functions to be tested
from main import (
    websocket_handler,
    register_client,
    unregister_client,
    clients,
    main,
    broadcast_telemetry
)


@pytest.fixture
def mock_redis():
    """Mocks the redis.Redis connection using fakeredis."""
    fake_redis = fakeredis.aioredis.FakeRedis()
    with patch('redis.asyncio.Redis', return_value=fake_redis):
        yield fake_redis


@pytest.fixture
def mock_websocket():
    """Creates a mock WebSocket with common attributes."""
    mock_ws = AsyncMock()
    mock_ws.remote_address = ("127.0.0.1", 12345)
    mock_ws.wait_closed = AsyncMock()
    return mock_ws


@pytest.fixture
def caplog_setup():
    """Setup logging capture for testing log messages."""
    with patch('main.logger') as mock_logger:
        # Ensure the mock logger captures all levels
        mock_logger.setLevel(logging.DEBUG)
        yield mock_logger


@pytest.fixture(autouse=True)
def clean_clients():
    """Automatically clean the clients set before and after each test."""
    clients.clear()
    yield
    clients.clear()


class TestWebSocketServerErrorHandling:
    """
    A. Test WebSocket Server Error Handling
    Tests for handling websockets.exceptions and proper logging.
    """

    @pytest.mark.asyncio
    async def test_websocket_handler_graceful_disconnect(self, mock_websocket, caplog_setup):
        """
        TDD_ANCHOR: test_websocket_handler_graceful_disconnect
        Test handling of ConnectionClosedOK with INFO-level logging.
        FAILING TEST - Current implementation doesn't handle ConnectionClosedOK specifically.
        """
        clients.clear()
        mock_logger = caplog_setup
        
        # Mock wait_closed to raise ConnectionClosedOK
        mock_websocket.wait_closed.side_effect = ConnectionClosedOK(None, None)
        
        # Execute the handler
        await websocket_handler(mock_websocket, "/test")
        
        # Verify client cleanup
        assert mock_websocket not in clients
        assert len(clients) == 0
        
        # Verify INFO-level logging for graceful disconnect
        mock_logger.info.assert_any_call(
            f"Client {mock_websocket.remote_address} disconnected gracefully."
        )

    @pytest.mark.asyncio
    async def test_websocket_handler_unexpected_disconnect(self, mock_websocket, caplog_setup):
        """
        TDD_ANCHOR: test_websocket_handler_unexpected_disconnect
        Test handling of ConnectionClosedError with WARNING-level logging.
        FAILING TEST - Current implementation doesn't handle ConnectionClosedError specifically.
        """
        clients.clear()
        mock_logger = caplog_setup
        
        # Mock wait_closed to raise ConnectionClosedError
        error_msg = "Connection lost unexpectedly"
        mock_exception = ConnectionClosedError(None, None, error_msg)
        # Mock the __str__ method to avoid string representation issues
        mock_exception.__str__ = lambda: error_msg
        mock_websocket.wait_closed.side_effect = mock_exception
        
        # Execute the handler
        await websocket_handler(mock_websocket, "/test")
        
        # Verify client cleanup
        assert mock_websocket not in clients
        assert len(clients) == 0
        
        # Verify WARNING-level logging for unexpected disconnect
        mock_logger.warning.assert_any_call(
            f"Client {mock_websocket.remote_address} disconnected unexpectedly."
        )

    @pytest.mark.asyncio
    async def test_websocket_handler_invalid_handshake(self, mock_websocket, caplog_setup):
        """
        Test handling of InvalidHandshake exception with proper logging.
        FAILING TEST - Current implementation doesn't handle InvalidHandshake specifically.
        """
        clients.clear()
        mock_logger = caplog_setup
        
        # Mock wait_closed to raise InvalidHandshake
        mock_websocket.wait_closed.side_effect = InvalidHandshake("Invalid handshake")
        
        # Execute the handler
        await websocket_handler(mock_websocket, "/test")
        
        # Verify client cleanup
        assert mock_websocket not in clients
        
        # Verify ERROR-level logging for invalid handshake
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_websocket_handler_invalid_message(self, mock_websocket, caplog_setup):
        """
        Test handling of InvalidMessage exception with proper logging.
        FAILING TEST - Current implementation doesn't handle InvalidMessage specifically.
        """
        clients.clear()
        mock_logger = caplog_setup
        
        # Mock wait_closed to raise InvalidMessage
        mock_websocket.wait_closed.side_effect = InvalidMessage("Invalid message format")
        
        # Execute the handler
        await websocket_handler(mock_websocket, "/test")
        
        # Verify client cleanup
        assert mock_websocket not in clients
        
        # Verify ERROR-level logging for invalid message
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_websocket_handler_multiple_clients_unaffected(self, caplog_setup):
        """
        TDD_ANCHOR: test_websocket_handler_multiple_clients_unaffected
        Test that one client's error doesn't affect other connected clients.
        FAILING TEST - Need to verify isolation between client connections.
        """
        clients.clear()
        mock_logger = caplog_setup
        
        # Create multiple mock clients
        client1 = AsyncMock()
        client1.remote_address = ("127.0.0.1", 1001)
        client1.wait_closed = AsyncMock()
        
        client2 = AsyncMock()
        client2.remote_address = ("127.0.0.1", 1002)
        mock_exception = ConnectionClosedError(None, None, "Network error")
        mock_exception.__str__ = lambda: "Network error"
        client2.wait_closed.side_effect = mock_exception
        
        client3 = AsyncMock()
        client3.remote_address = ("127.0.0.1", 1003)
        client3.wait_closed = AsyncMock()
        
        # Run handlers concurrently
        tasks = [
            websocket_handler(client1, "/test1"),
            websocket_handler(client2, "/test2"),
            websocket_handler(client3, "/test3")
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all clients are cleaned up
        assert len(clients) == 0
        assert client1 not in clients
        assert client2 not in clients
        assert client3 not in clients
        
        # Verify error logging only for client2
        mock_logger.warning.assert_called_once_with(
            f"Client {client2.remote_address} disconnected unexpectedly."
        )

    @pytest.mark.asyncio
    async def test_websocket_handler_general_exception_handling(self, mock_websocket, caplog_setup):
        """
        Test handling of unexpected exceptions with proper logging and cleanup.
        FAILING TEST - Current implementation may not log unexpected exceptions with exc_info.
        """
        clients.clear()
        mock_logger = caplog_setup
        
        # Mock wait_closed to raise unexpected exception
        unexpected_error = RuntimeError("Unexpected server error")
        mock_websocket.wait_closed.side_effect = unexpected_error
        
        # Execute the handler
        await websocket_handler(mock_websocket, "/test")
        
        # Verify client cleanup
        assert mock_websocket not in clients
        
        # Verify ERROR-level logging with exc_info for unexpected exceptions
        mock_logger.error.assert_any_call(
            f"An unexpected error occurred with client {mock_websocket.remote_address}: {unexpected_error}",
            exc_info=True
        )


class TestConnectionResilience:
    """
    B. Test Connection Resilience
    Tests for ping/pong heartbeat, health monitoring, retry logic, and timeouts.
    """

    @pytest.mark.asyncio
    async def test_server_sends_pings(self):
        """
        TDD_ANCHOR: test_server_sends_pings
        Test that server is configured with ping_interval for heartbeat mechanism.
        FAILING TEST - Current main() doesn't configure ping_interval.
        """
        with patch('websockets.serve', new_callable=AsyncMock) as mock_serve, \
             patch('main.initialize_krpc') as mock_init_krpc, \
             patch('asyncio.create_task') as mock_create_task, \
             patch('asyncio.gather', new_callable=AsyncMock) as mock_gather:
            
            # Mock the tasks to prevent actual execution
            mock_create_task.return_value = AsyncMock()
            mock_gather.return_value = AsyncMock()
            
            # Mock environment variables for ping configuration
            with patch.dict('os.environ', {
                'PING_INTERVAL_SECONDS': '20',
                'PING_TIMEOUT_SECONDS': '20'
            }):
                # This should fail because main() doesn't read ping config yet
                await main()
                
                # Verify websockets.serve was called with ping parameters
                mock_serve.assert_called_once()
                args, kwargs = mock_serve.call_args
                
                # These assertions will fail with current implementation
                assert 'ping_interval' in kwargs
                assert kwargs['ping_interval'] == 20
                assert 'ping_timeout' in kwargs
                assert kwargs['ping_timeout'] == 20

    @pytest.mark.asyncio
    async def test_server_disconnects_on_ping_timeout(self):
        """
        TDD_ANCHOR: test_server_disconnects_on_ping_timeout
        Test that server automatically closes connections on ping timeout.
        FAILING TEST - Current implementation doesn't configure ping_timeout.
        """
        with patch('websockets.serve', new_callable=AsyncMock) as mock_serve:
            
            with patch.dict('os.environ', {
                'PING_TIMEOUT_SECONDS': '10'
            }):
                # Mock the main function components
                with patch('main.initialize_krpc') as mock_init_krpc, \
                                     patch('asyncio.create_task') as mock_create_task, \
                                     patch('asyncio.gather', new_callable=AsyncMock) as mock_gather:
                    
                    mock_create_task.return_value = AsyncMock()
                    mock_gather.return_value = AsyncMock()
                    
                    await main()
                    
                    # Verify ping_timeout is configured
                    args, kwargs = mock_serve.call_args
                    assert 'ping_timeout' in kwargs
                    assert kwargs['ping_timeout'] == 10

    @pytest.mark.asyncio
    async def test_ping_interval_environment_variable(self):
        """
        Test that PING_INTERVAL_SECONDS environment variable is read correctly.
        """
        with patch.dict('os.environ', {'PING_INTERVAL_SECONDS': '30'}):
            import importlib
            import main
            importlib.reload(main) # Reload the module to pick up new env var
            assert main.PING_INTERVAL_SECONDS == 30

    @pytest.mark.asyncio
    async def test_ping_timeout_environment_variable(self):
        """
        Test that PING_TIMEOUT_SECONDS environment variable is read correctly.
        """
        with patch.dict('os.environ', {'PING_TIMEOUT_SECONDS': '25'}):
            import importlib
            import main
            importlib.reload(main) # Reload the module to pick up new env var
            assert main.PING_TIMEOUT_SECONDS == 25

    @pytest.mark.asyncio
    async def test_connection_health_monitoring(self, mock_websocket):
        """
        Test connection health monitoring through ping/pong mechanism.
        FAILING TEST - Need to verify ping/pong handling in websocket_handler.
        """
        clients.clear()
        
        # Mock ping method on websocket
        mock_websocket.ping = AsyncMock()
        mock_websocket.ping.return_value = AsyncMock()  # Mock pong response
        
        # Execute handler
        await websocket_handler(mock_websocket, "/test")
        
        # Verify client cleanup (basic test for now)
        assert mock_websocket not in clients


class TestDockerIntegration:
    """
    C. Test Docker Integration
    Tests for health check improvements, resource constraints, and network instability.
    """

    def test_health_check_script_exists(self):
        """
        Test that health check script will be created.
        FAILING TEST - healthcheck.py doesn't exist yet.
        """
        import os
        health_check_path = "gnc-flight-control/healthcheck.py"
        # This will fail because healthcheck.py doesn't exist yet
        assert os.path.exists(health_check_path)

    @pytest.mark.asyncio
    async def test_health_check_websocket_handshake(self):
        """
        Test that health check validates WebSocket handshake, not just TCP.
        FAILING TEST - healthcheck.py doesn't exist yet.
        """
        # This will fail because we need to create healthcheck.py
        import healthcheck
        
        with patch('websockets.connect') as mock_connect:
            mock_connect.return_value.__aenter__.return_value = AsyncMock()
            
            result = await healthcheck.check_websocket()
            assert result == 0  # Success
            mock_connect.assert_called_with("ws://localhost:8765")

    @pytest.mark.asyncio
    async def test_health_check_timeout_handling(self):
        """
        Test that health check handles connection timeouts gracefully.
        FAILING TEST - healthcheck.py doesn't exist yet.
        """
        import healthcheck
        
        with patch('websockets.connect') as mock_connect:
            mock_connect.side_effect = asyncio.TimeoutError("Connection timeout")
            
            result = await healthcheck.check_websocket()
            assert result == 1  # Failure

    def test_docker_compose_health_check_configuration(self):
        """
        Test that docker-compose.yml will be updated with proper health check.
        FAILING TEST - docker-compose.yml doesn't have the new health check yet.
        """
        # Read docker-compose.yml and verify health check configuration
        with open("docker-compose.yml", "r") as f:
            content = f.read()
        
        # This will fail because docker-compose.yml hasn't been updated yet
        assert 'test: ["CMD", "python", "/app/healthcheck.py"]' in content
        assert "interval: 30s" in content
        assert "timeout: 10s" in content

    @pytest.mark.asyncio
    async def test_resource_constraint_scenarios(self):
        """
        Test behavior under resource constraints.
        FAILING TEST - Need to implement resource monitoring in main.py.
        """
        # Mock resource constraints
        with patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.cpu_percent') as mock_cpu:
            
            # Simulate high memory usage
            mock_memory.return_value.percent = 90
            mock_cpu.return_value = 95
            
            # Test that service handles high resource usage gracefully
            # This will fail because we don't have resource monitoring yet
            from main import check_resource_usage
            result = await check_resource_usage()
            assert result is not None

    @pytest.mark.asyncio
    async def test_network_instability_simulation(self, mock_websocket, caplog_setup):
        """
        Test handling of network instability scenarios.
        FAILING TEST - Need network instability handling in websocket_handler.
        """
        clients.clear()
        
        # Simulate network instability with intermittent connection errors
        # The websocket_handler now logs a generic message for ConnectionClosedError
        mock_exception = ConnectionClosedError(None, None, "Network unreachable")
        mock_exception.__str__ = lambda: "Network unreachable" # Still mock for safety, though not directly asserted now
        
        mock_websocket.wait_closed.side_effect = mock_exception
        
        # Execute handler
        await websocket_handler(mock_websocket, "/test")
        
        # Verify proper error handling and cleanup
        assert mock_websocket not in clients
        
        # Verify a warning was logged for the unexpected disconnect
        mock_logger = caplog_setup
        mock_logger.warning.assert_any_call(
            f"Client {mock_websocket.remote_address} disconnected unexpectedly."
        )


class TestClientReconnectionLogic:
    """
    D. Test Client Reconnection Logic
    Tests for automatic reconnection, state management, and backoff strategies.
    Note: These are preparation tests for future client-side implementation.
    """

    def test_client_reconnection_test_file_creation(self):
        """
        Test that client reconnection test file will be created.
        FAILING TEST - We need to create the client-side test file.
        """
        import os
        client_test_path = "telemetry-dashboard/tests/test_client_reconnection.py"
        # This will fail because the file doesn't exist yet
        assert os.path.exists(client_test_path)

    def test_javascript_websocket_manager_class(self):
        """
        Test that WebSocketManager class will be implemented in main.js.
        FAILING TEST - Current main.js doesn't have WebSocketManager class.
        """
        with open("telemetry-dashboard/static/main.js", "r") as f:
            content = f.read()
        
        # This will fail because WebSocketManager class doesn't exist yet
        assert "class WebSocketManager" in content
        assert "reconnectAttempts" in content
        assert "exponential backoff" in content.lower() or "reconnectDelay" in content

    @pytest.mark.asyncio
    async def test_automatic_reconnection_on_disconnect(self):
        """
        Test client automatic reconnection logic.
        FAILING TEST - Need to implement reconnection logic.
        """
        # This test will drive the implementation of client-side reconnection
        # For now, it's a placeholder that will fail
        assert False, "Client reconnection logic not implemented yet"

    @pytest.mark.asyncio
    async def test_connection_state_management(self):
        """
        Test client connection state management.
        FAILING TEST - Need to implement state management.
        """
        # This test will drive the implementation of connection state tracking
        assert False, "Connection state management not implemented yet"

    @pytest.mark.asyncio
    async def test_exponential_backoff_strategy(self):
        """
        Test client exponential backoff strategy for reconnection.
        FAILING TEST - Need to implement backoff strategy.
        """
        # This test will drive the implementation of exponential backoff
        assert False, "Exponential backoff strategy not implemented yet"


class TestBroadcastTelemetryReliability:
    """
    Additional tests for broadcast_telemetry reliability under various conditions.
    """

    @pytest.mark.asyncio
    async def test_broadcast_telemetry_with_failed_client(self, caplog_setup):
        """
        TDD_ANCHOR: test_broadcast_telemetry_with_failed_client
        Test that broadcast_telemetry handles individual client send failures.
        """
        clients.clear()
        
        # Use the mock logger directly as the logger parameter
        mock_logger = caplog_setup
        
        # Create clients with different behaviors
        good_client = AsyncMock()
        good_client.send = AsyncMock(return_value=None)
        good_client.remote_address = ("127.0.0.1", 2001)

        bad_client = AsyncMock()
        bad_client.send = AsyncMock(side_effect=websockets.exceptions.ConnectionClosed(None, None))
        bad_client.remote_address = ("127.0.0.1", 2002)

        another_good_client = AsyncMock()
        another_good_client.send = AsyncMock(return_value=None)
        another_good_client.remote_address = ("127.0.0.1", 2003)
        
        clients.add(good_client)
        clients.add(bad_client)
        clients.add(another_good_client)
        
        telemetry_data = {"test": "data"}
        message = json.dumps(telemetry_data)
        
        # Configure bad_client.send to raise an exception
        bad_client.send.side_effect = websockets.exceptions.ConnectionClosed(None, None)
        
        # Should handle the failed client gracefully - pass the mock logger
        await broadcast_telemetry(telemetry_data, current_logger=mock_logger)
        
        # Debug: Check the actual clients in the set
        print(f"Clients in set after broadcast: {len(clients)}")
        for client in clients:
            print(f"Client: {client.remote_address}, send call_count: {client.send.call_count}")
        
        # Good clients should still receive the message
        assert good_client.send.call_count == 1, f"Expected 1 call, got {good_client.send.call_count}"
        assert good_client.send.call_args == call(message)
        assert another_good_client.send.call_count == 1, f"Expected 1 call, got {another_good_client.send.call_count}"
        assert another_good_client.send.call_args == call(message)
        
        # Verify that send was attempted on the bad client
        assert bad_client.send.call_count == 1, f"Expected 1 call, got {bad_client.send.call_count}"
        assert bad_client.send.call_args == call(message)
        
        # Verify a warning was logged for the bad client
        mock_logger.warning.assert_any_call(
            f"Failed to send message to client {bad_client.remote_address}: {bad_client.send.side_effect}"
        )
        
        clients.clear()

    @pytest.mark.asyncio
    async def test_broadcast_telemetry_concurrent_safety(self):
        """
        Test that broadcast_telemetry is safe for concurrent access.
        FAILING TEST - Need to verify thread safety of client set operations.
        """
        clients.clear()
        
        # Add multiple clients
        for i in range(10):
            client = AsyncMock()
            clients.add(client)
        
        telemetry_data = {"concurrent": "test"}
        
        # Run multiple broadcasts concurrently
        tasks = [broadcast_telemetry(telemetry_data) for _ in range(5)]
        await asyncio.gather(*tasks)
        
        # Verify no exceptions and proper behavior
        assert len(clients) == 10
        
        clients.clear()


class TestConfigurationManagement:
    """
    Tests for configuration management and environment variable handling.
    """

    def test_websocket_port_configuration(self):
        """
        Test WEBSOCKET_PORT environment variable handling.
        PASSING TEST - This should already work.
        """
        with patch.dict('os.environ', {'WEBSOCKET_PORT': '9000'}):
            # Reload the module to pick up new env var
            import importlib
            import main
            importlib.reload(main)
            
            from main import WEBSOCKET_PORT
            assert WEBSOCKET_PORT == 9000

    def test_default_ping_configuration_values(self):
        """
        Test default values for ping configuration.
        FAILING TEST - These constants don't exist yet.
        """
        # Clear environment variables
        with patch.dict('os.environ', {}, clear=True):
            import importlib
            import main
            importlib.reload(main)
            
            # This will fail because these constants don't exist yet
            from main import PING_INTERVAL_SECONDS, PING_TIMEOUT_SECONDS
            assert PING_INTERVAL_SECONDS == 20  # Default value
            assert PING_TIMEOUT_SECONDS == 20   # Default value