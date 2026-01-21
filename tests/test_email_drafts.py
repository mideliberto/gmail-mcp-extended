"""
Tests for mcp/tools - Email draft management tools

Tests for list_drafts, get_draft, update_draft, delete_draft functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import base64


def create_mock_gmail_service():
    """Create a mock Gmail API service for draft operations."""
    service = MagicMock()

    # Sample draft data
    draft_message = {
        "id": "msg001",
        "threadId": "thread001",
        "payload": {
            "headers": [
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Subject", "value": "Test Draft Subject"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "Date", "value": "Mon, 20 Jan 2026 10:00:00 -0800"},
            ],
            "body": {"data": base64.urlsafe_b64encode(b"This is the draft body content.").decode()},
        },
        "snippet": "This is the draft body content.",
        "labelIds": ["DRAFT"],
    }

    # Mock drafts().list()
    service.users().drafts().list().execute.return_value = {
        "drafts": [
            {"id": "draft001", "message": {"id": "msg001", "threadId": "thread001"}},
            {"id": "draft002", "message": {"id": "msg002", "threadId": "thread002"}},
        ],
        "resultSizeEstimate": 2,
    }

    # Mock drafts().get() for metadata format
    def mock_get_draft(*args, **kwargs):
        result = MagicMock()
        draft_id = kwargs.get("id", "draft001")
        format_type = kwargs.get("format", "full")

        if format_type == "metadata":
            result.execute.return_value = {
                "id": draft_id,
                "message": {
                    "id": "msg001",
                    "threadId": "thread001",
                    "payload": {
                        "headers": [
                            {"name": "To", "value": "recipient@example.com"},
                            {"name": "Subject", "value": "Test Draft Subject"},
                            {"name": "Date", "value": "Mon, 20 Jan 2026 10:00:00 -0800"},
                        ],
                    },
                    "snippet": "This is the draft body...",
                },
            }
        else:  # full format
            result.execute.return_value = {
                "id": draft_id,
                "message": draft_message,
            }
        return result

    service.users().drafts().get = mock_get_draft

    # Mock drafts().update()
    def mock_update_draft(*args, **kwargs):
        result = MagicMock()
        result.execute.return_value = {
            "id": kwargs.get("id", "draft001"),
            "message": {"id": "msg001"},
        }
        return result

    service.users().drafts().update = mock_update_draft

    # Mock drafts().delete()
    def mock_delete_draft(*args, **kwargs):
        result = MagicMock()
        result.execute.return_value = None  # delete returns empty
        return result

    service.users().drafts().delete = mock_delete_draft

    return service


class TestListDrafts:
    """Tests for list_drafts tool."""

    @patch("gmail_mcp.mcp.tools.email_drafts.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_drafts.get_gmail_service")
    def test_list_drafts_success(self, mock_get_service, mock_get_credentials):
        """Test successful draft listing."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        list_drafts = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_drafts":
                list_drafts = tool.fn
                break

        assert list_drafts is not None

        result = list_drafts()

        assert result["success"] is True
        assert len(result["drafts"]) == 2
        assert result["total_drafts"] == 2
        assert result["drafts"][0]["draft_id"] == "draft001"
        assert result["drafts"][0]["subject"] == "Test Draft Subject"

    @patch("gmail_mcp.mcp.tools.email_drafts.get_credentials")
    def test_list_drafts_not_authenticated(self, mock_get_credentials):
        """Test list_drafts when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        list_drafts = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_drafts":
                list_drafts = tool.fn
                break

        result = list_drafts()

        assert result["success"] is False
        assert "Not authenticated" in result["error"]

    @patch("gmail_mcp.mcp.tools.email_drafts.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_drafts.get_gmail_service")
    def test_list_drafts_empty(self, mock_get_service, mock_get_credentials):
        """Test list_drafts when no drafts exist."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials

        mock_service = MagicMock()
        mock_service.users().drafts().list().execute.return_value = {"drafts": []}
        mock_get_service.return_value = mock_service

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        list_drafts = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_drafts":
                list_drafts = tool.fn
                break

        result = list_drafts()

        assert result["success"] is True
        assert len(result["drafts"]) == 0
        assert "No drafts found" in result["message"]


