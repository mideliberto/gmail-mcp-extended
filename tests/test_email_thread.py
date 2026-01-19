"""
Tests for mcp/tools - Email thread/conversation tools

Tests for get_thread and get_thread_summary functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import base64


def create_mock_gmail_service():
    """Create a mock Gmail API service for thread operations."""
    service = MagicMock()

    # Create a sample thread with multiple messages
    thread_messages = [
        {
            "id": "msg001",
            "threadId": "thread001",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Project Update"},
                    {"name": "From", "value": "alice@example.com"},
                    {"name": "To", "value": "bob@example.com"},
                    {"name": "Date", "value": "Mon, 15 Jan 2024 10:00:00 -0800"},
                ],
                "body": {"data": base64.urlsafe_b64encode(b"Here's the initial project update.").decode()},
            },
            "snippet": "Here's the initial project update.",
            "labelIds": ["INBOX"],
        },
        {
            "id": "msg002",
            "threadId": "thread001",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Re: Project Update"},
                    {"name": "From", "value": "bob@example.com"},
                    {"name": "To", "value": "alice@example.com"},
                    {"name": "Date", "value": "Mon, 15 Jan 2024 11:00:00 -0800"},
                ],
                "body": {"data": base64.urlsafe_b64encode(b"Thanks for the update!").decode()},
            },
            "snippet": "Thanks for the update!",
            "labelIds": ["INBOX"],
        },
        {
            "id": "msg003",
            "threadId": "thread001",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Re: Project Update"},
                    {"name": "From", "value": "alice@example.com"},
                    {"name": "To", "value": "bob@example.com"},
                    {"name": "Cc", "value": "carol@example.com"},
                    {"name": "Date", "value": "Mon, 15 Jan 2024 12:00:00 -0800"},
                ],
                "body": {"data": base64.urlsafe_b64encode(b"Let me know if you have questions.").decode()},
            },
            "snippet": "Let me know if you have questions.",
            "labelIds": ["INBOX"],
        },
    ]

    # Mock threads().get()
    service.users().threads().get().execute.return_value = {
        "id": "thread001",
        "messages": thread_messages,
    }

    # Mock messages().get() for individual email
    service.users().messages().get().execute.return_value = {
        "id": "msg001",
        "threadId": "thread001",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Project Update"},
                {"name": "From", "value": "alice@example.com"},
                {"name": "To", "value": "bob@example.com"},
                {"name": "Date", "value": "Mon, 15 Jan 2024 10:00:00 -0800"},
            ],
            "body": {"data": base64.urlsafe_b64encode(b"Here's the initial project update.").decode()},
        },
        "snippet": "Here's the initial project update.",
        "labelIds": ["INBOX"],
    }

    return service


class TestGetThread:
    """Tests for get_thread tool."""

    @patch("gmail_mcp.mcp.tools.email_thread.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_thread.get_gmail_service")
    def test_get_thread_success(self, mock_get_service, mock_get_credentials):
        """Test successful thread retrieval."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_thread = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_thread":
                get_thread = tool.fn
                break

        assert get_thread is not None

        result = get_thread(thread_id="thread001")

        assert "error" not in result
        assert result["thread_id"] == "thread001"
        assert result["message_count"] == 3
        assert len(result["messages"]) == 3
        assert "alice@example.com" in result["participants"]
        assert "bob@example.com" in result["participants"]
        assert result["subject"] == "Project Update"
        assert "thread_link" in result

    @patch("gmail_mcp.mcp.tools.email_thread.get_credentials")
    def test_get_thread_not_authenticated(self, mock_get_credentials):
        """Test get_thread when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_thread = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_thread":
                get_thread = tool.fn
                break

        result = get_thread(thread_id="thread001")

        assert "error" in result
        assert "Not authenticated" in result["error"]

    @patch("gmail_mcp.mcp.tools.email_thread.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_thread.get_gmail_service")
    def test_get_thread_extracts_participants(self, mock_get_service, mock_get_credentials):
        """Test that participants are correctly extracted from all messages."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_thread = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_thread":
                get_thread = tool.fn
                break

        result = get_thread(thread_id="thread001")

        # Should include all participants including CC
        assert "alice@example.com" in result["participants"]
        assert "bob@example.com" in result["participants"]
        assert "carol@example.com" in result["participants"]


