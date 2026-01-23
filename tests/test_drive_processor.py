"""
Tests for Drive MCP processor.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestDriveProcessorFileOperations:
    """Tests for file operations."""

    @patch("drive_mcp.drive.processor.build")
    @patch("drive_mcp.drive.processor.get_credentials")
    def test_list_files_success(self, mock_creds, mock_build):
        """Test listing files in a folder."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.files().list().execute.return_value = {
            "files": [
                {"id": "file1", "name": "test.txt", "mimeType": "text/plain"},
                {"id": "file2", "name": "doc.docx", "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
            ],
            "nextPageToken": None,
        }

        from drive_mcp.drive.processor import DriveProcessor
        processor = DriveProcessor()

        result = processor.list_files()

        assert "files" in result
        assert len(result["files"]) == 2

    @patch("drive_mcp.drive.processor.build")
    @patch("drive_mcp.drive.processor.get_credentials")
    def test_search_files_success(self, mock_creds, mock_build):
        """Test searching for files."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.files().list().execute.return_value = {
            "files": [
                {"id": "file1", "name": "report.pdf", "mimeType": "application/pdf"},
            ],
            "nextPageToken": None,
        }

        from drive_mcp.drive.processor import DriveProcessor
        processor = DriveProcessor()

        result = processor.search_files("name contains 'report'")

        assert "files" in result
        assert len(result["files"]) == 1
        assert result["files"][0]["name"] == "report.pdf"

    @patch("drive_mcp.drive.processor.build")
    @patch("drive_mcp.drive.processor.get_credentials")
    def test_get_file_success(self, mock_creds, mock_build):
        """Test getting file metadata."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.files().get().execute.return_value = {
            "id": "file1",
            "name": "test.txt",
            "mimeType": "text/plain",
            "size": "1024",
            "modifiedTime": "2026-01-22T10:00:00Z",
        }

        from drive_mcp.drive.processor import DriveProcessor
        processor = DriveProcessor()

        result = processor.get_file("file1")

        assert result["id"] == "file1"
        assert result["name"] == "test.txt"

    @patch("drive_mcp.drive.processor.build")
    @patch("drive_mcp.drive.processor.get_credentials")
    def test_create_folder_success(self, mock_creds, mock_build):
        """Test creating a folder."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.files().create().execute.return_value = {
            "id": "folder1",
            "name": "New Folder",
            "mimeType": "application/vnd.google-apps.folder",
        }

        from drive_mcp.drive.processor import DriveProcessor
        processor = DriveProcessor()

        result = processor.create_folder("New Folder")

        assert result["name"] == "New Folder"
        assert "folder" in result["mimeType"]

    @patch("drive_mcp.drive.processor.build")
    @patch("drive_mcp.drive.processor.get_credentials")
    def test_trash_file_success(self, mock_creds, mock_build):
        """Test trashing a file."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.files().update().execute.return_value = {
            "id": "file1",
            "trashed": True,
        }

        from drive_mcp.drive.processor import DriveProcessor
        processor = DriveProcessor()

        result = processor.trash_file("file1")

        assert "success" in result or result.get("trashed") is True


class TestDriveProcessorSharing:
    """Tests for sharing operations."""

    @patch("drive_mcp.drive.processor.build")
    @patch("drive_mcp.drive.processor.get_credentials")
    def test_get_permissions_success(self, mock_creds, mock_build):
        """Test getting file permissions."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.permissions().list().execute.return_value = {
            "permissions": [
                {"id": "perm1", "role": "owner", "type": "user", "emailAddress": "owner@example.com"},
                {"id": "perm2", "role": "reader", "type": "user", "emailAddress": "viewer@example.com"},
            ],
        }

        from drive_mcp.drive.processor import DriveProcessor
        processor = DriveProcessor()

        result = processor.get_permissions("file1")

        # Result is a list of permissions
        assert isinstance(result, list)
        assert len(result) == 2

    @patch("drive_mcp.drive.processor.build")
    @patch("drive_mcp.drive.processor.get_credentials")
    def test_share_file_success(self, mock_creds, mock_build):
        """Test sharing a file."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.permissions().create().execute.return_value = {
            "id": "perm_new",
            "role": "reader",
            "type": "user",
            "emailAddress": "newuser@example.com",
        }

        from drive_mcp.drive.processor import DriveProcessor
        processor = DriveProcessor()

        result = processor.share_file("file1", email="newuser@example.com", role="reader")

        assert "success" in result or result.get("role") == "reader"


class TestDriveProcessorQuota:
    """Tests for quota operations."""

    @patch("drive_mcp.drive.processor.build")
    @patch("drive_mcp.drive.processor.get_credentials")
    def test_get_quota_success(self, mock_creds, mock_build):
        """Test getting storage quota."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.about().get().execute.return_value = {
            "storageQuota": {
                "limit": "15000000000",
                "usage": "5000000000",
                "usageInDrive": "3000000000",
                "usageInDriveTrash": "100000000",
            },
        }

        from drive_mcp.drive.processor import DriveProcessor
        processor = DriveProcessor()

        result = processor.get_quota()

        # Result has quota nested under "quota" key
        assert "quota" in result
        assert "limit" in result["quota"] or "usage" in result["quota"]


class TestDriveProcessorWorkspaceFiles:
    """Tests for Google Workspace file operations."""

    @patch("drive_mcp.drive.processor.build")
    @patch("drive_mcp.drive.processor.get_credentials")
    def test_create_google_doc_success(self, mock_creds, mock_build):
        """Test creating a Google Doc."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.files().create().execute.return_value = {
            "id": "doc1",
            "name": "New Document",
            "mimeType": "application/vnd.google-apps.document",
        }

        from drive_mcp.drive.processor import DriveProcessor
        processor = DriveProcessor()

        result = processor.create_google_doc("New Document")

        assert result["name"] == "New Document"
        assert "document" in result["mimeType"]

    @patch("drive_mcp.drive.processor.build")
    @patch("drive_mcp.drive.processor.get_credentials")
    def test_create_google_sheet_success(self, mock_creds, mock_build):
        """Test creating a Google Sheet."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.files().create().execute.return_value = {
            "id": "sheet1",
            "name": "New Spreadsheet",
            "mimeType": "application/vnd.google-apps.spreadsheet",
        }

        from drive_mcp.drive.processor import DriveProcessor
        processor = DriveProcessor()

        result = processor.create_google_sheet("New Spreadsheet")

        assert result["name"] == "New Spreadsheet"
        assert "spreadsheet" in result["mimeType"]


class TestDriveMcpTools:
    """Tests for drive-mcp tool registration."""

    def test_tools_registered(self):
        """Test that all tools are registered."""
        from drive_mcp.main import mcp

        tools = list(mcp._tool_manager._tools.keys())

        # Verify expected tools exist
        expected_tools = [
            "list_drive_files",
            "search_drive_files",
            "get_drive_file",
            "create_drive_folder",
            "share_drive_file",
            "get_drive_quota",
            "create_google_doc",
        ]

        for tool in expected_tools:
            assert tool in tools, f"Missing tool: {tool}"

    def test_tool_count(self):
        """Test that we have the expected number of tools."""
        from drive_mcp.main import mcp

        tools = list(mcp._tool_manager._tools.keys())
        assert len(tools) == 43, f"Expected 43 tools, got {len(tools)}"
