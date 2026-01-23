#!/usr/bin/env python3
"""
Drive MCP Server

This module provides the main entry point for the Drive MCP server.
"""

import os
import sys
import traceback

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger, setup_logger
from gmail_mcp.utils.config import get_config
from gmail_mcp.auth.token_manager import get_token_manager

# Setup logger for drive_mcp
setup_logger("drive_mcp")
logger = get_logger("drive_mcp")

# Get configuration
config = get_config()

# Create FastMCP application
mcp = FastMCP(
    name=os.getenv("MCP_SERVER_NAME", "Drive MCP"),
)

# Import and setup tools after mcp is created
from drive_mcp.mcp.tools import setup_tools
from drive_mcp.mcp.resources import setup_resources

setup_tools(mcp)
setup_resources(mcp)


def get_drive_scopes() -> list:
    """
    Get the OAuth scopes required for Drive API.

    Returns:
        list: The list of OAuth scopes.
    """
    return [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.labels",
        "https://www.googleapis.com/auth/drive.activity.readonly",
        # User info scopes
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid",
    ]


def check_authentication(max_attempts: int = 3, timeout: int = 300) -> bool:
    """
    Check if the user is authenticated with Drive scopes.

    This reuses the gmail-mcp token storage. If tokens exist and include
    Drive scopes, we're good. Otherwise, need to re-authenticate with
    combined scopes.

    Args:
        max_attempts: Maximum number of authentication attempts.
        timeout: Timeout for each authentication attempt in seconds.

    Returns:
        bool: True if authentication is successful, False otherwise.
    """
    token_manager = get_token_manager()

    # If tokens already exist, check if they have Drive scope
    if token_manager.tokens_exist():
        logger.info("Authentication tokens found, checking scopes")
        try:
            from gmail_mcp.auth.oauth import get_credentials
            credentials = get_credentials()
            if credentials:
                # Check if Drive scope is present
                if credentials.scopes and "https://www.googleapis.com/auth/drive" in credentials.scopes:
                    logger.info("Credentials include Drive scope")
                    return True
                else:
                    logger.warning("Credentials missing Drive scope, need to re-authenticate")
                    logger.info(f"Current scopes: {credentials.scopes}")
                    # Don't clear tokens - user may need them for gmail-mcp
                    # Just warn that Drive scope is missing
                    print("\n" + "=" * 80)
                    print("DRIVE SCOPE MISSING")
                    print("=" * 80)
                    print("Your current authentication doesn't include Google Drive access.")
                    print("Please re-authenticate with Drive scopes enabled.")
                    print("You may need to update your config.yaml to include Drive scopes.")
                    print("=" * 80 + "\n")
                    return False
        except Exception as e:
            logger.error(f"Error checking credentials: {e}")
            return False

    # No tokens found
    logger.warning("No authentication tokens found")
    print("\n" + "=" * 80)
    print("NOT AUTHENTICATED")
    print("=" * 80)
    print("Please authenticate using gmail-mcp first, with Drive scopes enabled.")
    print("=" * 80 + "\n")
    return False


def main() -> None:
    """
    Main entry point for the Drive MCP server.
    """
    try:
        # Check authentication
        if not check_authentication():
            logger.error("Authentication failed or missing Drive scope, exiting")
            sys.exit(1)

        # Run the MCP server
        logger.info("Starting Drive MCP server")
        mcp.run()
    except Exception as e:
        logger.error(f"Error running MCP server: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
