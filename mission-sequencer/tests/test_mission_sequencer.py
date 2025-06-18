import json
import time
import pytest
import sys
from unittest.mock import MagicMock, patch
import fakeredis
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import MissionSequencer

@pytest.fixture
def mission_sequencer():
    """Fixture to create a MissionSequencer instance with a mock Redis connection."""
    redis_conn = fakeredis.FakeStrictRedis()
    mock_krpc_module = MagicMock()
    with patch.dict('sys.modules', {'krpc': mock_krpc_module}):
        sequencer = MissionSequencer(redis_conn)
        sequencer.krpc_conn = mock_krpc_module.connect.return_value
        yield sequencer
def test_validate_mission_plan_valid(mission_sequencer):
    """Tests that a valid mission plan is accepted."""
    mission_plan = {
        "mission_id": "test-mission-123",
        "mission_name": "Test Mission",
        "sequence": [
            {"command": "SET_THROTTLE", "value": 1.0},
            {"command": "WAIT", "value": 5},
            {"command": "SET_THROTTLE", "value": 0.0}
        ]
    }
    is_valid, message = mission_sequencer.validate_mission_plan(mission_plan)
    assert is_valid is True
    assert message == "Mission plan is valid."

def test_validate_mission_plan_invalid_missing_name(mission_sequencer):
    """Tests that a mission plan with a missing 'mission_name' is rejected."""
    mission_plan = {
        "mission_id": "test-mission-123",
        "sequence": [
            {"command": "SET_THROTTLE", "value": 1.0}
        ]
    }
    is_valid, message = mission_sequencer.validate_mission_plan(mission_plan)
    assert is_valid is False
    assert "is a required property" in message
import threading

def test_mission_execution(mission_sequencer):
    """Tests that a simple mission is executed correctly."""
    mission_plan = {
        "mission_id": "test-execution-123",
        "mission_name": "Test Execution",
        "sequence": [
            {"command": "SET_THROTTLE", "value": 1.0},
            {"command": "STAGE"},
            {"command": "SET_THROTTLE", "value": 0.5},
        ]
    }
    mission_plan_json = json.dumps(mission_plan)
    mission_sequencer.redis.rpush('mission_plan_queue', mission_plan_json)

    # Run the mission processor in a separate thread
    processor_thread = threading.Thread(target=mission_sequencer.process_missions)
    processor_thread.start()

    # Give the processor time to execute the mission
    time.sleep(2)
    mission_sequencer.stop()
    processor_thread.join()

    # Verify that the commands were pushed to the GNC queue
    gnc_commands = mission_sequencer.redis.lrange('gnc_command_queue', 0, -1)
    assert len(gnc_commands) == 3
    assert json.loads(gnc_commands[0]) == {"command": "SET_THROTTLE", "value": 1.0}
    assert json.loads(gnc_commands[1]) == {"command": "STAGE"}
    assert json.loads(gnc_commands[2]) == {"command": "SET_THROTTLE", "value": 0.5}
def test_mission_status_transitions(mission_sequencer):
    """Tests that the mission status transitions correctly."""
    mission_id = "test-status-123"
    mission_plan = {
        "mission_id": mission_id,
        "mission_name": "Test Status Transitions",
        "sequence": [
            {"command": "WAIT", "value": 0.1}
        ]
    }

    # Subscribe to the mission status channel
    pubsub = mission_sequencer.redis.pubsub()
    pubsub.subscribe(f"mission_status:{mission_id}")
    pubsub.get_message() # Consume the subscription confirmation

    # Submit the mission
    mission_sequencer.submit_mission(mission_plan)

    # Check for QUEUED status
    status_message = pubsub.get_message(timeout=1)
    assert status_message is not None
    status_data = json.loads(status_message['data'])
    assert status_data['status'] == 'QUEUED'

    # Run the mission processor in a separate thread
    processor_thread = threading.Thread(target=mission_sequencer.process_missions)
    processor_thread.start()

    # Check for IN_PROGRESS status
    status_message = pubsub.get_message(timeout=1)
    assert status_message is not None
    status_data = json.loads(status_message['data'])
    assert status_data['status'] == 'IN_PROGRESS'

    # Check for EXECUTING_COMMAND status
    status_message = pubsub.get_message(timeout=1)
    assert status_message is not None
    status_data = json.loads(status_message['data'])
    assert status_data['status'] == 'EXECUTING_COMMAND'
    assert status_data['details']['sequence_index'] == 0

    # Check for COMPLETED status
    status_message = pubsub.get_message(timeout=1)
    assert status_message is not None
    status_data = json.loads(status_message['data'])
    assert status_data['status'] == 'COMPLETED'

    mission_sequencer.stop()
    processor_thread.join()
