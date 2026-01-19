"""
Logger Utility Module

This module provides functions for setting up and configuring the application logger.
"""

import os
import logging
import sys
import yaml
from pathlib import Path
from typing import Optional


def get_log_level() -> str:
    """
    Get the log level from config.yaml.
    
    Returns:
        str: The log level (INFO by default).
    """
    try:
        config_path = Path(os.getenv("CONFIG_FILE_PATH", "config.yaml"))
        if config_path.exists():
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
                server_config = config.get("server", {})
                return server_config.get("log_level", "INFO")
        return "INFO"
    except Exception:
        return "INFO"


def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Set up and configure a logger.

    Args:
        name (Optional[str], optional): The name of the logger. Defaults to None.

    Returns:
        logging.Logger: The configured logger.
    """
    # Get the logger
    logger = logging.getLogger(name or "gmail_mcp")

    # Avoid adding duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    # Set the log level from config or default to INFO
    log_level_str = get_log_level().upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(log_level)

    # Create a console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Create a formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name (str): The name of the logger.

    Returns:
        logging.Logger: The logger.
    """
    return logging.getLogger(name) 