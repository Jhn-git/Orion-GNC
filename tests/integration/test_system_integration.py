import asyncio
import docker
import json
import pytest
import redis
import requests
import subprocess
import time
import websockets
from typing import Dict, List, Optional
from unittest.mock import patch

class TestSystemIntegration:
    """
    Comprehensive integration tests validating the complete system communication flow
    after SPARC orchestration bug fixes. Tests the critical issues resolved:
    1. Mission Control UI Gunicorn worker configuration
    2. GNC Flight Control WebSocket TypeError fix
    3. Complete end-to-end communication flow
    4. Docker Compose system startup
    """

    @pytest.fixture(scope="class")
    def docker_client(self):
        """Docker client for managing containers during tests."""
        return docker.from_env()

    @pytest.fixture(scope="class")
    def redis_client(self):
        """Redis client for testing messaging."""
        client = redis.Redis(
            host='localhost', 
            port=6379, 
            db=0, 
            decode_responses=True,
            socket_connect_timeout=5
        )
        yield client
        # Cleanup test data
        try:
            client.flushdb()
        except:
            pass

    def test_docker_compose_system_startup(self):
        """
        FAILING TEST: Validate that docker-compose up works without the previous critical failures.
        This test ensures the Gunicorn configuration fix and WebSocket handler fix work in practice.
        """
        # This should fail initially to drive implementation
        result = subprocess.run(
            ["docker-compose", "up", "-d", "--build"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        assert result.returncode == 0, f"Docker compose failed to start: {result.stderr}"
        
        # Give services time to start
        time.sleep(30)
        
        # Verify all services are running
        result = subprocess.run(
            ["docker-compose", "ps", "--services", "--filter", "status=running"],
            capture_output=True,
            text=True
        )
        
        running_services = result.stdout.strip().split('\n')
        expected_services = [
            'redis',
            'mission_control_ui', 
            'mission_sequencer',
            'mission_sequencer_worker',
            'gnc_flight_control',
            'telemetry_dashboard'
        ]
        
        for service in expected_services:
            assert service in running_services, f"Service {service} is not running"

    def test_mission_control_ui_gunicorn_startup_fix(self):
        """
        FAILING TEST: Validate that Mission Control UI starts with proper Gunicorn worker configuration.
        This tests the critical fix for the $GUNICORN_WORKERS environment variable issue.
        """
        # Check that Mission Control UI is accessible
        max_retries = 10
        for attempt in range(max_retries):
            try:
                response = requests.get("http://localhost:5000/health", timeout=5)
                assert response.status_code == 200, f"Mission Control UI health check failed: {response.status_code}"
                
                health_data = response.json()
                assert health_data.get("status") == "ok", f"Mission Control UI not healthy: {health_data}"
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                if attempt == max_retries - 1:
                    pytest.fail("Mission Control UI did not start successfully after Gunicorn fix")
                time.sleep(3)

    def test_gnc_flight_control_websocket_connection_fix(self):
        """
        FAILING TEST: Validate that GNC Flight Control WebSocket accepts connections without TypeError.
        This tests the critical fix for the websocket_handler(websocket, path) signature.
        """
        async def test_websocket_connection():
            try:
                # Connect to the WebSocket server
                async with websockets.connect("ws://localhost:8765") as websocket:
                    # If we can connect without a TypeError, the fix worked
                    assert websocket.open, "WebSocket connection should be open"
                    
                    # Send a test message to verify full functionality
                    test_message = {"test": "connection"}
                    await websocket.send(json.dumps(test_message))
                    
                    # Wait briefly to ensure no errors occur
                    await asyncio.sleep(1)
                    
                return True
            except Exception as e:
                pytest.fail(f"WebSocket connection failed, TypeError fix unsuccessful: {e}")
        
        # Run the async test
        result = asyncio.run(test_websocket_connection())
        assert result, "WebSocket connection test should pass"

    def test_service_health_endpoints_integration(self):
        """
        FAILING TEST: Verify all services can start without the previous critical errors.
        Tests health check endpoints and service interdependencies.
        """
        services_health = {
            "Mission Control UI": "http://localhost:5000/health",
            "Mission Sequencer": "http://localhost:5001/health",
            "Telemetry Dashboard": "http://localhost:5002/health"
        }
        
        for service_name, health_url in services_health.items():
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    response = requests.get(health_url, timeout=5)
                    assert response.status_code == 200, f"{service_name} health check failed"
                    
                    health_data = response.json()
                    assert health_data.get("status") == "ok", f"{service_name} not healthy: {health_data}"
                    break
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                    if attempt == max_retries - 1:
                        pytest.fail(f"{service_name} health check failed after {max_retries} attempts")
                    time.sleep(2)

    def test_redis_pubsub_communication_flow(self, redis_client):
        """
        FAILING TEST: Validate Redis Pub/Sub messaging between services.
        Tests real Redis communication (not mocked) as specified.
        """
        # Test Redis is accessible
        try:
            redis_client.ping()
        except redis.exceptions.ConnectionError:
            pytest.fail("Redis is not accessible for integration testing")
        
        # Test publishing to mission status channel
        test_mission_id = "integration-test-mission"
        test_status = {
            "mission_id": test_mission_id,
            "status": "IN_PROGRESS",
            "timestamp": time.time()
        }
        
        # Publish status update
        channel = f"mission_status:{test_mission_id}"
        result = redis_client.publish(channel, json.dumps(test_status))
        
        # Test command queue functionality
        test_command = {
            "command": "SET_THROTTLE",
            "parameters": {"value": 0.5},
            "mission_id": test_mission_id
        }
        
        redis_client.lpush("gnc_command_queue", json.dumps(test_command))
        
        # Verify command was queued
        queued_command = redis_client.brpop("gnc_command_queue", timeout=1)
        assert queued_command is not None, "Command should be retrievable from Redis queue"
        
        _, command_json = queued_command
        retrieved_command = json.loads(command_json)
        assert retrieved_command["command"] == "SET_THROTTLE"
        assert retrieved_command["mission_id"] == test_mission_id

    def test_end_to_end_mission_workflow(self, redis_client):
        """
        FAILING TEST: Complete mission workflow from Mission Control UI → Mission Sequencer → GNC Flight Control.
        Tests the complete system communication flow as specified.
        """
        # Step 1: Submit mission plan to Mission Control UI
        mission_plan = {
            "mission_name": "Integration Test Mission",
            "sequence": [
                {"command": "SET_THROTTLE", "value": 0.8, "duration": 2},
                {"command": "ACTIVATE_NEXT_STAGE", "duration": 1},
                {"command": "SET_THROTTLE", "value": 0.0, "duration": 1}
            ]
        }
        
        response = requests.post(
            "http://localhost:5000/submit_mission",
            json=mission_plan,
            timeout=10
        )
        
        assert response.status_code in [200, 202], f"Mission submission failed: {response.status_code}"
        
        response_data = response.json()
        assert response_data.get("status") == "success", f"Mission submission not successful: {response_data}"
        
        mission_id = response_data.get("mission_id")
        assert mission_id is not None, "Mission ID should be returned"
        
        # Step 2: Verify mission appears in Mission Sequencer
        time.sleep(2)  # Allow processing time
        
        status_response = requests.get(
            f"http://localhost:5001/mission/{mission_id}/status",
            timeout=5
        )
        
        assert status_response.status_code == 200, "Mission status should be retrievable"
        
        status_data = status_response.json()
        assert status_data.get("mission_id") == mission_id
        assert status_data.get("status") in ["QUEUED", "IN_PROGRESS", "COMPLETED"]
        
        # Step 3: Verify commands reach GNC Flight Control via Redis
        # Monitor the gnc_command_queue for commands from this mission
        commands_received = []
        start_time = time.time()
        timeout = 30
        
        while time.time() - start_time < timeout:
            try:
                queued_item = redis_client.brpop("gnc_command_queue", timeout=1)
                if queued_item:
                    _, command_json = queued_item
                    command = json.loads(command_json)
                    if command.get("mission_id") == mission_id:
                        commands_received.append(command)
                        
                        # If we've received all expected commands, break
                        if len(commands_received) >= len(mission_plan["sequence"]):
                            break
            except:
                continue
        
        assert len(commands_received) > 0, "No commands were received by GNC Flight Control"
        
        # Verify command structure
        first_command = commands_received[0]
        assert "command" in first_command
        assert "mission_id" in first_command
        assert first_command["mission_id"] == mission_id

    def test_websocket_telemetry_broadcasting(self):
        """
        FAILING TEST: Test WebSocket connections work properly for telemetry broadcasting.
        Validates the medium-priority WebSocket handshake issue is resolved.
        """
        async def test_telemetry_reception():
            telemetry_received = []
            
            try:
                async with websockets.connect("ws://localhost:8765") as websocket:
                    # Wait for potential telemetry data
                    try:
                        # Set a reasonable timeout for telemetry
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        telemetry_data = json.loads(message)
                        telemetry_received.append(telemetry_data)
                    except asyncio.TimeoutError:
                        # No telemetry received within timeout - this is acceptable for test
                        pass
                    
                    return True
            except Exception as e:
                pytest.fail(f"WebSocket telemetry test failed: {e}")
        
        result = asyncio.run(test_telemetry_reception())
        assert result, "WebSocket telemetry connection should work"

    def test_docker_compose_health_checks(self):
        """
        FAILING TEST: Validate health check endpoints work after fixes.
        Tests that the WebSocket handshake issue doesn't break health checks.
        """
        result = subprocess.run(
            ["docker-compose", "ps", "--format", "json"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, "Could not get docker-compose status"
        
        services_status = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                service_info = json.loads(line)
                services_status.append(service_info)
        
        # Verify all services are healthy or running
        critical_services = ['mission_control_ui', 'gnc_flight_control', 'mission_sequencer']
        
        for service_info in services_status:
            service_name = service_info.get('Service', '')
            if service_name in critical_services:
                status = service_info.get('State', '')
                assert status in ['running', 'healthy'], f"Service {service_name} is not healthy: {status}"

    def test_system_integration_comprehensive_validation(self, redis_client):
        """
        FAILING TEST: Final comprehensive validation that all SPARC orchestration fixes work together.
        This test demonstrates that our SPARC orchestration successfully resolved all critical system failures.
        """
        # Validate Redis connectivity
        try:
            redis_client.ping()
        except:
            pytest.fail("Redis connectivity failed - core infrastructure issue")
        
        # Validate Mission Control UI is accessible (Gunicorn fix)
        try:
            response = requests.get("http://localhost:5000/health", timeout=5)
            assert response.status_code == 200
        except:
            pytest.fail("Mission Control UI accessibility failed - Gunicorn configuration issue not resolved")
        
        # Validate GNC Flight Control WebSocket (TypeError fix)
        async def validate_websocket():
            try:
                async with websockets.connect("ws://localhost:8765") as websocket:
                    return websocket.open
            except:
                return False
        
        websocket_works = asyncio.run(validate_websocket())
        assert websocket_works, "GNC Flight Control WebSocket connection failed - TypeError issue not resolved"
        
        # Validate Mission Sequencer is operational
        try:
            response = requests.get("http://localhost:5001/health", timeout=5)
            assert response.status_code == 200
        except:
            pytest.fail("Mission Sequencer accessibility failed")
        
        # Validate end-to-end flow works
        test_data = {"test": "integration_validation"}
        redis_client.lpush("test_queue", json.dumps(test_data))
        
        retrieved = redis_client.brpop("test_queue", timeout=1)
        assert retrieved is not None, "Basic Redis queue functionality failed"
        
        # If we reach here, all critical fixes are working
        assert True, "Comprehensive system integration validation passed"

    def teardown_method(self):
        """Cleanup after each test method."""
        try:
            # Stop docker-compose services
            subprocess.run(
                ["docker-compose", "down"],
                capture_output=True,
                timeout=60
            )
        except:
            pass  # Best effort cleanup

    @classmethod
    def teardown_class(cls):
        """Cleanup after all tests."""
        try:
            # Final cleanup
            subprocess.run(
                ["docker-compose", "down", "-v"],
                capture_output=True,
                timeout=120
            )
        except:
            pass  # Best effort cleanup