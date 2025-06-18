import asyncio
import sys
import websockets
import os

async def check_websocket():
    """
    Performs a health check by connecting to the WebSocket server.
    """
    websocket_port = os.getenv("WEBSOCKET_PORT", 8765)
    uri = f"ws://localhost:{websocket_port}"
    try:
        # Connect to the server with a short timeout (Python 3.8+ compatible).
        try:
            async def connect_ws():
                async with websockets.connect(uri) as websocket:
                    print("WebSocket handshake successful.")
                    return 0
            return await asyncio.wait_for(connect_ws(), timeout=10)
        except asyncio.TimeoutError as e:
            print(f"Health check failed: {e}", file=sys.stderr)
            return 1
    except (asyncio.TimeoutError, websockets.exceptions.WebSocketException) as e:
        print(f"Health check failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"An unexpected error occurred during health check: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    # In Python 3.10+, the default event loop policy on Windows may not
    # support this script if run outside of an async function.
    # We ensure a compatible event loop is used.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    sys.exit(asyncio.run(check_websocket()))