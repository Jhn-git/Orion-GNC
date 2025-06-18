import os
import logging
import requests
import redis
import json
from threading import Thread
from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS
from flask_socketio import SocketIO
from dotenv import load_dotenv

# --- Initial Setup ---
load_dotenv()

# --- Flask App Initialization ---
app = Flask(__name__, static_folder='static')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Configuration ---
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
MISSION_SEQUENCER_URL = os.environ.get("MISSION_SEQUENCER_URL", "http://localhost:5001")
LOGS_DIR = os.environ.get("LOGS_DIR", "/app/logs")

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Redis Connection ---
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    redis_client.ping()
    logging.info("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    logging.error(f"Could not connect to Redis: {e}")
    redis_client = None

# --- API Proxy Endpoints ---

@app.route('/submit_mission', methods=['POST'])
def submit_mission():
    """Proxy for submitting a mission to the Mission Sequencer."""
    try:
        response = requests.post(f"{MISSION_SEQUENCER_URL}/submit_mission", json=request.get_json())
        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        logging.error(f"Error proxying to mission sequencer: {e}")
        return jsonify({"error": "Failed to connect to Mission Sequencer"}), 502

@app.route('/mission_status/<string:mission_id>', methods=['GET'])
def get_mission_status(mission_id):
    """Proxy for getting mission status from the Mission Sequencer."""
    try:
        response = requests.get(f"{MISSION_SEQUENCER_URL}/mission_status/{mission_id}")
        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        logging.error(f"Error proxying to mission sequencer: {e}")
        error_message = f"Failed to connect to Mission Sequencer: {e}"
        status_code = 502

        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Mission sequencer response status: {e.response.status_code}")
            logging.error(f"Mission sequencer response text: {e.response.text}")
            error_message = f"Mission Sequencer responded with error: {e.response.status_code}"
            status_code = e.response.status_code
            try:
                error_details = e.response.json()
                logging.error(f"Mission sequencer response JSON: {error_details}")
                if "error" in error_details:
                    error_message = f"Mission Sequencer error: {error_details['error']}"
                if "details" in error_details:
                    error_message += f" - Details: {error_details['details']}"
            except json.JSONDecodeError:
                pass # Not a JSON response, already logged as text

        try:
            payload = request.get_json()
            logging.error(f"Request payload sent to mission sequencer: {json.dumps(payload, indent=2)}")
        except Exception as payload_error:
            logging.error(f"Failed to get request payload: {payload_error}")
            
        return jsonify({"error": error_message}), status_code

@app.route('/abort_mission/<string:mission_id>', methods=['DELETE'])
def abort_mission(mission_id):
    """Proxy for aborting a mission via the Mission Sequencer."""
    try:
        response = requests.delete(f"{MISSION_SEQUENCER_URL}/abort_mission/{mission_id}")
        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        # Log detailed error information
        logging.error(f"Error proxying to mission sequencer: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                # Try to get JSON response if available
                error_details = e.response.json()
                logging.error(f"Mission sequencer response details: {error_details}")
            except json.JSONDecodeError:
                logging.error(f"Mission sequencer response text: {e.response.text}")
        
        # Also log the request payload for debugging
        try:
            payload = request.get_json()
            logging.error(f"Request payload sent to mission sequencer: {json.dumps(payload, indent=2)}")
        except Exception as payload_error:
            logging.error(f"Failed to log request payload: {payload_error}")
            
        return jsonify({"error": "Failed to connect to Mission Sequencer"}), 502

# --- UI Specific Endpoints ---

@app.route('/list_mission_logs', methods=['GET'])
def list_mission_logs():
    """List available mission logs from the shared volume."""
    if not os.path.exists(LOGS_DIR):
        logging.warning(f"Logs directory not found: {LOGS_DIR}")
        return jsonify([])
    try:
        logs = [f for f in os.listdir(LOGS_DIR) if f.startswith('mission_') and f.endswith('.log')]
        return jsonify(sorted(logs, reverse=True))
    except Exception as e:
        logging.error(f"Error reading logs directory: {e}")
        return jsonify({"error": "Could not list mission logs"}), 500

@app.route('/analyze_mission', methods=['POST'])
def analyze_mission():
    """Placeholder for post-mission analysis."""
    # In a real implementation, this would trigger a complex analysis task.
    # For now, we'll return a mock response.
    data = request.get_json()
    log_file = data.get('log_file')
    question = data.get('question')
    logging.info(f"Received analysis request for {log_file} with question: '{question}'")
    
    return jsonify({
        "message": "Analysis request received. This is a placeholder implementation.",
        "results": [
            f"Mock analysis result for {log_file}.",
            "Conclusion: Mission parameters were nominal."
        ]
    })

# --- Static File Serving ---

@app.route('/')
def serve_index():
    """Serve the main index.html file."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    """Serve other static files (JS, CSS, etc.)."""
    return send_from_directory(app.static_folder, path)

# --- WebSocket Handling ---

@socketio.on('connect')
def handle_connect():
    logging.info('Client connected to WebSocket')

@socketio.on('disconnect')
def handle_disconnect():
    logging.info('Client disconnected from WebSocket')

def redis_pubsub_listener():
    """Listens to Redis pub/sub for mission status updates."""
    if not redis_client:
        logging.error("Cannot start Redis listener: no connection.")
        return
    
    pubsub = redis_client.pubsub()
    pubsub.subscribe('mission_status')
    logging.info("Subscribed to 'mission_status' channel on Redis.")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            logging.info(f"Received status update from Redis: {message['data']}")
            try:
                data = json.loads(message['data'])
                socketio.emit('mission_update', data)
            except json.JSONDecodeError:
                logging.error(f"Could not decode JSON from Redis: {message['data']}")

# --- Health Check ---

@app.route('/health')
def health_check():
    """Health check endpoint."""
    redis_ok = False
    if redis_client:
        try:
            redis_client.ping()
            redis_ok = True
        except redis.exceptions.ConnectionError:
            pass
            
    return jsonify({
        "service": "Mission Control UI",
        "status": "ok" if redis_ok else "degraded",
        "dependencies": {
            "redis": "ok" if redis_ok else "error"
        }
    })

# --- Main Execution ---

if __name__ == '__main__':
    # Start the Redis listener in a background thread
    listener_thread = Thread(target=redis_pubsub_listener, daemon=True)
    listener_thread.start()
    
    # Start the Flask-SocketIO server
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)