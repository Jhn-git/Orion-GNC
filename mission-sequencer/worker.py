import os
import json
import time
import logging
import redis
from celery import Celery

# --- Configuration ---
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', f'redis://{REDIS_HOST}:{REDIS_PORT}/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', f'redis://{REDIS_HOST}:{REDIS_PORT}/0')

# --- Celery Initialization ---
celery_app = Celery('mission_worker', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

# --- Redis Connection ---
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def update_mission_status(mission_id, status, details):
    """Updates and publishes the mission status."""
    status_payload = {
        "status": status,
        "details": details
    }
    redis_client.set(f"mission:{mission_id}:status", json.dumps(status_payload))
    redis_client.publish('mission_status', json.dumps({"mission_id": mission_id, **status_payload}))
    logging.info(f"Mission {mission_id} status updated to {status}: {details}")

@celery_app.task(bind=True, acks_late=True)
def execute_mission(self, mission_plan):
    """
    Celery task to execute a mission plan.
    """
    mission_id = mission_plan['mission_id']
    update_mission_status(mission_id, "IN_PROGRESS", "Starting mission execution.")

    # Subscribe to the abort channel
    abort_pubsub = redis_client.pubsub()
    abort_pubsub.subscribe(f'mission_abort_commands')

    try:
        for i, cmd in enumerate(mission_plan['flight_plan']):
            # Check for abort signal
            message = abort_pubsub.get_message()
            if message and message['type'] == 'message' and message['data'] == mission_id:
                update_mission_status(mission_id, "ABORTED", "Mission aborted by operator.")
                return {"status": "ABORTED"}

            update_mission_status(mission_id, "IN_PROGRESS", f"Executing command {i+1}/{len(mission_plan['flight_plan'])}: {cmd['command']}")
            
            # Publish command to GNC service
            redis_client.publish('gnc_commands', json.dumps(cmd))

            # Wait for the specified delay, or 1 second if not specified
            delay = cmd.get('delay_ms', 1000) / 1000.0
            time.sleep(delay)

        update_mission_status(mission_id, "COMPLETED", "All mission commands executed successfully.")
        return {"status": "COMPLETED"}

    except Exception as e:
        logging.error(f"Error executing mission {mission_id}: {e}")
        update_mission_status(mission_id, "FAILED", f"An error occurred: {e}")
        raise
    finally:
        abort_pubsub.unsubscribe()
        abort_pubsub.close()

if __name__ == '__main__':
    # This script is not meant to be run directly.
    # Start the Celery worker with:
    # celery -A worker worker --loglevel=info
    pass