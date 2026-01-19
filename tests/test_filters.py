"""
Tests for mcp/tools/filters.py - Gmail filter management tools

These tests mock the Gmail API to verify filter functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


SAMPLE_FILTER = {
    "id": "filter001",
    "criteria": {
        "from": "newsletter@example.com",
        "subject": "Weekly Update",
    },
    "action": {
        "addLabelIds": ["Label_1"],
        "removeLabelIds": ["INBOX"],
    }
}

SAMPLE_FILTER_2 = {
    "id": "filter002",
    "criteria": {
        "query": "is:important",
    },
    "action": {
        "addLabelIds": ["STARRED"],
    }
}


def create_mock_gmail_service():
    """Create a mock Gmail API service for filter operations."""
    service = MagicMock()

    # Mock users().settings().filters().list()
    service.users().settings().filters().list().execute.return_value = {
        "filter": [SAMPLE_FILTER, SAMPLE_FILTER_2]
    }

    # Mock users().settings().filters().get()
    def mock_get_filter(userId, id):
        mock = MagicMock()
        if id == "filter001":
            mock.execute.return_value = SAMPLE_FILTER
        elif id == "filter002":
            mock.execute.return_value = SAMPLE_FILTER_2
        else:
            mock.execute.side_effect = Exception("Filter not found")
        return mock

    service.users().settings().filters().get = mock_get_filter

    # Mock users().settings().filters().create()
    def mock_create_filter(userId, body):
        mock = MagicMock()
        new_filter = {
            "id": "filter_new",
            "criteria": body.get("criteria", {}),
            "action": body.get("action", {}),
        }
        mock.execute.return_value = new_filter
        return mock

    service.users().settings().filters().create = mock_create_filter

    # Mock users().settings().filters().delete()
    service.users().settings().filters().delete().execute.return_value = {}

    # Mock users().labels().list() for Claude review labels
    service.users().labels().list().execute.return_value = {
        "labels": [
            {"id": "Label_1", "name": "Label 1"},
            {"id": "Label_Claude_Review", "name": "Claude/Review"},
        ]
    }

    return service


class TestListFilters:
    """Tests for list_filters tool."""

    @patch("gmail_mcp.mcp.tools.filters.get_credentials")
    @patch("gmail_mcp.mcp.tools.filters.get_gmail_service")
    def test_list_filters_success(self, mock_get_service, mock_get_credentials):
        """Test successful filter listing."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        list_filters = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_filters":
                list_filters = tool.fn
                break

        assert list_filters is not None, "list_filters tool not found"

        result = list_filters()

        assert "error" not in result
        assert "filters" in result
        assert len(result["filters"]) == 2
        assert result["filters"][0]["id"] == "filter001"

    @patch("gmail_mcp.mcp.tools.filters.get_credentials")
    def test_list_filters_not_authenticated(self, mock_get_credentials):
        """Test list_filters when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        list_filters = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_filters":
                list_filters = tool.fn
                break

        result = list_filters()

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestCreateFilter:
    """Tests for create_filter tool."""

    @patch("gmail_mcp.mcp.tools.filters.get_credentials")
    @patch("gmail_mcp.mcp.tools.filters.get_gmail_service")
    def test_create_filter_success(self, mock_get_service, mock_get_credentials):
        """Test successful filter creation."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        create_filter = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "create_filter":
                create_filter = tool.fn
                break

        assert create_filter is not None

        result = create_filter(
            from_address="test@example.com",
            add_label_ids=["STARRED"]
        )

        assert result["success"] is True
        assert "filter_id" in result

    @patch("gmail_mcp.mcp.tools.filters.get_credentials")
    def test_create_filter_not_authenticated(self, mock_get_credentials):
        """Test create_filter when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        create_filter = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "create_filter":
                create_filter = tool.fn
                break

        result = create_filter(from_address="test@example.com")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestDeleteFilter:
    """Tests for delete_filter tool."""

    @patch("gmail_mcp.mcp.tools.filters.get_credentials")
    @patch("gmail_mcp.mcp.tools.filters.get_gmail_service")
    def test_delete_filter_success(self, mock_get_service, mock_get_credentials):
        """Test successful filter deletion."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        delete_filter = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "delete_filter":
                delete_filter = tool.fn
                break

        assert delete_filter is not None

        result = delete_filter(filter_id="filter001")

        assert result["success"] is True


class TestGetFilter:
    """Tests for get_filter tool."""

    @patch("gmail_mcp.mcp.tools.filters.get_credentials")
    @patch("gmail_mcp.mcp.tools.filters.get_gmail_service")
    def test_get_filter_success(self, mock_get_service, mock_get_credentials):
        """Test successful filter retrieval."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_filter = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_filter":
                get_filter = tool.fn
                break

        assert get_filter is not None

        result = get_filter(filter_id="filter001")

        assert result["success"] is True
        assert "filter" in result
        assert result["filter"]["id"] == "filter001"


class TestCreateClaudeReviewFilter:
    """Tests for create_claude_review_filter tool."""

    @patch("gmail_mcp.mcp.tools.filters.get_credentials")
    @patch("gmail_mcp.mcp.tools.filters.get_gmail_service")
    def test_create_claude_review_filter_success(self, mock_get_service, mock_get_credentials):
        """Test successful Claude review filter creation."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        create_claude_review_filter = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "create_claude_review_filter":
                create_claude_review_filter = tool.fn
                break

        assert create_claude_review_filter is not None

        result = create_claude_review_filter(
            from_address="important@example.com",
            review_type="Review"
        )

        assert result["success"] is True
