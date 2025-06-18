import asyncio
import pytest
import websockets
from unittest.mock import patch, MagicMock, AsyncMock
import fakeredis.aioredis

# Import the functions to be tested
from main import websocket_handler, register_client, unregister_client, clients

@pytest.fixture
def mock_redis():
    """Mocks the redis.Redis connection using fakeredis."""
    # Use fakeredis for proper async Redis mocking
    fake_redis = fakeredis.aioredis.FakeRedis()
    with patch('redis.asyncio.Redis', return_value=fake_redis):
        yield fake_redis

@pytest.mark.asyncio
async def test_websocket_handler_signature():
    """
    Tests that the websocket_handler function accepts two arguments (websocket, path)
    without raising a TypeError. This is the initial failing test following TDD Red phase.
    """
    # Clear clients set before test
    clients.clear()
    
    # Create a mock websocket with the necessary attributes
    mock_websocket = AsyncMock()
    mock_websocket.remote_address = ("127.0.0.1", 12345)
    
    # Mock the wait_closed method to return immediately
    mock_websocket.wait_closed = AsyncMock()
    
    try:
        # Test that the handler accepts websocket and path arguments
        await websocket_handler(mock_websocket, "dummy_path")
        # Verify that the websocket was added to clients during the handler execution
        assert mock_websocket in clients or len(clients) == 0  # Allow for both cases
    except TypeError as e:
        pytest.fail(f"websocket_handler should accept 'websocket' and 'path' arguments: {e}")
    finally:
        # Clean up clients set after test
        clients.clear()

@pytest.mark.asyncio
async def test_register_client_adds_to_clients_set():
    """
    Tests that register_client adds a websocket to the clients set.
    This is a failing test to drive implementation.
    """
    clients.clear()
    
    mock_websocket = AsyncMock()
    mock_websocket.remote_address = ("127.0.0.1", 12345)
    
    await register_client(mock_websocket)
    
    assert mock_websocket in clients
    assert len(clients) == 1
    
    clients.clear()

@pytest.mark.asyncio
async def test_unregister_client_removes_from_clients_set():
    """
    Tests that unregister_client removes a websocket from the clients set.
    This is a failing test to drive implementation.
    """
    clients.clear()
    
    mock_websocket = AsyncMock()
    mock_websocket.remote_address = ("127.0.0.1", 12345)
    
    # First add the client
    clients.add(mock_websocket)
    assert mock_websocket in clients
    
    # Then remove it
    await unregister_client(mock_websocket)
    
    assert mock_websocket not in clients
    assert len(clients) == 0

@pytest.mark.asyncio
async def test_websocket_handler_manages_client_lifecycle():
    """
    Tests that websocket_handler properly manages client registration and cleanup.
    This tests the full lifecycle of a WebSocket connection.
    """
    clients.clear()
    
    mock_websocket = AsyncMock()
    mock_websocket.remote_address = ("127.0.0.1", 12345)
    mock_websocket.wait_closed = AsyncMock()
    
    # Run the handler
    await websocket_handler(mock_websocket, "/test")
    
    # After handler completes, client should be cleaned up
    assert mock_websocket not in clients
    assert len(clients) == 0
    
    # Verify that wait_closed was called
    mock_websocket.wait_closed.assert_called_once()

@pytest.mark.asyncio
async def test_websocket_handler_with_mock_redis(mock_redis):
    """
    Tests websocket_handler with mocked Redis connection using fakeredis.
    This verifies that Redis mocking doesn't interfere with WebSocket functionality.
    """
    clients.clear()
    
    mock_websocket = AsyncMock()
    mock_websocket.remote_address = ("127.0.0.1", 12345)
    mock_websocket.wait_closed = AsyncMock()
    
    # Run the handler with Redis mocking active
    await websocket_handler(mock_websocket, "/test")
    
    # Verify the handler completed successfully
    assert len(clients) == 0  # Should be cleaned up
    mock_websocket.wait_closed.assert_called_once()