class TestGetThreadSummary:
    """Tests for get_thread_summary tool."""

    @patch("gmail_mcp.mcp.tools.email_thread.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_thread.get_gmail_service")
    def test_get_thread_summary_success(self, mock_get_service, mock_get_credentials):
        """Test successful thread summary retrieval."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_thread_summary = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_thread_summary":
                get_thread_summary = tool.fn
                break

        assert get_thread_summary is not None

        result = get_thread_summary(thread_id="thread001")

        assert "error" not in result
        assert result["thread_id"] == "thread001"
        assert result["message_count"] == 3
        assert "original_message" in result
        assert "timeline" in result
        assert "recent_messages" in result
        assert result["original_message"]["id"] == "msg001"

    @patch("gmail_mcp.mcp.tools.email_thread.get_credentials")
    def test_get_thread_summary_not_authenticated(self, mock_get_credentials):
        """Test get_thread_summary when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_thread_summary = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_thread_summary":
                get_thread_summary = tool.fn
                break

        result = get_thread_summary(thread_id="thread001")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestGetEmailWithThread:
    """Tests for get_email with include_thread option."""

    @patch("gmail_mcp.mcp.tools.email_read.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_read.get_gmail_service")
    def test_get_email_without_thread(self, mock_get_service, mock_get_credentials):
        """Test get_email without thread context (default)."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_email":
                get_email = tool.fn
                break

        assert get_email is not None

        result = get_email(email_id="msg001")

        assert "error" not in result
        assert result["id"] == "msg001"
        assert "thread" not in result  # Thread should not be included by default

    @patch("gmail_mcp.mcp.tools.email_read.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_read.get_gmail_service")
    def test_get_email_with_thread(self, mock_get_service, mock_get_credentials):
        """Test get_email with thread context included."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_service = create_mock_gmail_service()
        mock_get_service.return_value = mock_service

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_email":
                get_email = tool.fn
                break

        result = get_email(email_id="msg001", include_thread=True)

        assert "error" not in result
        assert result["id"] == "msg001"
        assert "thread" in result
        assert result["thread"]["message_count"] == 3
        assert len(result["thread"]["participants"]) > 0


class TestBulkOperationsPagination:
    """Tests for bulk operations pagination fix."""

    @patch("gmail_mcp.mcp.tools.bulk.get_credentials")
    @patch("gmail_mcp.mcp.tools.bulk.get_gmail_service")
    def test_bulk_archive_pagination(self, mock_get_service, mock_get_credentials):
        """Test that bulk_archive uses pagination to fetch all messages."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials

        # Create a mock service that returns messages across multiple pages
        mock_service = MagicMock()

        # First page returns 100 messages with a nextPageToken
        page1_messages = [{"id": f"msg{i:03d}"} for i in range(100)]
        page2_messages = [{"id": f"msg{i:03d}"} for i in range(100, 150)]

        call_count = [0]

        def mock_list(*args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.execute.return_value = {
                    "messages": page1_messages,
                    "nextPageToken": "token123"
                }
            else:
                result.execute.return_value = {
                    "messages": page2_messages,
                    # No nextPageToken - end of results
                }
            return result

        mock_service.users().messages().list = mock_list

        # Mock batch API
        def mock_batch_http_request(callback=None):
            batch = MagicMock()
            batch._requests = []

            def add_request(request, callback=None):
                batch._requests.append((request, callback))

            def execute_batch():
                for i, (request, cb) in enumerate(batch._requests):
                    if cb:
                        cb(str(i), {"id": f"msg{i:03d}"}, None)

            batch.add = add_request
            batch.execute = execute_batch
            return batch

        mock_service.new_batch_http_request = mock_batch_http_request

        mock_get_service.return_value = mock_service

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        bulk_archive = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "bulk_archive":
                bulk_archive = tool.fn
                break

        # Request 150 emails - should trigger pagination
        result = bulk_archive(query="test", max_emails=150)

        assert "error" not in result
        # Should have made 2 API calls for listing
        assert call_count[0] == 2
        # Should have archived 150 emails
        assert result["archived"] == 150

    @patch("gmail_mcp.mcp.tools.bulk.get_credentials")
    @patch("gmail_mcp.mcp.tools.bulk.get_gmail_service")
    def test_bulk_trash_respects_max_emails(self, mock_get_service, mock_get_credentials):
        """Test that bulk_trash respects max_emails limit."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials

        mock_service = MagicMock()

        # Return 50 messages (less than requested)
        messages = [{"id": f"msg{i:03d}"} for i in range(50)]
        mock_service.users().messages().list().execute.return_value = {
            "messages": messages,
        }

        # Mock batch API
        def mock_batch_http_request(callback=None):
            batch = MagicMock()
            batch._requests = []

            def add_request(request, callback=None):
                batch._requests.append((request, callback))

            def execute_batch():
                for i, (request, cb) in enumerate(batch._requests):
                    if cb:
                        cb(str(i), {"id": f"msg{i:03d}"}, None)

            batch.add = add_request
            batch.execute = execute_batch
            return batch

        mock_service.new_batch_http_request = mock_batch_http_request
        mock_get_service.return_value = mock_service

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        bulk_trash = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "bulk_trash":
                bulk_trash = tool.fn
                break

        result = bulk_trash(query="test", max_emails=100)

        assert "error" not in result
        assert result["trashed"] == 50  # Only 50 available
