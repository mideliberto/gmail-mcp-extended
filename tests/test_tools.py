"""
Tests for mcp/tools - Gmail tools

These tests mock the Gmail API to verify tool functionality.

NOTE: After modular refactor, patches target specific modules:
- Email read tools: gmail_mcp.mcp.tools.email_read
- Email send tools: gmail_mcp.mcp.tools.email_send
- Email manage tools: gmail_mcp.mcp.tools.email_manage
- etc.

Service mocks target: gmail_mcp.utils.services
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


# Sample Gmail API response data
SAMPLE_MESSAGE = {
    "id": "msg001",
    "threadId": "thread001",
    "snippet": "Hello, this is a test email...",
    "labelIds": ["INBOX", "UNREAD"],
    "payload": {
        "headers": [
            {"name": "Subject", "value": "Test Email"},
            {"name": "From", "value": "sender@example.com"},
            {"name": "To", "value": "recipient@example.com"},
            {"name": "Cc", "value": "cc@example.com"},
            {"name": "Date", "value": "Mon, 15 Jan 2024 10:00:00 -0800"},
        ],
        "body": {"data": "SGVsbG8gV29ybGQ="},  # "Hello World" base64 encoded
    }
}

SAMPLE_MESSAGE_2 = {
    "id": "msg002",
    "threadId": "thread002",
    "snippet": "Another test email...",
    "labelIds": ["INBOX"],
    "payload": {
        "headers": [
            {"name": "Subject", "value": "Second Email"},
            {"name": "From", "value": "other@example.com"},
            {"name": "To", "value": "recipient@example.com"},
            {"name": "Date", "value": "Tue, 16 Jan 2024 11:00:00 -0800"},
        ],
        "body": {"data": "VGVzdCBib2R5"},
    }
}

SAMPLE_PROFILE = {
    "emailAddress": "user@example.com",
    "messagesTotal": 1000,
    "threadsTotal": 500,
    "historyId": "12345",
}

SAMPLE_LABELS = {
    "labels": [
        {"id": "INBOX", "name": "INBOX", "type": "system"},
        {"id": "SENT", "name": "SENT", "type": "system"},
        {"id": "UNREAD", "name": "UNREAD", "type": "system"},
        {"id": "DRAFT", "name": "DRAFT", "type": "system"},
        {"id": "SPAM", "name": "SPAM", "type": "system"},
        {"id": "TRASH", "name": "TRASH", "type": "system"},
    ]
}

SAMPLE_LABEL_DETAIL = {
    "messagesTotal": 50,
    "messagesUnread": 10,
}


def create_mock_gmail_service():
    """Create a mock Gmail API service with batch support."""
    service = MagicMock()

    # Mock users().messages().list()
    service.users().messages().list().execute.return_value = {
        "messages": [{"id": "msg001"}, {"id": "msg002"}],
        "nextPageToken": "token123",
    }

    # Mock users().messages().get() for single gets
    def mock_get_message(userId, id, format=None):
        mock = MagicMock()
        if id == "msg001":
            mock.execute.return_value = SAMPLE_MESSAGE
        elif id == "msg002":
            mock.execute.return_value = SAMPLE_MESSAGE_2
        else:
            mock.execute.return_value = SAMPLE_MESSAGE
        return mock

    service.users().messages().get = mock_get_message

    # Mock batch API for _batch_get_emails
    def mock_batch_http_request(callback=None):
        batch = MagicMock()
        batch._requests = []
        batch._callback = callback

        def add_request(request, callback=None):
            batch._requests.append((request, callback))

        def execute_batch():
            # Simulate batch execution by calling callbacks
            for i, (request, cb) in enumerate(batch._requests):
                # Get the message ID from the request
                msg_id = f"msg00{i+1}"
                if msg_id == "msg001":
                    response = SAMPLE_MESSAGE
                elif msg_id == "msg002":
                    response = SAMPLE_MESSAGE_2
                else:
                    response = SAMPLE_MESSAGE
                if cb:
                    cb(str(i), response, None)

        batch.add = add_request
        batch.execute = execute_batch
        return batch

    service.new_batch_http_request = mock_batch_http_request

    # Mock users().getProfile()
    service.users().getProfile().execute.return_value = SAMPLE_PROFILE

    # Mock users().labels().list()
    service.users().labels().list().execute.return_value = SAMPLE_LABELS

    # Mock users().labels().get()
    service.users().labels().get().execute.return_value = SAMPLE_LABEL_DETAIL

    return service


class TestListEmails:
    """Tests for list_emails tool."""

    @patch("gmail_mcp.mcp.tools.email_read.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_read.get_gmail_service")
    def test_list_emails_success(self, mock_get_service, mock_get_credentials):
        """Test successful email listing."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        # Setup mocks
        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        # Create MCP and setup tools
        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        # Get the list_emails tool
        list_emails = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_emails":
                list_emails = tool.fn
                break

        assert list_emails is not None, "list_emails tool not found"

        # Call the tool
        result = list_emails(max_results=10, label="INBOX")

        # Verify result
        assert "error" not in result
        assert "emails" in result
        assert len(result["emails"]) == 2
        assert result["next_page_token"] == "token123"

        # Verify email structure
        email = result["emails"][0]
        assert email["id"] == "msg001"
        assert email["thread_id"] == "thread001"
        assert email["subject"] == "Test Email"
        assert email["from"] == "sender@example.com"
        assert "email_link" in email

    @patch("gmail_mcp.mcp.tools.email_read.get_credentials")
    def test_list_emails_not_authenticated(self, mock_get_credentials):
        """Test list_emails when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        list_emails = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_emails":
                list_emails = tool.fn
                break

        result = list_emails(max_results=10, label="INBOX")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestSearchEmails:
    """Tests for search_emails tool."""

    @patch("gmail_mcp.mcp.tools.email_read.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_read.get_gmail_service")
    def test_search_emails_success(self, mock_get_service, mock_get_credentials):
        """Test successful email search."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        search_emails = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "search_emails":
                search_emails = tool.fn
                break

        assert search_emails is not None

        result = search_emails(query="from:sender@example.com", max_results=10)

        assert "error" not in result
        assert "emails" in result
        assert "query" in result
        assert result["query"] == "from:sender@example.com"
        assert len(result["emails"]) == 2

    @patch("gmail_mcp.mcp.tools.email_read.get_credentials")
    def test_search_emails_not_authenticated(self, mock_get_credentials):
        """Test search_emails when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        search_emails = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "search_emails":
                search_emails = tool.fn
                break

        result = search_emails(query="test", max_results=10)

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestGetEmail:
    """Tests for get_email tool."""

    @patch("gmail_mcp.mcp.tools.email_read.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_read.get_gmail_service")
    def test_get_email_success(self, mock_get_service, mock_get_credentials):
        """Test successful email retrieval."""
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
        assert result["thread_id"] == "thread001"
        assert result["subject"] == "Test Email"
        assert result["from"] == "sender@example.com"
        assert "email_link" in result

    @patch("gmail_mcp.mcp.tools.email_read.get_credentials")
    def test_get_email_not_authenticated(self, mock_get_credentials):
        """Test get_email when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_email":
                get_email = tool.fn
                break

        result = get_email(email_id="msg001")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestGetEmailOverview:
    """Tests for get_email_overview tool."""

    @patch("gmail_mcp.mcp.tools.email_read.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_read.get_gmail_service")
    def test_get_email_overview_success(self, mock_get_service, mock_get_credentials):
        """Test successful email overview retrieval."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_service = create_mock_gmail_service()
        mock_get_service.return_value = mock_service

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_email_overview = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_email_overview":
                get_email_overview = tool.fn
                break

        assert get_email_overview is not None

        result = get_email_overview()

        assert "error" not in result
        assert "account" in result
        assert "counts" in result
        assert "recent_emails" in result

        # Verify account info
        assert result["account"]["email"] == "user@example.com"
        assert result["account"]["total_messages"] == 1000

    @patch("gmail_mcp.mcp.tools.email_read.get_credentials")
    def test_get_email_overview_not_authenticated(self, mock_get_credentials):
        """Test get_email_overview when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_email_overview = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_email_overview":
                get_email_overview = tool.fn
                break

        result = get_email_overview()

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestExtractEmailInfoIntegration:
    """Integration tests verifying extract_email_info is used correctly."""

    @patch("gmail_mcp.mcp.tools.email_read.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_read.get_gmail_service")
    def test_list_emails_uses_helper(self, mock_get_service, mock_get_credentials):
        """Verify list_emails uses extract_email_info helper."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        list_emails = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_emails":
                list_emails = tool.fn
                break

        result = list_emails(max_results=10, label="INBOX")

        # Verify the email structure matches extract_email_info output
        email = result["emails"][0]
        expected_keys = ["id", "thread_id", "subject", "from", "to", "cc", "date", "snippet", "labels", "email_link"]
        for key in expected_keys:
            assert key in email, f"Missing key: {key}"

    @patch("gmail_mcp.mcp.tools.email_read.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_read.get_gmail_service")
    def test_search_emails_uses_helper(self, mock_get_service, mock_get_credentials):
        """Verify search_emails uses extract_email_info helper."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        search_emails = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "search_emails":
                search_emails = tool.fn
                break

        result = search_emails(query="test", max_results=10)

        # Verify the email structure matches extract_email_info output
        email = result["emails"][0]
        expected_keys = ["id", "thread_id", "subject", "from", "to", "cc", "date", "snippet", "labels", "email_link"]
        for key in expected_keys:
            assert key in email, f"Missing key: {key}"


