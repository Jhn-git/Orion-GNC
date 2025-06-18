import json
import time
import pytest
import sys
from unittest.mock import MagicMock, patch
import fakeredis
import os
import threading

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

def test_mission_with_empty_sequence(mission_sequencer):
    """Tests that a mission with an empty sequence completes successfully."""
    mission_id = "test-empty-sequence-123"
    mission_plan = {
        "mission_id": mission_id,
        "mission_name": "Test Empty Sequence",
        "sequence": []
    }
    mission_plan_json = json.dumps(mission_plan)
    mission_sequencer.redis.rpush('mission_plan_queue', mission_plan_json)

    processor_thread = threading.Thread(target=mission_sequencer.process_missions)
    processor_thread.start()

    time.sleep(1)  # Give processor time to run
    mission_sequencer.stop()
    processor_thread.join()

    status_json = mission_sequencer.redis.get(f"mission:{mission_id}:status")
    assert status_json is not None
    status_data = json.loads(status_json)
    assert status_data['status'] == 'COMPLETED'

def test_mission_with_invalid_command(mission_sequencer):
    """Tests that a mission with an invalid command fails."""
    mission_id = "test-invalid-command-123"
    mission_plan = {
        "mission_id": mission_id,
        "mission_name": "Test Invalid Command",
        "sequence": [
            {"command": "INVALID_COMMAND", "value": 1.0}
        ]
    }
    mission_plan_json = json.dumps(mission_plan)
    mission_sequencer.redis.rpush('mission_plan_queue', mission_plan_json)

    processor_thread = threading.Thread(target=mission_sequencer.process_missions)
    processor_thread.start()

    time.sleep(1)
    mission_sequencer.stop()
    processor_thread.join()

    status_json = mission_sequencer.redis.get(f"mission:{mission_id}:status")
    assert status_json is not None
    status_data = json.loads(status_json)
    assert status_data['status'] == 'FAILED'
    assert "Invalid command" in status_data['details']['error']

def test_mission_with_large_sequence(mission_sequencer):
    """Tests that a mission with a large number of sequence items is processed correctly."""
    mission_id = "test-large-sequence-123"
    sequence = [{"command": "SET_THROTTLE", "value": 0.1} for _ in range(1000)]
    mission_plan = {
        "mission_id": mission_id,
        "mission_name": "Test Large Sequence",
        "sequence": sequence
    }
    mission_plan_json = json.dumps(mission_plan)
    mission_sequencer.redis.rpush('mission_plan_queue', mission_plan_json)

    processor_thread = threading.Thread(target=mission_sequencer.process_missions)
    processor_thread.start()

    # Wait long enough for all commands to be processed
    time.sleep(5)
    mission_sequencer.stop()
    processor_thread.join()

    # Verify that all commands were pushed to the GNC queue
    gnc_commands = mission_sequencer.redis.lrange('gnc_command_queue', 0, -1)
    assert len(gnc_commands) == 1000

    # Verify the mission status is COMPLETED
    status_json = mission_sequencer.redis.get(f"mission:{mission_id}:status")
    assert status_json is not None
    status_data = json.loads(status_json)
    assert status_data['status'] == 'COMPLETED'