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

def test_service_restart_aborts_mission(mission_sequencer):
    """
    Tests that a mission is aborted if the service is restarted.
    """
    mission_id = "test-restart-123"
    mission_plan = {
        "mission_id": mission_id,
        "mission_name": "Test Service Restart",
        "sequence": [
            {"command": "WAIT", "value": 5}  # A long-running command
        ]
    }
    mission_plan_json = json.dumps(mission_plan)
    mission_sequencer.redis.rpush('mission_plan_queue', mission_plan_json)

    processor_thread = threading.Thread(target=mission_sequencer.process_missions)
    processor_thread.start()

    # Give the mission time to start
    time.sleep(1)

    # Simulate a service restart by stopping the sequencer
    mission_sequencer.stop()
    processor_thread.join()

    # The mission status should be ABORTED
    status_json = mission_sequencer.redis.get(f"mission:{mission_id}:status")
    assert status_json is not None
    status_data = json.loads(status_json)
    assert status_data['status'] == 'ABORTED'
    assert status_data['details']['reason'] == 'Service shutdown'