"""
Tests for subscription management tools.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from mcp.server.fastmcp import FastMCP


def get_tool(name: str):
    """Helper to get a tool function from the MCP instance."""
    from gmail_mcp.mcp.tools.subscriptions import setup_subscription_tools
    mcp = FastMCP("test")
    setup_subscription_tools(mcp)
    return mcp._tool_manager._tools[name].fn


class TestSetupSubscriptionLabels:
    """Tests for setup_subscription_labels tool."""

    @patch("gmail_mcp.mcp.tools.subscriptions.get_credentials")
    @patch("gmail_mcp.mcp.tools.subscriptions.get_gmail_service")
    def test_setup_labels_creates_labels(self, mock_gmail, mock_creds):
        """Test that setup creates subscription labels."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_gmail.return_value = mock_service

        # Mock existing labels (none of our subscription labels exist)
        mock_service.users().labels().list().execute.return_value = {
            "labels": [
                {"id": "INBOX", "name": "INBOX"},
            ]
        }

        # Mock label creation
        mock_service.users().labels().create().execute.return_value = {
            "id": "Label_123",
            "name": "Subscriptions/Review",
        }

        setup_subscription_labels = get_tool("setup_subscription_labels")
        result = setup_subscription_labels()

        assert result["success"] is True

    @patch("gmail_mcp.mcp.tools.subscriptions.get_credentials")
    def test_setup_labels_not_authenticated(self, mock_creds):
        """Test unauthenticated request."""
        mock_creds.return_value = None

        setup_subscription_labels = get_tool("setup_subscription_labels")
        result = setup_subscription_labels()

        assert result["success"] is False


class TestFindSubscriptionEmails:
    """Tests for find_subscription_emails tool."""

    @patch("gmail_mcp.mcp.tools.subscriptions.get_credentials")
    @patch("gmail_mcp.mcp.tools.subscriptions.get_gmail_service")
    def test_find_subscriptions_success(self, mock_gmail, mock_creds):
        """Test finding subscription emails."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_gmail.return_value = mock_service

        # Mock search results
        mock_service.users().messages().list().execute.return_value = {
            "messages": [
                {"id": "msg1"},
                {"id": "msg2"},
            ]
        }

        # Mock getting message details with unsubscribe header
        mock_service.users().messages().get().execute.return_value = {
            "id": "msg1",
            "payload": {
                "headers": [
                    {"name": "From", "value": "newsletter@company.com"},
                    {"name": "List-Unsubscribe", "value": "<https://unsubscribe.example.com>"},
                ]
            }
        }

        find_subscription_emails = get_tool("find_subscription_emails")
        result = find_subscription_emails(max_results=10)

        assert result["success"] is True
        # Result uses 'subscriptions' key
        assert "subscriptions" in result

    @patch("gmail_mcp.mcp.tools.subscriptions.get_credentials")
    def test_find_subscriptions_not_authenticated(self, mock_creds):
        """Test unauthenticated request."""
        mock_creds.return_value = None

        find_subscription_emails = get_tool("find_subscription_emails")
        result = find_subscription_emails()

        assert result["success"] is False


class TestGetUnsubscribeLink:
    """Tests for get_unsubscribe_link tool."""

    @patch("gmail_mcp.mcp.tools.subscriptions.get_credentials")
    @patch("gmail_mcp.mcp.tools.subscriptions.get_gmail_service")
    def test_get_link_from_header(self, mock_gmail, mock_creds):
        """Test extracting unsubscribe link from header."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_gmail.return_value = mock_service

        mock_service.users().messages().get().execute.return_value = {
            "id": "msg1",
            "payload": {
                "headers": [
                    {"name": "List-Unsubscribe", "value": "<https://unsubscribe.example.com/abc123>"},
                ],
                "body": {"data": ""}
            }
        }

        get_unsubscribe_link = get_tool("get_unsubscribe_link")
        result = get_unsubscribe_link(email_id="msg1")

        assert result["success"] is True
        assert "unsubscribe.example.com" in result["unsubscribe_link"]

    @patch("gmail_mcp.mcp.tools.subscriptions.get_credentials")
    @patch("gmail_mcp.mcp.tools.subscriptions.get_gmail_service")
    def test_get_link_no_link_found(self, mock_gmail, mock_creds):
        """Test when no unsubscribe link is found."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_gmail.return_value = mock_service

        mock_service.users().messages().get().execute.return_value = {
            "id": "msg1",
            "payload": {
                "headers": [
                    {"name": "From", "value": "someone@example.com"},
                ],
                "body": {"data": "SGVsbG8gV29ybGQ="}  # "Hello World"
            }
        }

        get_unsubscribe_link = get_tool("get_unsubscribe_link")
        result = get_unsubscribe_link(email_id="msg1")

        # Should either fail or return None for the link
        assert result["success"] is False or result.get("unsubscribe_link") is None

    @patch("gmail_mcp.mcp.tools.subscriptions.get_credentials")
    def test_get_link_not_authenticated(self, mock_creds):
        """Test unauthenticated request."""
        mock_creds.return_value = None

        get_unsubscribe_link = get_tool("get_unsubscribe_link")
        result = get_unsubscribe_link(email_id="msg1")

        assert result["success"] is False


class TestUnsubscribeAndCleanup:
    """Tests for unsubscribe_and_cleanup tool."""

    @patch("gmail_mcp.mcp.tools.subscriptions.get_credentials")
    @patch("gmail_mcp.mcp.tools.subscriptions.get_gmail_service")
    def test_unsubscribe_workflow(self, mock_gmail, mock_creds):
        """Test full unsubscribe workflow."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_gmail.return_value = mock_service

        # Mock finding emails from sender
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }

        # Mock getting message with unsubscribe link
        mock_service.users().messages().get().execute.return_value = {
            "id": "msg1",
            "payload": {
                "headers": [
                    {"name": "From", "value": "newsletter@spam.com"},
                    {"name": "List-Unsubscribe", "value": "<https://unsubscribe.spam.com>"},
                ]
            }
        }

        # Mock label list for filter creation
        mock_service.users().labels().list().execute.return_value = {
            "labels": [
                {"id": "Label_Sub", "name": "Subscriptions/Unsubscribed"},
            ]
        }

        # Mock filter creation
        mock_service.users().settings().filters().create().execute.return_value = {
            "id": "filter123"
        }

        unsubscribe_and_cleanup = get_tool("unsubscribe_and_cleanup")
        result = unsubscribe_and_cleanup(from_address="newsletter@spam.com")

        assert result["success"] is True
        assert "unsubscribe_link" in result

    @patch("gmail_mcp.mcp.tools.subscriptions.get_credentials")
    def test_unsubscribe_not_authenticated(self, mock_creds):
        """Test unauthenticated request."""
        mock_creds.return_value = None

        unsubscribe_and_cleanup = get_tool("unsubscribe_and_cleanup")
        result = unsubscribe_and_cleanup(from_address="test@example.com")

        assert result["success"] is False


