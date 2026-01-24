"""
Pytest configuration and fixtures for Gmail MCP tests.

IMPORTANT: Patches must target functions WHERE THEY ARE USED (imported), not
where they are defined. Each tool module imports get_gmail_service at module
level, so patch the import location:

    For email_read tools:
        @patch("gmail_mcp.mcp.tools.email_read.get_credentials")
        @patch("gmail_mcp.mcp.tools.email_read.get_gmail_service")

    For email_send tools:
        @patch("gmail_mcp.mcp.tools.email_send.get_credentials")
        @patch("gmail_mcp.mcp.tools.email_send.get_gmail_service")

    For email_manage tools:
        @patch("gmail_mcp.mcp.tools.email_manage.get_credentials")
        @patch("gmail_mcp.mcp.tools.email_manage.get_gmail_service")

    For labels tools:
        @patch("gmail_mcp.mcp.tools.labels.get_credentials")
        @patch("gmail_mcp.mcp.tools.labels.get_gmail_service")

    For attachments tools:
        @patch("gmail_mcp.mcp.tools.attachments.get_credentials")
        @patch("gmail_mcp.mcp.tools.attachments.get_gmail_service")

    For bulk tools:
        @patch("gmail_mcp.mcp.tools.bulk.get_credentials")
        @patch("gmail_mcp.mcp.tools.bulk.get_gmail_service")

    For calendar tools:
        @patch("gmail_mcp.mcp.tools.calendar.get_credentials")
        @patch("gmail_mcp.mcp.tools.calendar.get_calendar_service")

    For filter tools:
        @patch("gmail_mcp.mcp.tools.filters.get_credentials")
        @patch("gmail_mcp.mcp.tools.filters.get_gmail_service")

    For vault tools:
        @patch("gmail_mcp.mcp.tools.vault.get_credentials")
        @patch("gmail_mcp.mcp.tools.vault.get_gmail_service")

    For conflict tools:
        @patch("gmail_mcp.mcp.tools.conflict.get_credentials")
        @patch("gmail_mcp.mcp.tools.conflict.get_calendar_service")
"""

import os
import pytest
from unittest.mock import Mock, MagicMock, patch


@pytest.fixture(autouse=True)
def set_test_encryption_key(tmp_path, monkeypatch):
    """
    Set TOKEN_ENCRYPTION_KEY for all tests and reset token manager singleton.

    This ensures tests don't fail due to missing encryption key.
    """
    # Set encryption key in environment
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "test_encryption_key_for_pytest")

    # Reset the token manager singleton before each test
    import gmail_mcp.auth.token_manager as tm_module
    tm_module._instance = None

    yield

    # Reset singleton after test
    tm_module._instance = None


# Common mock creators
def create_mock_gmail_service():
    """Create a mock Gmail API service."""
    service = MagicMock()
    return service


def create_mock_calendar_service():
    """Create a mock Calendar API service."""
    service = MagicMock()
    return service


@pytest.fixture(autouse=True)
def clear_service_cache_fixture():
    """Clear the service cache before each test to prevent test pollution."""
    from gmail_mcp.utils.services import clear_service_cache
    clear_service_cache()
    yield
    clear_service_cache()


@pytest.fixture
def mock_credentials():
    """Fixture providing mock credentials."""
    return Mock()


@pytest.fixture
def mock_gmail_service():
    """Fixture providing a mock Gmail service."""
    return create_mock_gmail_service()


@pytest.fixture
def mock_calendar_service():
    """Fixture providing a mock Calendar service."""
    return create_mock_calendar_service()
