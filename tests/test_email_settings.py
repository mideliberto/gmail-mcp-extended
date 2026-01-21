"""
Tests for mcp/tools/email_settings.py - Email settings tools

Tests for get_vacation_responder, set_vacation_responder, disable_vacation_responder.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


# Sample vacation settings response data
SAMPLE_VACATION_ENABLED = {
    "enableAutoReply": True,
    "responseSubject": "Out of Office",
    "responseBodyPlainText": "I'm away until Feb 7. For urgent matters, contact backup@company.com",
    "restrictToContacts": False,
    "restrictToDomain": False,
    "startTime": str(int(datetime(2026, 2, 1, 0, 0, 0).timestamp() * 1000)),
    "endTime": str(int(datetime(2026, 2, 7, 23, 59, 59).timestamp() * 1000)),
}

SAMPLE_VACATION_DISABLED = {
    "enableAutoReply": False,
    "responseSubject": "",
    "responseBodyPlainText": "",
    "restrictToContacts": False,
    "restrictToDomain": False,
}


def create_mock_gmail_service_for_vacation():
    """Create a mock Gmail API service for vacation responder operations."""
    service = MagicMock()

    # Mock users().settings().getVacation()
    service.users().settings().getVacation().execute.return_value = SAMPLE_VACATION_ENABLED

    # Mock users().settings().updateVacation()
    def mock_update_vacation(*args, **kwargs):
        result = MagicMock()
        body = kwargs.get("body", {})
        result.execute.return_value = {
            "enableAutoReply": body.get("enableAutoReply", False),
            "responseSubject": body.get("responseSubject", ""),
            "responseBodyPlainText": body.get("responseBodyPlainText", ""),
            "restrictToContacts": body.get("restrictToContacts", False),
            "restrictToDomain": body.get("restrictToDomain", False),
        }
        return result

    service.users().settings().updateVacation = mock_update_vacation

    return service


class TestGetVacationResponder:
    """Tests for get_vacation_responder tool."""

    @patch("gmail_mcp.mcp.tools.email_settings.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_settings.get_gmail_service")
    def test_get_vacation_enabled(self, mock_get_service, mock_get_credentials):
        """Test getting vacation responder when enabled."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service_for_vacation()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_vacation_responder = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_vacation_responder":
                get_vacation_responder = tool.fn
                break

        assert get_vacation_responder is not None, "get_vacation_responder tool not found"

        result = get_vacation_responder()

        assert result["success"] is True
        assert result["enabled"] is True
        assert result["subject"] == "Out of Office"
        assert "I'm away until Feb 7" in result["message"]
        assert "start_time" in result
        assert "end_time" in result

    @patch("gmail_mcp.mcp.tools.email_settings.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_settings.get_gmail_service")
    def test_get_vacation_disabled(self, mock_get_service, mock_get_credentials):
        """Test getting vacation responder when disabled."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials

        mock_service = MagicMock()
        mock_service.users().settings().getVacation().execute.return_value = SAMPLE_VACATION_DISABLED
        mock_get_service.return_value = mock_service

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_vacation_responder = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_vacation_responder":
                get_vacation_responder = tool.fn
                break

        result = get_vacation_responder()

        assert result["success"] is True
        assert result["enabled"] is False

    @patch("gmail_mcp.mcp.tools.email_settings.get_credentials")
    def test_get_vacation_not_authenticated(self, mock_get_credentials):
        """Test get_vacation_responder when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_vacation_responder = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_vacation_responder":
                get_vacation_responder = tool.fn
                break

        result = get_vacation_responder()

        assert result["success"] is False
        assert "Not authenticated" in result["error"]