class TestCreateSubscriptionFilter:
    """Tests for create_subscription_filter tool."""

    @patch("gmail_mcp.mcp.tools.subscriptions.get_credentials")
    @patch("gmail_mcp.mcp.tools.subscriptions.get_gmail_service")
    def test_create_filter_retain(self, mock_gmail, mock_creds):
        """Test creating retain filter for subscription."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_gmail.return_value = mock_service

        mock_service.users().labels().list().execute.return_value = {
            "labels": [
                {"id": "Label_Retained", "name": "Subscriptions/Retained"},
            ]
        }

        mock_service.users().settings().filters().create().execute.return_value = {
            "id": "filter456",
            "criteria": {"from": "newsletter@example.com"},
            "action": {"removeLabelIds": ["INBOX"]}
        }

        create_subscription_filter = get_tool("create_subscription_filter")
        result = create_subscription_filter(
            from_address="newsletter@example.com",
            action="retain"  # Use 'retain' not 'archive'
        )

        assert result["success"] is True

    @patch("gmail_mcp.mcp.tools.subscriptions.get_credentials")
    def test_create_filter_not_authenticated(self, mock_creds):
        """Test unauthenticated request."""
        mock_creds.return_value = None

        create_subscription_filter = get_tool("create_subscription_filter")
        result = create_subscription_filter(from_address="test@example.com")

        assert result["success"] is False


class TestMarkSenderAsJunk:
    """Tests for mark_sender_as_junk tool."""

    @patch("gmail_mcp.mcp.tools.subscriptions.get_credentials")
    @patch("gmail_mcp.mcp.tools.subscriptions.get_gmail_service")
    def test_mark_as_junk_success(self, mock_gmail, mock_creds):
        """Test marking sender as junk."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_gmail.return_value = mock_service

        # Mock filter creation
        mock_service.users().settings().filters().create().execute.return_value = {
            "id": "filter789"
        }

        # Mock finding and trashing existing emails
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}, {"id": "msg2"}]
        }

        mock_service.users().messages().batchModify().execute.return_value = {}

        mark_sender_as_junk = get_tool("mark_sender_as_junk")
        result = mark_sender_as_junk(from_address="spammer@junk.com")

        assert result["success"] is True

    @patch("gmail_mcp.mcp.tools.subscriptions.get_credentials")
    def test_mark_as_junk_not_authenticated(self, mock_creds):
        """Test unauthenticated request."""
        mock_creds.return_value = None

        mark_sender_as_junk = get_tool("mark_sender_as_junk")
        result = mark_sender_as_junk(from_address="test@example.com")

        assert result["success"] is False
