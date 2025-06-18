import os
import json
import logging
from flask import Flask, request, jsonify
import redis
from jsonschema import validate, ValidationError
from worker import execute_mission

# --- Configuration ---
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
SCHEMA_PATH = '/app/docs/schemas/mission_plan_schema.json'

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Redis Connection ---
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Redis Connection ---
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True, socket_connect_timeout=5)

def load_mission_schema():
    """Load the mission plan schema from the file."""
    try:
        with open(SCHEMA_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error("Mission plan schema not found at %s", SCHEMA_PATH)
        return None
    except json.JSONDecodeError:
        logging.error("Invalid JSON in mission plan schema at %s", SCHEMA_PATH)
        return None

mission_schema = load_mission_schema()

@app.route('/submit_mission', methods=['POST'])
def submit_mission():
    """
    Accepts and validates a mission plan, then queues it for execution.
    """
    mission_plan = request.get_json()
    logging.info(f"Received mission plan payload: {mission_plan}") # Debug print
    if not mission_plan:
        logging.error("Received empty or invalid JSON payload.")
        return jsonify({"error": "Invalid JSON payload"}), 400

    if not mission_schema:
        logging.error("Mission schema not loaded.")
        return jsonify({"error": "Mission schema not loaded"}), 500

    try:
        validate(instance=mission_plan, schema=mission_schema)
    except ValidationError as e:
        logging.error(f"Schema validation failed: {str(e)}")
        logging.error(f"Received mission plan: {json.dumps(mission_plan, indent=2)}") # Ensure full payload is logged
        print(f"DEBUG: Schema validation failed (RAW): {str(e)}") # Direct print for visibility
        print(f"DEBUG: Received mission plan (RAW): {json.dumps(mission_plan, indent=2)}") # Direct print for visibility
        return jsonify({"error": "Schema validation failed", "details": str(e)}), 400

    mission_id = mission_plan['mission_id']
    
    # Check for existing mission
    if redis_client.exists(f"mission:{mission_id}:status"):
        return jsonify({"error": "Mission with this ID already exists"}), 409

    # Queue the mission for the Celery worker
    execute_mission.delay(mission_plan)
    
    initial_status = {
        "status": "QUEUED",
        "details": "Mission plan validated and queued for execution."
    }
    redis_client.set(f"mission:{mission_id}:status", json.dumps(initial_status))
    redis_client.publish('mission_status', json.dumps({"mission_id": mission_id, **initial_status}))

    return jsonify({"message": "Mission accepted", "mission_id": mission_id}), 202

@app.route('/mission_status/<string:mission_id>', methods=['GET'])
def get_mission_status(mission_id):
    """
    Returns the current status of a mission.
    """
    status_json = redis_client.get(f"mission:{mission_id}:status")
    if not status_json:
        return jsonify({"error": "Mission not found"}), 404
    
    return jsonify(json.loads(status_json)), 200

@app.route('/abort_mission/<string:mission_id>', methods=['DELETE'])
def abort_mission(mission_id):
    """
    Sends an abort signal for a running mission.
    """
    if not redis_client.exists(f"mission:{mission_id}:status"):
        return jsonify({"error": "Mission not found"}), 404

    # Publish an abort message to a specific channel that the worker will listen to
    redis_client.publish('mission_abort_commands', mission_id)

    abort_status = {
        "status": "ABORT_REQUESTED",
        "details": "Abort signal sent to mission worker."
    }
    redis_client.set(f"mission:{mission_id}:status", json.dumps(abort_status))
    redis_client.publish('mission_status', json.dumps({"mission_id": mission_id, **abort_status}))

    return jsonify({"message": "Abort signal sent", "mission_id": mission_id}), 200

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify service status.
    """
    try:
        redis_client.ping()
        redis_ok = True
    except redis.exceptions.ConnectionError:
        redis_ok = False
        
    status_code = 200 if redis_ok else 503
    return jsonify({
        "service": "Mission Sequencer",
        "status": "ok" if redis_ok else "degraded",
        "dependencies": {
            "redis": "ok" if redis_ok else "error"
        }
    }), status_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)