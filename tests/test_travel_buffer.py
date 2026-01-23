"""
Tests for add_travel_buffer calendar tool.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta


class TestAddTravelBuffer:
    """Tests for add_travel_buffer tool."""

    @patch("gmail_mcp.mcp.tools.calendar.get_credentials")
    @patch("gmail_mcp.mcp.tools.calendar.get_calendar_service")
    def test_add_buffer_success(self, mock_calendar, mock_creds):
        """Test successfully adding travel buffer."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_calendar.return_value = mock_service

        # Mock getting the target event
        event_start = datetime.now() + timedelta(hours=2)
        mock_service.events().get().execute.return_value = {
            "id": "event123",
            "summary": "Team Meeting",
            "start": {
                "dateTime": event_start.isoformat(),
                "timeZone": "America/Los_Angeles"
            },
            "end": {
                "dateTime": (event_start + timedelta(hours=1)).isoformat(),
                "timeZone": "America/Los_Angeles"
            }
        }

        # Mock no conflicts
        mock_service.events().list().execute.return_value = {"items": []}

        # Mock creating buffer event
        mock_service.events().insert().execute.return_value = {
            "id": "buffer456",
            "htmlLink": "https://calendar.google.com/event?eid=buffer456",
            "summary": "Travel time - Team Meeting"
        }

        from gmail_mcp.mcp.tools.calendar import setup_calendar_tools
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        setup_calendar_tools(mcp)

        # Get the tool function
        add_travel_buffer = mcp._tool_manager._tools["add_travel_buffer"].fn

        result = add_travel_buffer(event_id="event123", minutes=30)

        assert result["success"] is True
        assert "buffer_event_id" in result
        assert result["buffer_details"]["duration_minutes"] == 30

    @patch("gmail_mcp.mcp.tools.calendar.get_credentials")
    @patch("gmail_mcp.mcp.tools.calendar.get_calendar_service")
    def test_add_buffer_conflict(self, mock_calendar, mock_creds):
        """Test buffer creation blocked by conflict."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_calendar.return_value = mock_service

        event_start = datetime.now() + timedelta(hours=2)
        mock_service.events().get().execute.return_value = {
            "id": "event123",
            "summary": "Team Meeting",
            "start": {
                "dateTime": event_start.isoformat(),
                "timeZone": "America/Los_Angeles"
            }
        }

        # Mock existing conflict
        mock_service.events().list().execute.return_value = {
            "items": [
                {
                    "id": "conflict789",
                    "summary": "Existing Meeting"
                }
            ]
        }

        from gmail_mcp.mcp.tools.calendar import setup_calendar_tools
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        setup_calendar_tools(mcp)

        add_travel_buffer = mcp._tool_manager._tools["add_travel_buffer"].fn

        result = add_travel_buffer(event_id="event123", minutes=30)

        assert result["success"] is False
        assert "conflict" in result["error"].lower()

    @patch("gmail_mcp.mcp.tools.calendar.get_credentials")
    @patch("gmail_mcp.mcp.tools.calendar.get_calendar_service")
    def test_add_buffer_all_day_event_fails(self, mock_calendar, mock_creds):
        """Test that all-day events are rejected."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_calendar.return_value = mock_service

        # All-day event (has date, not dateTime)
        mock_service.events().get().execute.return_value = {
            "id": "event123",
            "summary": "All Day Event",
            "start": {"date": "2026-01-25"},
            "end": {"date": "2026-01-26"}
        }

        from gmail_mcp.mcp.tools.calendar import setup_calendar_tools
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        setup_calendar_tools(mcp)

        add_travel_buffer = mcp._tool_manager._tools["add_travel_buffer"].fn

        result = add_travel_buffer(event_id="event123")

        assert result["success"] is False
        assert "all-day" in result["error"].lower()

    @patch("gmail_mcp.mcp.tools.calendar.get_credentials")
    def test_add_buffer_not_authenticated(self, mock_creds):
        """Test unauthenticated request."""
        mock_creds.return_value = None

        from gmail_mcp.mcp.tools.calendar import setup_calendar_tools
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        setup_calendar_tools(mcp)

        add_travel_buffer = mcp._tool_manager._tools["add_travel_buffer"].fn

        result = add_travel_buffer(event_id="event123")

        assert result["success"] is False
        assert "authenticated" in result["error"].lower()

    @patch("gmail_mcp.mcp.tools.calendar.get_credentials")
    @patch("gmail_mcp.mcp.tools.calendar.get_calendar_service")
    def test_add_buffer_custom_label(self, mock_calendar, mock_creds):
        """Test custom label for buffer event."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_calendar.return_value = mock_service

        event_start = datetime.now() + timedelta(hours=2)
        mock_service.events().get().execute.return_value = {
            "id": "event123",
            "summary": "Client Meeting",
            "start": {
                "dateTime": event_start.isoformat(),
                "timeZone": "America/Los_Angeles"
            }
        }

        mock_service.events().list().execute.return_value = {"items": []}

        mock_service.events().insert().execute.return_value = {
            "id": "buffer456",
            "htmlLink": "https://calendar.google.com/event?eid=buffer456",
            "summary": "Commute to - Client Meeting"
        }

        from gmail_mcp.mcp.tools.calendar import setup_calendar_tools
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        setup_calendar_tools(mcp)

        add_travel_buffer = mcp._tool_manager._tools["add_travel_buffer"].fn

        result = add_travel_buffer(
            event_id="event123",
            minutes=45,
            label="Commute to"
        )

        assert result["success"] is True
        assert result["buffer_details"]["duration_minutes"] == 45
