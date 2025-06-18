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

def test_concurrent_mission_processing(mission_sequencer):
    """
    Tests that the system can handle multiple missions submitted concurrently.
    """
    num_missions = 10
    mission_ids = [f"test-concurrent-{i}" for i in range(num_missions)]
    mission_plans = []
    for mission_id in mission_ids:
        mission_plans.append({
            "mission_id": mission_id,
            "mission_name": f"Concurrent Mission {mission_id}",
            "sequence": [{"command": "SET_THROTTLE", "value": 0.1}]
        })

    def submit_mission(plan):
        mission_plan_json = json.dumps(plan)
        mission_sequencer.redis.rpush('mission_plan_queue', mission_plan_json)

    # Start the mission processor
    processor_thread = threading.Thread(target=mission_sequencer.process_missions)
    processor_thread.start()

    # Submit missions concurrently
    submission_threads = []
    for plan in mission_plans:
        thread = threading.Thread(target=submit_mission, args=(plan,))
        submission_threads.append(thread)
        thread.start()

    # Wait for all submission threads to complete
    for thread in submission_threads:
        thread.join()

    # Give the processor time to execute all missions
    time.sleep(5)

    mission_sequencer.stop()
    processor_thread.join()

    # Verify that all missions are completed
    for mission_id in mission_ids:
        status_json = mission_sequencer.redis.get(f"mission:{mission_id}:status")
        assert status_json is not None
        status_data = json.loads(status_json)
        assert status_data['status'] == 'COMPLETED'