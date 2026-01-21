"""
Tests for mcp/tools - Email retention policy tools

Tests for setup_retention_labels, enforce_retention_policies, get_retention_status.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


def create_mock_gmail_service_with_labels():
    """Create a mock Gmail API service for retention operations."""
    service = MagicMock()

    # Mock labels - include retention labels
    labels_data = {
        "labels": [
            {"id": "Label_1", "name": "Retention", "type": "user"},
            {"id": "Label_2", "name": "Retention/7-days", "type": "user"},
            {"id": "Label_3", "name": "Retention/30-days", "type": "user"},
            {"id": "Label_4", "name": "Retention/90-days", "type": "user"},
            {"id": "Label_5", "name": "Retention/6-months", "type": "user"},
            {"id": "Label_6", "name": "Retention/1-year", "type": "user"},
            {"id": "Label_7", "name": "Retention/3-years", "type": "user"},
            {"id": "Label_8", "name": "Retention/7-years", "type": "user"},
            {"id": "Label_9", "name": "Retention/INDEF", "type": "user"},
            {"id": "INBOX", "name": "INBOX", "type": "system"},
        ]
    }

    service.users().labels().list().execute.return_value = labels_data

    # Mock messages list - return some results
    service.users().messages().list().execute.return_value = {
        "messages": [{"id": f"msg{i:03d}"} for i in range(5)],
        "resultSizeEstimate": 5
    }

    # Mock batch modify
    service.users().messages().batchModify().execute.return_value = None

    return service


def create_mock_gmail_service_no_labels():
    """Create a mock Gmail API service with no retention labels."""
    service = MagicMock()

    # No retention labels
    labels_data = {
        "labels": [
            {"id": "INBOX", "name": "INBOX", "type": "system"},
            {"id": "SENT", "name": "SENT", "type": "system"},
        ]
    }

    service.users().labels().list().execute.return_value = labels_data

    # Mock label creation
    def mock_create_label(*args, **kwargs):
        result = MagicMock()
        body = kwargs.get("body", {})
        result.execute.return_value = {
            "id": f"Label_new_{body.get('name', 'unknown')}",
            "name": body.get("name", "unknown")
        }
        return result

    service.users().labels().create = mock_create_label

    return service


class TestSetupRetentionLabels:
    """Tests for setup_retention_labels tool."""

    @patch("gmail_mcp.mcp.tools.email_retention.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_retention.get_gmail_service")
    def test_setup_retention_labels_creates_missing(self, mock_get_service, mock_get_credentials):
        """Test that setup creates missing retention labels."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service_no_labels()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        setup_retention_labels = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "setup_retention_labels":
                setup_retention_labels = tool.fn
                break

        assert setup_retention_labels is not None

        result = setup_retention_labels()

        assert result["success"] is True
        assert len(result["created"]) > 0
        assert "Retention/7-days" in result["created"]

    @patch("gmail_mcp.mcp.tools.email_retention.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_retention.get_gmail_service")
    def test_setup_retention_labels_skips_existing(self, mock_get_service, mock_get_credentials):
        """Test that setup skips existing labels."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service_with_labels()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        setup_retention_labels = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "setup_retention_labels":
                setup_retention_labels = tool.fn
                break

        result = setup_retention_labels()

        assert result["success"] is True
        assert len(result["existing"]) > 0
        assert len(result["created"]) == 0

    @patch("gmail_mcp.mcp.tools.email_retention.get_credentials")
    def test_setup_retention_labels_not_authenticated(self, mock_get_credentials):
        """Test setup_retention_labels when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        setup_retention_labels = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "setup_retention_labels":
                setup_retention_labels = tool.fn
                break

        result = setup_retention_labels()

        assert result["success"] is False
        assert "Not authenticated" in result["error"]


class TestEnforceRetentionPolicies:
    """Tests for enforce_retention_policies tool."""

    @patch("gmail_mcp.mcp.tools.email_retention.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_retention.get_gmail_service")
    def test_enforce_dry_run(self, mock_get_service, mock_get_credentials):
        """Test enforce_retention_policies in dry run mode."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service_with_labels()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        enforce_retention = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "enforce_retention_policies":
                enforce_retention = tool.fn
                break

        assert enforce_retention is not None

        result = enforce_retention(dry_run=True)

        assert result["success"] is True
        assert result["dry_run"] is True
        assert "summary" in result
        assert "by_label" in result

    @patch("gmail_mcp.mcp.tools.email_retention.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_retention.get_gmail_service")
    def test_enforce_actual_deletion(self, mock_get_service, mock_get_credentials):
        """Test enforce_retention_policies with actual deletion."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service_with_labels()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        enforce_retention = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "enforce_retention_policies":
                enforce_retention = tool.fn
                break

        result = enforce_retention(dry_run=False)

        assert result["success"] is True
        assert result["dry_run"] is False
        assert "summary" in result
        assert result["summary"]["total_processed"] >= 0

    @patch("gmail_mcp.mcp.tools.email_retention.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_retention.get_gmail_service")
    def test_enforce_handles_missing_labels(self, mock_get_service, mock_get_credentials):
        """Test enforce_retention_policies handles missing labels gracefully."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service_no_labels()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        enforce_retention = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "enforce_retention_policies":
                enforce_retention = tool.fn
                break

        result = enforce_retention(dry_run=True)

        assert result["success"] is True
        # All labels should be skipped since they don't exist
        for label_name, label_result in result["by_label"].items():
            assert label_result["status"] == "skipped"

    @patch("gmail_mcp.mcp.tools.email_retention.get_credentials")
    def test_enforce_not_authenticated(self, mock_get_credentials):
        """Test enforce_retention_policies when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        enforce_retention = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "enforce_retention_policies":
                enforce_retention = tool.fn
                break

        result = enforce_retention()

        assert result["success"] is False
        assert "Not authenticated" in result["error"]


class TestGetRetentionStatus:
    """Tests for get_retention_status tool."""

    @patch("gmail_mcp.mcp.tools.email_retention.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_retention.get_gmail_service")
    def test_get_retention_status_success(self, mock_get_service, mock_get_credentials):
        """Test successful retention status retrieval."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service_with_labels()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_status = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_retention_status":
                get_status = tool.fn
                break

        assert get_status is not None

        result = get_status()

        assert result["success"] is True
        assert "summary" in result
        assert "by_label" in result
        assert "Retention/7-days" in result["by_label"]
        assert result["by_label"]["Retention/7-days"]["exists"] is True

    @patch("gmail_mcp.mcp.tools.email_retention.get_credentials")
    @patch("gmail_mcp.mcp.tools.email_retention.get_gmail_service")
    def test_get_retention_status_missing_labels(self, mock_get_service, mock_get_credentials):
        """Test get_retention_status when labels don't exist."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_gmail_service_no_labels()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_status = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_retention_status":
                get_status = tool.fn
                break

        result = get_status()

        assert result["success"] is True
        # All labels should show exists=False
        for label_name, label_result in result["by_label"].items():
            assert label_result["exists"] is False

    @patch("gmail_mcp.mcp.tools.email_retention.get_credentials")
    def test_get_retention_status_not_authenticated(self, mock_get_credentials):
        """Test get_retention_status when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_status = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_retention_status":
                get_status = tool.fn
                break

        result = get_status()

        assert result["success"] is False
        assert "Not authenticated" in result["error"]
