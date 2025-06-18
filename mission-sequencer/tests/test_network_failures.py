import json
import time
import pytest
import sys
from unittest.mock import MagicMock, patch, mock_open
import fakeredis
import os
import threading
import redis

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import MissionSequencer

@pytest.fixture
def mission_sequencer():
    """Fixture to create a MissionSequencer instance with a mock Redis connection."""
    redis_conn = fakeredis.FakeStrictRedis()

    # Create a stateful side effect for blpop
    blpop_calls = 0
    def blpop_effect(*args, **kwargs):
        nonlocal blpop_calls
        blpop_calls += 1
        if blpop_calls == 1:
            # First call: simulate connection error
            raise redis.exceptions.ConnectionError("Simulated connection error")
        elif blpop_calls == 2:
            # Second call: return the mission
            return (b'mission_plan_queue', b'{"mission_id": "test-mission-123", "mission_name": "Test Mission", "sequence": [{"command": "SET_THROTTLE", "value": 1.0}]}')
        else:
            # Subsequent calls: simulate empty queue with timeout
            time.sleep(1)
            return None

    redis_conn.blpop = MagicMock(side_effect=blpop_effect)

    mock_krpc_module = MagicMock()
    with patch.dict('sys.modules', {'krpc': mock_krpc_module}):
        sequencer = MissionSequencer(redis_conn)
        sequencer.krpc_conn = mock_krpc_module.connect.return_value
        yield sequencer

def test_redis_connection_lost_and_restored(mission_sequencer):
    """
    Tests that the mission sequencer can recover from a Redis connection error.
    """
    mission_id = "test-mission-123"

    processor_thread = threading.Thread(target=mission_sequencer.process_missions)
    processor_thread.start()

    # Give the processor time to encounter the connection error and recover
    time.sleep(6) 
    mission_sequencer.stop()
    processor_thread.join()

    # After recovery, the mission should be processed
    gnc_commands = mission_sequencer.redis.lrange('gnc_command_queue', 0, -1)
    assert len(gnc_commands) == 1
    assert json.loads(gnc_commands[0]) == {"command": "SET_THROTTLE", "value": 1.0}

    status_json = mission_sequencer.redis.get(f"mission:{mission_id}:status")
    assert status_json is not None
    status_data = json.loads(status_json)
    assert status_data['status'] == 'COMPLETED'