def test_mission_failure_invalid_command(mission_sequencer):
    """Tests that a mission fails if it contains an invalid command."""
    mission_id = "test-failure-123"
    mission_plan = {
        "mission_id": mission_id,
        "mission_name": "Test Failure",
        "sequence": [
            {"command": "INVALID_COMMAND", "value": 1.0}
        ]
    }
    mission_plan_json = json.dumps(mission_plan)
    mission_sequencer.redis.rpush('mission_plan_queue', mission_plan_json)

    # Run the mission processor in a separate thread
    processor_thread = threading.Thread(target=mission_sequencer.process_missions)
    processor_thread.start()

    # Give the processor time to execute the mission
    time.sleep(2)
    mission_sequencer.stop()
    processor_thread.join()

    # Verify that the mission status is FAILED
    status_json = mission_sequencer.redis.get(f"mission:{mission_id}:status")
    assert status_json is not None
    status_data = json.loads(status_json)
    assert status_data['status'] == 'FAILED'
    assert "Invalid command" in status_data['details']['error']
def test_wait_command_timing(mission_sequencer):
    """Tests that the WAIT command waits for the correct duration."""
    mission_id = "test-wait-123"
    wait_duration = 1.5
    mission_plan = {
        "mission_id": mission_id,
        "mission_name": "Test Wait Command",
        "sequence": [
            {"command": "WAIT", "value": wait_duration}
        ]
    }
    mission_plan_json = json.dumps(mission_plan)
    mission_sequencer.redis.rpush('mission_plan_queue', mission_plan_json)

    start_time = time.time()

    # Run the mission processor in a separate thread
    processor_thread = threading.Thread(target=mission_sequencer.process_missions)
    processor_thread.start()
    
    # Give the processor time to execute the mission
    time.sleep(wait_duration + 0.5) # Add a buffer
    mission_sequencer.stop()
    processor_thread.join()

    end_time = time.time()
    execution_time = end_time - start_time

    # Verify that the mission status is COMPLETED
    status_json = mission_sequencer.redis.get(f"mission:{mission_id}:status")
    assert status_json is not None
    status_data = json.loads(status_json)
    assert status_data['status'] == 'COMPLETED'
    
    # Verify the execution time
    assert execution_time >= wait_duration
def test_wait_until_apoapsis_command(mission_sequencer):
    """Tests that the WAIT_UNTIL_APOAPSIS command waits for the condition to be met."""
    mission_id = "test-apoapsis-123"
    mission_plan = {
        "mission_id": mission_id,
        "mission_name": "Test Wait Until Apoapsis",
        "sequence": [
            {"command": "WAIT_UNTIL_APOAPSIS"}
        ]
    }
    mission_plan_json = json.dumps(mission_plan)
    mission_sequencer.redis.rpush('mission_plan_queue', mission_plan_json)

    # Mock the kRPC stream for apoapsis altitude
    apoapsis_values = [100000, 101000, 102000, 102500, 102400]
    apoapsis_stream_callable = MagicMock(side_effect=apoapsis_values)
    apoapsis_stream_callable.remove = MagicMock()
    mission_sequencer.krpc_conn.add_stream.return_value = apoapsis_stream_callable

    # Run the mission processor in a separate thread
    processor_thread = threading.Thread(target=mission_sequencer.process_missions)
    processor_thread.start()

    # Give the processor time to execute the mission
    time.sleep(2)
    mission_sequencer.stop()
    processor_thread.join()

    # Verify that the mission status is COMPLETED
    status_json = mission_sequencer.redis.get(f"mission:{mission_id}:status")
    assert status_json is not None
    status_data = json.loads(status_json)
    assert status_data['status'] == 'COMPLETED'

    # Verify that the stream was called until the value decreased
    assert apoapsis_stream_callable.call_count == 5
    apoapsis_stream_callable.remove.assert_called_once()