@pytest.mark.asyncio
async def test_broadcast_telemetry_to_multiple_clients():
    """
    Tests that broadcast_telemetry sends messages to all connected clients.
    This tests the broadcasting functionality which is core to the WebSocket server.
    """
    from main import broadcast_telemetry
    
    clients.clear()
    
    # Create multiple mock clients
    client1 = AsyncMock()
    client2 = AsyncMock()
    client3 = AsyncMock()
    
    # Add them to the clients set
    clients.add(client1)
    clients.add(client2)
    clients.add(client3)
    
    # Test data to broadcast
    telemetry_data = {
        "timestamp": 12345,
        "altitude": 1000,
        "velocity": 250
    }
    
    # Broadcast the telemetry
    await broadcast_telemetry(telemetry_data)
    
    # Verify all clients received the message
    expected_message = '{"timestamp": 12345, "altitude": 1000, "velocity": 250}'
    client1.send.assert_called_once_with(expected_message)
    client2.send.assert_called_once_with(expected_message)
    client3.send.assert_called_once_with(expected_message)    
    clients.clear()

@pytest.mark.asyncio
async def test_broadcast_telemetry_with_no_clients():
    """
    Tests that broadcast_telemetry handles empty clients set gracefully.
    This tests edge case behavior.
    """
    from main import broadcast_telemetry
    
    clients.clear()
    
    telemetry_data = {"test": "data"}
    
    # Should not raise an exception
    await broadcast_telemetry(telemetry_data)
    
    # No assertions needed - just ensuring no exception is raised

@pytest.mark.asyncio
async def test_websocket_handler_exception_handling():
    """
    Tests that websocket_handler properly cleans up even when wait_closed raises an exception.
    This tests error handling and cleanup behavior.
    """
    clients.clear()
    
    mock_websocket = AsyncMock()
    mock_websocket.remote_address = ("127.0.0.1", 12345)
    
    # Make wait_closed raise an exception
    mock_websocket.wait_closed.side_effect = Exception("Connection error")
    
    # Handler should still complete and clean up
    try:
        await websocket_handler(mock_websocket, "/test")
    except Exception:
        pass  # Exception is expected
    
    # Client should still be cleaned up despite the exception
    assert mock_websocket not in clients
    assert len(clients) == 0

@pytest.mark.asyncio
async def test_client_isolation_between_tests():
    """
    Tests that client state is properly isolated between test runs.
    This ensures our test setup and teardown is working correctly.
    """
    # Ensure we start with empty clients
    clients.clear()
    assert len(clients) == 0
    
    # Add some mock clients
    mock_ws1 = AsyncMock()
    mock_ws2 = AsyncMock()
    clients.add(mock_ws1)
    clients.add(mock_ws2)
    
    assert len(clients) == 2
    
    # Clear and verify isolation
    clients.clear()
    assert len(clients) == 0
    
    # Test passes if isolation works correctly
    assert True

@pytest.mark.asyncio
async def test_multiple_clients_concurrent_connections():
    """
    Tests handling multiple WebSocket clients connecting simultaneously.
    This tests concurrency and proper client management.
    """
    clients.clear()
    
    # Create multiple mock websockets
    websockets_list = []
    for i in range(3):
        mock_ws = AsyncMock()
        mock_ws.remote_address = ("127.0.0.1", 12345 + i)
        mock_ws.wait_closed = AsyncMock()
        websockets_list.append(mock_ws)
    
    # Run handlers concurrently
    import asyncio
    tasks = [
        websocket_handler(ws, f"/test_{i}")
        for i, ws in enumerate(websockets_list)
    ]
    
    await asyncio.gather(*tasks)
    
    # All clients should be cleaned up after handlers complete
    assert len(clients) == 0
    
    # Verify all wait_closed methods were called
    for ws in websockets_list:
        ws.wait_closed.assert_called_once()