class TestGetDraft:
    """Tests for get_draft tool."""

    @patch("gmail_mcp.mcp.tools.email_drafts.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_drafts.get_gmail_service")
    def test_get_draft_success(self, mock_get_service, mock_get_credentials):
        """Test successful draft retrieval."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_draft = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_draft":
                get_draft = tool.fn
                break

        assert get_draft is not None

        result = get_draft(draft_id="draft001")

        assert result["success"] is True
        assert result["draft_id"] == "draft001"
        assert result["subject"] == "Test Draft Subject"
        assert result["to"] == "recipient@example.com"
        assert "This is the draft body content" in result["body"]

    @patch("gmail_mcp.mcp.tools.email_drafts.get_credentials")
    def test_get_draft_not_authenticated(self, mock_get_credentials):
        """Test get_draft when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_draft = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_draft":
                get_draft = tool.fn
                break

        result = get_draft(draft_id="draft001")

        assert result["success"] is False
        assert "Not authenticated" in result["error"]


class TestUpdateDraft:
    """Tests for update_draft tool."""

    @patch("gmail_mcp.mcp.tools.email_drafts.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_drafts.get_gmail_service")
    def test_update_draft_subject(self, mock_get_service, mock_get_credentials):
        """Test updating draft subject."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        update_draft = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "update_draft":
                update_draft = tool.fn
                break

        assert update_draft is not None

        result = update_draft(draft_id="draft001", subject="Updated Subject")

        assert result["success"] is True
        assert "Draft updated successfully" in result["message"]

    @patch("gmail_mcp.mcp.tools.email_drafts.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_drafts.get_gmail_service")
    def test_update_draft_body(self, mock_get_service, mock_get_credentials):
        """Test updating draft body."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        update_draft = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "update_draft":
                update_draft = tool.fn
                break

        result = update_draft(draft_id="draft001", body="New body content here")

        assert result["success"] is True

    @patch("gmail_mcp.mcp.tools.email_drafts.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_drafts.get_gmail_service")
    def test_update_draft_multiple_fields(self, mock_get_service, mock_get_credentials):
        """Test updating multiple draft fields at once."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        update_draft = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "update_draft":
                update_draft = tool.fn
                break

        result = update_draft(
            draft_id="draft001",
            to="newrecipient@example.com",
            subject="New Subject",
            body="New body"
        )

        assert result["success"] is True

    @patch("gmail_mcp.mcp.tools.email_drafts.get_credentials")
    def test_update_draft_not_authenticated(self, mock_get_credentials):
        """Test update_draft when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        update_draft = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "update_draft":
                update_draft = tool.fn
                break

        result = update_draft(draft_id="draft001", subject="Test")

        assert result["success"] is False
        assert "Not authenticated" in result["error"]


class TestDeleteDraft:
    """Tests for delete_draft tool."""

    @patch("gmail_mcp.mcp.tools.email_drafts.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_drafts.get_gmail_service")
    def test_delete_draft_success(self, mock_get_service, mock_get_credentials):
        """Test successful draft deletion."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        delete_draft = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "delete_draft":
                delete_draft = tool.fn
                break

        assert delete_draft is not None

        result = delete_draft(draft_id="draft001")

        assert result["success"] is True
        assert "deleted permanently" in result["message"]
        assert result["draft_id"] == "draft001"

    @patch("gmail_mcp.mcp.tools.email_drafts.get_credentials")
    def test_delete_draft_not_authenticated(self, mock_get_credentials):
        """Test delete_draft when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        delete_draft = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "delete_draft":
                delete_draft = tool.fn
                break

        result = delete_draft(draft_id="draft001")

        assert result["success"] is False
        assert "Not authenticated" in result["error"]
