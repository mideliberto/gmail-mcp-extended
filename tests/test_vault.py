"""
Tests for mcp/tools/vault.py - Obsidian vault integration tools

These tests mock the Gmail API and filesystem to verify vault functionality.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock


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
        "parts": []
    }
}


def create_mock_gmail_service():
    """Create a mock Gmail API service for vault operations."""
    service = MagicMock()

    # Mock users().messages().get() - handles any kwargs
    def mock_get_message(userId="me", id=None, format=None, metadataHeaders=None):
        mock = MagicMock()
        mock.execute.return_value = SAMPLE_MESSAGE
        return mock

    service.users().messages().get = mock_get_message

    # Mock users().messages().list() - handles any kwargs
    def mock_list_messages(userId="me", q=None, maxResults=None, labelIds=None):
        mock = MagicMock()
        mock.execute.return_value = {
            "messages": [{"id": "msg001"}, {"id": "msg002"}],
        }
        return mock

    service.users().messages().list = mock_list_messages

    return service


class TestSaveEmailToVault:
    """Tests for save_email_to_vault tool."""

    @patch("gmail_mcp.mcp.tools.vault.get_credentials")
    @patch("gmail_mcp.mcp.tools.vault.get_gmail_service")
    def test_save_email_to_vault_success(self, mock_get_service, mock_get_credentials):
        """Test successful email save to vault."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        save_email_to_vault = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "save_email_to_vault":
                save_email_to_vault = tool.fn
                break

        assert save_email_to_vault is not None, "save_email_to_vault tool not found"

        # Create a temporary directory for the vault
        with tempfile.TemporaryDirectory() as temp_dir:
            inbox_folder = os.path.join(temp_dir, "0-inbox")
            os.makedirs(inbox_folder)

            result = save_email_to_vault(
                email_id="msg001",
                vault_path=temp_dir,
                inbox_folder="0-inbox",
                tags=["test", "email"]
            )

            assert result["success"] is True
            assert "file_path" in result

            # Verify file was created
            file_path = result["file_path"]
            assert os.path.exists(file_path)

            # Verify content
            with open(file_path, 'r') as f:
                content = f.read()
                assert "Test Email" in content
                assert "sender@example.com" in content
                assert "email" in content  # tag

    @patch("gmail_mcp.mcp.tools.vault.get_credentials")
    def test_save_email_to_vault_not_authenticated(self, mock_get_credentials):
        """Test save_email_to_vault when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        save_email_to_vault = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "save_email_to_vault":
                save_email_to_vault = tool.fn
                break

        result = save_email_to_vault(email_id="msg001")

        assert "error" in result
        assert "Not authenticated" in result["error"]

    @patch("gmail_mcp.mcp.tools.vault.get_credentials")
    @patch("gmail_mcp.mcp.tools.vault.get_gmail_service")
    def test_save_email_to_vault_no_vault_path(self, mock_get_service, mock_get_credentials):
        """Test save_email_to_vault with no vault path configured."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        save_email_to_vault = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "save_email_to_vault":
                save_email_to_vault = tool.fn
                break

        # Call without vault_path and with no config
        with patch("gmail_mcp.mcp.tools.vault.get_config", return_value={}):
            with patch.dict(os.environ, {}, clear=True):
                result = save_email_to_vault(email_id="msg001")

        assert result["success"] is False
        assert "vault" in result.get("error", "").lower() or "vault_path" in result.get("message", "").lower()


class TestBatchSaveEmailsToVault:
    """Tests for batch_save_emails_to_vault tool."""

    @patch("gmail_mcp.mcp.tools.vault.get_credentials")
    @patch("gmail_mcp.mcp.tools.vault.get_gmail_service")
    def test_batch_save_success(self, mock_get_service, mock_get_credentials):
        """Test successful batch email save to vault."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        batch_save = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "batch_save_emails_to_vault":
                batch_save = tool.fn
                break

        assert batch_save is not None, "batch_save_emails_to_vault tool not found"

        # Create a temporary directory for the vault
        with tempfile.TemporaryDirectory() as temp_dir:
            inbox_folder = os.path.join(temp_dir, "0-inbox")
            os.makedirs(inbox_folder)

            result = batch_save(
                query="from:sender@example.com",
                vault_path=temp_dir,
                inbox_folder="0-inbox",
                max_emails=2
            )

            assert result["success"] is True
            assert result["saved"] >= 1
            assert "saved_details" in result

    @patch("gmail_mcp.mcp.tools.vault.get_credentials")
    def test_batch_save_not_authenticated(self, mock_get_credentials):
        """Test batch_save_emails_to_vault when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        batch_save = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "batch_save_emails_to_vault":
                batch_save = tool.fn
                break

        result = batch_save(query="from:sender@example.com")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestVaultMarkdownFormatting:
    """Tests for vault markdown file formatting."""

    @patch("gmail_mcp.mcp.tools.vault.get_credentials")
    @patch("gmail_mcp.mcp.tools.vault.get_gmail_service")
    def test_frontmatter_format(self, mock_get_service, mock_get_credentials):
        """Test that saved emails have correct frontmatter."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        save_email_to_vault = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "save_email_to_vault":
                save_email_to_vault = tool.fn
                break

        with tempfile.TemporaryDirectory() as temp_dir:
            inbox_folder = os.path.join(temp_dir, "0-inbox")
            os.makedirs(inbox_folder)

            result = save_email_to_vault(
                email_id="msg001",
                vault_path=temp_dir,
                inbox_folder="0-inbox",
                tags=["important", "follow-up"]
            )

            assert result["success"] is True

            with open(result["file_path"], 'r') as f:
                content = f.read()

            # Check frontmatter structure
            assert content.startswith("---")
            assert "type: email" in content
            # Note: frontmatter values are quoted
            assert '"sender@example.com"' in content or "sender@example.com" in content
            assert '"recipient@example.com"' in content or "recipient@example.com" in content
            assert "important" in content
            assert "follow-up" in content
            assert "---" in content[3:]  # Closing frontmatter
