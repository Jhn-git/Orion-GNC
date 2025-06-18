"""
Configuration module for GNC Flight Control Service
Zero-dependency configuration using Python standard library only
"""

import os
import logging

# Service Configuration
SERVICE_NAME = "gnc-flight-control"
SERVICE_PORT = 8765
SERVICE_HOST = "0.0.0.0"

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Queue Configuration
GNC_COMMAND_QUEUE = "gnc_command_queue"
TELEMETRY_TOPIC = "telemetry"

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Health Check Configuration
HEALTH_CHECK_INTERVAL = 30
HEALTH_CHECK_TIMEOUT = 10

# KSP Integration (if available)
KRPC_HOST = os.getenv("KRPC_HOST", "127.0.0.1")
KRPC_PORT = int(os.getenv("KRPC_PORT", "50000"))
KRPC_RPC_PORT = int(os.getenv("KRPC_RPC_PORT", "50001"))

def get_log_level():
    """Convert string log level to logging constant"""
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    return level_map.get(LOG_LEVEL.upper(), logging.INFO)