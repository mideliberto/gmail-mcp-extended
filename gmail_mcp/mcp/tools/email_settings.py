"""
Email Settings Tools Module

Handles Gmail settings like vacation responder/out of office.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_gmail_service
from gmail_mcp.utils.date_parser import parse_natural_date
from gmail_mcp.auth.oauth import get_credentials

logger = get_logger(__name__)


def setup_email_settings_tools(mcp: FastMCP) -> None:
    """Set up email settings tools on the FastMCP application."""

    @mcp.tool()
    def get_vacation_responder() -> Dict[str, Any]:
        """
        Get the current vacation responder settings.

        Returns:
            Dict[str, Any]: Current vacation responder status including:
                - enabled: Whether vacation responder is on
                - start_time: When it starts (if set)
                - end_time: When it ends (if set)
                - subject: Response subject
                - message: Response message body
                - contacts_only: Whether to only respond to contacts

        Example usage:
            get_vacation_responder()
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            settings = service.users().settings().getVacation(userId="me").execute()

            result = {
                "success": True,
                "enabled": settings.get("enableAutoReply", False),
                "subject": settings.get("responseSubject", ""),
                "message": settings.get("responseBodyPlainText", ""),
                "contacts_only": settings.get("restrictToContacts", False),
                "domain_only": settings.get("restrictToDomain", False),
            }

            # Parse timestamps if present
            if settings.get("startTime"):
                start_ms = int(settings["startTime"])
                result["start_time"] = datetime.fromtimestamp(start_ms / 1000).isoformat()

            if settings.get("endTime"):
                end_ms = int(settings["endTime"])
                result["end_time"] = datetime.fromtimestamp(end_ms / 1000).isoformat()

            return result

        except Exception as e:
            logger.error(f"Failed to get vacation responder: {e}")
            return {"success": False, "error": f"Failed to get vacation responder: {e}"}

    @mcp.tool()
    def set_vacation_responder(
        enabled: bool = True,
        subject: Optional[str] = None,
        message: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        contacts_only: bool = False,
        domain_only: bool = False
    ) -> Dict[str, Any]:
        """
        Set up or update the vacation responder (out of office auto-reply).

        Args:
            enabled (bool): Whether to enable the vacation responder (default: True)
            subject (str, optional): Subject line for auto-reply. Required when enabling.
            message (str, optional): Body text for auto-reply. Required when enabling.
            start_date (str, optional): When to start auto-replies (e.g., "tomorrow", "2026-02-01").
                If not provided, starts immediately.
            end_date (str, optional): When to stop auto-replies (e.g., "next friday", "2026-02-07").
                If not provided, runs indefinitely until disabled.
            contacts_only (bool): Only reply to people in your contacts (default: False)
            domain_only (bool): Only reply to people in your organization (default: False)

        Returns:
            Dict[str, Any]: Result of the operation

        Example usage:
        1. Enable vacation responder:
           set_vacation_responder(
               subject="Out of Office",
               message="I'm away until Feb 7. For urgent matters, contact backup@company.com",
               start_date="tomorrow",
               end_date="next friday"
           )

        2. Simple out of office:
           set_vacation_responder(
               subject="Away from email",
               message="I have limited email access. I'll respond when I return."
           )

        3. Disable vacation responder:
           set_vacation_responder(enabled=False)
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        # Validate required fields when enabling
        if enabled and not subject:
            return {"success": False, "error": "Subject is required when enabling vacation responder"}
        if enabled and not message:
            return {"success": False, "error": "Message is required when enabling vacation responder"}

        try:
            service = get_gmail_service(credentials)

            vacation_settings = {
                "enableAutoReply": enabled,
                "restrictToContacts": contacts_only,
                "restrictToDomain": domain_only,
            }

            if enabled:
                vacation_settings["responseSubject"] = subject
                vacation_settings["responseBodyPlainText"] = message

                # Parse start date
                if start_date:
                    start_dt = parse_natural_date(start_date, prefer_future=True)
                    if start_dt:
                        # Convert to milliseconds since epoch
                        vacation_settings["startTime"] = str(int(start_dt.timestamp() * 1000))
                    else:
                        return {"success": False, "error": f"Could not parse start date: {start_date}"}

                # Parse end date
                if end_date:
                    end_dt = parse_natural_date(end_date, prefer_future=True)
                    if end_dt:
                        # Set to end of day
                        end_dt = end_dt.replace(hour=23, minute=59, second=59)
                        vacation_settings["endTime"] = str(int(end_dt.timestamp() * 1000))
                    else:
                        return {"success": False, "error": f"Could not parse end date: {end_date}"}

            result = service.users().settings().updateVacation(
                userId="me",
                body=vacation_settings
            ).execute()

            response = {
                "success": True,
                "enabled": result.get("enableAutoReply", False),
            }

            if enabled:
                response["message"] = "Vacation responder enabled successfully."
                response["subject"] = result.get("responseSubject", "")
                if start_date:
                    response["starts"] = start_date
                if end_date:
                    response["ends"] = end_date
            else:
                response["message"] = "Vacation responder disabled."

            return response

        except Exception as e:
            logger.error(f"Failed to set vacation responder: {e}")
            return {"success": False, "error": f"Failed to set vacation responder: {e}"}

    @mcp.tool()
    def disable_vacation_responder() -> Dict[str, Any]:
        """
        Disable the vacation responder.

        This is a convenience function - equivalent to set_vacation_responder(enabled=False).

        Returns:
            Dict[str, Any]: Result of the operation

        Example usage:
            disable_vacation_responder()
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            vacation_settings = {
                "enableAutoReply": False,
            }

            service.users().settings().updateVacation(
                userId="me",
                body=vacation_settings
            ).execute()

            return {
                "success": True,
                "message": "Vacation responder disabled."
            }

        except Exception as e:
            logger.error(f"Failed to disable vacation responder: {e}")
            return {"success": False, "error": f"Failed to disable vacation responder: {e}"}
