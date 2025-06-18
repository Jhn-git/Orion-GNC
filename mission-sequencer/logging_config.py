"""
Logging configuration for Mission Sequencer Service
Zero-dependency logging using Python standard library only
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path

def setup_logging(service_name="mission-sequencer", log_level="INFO"):
    """
    Setup logging configuration for the service
    
    Args:
        service_name (str): Name of the service for log formatting
        log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    
    # Convert string log level to logging constant
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    numeric_level = level_map.get(log_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(numeric_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if logs directory exists)
    logs_dir = Path("/app/logs")
    if logs_dir.exists():
        file_handler = logging.handlers.RotatingFileHandler(
            logs_dir / f"{service_name}.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger

def get_logger(name=None):
    """
    Get a logger instance
    
    Args:
        name (str): Logger name, defaults to calling module name
    
    Returns:
        logging.Logger: Logger instance
    """
    if name is None:
        name = "mission-sequencer"
    
    return logging.getLogger(name)