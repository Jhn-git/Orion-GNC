import asyncio
import json
import logging
import os
import redis.asyncio as redis
import psutil
import websockets
from websockets.exceptions import (
    ConnectionClosedOK,
    ConnectionClosedError,
    InvalidHandshake,
    InvalidMessage,
)

try:
    import krpc
except ImportError:
    krpc = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", 8765))
KRPC_HOST = os.getenv("KRPC_HOST", "127.0.0.1")
KRPC_PORT = int(os.getenv("KRPC_PORT", 50000))
KRPC_STREAM_PORT = int(os.getenv("KRPC_STREAM_PORT", 50001))

# WebSocket Reliability Configuration
PING_INTERVAL_SECONDS = int(os.getenv("PING_INTERVAL_SECONDS", 20))
PING_TIMEOUT_SECONDS = int(os.getenv("PING_TIMEOUT_SECONDS", 20))
def reload_ping_config():
    global PING_INTERVAL_SECONDS, PING_TIMEOUT_SECONDS
    PING_INTERVAL_SECONDS = int(os.getenv("PING_INTERVAL_SECONDS", 20))
    PING_TIMEOUT_SECONDS = int(os.getenv("PING_TIMEOUT_SECONDS", 20))

# --- Global State ---
clients = set()
krpc_conn = None
vessel = None

# --- kRPC Integration ---
async def initialize_krpc():
    """Initializes the connection to the kRPC server and gets the active vessel."""
    global krpc_conn, vessel
    if krpc is None:
        logger.warning("kRPC module not available. kRPC functionality disabled.")
        krpc_conn = None
        vessel = None
        return
    
    try:
        logger.info(f"Connecting to kRPC server at {KRPC_HOST}:{KRPC_PORT}")
        krpc_conn = krpc.connect(
            name="GNC Flight Control",
            address=KRPC_HOST,
            rpc_port=KRPC_PORT,
            stream_port=KRPC_STREAM_PORT,
        )
        vessel = krpc_conn.space_center.active_vessel
        logger.info(f"Connected to kRPC server. Active vessel: {vessel.name}")
    except ConnectionRefusedError:
        logger.error("kRPC connection refused. Make sure the kRPC server is running in Kerbal Space Program.")
        krpc_conn = None
        vessel = None

# --- WebSocket Server ---
async def register_client(websocket):
    """Adds a new client to the set of connected clients."""
    clients.add(websocket)
    logger.info(f"New client connected: {websocket.remote_address}")

async def unregister_client(websocket):
    """Removes a client from the set of connected clients."""
    clients.remove(websocket)
    logger.info(f"Client disconnected: {websocket.remote_address}")

async def broadcast_telemetry(telemetry_data, current_logger=None):
    """Broadcasts telemetry data to all connected WebSocket clients."""
    # Use the provided logger or the default module logger
    log = current_logger if current_logger else logger

    if clients:
        message = json.dumps(telemetry_data)
        log.info(f"Attempting to broadcast to {len(clients)} clients.")
        log.debug(f"Broadcasting to {len(clients)} clients. Message size: {len(message)} bytes.")
        tasks = []
        clients_list = list(clients) # Create a stable list for iteration
        for client in clients_list:
            log.debug(f"Creating task for client {client.remote_address}")
            tasks.append(asyncio.create_task(client.send(message)))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for client, result in zip(clients_list, results):
            if isinstance(result, Exception):
                log.warning(
                    f"Failed to send message to client {client.remote_address}: {result}"
                )
            else:
                log.debug(f"Successfully sent message to client {client.remote_address}")
    else:
        log.info("No clients connected, skipping broadcast.")

async def websocket_handler(websocket, path):
    """Handles WebSocket connections with enhanced error handling and logging."""
    # The 'path' parameter is required by the websockets library but is not used in this handler.
    _ = path
    await register_client(websocket)
    try:
        await websocket.wait_closed()
    except ConnectionClosedOK:
        logger.info(f"Client {websocket.remote_address} disconnected gracefully.")
    except ConnectionClosedError:
        logger.warning(f"Client {websocket.remote_address} disconnected unexpectedly.")
    except InvalidHandshake as e:
        logger.error(f"Invalid handshake from client {websocket.remote_address}: {e}")
    except InvalidMessage as e:
        logger.error(f"Invalid message from client {websocket.remote_address}: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred with client {websocket.remote_address}: {e}", exc_info=True)
    finally:
        await unregister_client(websocket)

