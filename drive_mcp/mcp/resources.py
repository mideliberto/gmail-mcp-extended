"""
MCP Resources for Drive MCP server.

This module provides resource definitions for the Drive MCP server.
"""

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.auth.token_manager import get_token_manager
from gmail_mcp.auth.oauth import get_credentials

logger = get_logger("drive_mcp.resources")


def setup_resources(mcp: FastMCP) -> None:
    """
    Set up all Drive MCP resources.

    Args:
        mcp: The FastMCP application instance.
    """

    @mcp.resource("auth://status")
    def auth_status() -> Dict[str, Any]:
        """
        Get the current authentication status.

        Returns:
            Dict containing authentication status information.
        """
        token_manager = get_token_manager()

        if not token_manager.tokens_exist():
            return {
                "authenticated": False,
                "message": "Not authenticated. Please authenticate using gmail-mcp first.",
                "has_drive_scope": False,
            }

        try:
            credentials = get_credentials()
            if credentials:
                has_drive_scope = (
                    credentials.scopes
                    and "https://www.googleapis.com/auth/drive" in credentials.scopes
                )
                return {
                    "authenticated": True,
                    "has_drive_scope": has_drive_scope,
                    "scopes": list(credentials.scopes) if credentials.scopes else [],
                    "message": (
                        "Authenticated with Drive access"
                        if has_drive_scope
                        else "Authenticated but missing Drive scope"
                    ),
                }
            else:
                return {
                    "authenticated": False,
                    "message": "Credentials invalid or expired",
                    "has_drive_scope": False,
                }
        except Exception as e:
            logger.error(f"Error checking auth status: {e}")
            return {
                "authenticated": False,
                "message": f"Error checking authentication: {e}",
                "has_drive_scope": False,
            }

    logger.info("Drive MCP resources registered successfully")
