import os
import redis
import logging
from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS

# --- Configuration ---
PORT = 5001
HOST = "0.0.0.0"
STATIC_DIR = "static"
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_CHANNEL = "telemetry"

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Flask App Initialization ---
app = Flask(__name__, static_folder=STATIC_DIR)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Redis Connection ---
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    redis_client.ping()
    logging.info(f"Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
except redis.exceptions.ConnectionError as e:
    logging.error(f"Could not connect to Redis: {e}")
    redis_client = None

# --- Static File Serving ---
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

# --- WebSocket Event Handlers ---
@socketio.on('connect')
def handle_connect():
    logging.info("Client connected to Telemetry Dashboard")

@socketio.on('disconnect')
def handle_disconnect():
    logging.info("Client disconnected from Telemetry Dashboard")

# --- Redis Subscriber ---
def redis_subscriber():
    """Listen to Redis channel and broadcast messages to clients."""
    if not redis_client:
        logging.error("Redis client not available. Cannot subscribe to telemetry channel.")
        return

    pubsub = redis_client.pubsub()
    pubsub.subscribe(REDIS_CHANNEL)
    logging.info(f"Subscribed to Redis channel: '{REDIS_CHANNEL}'")

    for message in pubsub.listen():
        if message['type'] == 'message':
            logging.info(f"Received from Redis: {message['data']}")
            socketio.emit('telemetry', message['data'])

# --- Main Execution ---
def main():
    """Start the Flask-SocketIO server and Redis subscriber."""
    if redis_client:
        # Start the Redis subscriber in a background thread
        socketio.start_background_task(redis_subscriber)
    
    logging.info(f"Telemetry Dashboard starting on http://{HOST}:{PORT}")
    socketio.run(app, host=HOST, port=PORT, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()