# --- Redis Integration ---
async def redis_subscriber():
    """Subscribes to the 'gnc_commands' Redis channel and processes incoming commands."""
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("gnc_commands")
    logger.info("Subscribed to 'gnc_commands' channel.")

    while True:
        try:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                command_data = json.loads(message["data"])
                logger.info(f"Received command: {command_data}")
                await execute_command(command_data)
        except asyncio.CancelledError:
            logger.info("Redis subscriber task cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in Redis subscriber: {e}")

async def redis_publisher(redis_client, channel, data):
    """Publishes data to a Redis channel."""
    await redis_client.publish(channel, json.dumps(data))

# --- Telemetry ---
async def telemetry_loop():
    """Continuously gathers and broadcasts telemetry data."""
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    while True:
        if krpc_conn and vessel:
            try:
                telemetry_data = {
                    "timestamp": krpc_conn.space_center.ut,
                    "mission_time": vessel.met,
                    "altitude": vessel.flight().mean_altitude,
                    "apoapsis": vessel.orbit.apoapsis_altitude,
                    "periapsis": vessel.orbit.periapsis_altitude,
                    "velocity": vessel.flight(vessel.orbit.body.reference_frame).speed,
                    "throttle": vessel.control.throttle,
                    "stage_resources": [
                        {
                            "name": res.name,
                            "amount": res.amount,
                            "max": res.max,
                        }
                        for res in vessel.resources.all
                    ],
                }
                await broadcast_telemetry(telemetry_data)
                await redis_publisher(redis_client, "telemetry", telemetry_data)
            except krpc.error.RPCError as e:
                logger.error(f"kRPC Error during telemetry gathering: {e}")
                # Attempt to reconnect
                await initialize_krpc()

        await asyncio.sleep(1)

async def check_resource_usage():
    """
    Checks current CPU and memory usage and logs warnings if thresholds are exceeded.
    Returns True if resource usage is high, False otherwise.
    """
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent

    if cpu_percent > 80:
        logger.warning(f"High CPU usage detected: {cpu_percent}%")
    if memory_percent > 80:
        logger.warning(f"High memory usage detected: {memory_percent}%")
    
    return cpu_percent > 80 or memory_percent > 80

# --- Command Execution ---
async def execute_command(command_data):
    """Executes a command received from the Mission Sequencer."""
    if not krpc_conn or not vessel:
        logger.error("Cannot execute command: kRPC is not connected.")
        return

    command = command_data.get("command")
    params = command_data.get("parameters", {})
    logger.info(f"Executing command: {command} with parameters: {params}")

    try:
        if command == "SET_THROTTLE":
            vessel.control.throttle = float(params.get("value", 0.0))
        elif command == "ACTIVATE_NEXT_STAGE":
            vessel.control.activate_next_stage()
        elif command == "SET_SAS":
            vessel.control.sas = bool(params.get("value", False))
        elif command == "SET_RCS":
            vessel.control.rcs = bool(params.get("value", False))
        elif command == "SET_AUTOPILOT_PITCH_AND_HEADING":
            ap = vessel.auto_pilot
            ap.engage()
            ap.target_pitch_and_heading(
                float(params.get("pitch", 90)),
                float(params.get("heading", 90))
            )
        else:
            logger.warning(f"Unknown command: {command}")
    except krpc.error.RPCError as e:
        logger.error(f"kRPC Error executing command '{command}': {e}")
    except Exception as e:
        logger.error(f"Error executing command '{command}': {e}")

# --- Main Application ---
async def main():
    """Main application entry point."""
    reload_ping_config()
    await initialize_krpc()

    websocket_server = await websockets.serve(
        websocket_handler,
        "0.0.0.0",
        WEBSOCKET_PORT,
        ping_interval=PING_INTERVAL_SECONDS,
        ping_timeout=PING_TIMEOUT_SECONDS,
    )
    logger.info(f"WebSocket server started on port {WEBSOCKET_PORT} with a {PING_INTERVAL_SECONDS}s ping interval.")

    redis_task = asyncio.create_task(redis_subscriber())
    telemetry_task = asyncio.create_task(telemetry_loop())
    resource_monitor_task = asyncio.create_task(
        _resource_monitor_loop()
    )  # New task

    await asyncio.gather(redis_task, telemetry_task, resource_monitor_task)

    websocket_server.close()
    await websocket_server.wait_closed()

async def _resource_monitor_loop():
    """Continuously monitors resource usage."""
    while True:
        await check_resource_usage()
        await asyncio.sleep(5)  # Check every 5 seconds

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down GNC Flight Control service.")