class TestSetVacationResponder:
    """Tests for set_vacation_responder tool."""

    @patch("gmail_mcp.mcp.tools.email_settings.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_settings.get_gmail_service")
    def test_set_vacation_enabled(self, mock_get_service, mock_get_credentials):
        """Test enabling vacation responder with all fields."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service_for_vacation()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        set_vacation_responder = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "set_vacation_responder":
                set_vacation_responder = tool.fn
                break

        assert set_vacation_responder is not None, "set_vacation_responder tool not found"

        result = set_vacation_responder(
            enabled=True,
            subject="Out of Office",
            message="I'm away from my desk.",
            start_date="2026-02-01",
            end_date="2026-02-07"
        )

        assert result["success"] is True
        assert "enabled" in result["message"].lower()

    @patch("gmail_mcp.mcp.tools.email_settings.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_settings.get_gmail_service")
    def test_set_vacation_minimal(self, mock_get_service, mock_get_credentials):
        """Test enabling vacation responder with minimal fields."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service_for_vacation()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        set_vacation_responder = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "set_vacation_responder":
                set_vacation_responder = tool.fn
                break

        result = set_vacation_responder(
            enabled=True,
            subject="Away",
            message="I'm away."
        )

        assert result["success"] is True

    @patch("gmail_mcp.mcp.tools.email_settings.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_settings.get_gmail_service")
    def test_set_vacation_contacts_only(self, mock_get_service, mock_get_credentials):
        """Test setting vacation responder to contacts only."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service_for_vacation()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        set_vacation_responder = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "set_vacation_responder":
                set_vacation_responder = tool.fn
                break

        result = set_vacation_responder(
            enabled=True,
            subject="Away",
            message="I'm away.",
            contacts_only=True
        )

        assert result["success"] is True

    @patch("gmail_mcp.mcp.tools.email_settings.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_settings.get_gmail_service")
    def test_set_vacation_disabled(self, mock_get_service, mock_get_credentials):
        """Test disabling vacation responder via set_vacation_responder."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service_for_vacation()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        set_vacation_responder = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "set_vacation_responder":
                set_vacation_responder = tool.fn
                break

        result = set_vacation_responder(enabled=False)

        assert result["success"] is True
        assert "disabled" in result["message"].lower()

    @patch("gmail_mcp.mcp.tools.email_settings.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_settings.get_gmail_service")
    def test_set_vacation_missing_subject(self, mock_get_service, mock_get_credentials):
        """Test set_vacation_responder fails without subject when enabling."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service_for_vacation()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        set_vacation_responder = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "set_vacation_responder":
                set_vacation_responder = tool.fn
                break

        result = set_vacation_responder(enabled=True, message="Test message")

        assert result["success"] is False
        assert "Subject is required" in result["error"]

    @patch("gmail_mcp.mcp.tools.email_settings.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_settings.get_gmail_service")
    def test_set_vacation_missing_message(self, mock_get_service, mock_get_credentials):
        """Test set_vacation_responder fails without message when enabling."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service_for_vacation()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        set_vacation_responder = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "set_vacation_responder":
                set_vacation_responder = tool.fn
                break

        result = set_vacation_responder(enabled=True, subject="Test subject")

        assert result["success"] is False
        assert "Message is required" in result["error"]

    @patch("gmail_mcp.mcp.tools.email_settings.get_credentials")
    def test_set_vacation_not_authenticated(self, mock_get_credentials):
        """Test set_vacation_responder when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        set_vacation_responder = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "set_vacation_responder":
                set_vacation_responder = tool.fn
                break

        result = set_vacation_responder(
            enabled=True,
            subject="Test",
            message="Test"
        )

        assert result["success"] is False
        assert "Not authenticated" in result["error"]

    @patch("gmail_mcp.mcp.tools.email_settings.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_settings.get_gmail_service")
    def test_set_vacation_with_nlp_dates(self, mock_get_service, mock_get_credentials):
        """Test set_vacation_responder with natural language dates."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service_for_vacation()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        set_vacation_responder = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "set_vacation_responder":
                set_vacation_responder = tool.fn
                break

        result = set_vacation_responder(
            enabled=True,
            subject="Out of Office",
            message="I'm away.",
            start_date="tomorrow",
            end_date="next friday"
        )

        assert result["success"] is True


class TestDisableVacationResponder:
    """Tests for disable_vacation_responder tool."""

    @patch("gmail_mcp.mcp.tools.email_settings.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_settings.get_gmail_service")
    def test_disable_vacation_success(self, mock_get_service, mock_get_credentials):
        """Test successfully disabling vacation responder."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service_for_vacation()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        disable_vacation_responder = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "disable_vacation_responder":
                disable_vacation_responder = tool.fn
                break

        assert disable_vacation_responder is not None, "disable_vacation_responder tool not found"

        result = disable_vacation_responder()

        assert result["success"] is True
        assert "disabled" in result["message"].lower()

    @patch("gmail_mcp.mcp.tools.email_settings.get_credentials")
    def test_disable_vacation_not_authenticated(self, mock_get_credentials):
        """Test disable_vacation_responder when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        disable_vacation_responder = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "disable_vacation_responder":
                disable_vacation_responder = tool.fn
                break

        result = disable_vacation_responder()

        assert result["success"] is False
        assert "Not authenticated" in result["error"]

    @patch("gmail_mcp.mcp.tools.email_settings.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_settings.get_gmail_service")
    def test_disable_vacation_api_error(self, mock_get_service, mock_get_credentials):
        """Test disable_vacation_responder handles API errors."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials

        mock_service = MagicMock()
        mock_service.users().settings().updateVacation().execute.side_effect = Exception("API Error")
        mock_get_service.return_value = mock_service

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        disable_vacation_responder = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "disable_vacation_responder":
                disable_vacation_responder = tool.fn
                break

        result = disable_vacation_responder()

        assert result["success"] is False
        assert "error" in result