class TestComposeEmailScheduledSend:
    """Tests for compose_email tool with send_at parameter (scheduled send)."""

    @patch("gmail_mcp.mcp.tools.email_send.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_send.get_gmail_service")
    def test_compose_email_no_schedule(self, mock_get_service, mock_get_credentials):
        """Test compose_email without scheduling."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials

        mock_service = MagicMock()
        mock_service.users().drafts().create().execute.return_value = {
            "id": "draft123",
            "message": {"id": "msg123"}
        }
        mock_get_service.return_value = mock_service

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        compose_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "compose_email":
                compose_email = tool.fn
                break

        assert compose_email is not None, "compose_email tool not found"

        result = compose_email(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test body content"
        )

        assert result["success"] is True
        assert result["draft_id"] == "draft123"
        assert result["confirmation_required"] is True
        assert "scheduled_for" not in result
        assert "event_id" not in result

    @patch("gmail_mcp.mcp.tools.email_send.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_send.get_gmail_service")
    @patch("gmail_mcp.mcp.tools.email_send.get_calendar_service")
    def test_compose_email_with_schedule(self, mock_get_calendar_service, mock_get_service, mock_get_credentials):
        """Test compose_email with send_at scheduling."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials

        # Mock Gmail service
        mock_gmail_service = MagicMock()
        mock_gmail_service.users().drafts().create().execute.return_value = {
            "id": "draft456",
            "message": {"id": "msg456"}
        }
        mock_get_service.return_value = mock_gmail_service

        # Mock Calendar service
        mock_calendar_service = MagicMock()
        mock_calendar_service.events().insert().execute.return_value = {
            "id": "event789",
            "htmlLink": "https://calendar.google.com/event?eid=event789"
        }
        mock_get_calendar_service.return_value = mock_calendar_service

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        compose_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "compose_email":
                compose_email = tool.fn
                break

        result = compose_email(
            to="recipient@example.com",
            subject="Scheduled Email",
            body="This will be scheduled.",
            send_at="tomorrow 8am"
        )

        assert result["success"] is True
        assert result["draft_id"] == "draft456"
        assert "scheduled_for" in result
        assert result["event_id"] == "event789"
        assert "event_link" in result
        assert "next_steps" in result

    @patch("gmail_mcp.mcp.tools.email_send.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_send.get_gmail_service")
    def test_compose_email_invalid_schedule_date(self, mock_get_service, mock_get_credentials):
        """Test compose_email with invalid send_at date."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials

        mock_service = MagicMock()
        mock_service.users().drafts().create().execute.return_value = {
            "id": "draft789",
            "message": {"id": "msg789"}
        }
        mock_get_service.return_value = mock_service

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        compose_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "compose_email":
                compose_email = tool.fn
                break

        result = compose_email(
            to="recipient@example.com",
            subject="Test",
            body="Test",
            send_at="invalid date format xyz"
        )

        # Draft should still be created, but with a warning about date parsing
        assert result["success"] is True
        assert result["draft_id"] == "draft789"
        assert "warning" in result
        assert "event_id" not in result

    @patch("gmail_mcp.mcp.tools.email_send.get_credentials")
    def test_compose_email_not_authenticated(self, mock_get_credentials):
        """Test compose_email when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        compose_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "compose_email":
                compose_email = tool.fn
                break

        result = compose_email(
            to="recipient@example.com",
            subject="Test",
            body="Test"
        )

        assert result["success"] is False
        assert "Not authenticated" in result["error"]

    @patch("gmail_mcp.mcp.tools.email_send.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_send.get_gmail_service")
    def test_compose_email_with_cc_bcc(self, mock_get_service, mock_get_credentials):
        """Test compose_email with CC and BCC recipients."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials

        mock_service = MagicMock()
        mock_service.users().drafts().create().execute.return_value = {
            "id": "draft_cc_bcc",
            "message": {"id": "msg_cc_bcc"}
        }
        mock_get_service.return_value = mock_service

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        compose_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "compose_email":
                compose_email = tool.fn
                break

        result = compose_email(
            to="recipient@example.com",
            subject="Test with CC/BCC",
            body="Test body",
            cc="cc@example.com",
            bcc="bcc@example.com"
        )

        assert result["success"] is True
        assert result["draft_id"] == "draft_cc_bcc"
