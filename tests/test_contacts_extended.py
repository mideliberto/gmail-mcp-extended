"""
Tests for extended contact tools (hygiene, CRUD, groups).
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from mcp.server.fastmcp import FastMCP


def get_tool(name: str):
    """Helper to get a tool function from the MCP instance."""
    from gmail_mcp.mcp.tools.contacts import setup_contact_tools
    mcp = FastMCP("test")
    setup_contact_tools(mcp)
    return mcp._tool_manager._tools[name].fn


# Mock config that enables contacts API
def mock_config():
    config = MagicMock()
    config.get.return_value = True
    config.contacts_api_enabled = True
    return config


class TestFindDuplicateContacts:
    """Tests for find_duplicate_contacts tool."""

    @patch("gmail_mcp.mcp.tools.contacts.get_config", mock_config)
    @patch("gmail_mcp.mcp.tools.contacts.get_credentials")
    @patch("gmail_mcp.mcp.tools.contacts.get_people_service")
    def test_find_duplicates_exact_email_match(self, mock_people, mock_creds):
        """Test finding duplicates with exact email match."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_people.return_value = mock_service

        # Two contacts with same email
        mock_service.people().connections().list().execute.return_value = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "John Doe"}],
                    "emailAddresses": [{"value": "john@example.com"}],
                },
                {
                    "resourceName": "people/c2",
                    "names": [{"displayName": "Johnny Doe"}],
                    "emailAddresses": [{"value": "john@example.com"}],
                },
            ]
        }

        find_duplicate_contacts = get_tool("find_duplicate_contacts")
        result = find_duplicate_contacts(threshold=0.8, max_results=50)

        assert result["success"] is True
        assert len(result["duplicate_groups"]) >= 1

    @patch("gmail_mcp.mcp.tools.contacts.get_credentials")
    def test_find_duplicates_not_authenticated(self, mock_creds):
        """Test that unauthenticated request returns error."""
        mock_creds.return_value = None

        find_duplicate_contacts = get_tool("find_duplicate_contacts")
        result = find_duplicate_contacts()

        assert result["success"] is False
        # May say "not authenticated" or "contacts api not enabled"
        assert "error" in result


class TestFindStaleContacts:
    """Tests for find_stale_contacts tool."""

    @patch("gmail_mcp.mcp.tools.contacts.get_config", mock_config)
    @patch("gmail_mcp.mcp.tools.contacts.get_credentials")
    @patch("gmail_mcp.mcp.tools.contacts.get_people_service")
    @patch("gmail_mcp.mcp.tools.contacts.get_gmail_service")
    def test_find_stale_contacts_success(self, mock_gmail, mock_people, mock_creds):
        """Test finding stale contacts."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_people.return_value = mock_service

        # Contact with email
        mock_service.people().connections().list().execute.return_value = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "Old Contact"}],
                    "emailAddresses": [{"value": "old@example.com"}],
                },
            ]
        }

        # No recent email activity
        mock_gmail_service = MagicMock()
        mock_gmail.return_value = mock_gmail_service
        mock_gmail_service.users().messages().list().execute.return_value = {
            "messages": []
        }

        find_stale_contacts = get_tool("find_stale_contacts")
        result = find_stale_contacts(months=12, max_results=100)

        assert result["success"] is True
        assert "stale_contacts" in result

    @patch("gmail_mcp.mcp.tools.contacts.get_credentials")
    def test_find_stale_not_authenticated(self, mock_creds):
        """Test unauthenticated request."""
        mock_creds.return_value = None

        find_stale_contacts = get_tool("find_stale_contacts")
        result = find_stale_contacts()

        assert result["success"] is False


class TestFindIncompleteContacts:
    """Tests for find_incomplete_contacts tool."""

    @patch("gmail_mcp.mcp.tools.contacts.get_config", mock_config)
    @patch("gmail_mcp.mcp.tools.contacts.get_credentials")
    @patch("gmail_mcp.mcp.tools.contacts.get_people_service")
    def test_find_incomplete_missing_email(self, mock_people, mock_creds):
        """Test finding contacts missing email."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_people.return_value = mock_service

        mock_service.people().connections().list().execute.return_value = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "No Email Person"}],
                    # No emailAddresses
                },
            ]
        }

        find_incomplete_contacts = get_tool("find_incomplete_contacts")
        result = find_incomplete_contacts(require_email=True, require_phone=False)

        assert result["success"] is True
        assert len(result["incomplete_contacts"]) == 1
        assert "email" in result["incomplete_contacts"][0]["missing_fields"]

    @patch("gmail_mcp.mcp.tools.contacts.get_credentials")
    def test_find_incomplete_not_authenticated(self, mock_creds):
        """Test unauthenticated request."""
        mock_creds.return_value = None

        find_incomplete_contacts = get_tool("find_incomplete_contacts")
        result = find_incomplete_contacts()

        assert result["success"] is False


class TestExportContacts:
    """Tests for export_contacts tool."""

    @patch("gmail_mcp.mcp.tools.contacts.get_config", mock_config)
    @patch("gmail_mcp.mcp.tools.contacts.get_credentials")
    @patch("gmail_mcp.mcp.tools.contacts.get_people_service")
    def test_export_contacts_csv(self, mock_people, mock_creds, tmp_path):
        """Test exporting contacts to CSV."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_people.return_value = mock_service

        mock_service.people().connections().list().execute.return_value = {
            "connections": [
                {
                    "resourceName": "people/c1",
                    "names": [{"displayName": "Test User"}],
                    "emailAddresses": [{"value": "test@example.com"}],
                    "phoneNumbers": [{"value": "555-1234"}],
                },
            ]
        }

        output_file = tmp_path / "contacts.csv"

        export_contacts = get_tool("export_contacts")
        result = export_contacts(file_path=str(output_file), format="csv")

        assert result["success"] is True
        assert output_file.exists()
        content = output_file.read_text()
        assert "Test User" in content
        assert "test@example.com" in content

    @patch("gmail_mcp.mcp.tools.contacts.get_credentials")
    def test_export_contacts_not_authenticated(self, mock_creds):
        """Test unauthenticated request."""
        mock_creds.return_value = None

        export_contacts = get_tool("export_contacts")
        result = export_contacts(file_path="/tmp/test.csv")

        assert result["success"] is False


class TestContactCRUD:
    """Tests for contact CRUD operations."""

    @patch("gmail_mcp.mcp.tools.contacts.get_config", mock_config)
    @patch("gmail_mcp.mcp.tools.contacts.get_credentials")
    @patch("gmail_mcp.mcp.tools.contacts.get_people_service")
    def test_create_contact_success(self, mock_people, mock_creds):
        """Test creating a contact."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_people.return_value = mock_service

        mock_service.people().createContact().execute.return_value = {
            "resourceName": "people/c123",
            "names": [{"displayName": "New Contact"}],
            "emailAddresses": [{"value": "new@example.com"}],
        }

        create_contact = get_tool("create_contact")
        result = create_contact(
            name="New Contact",
            email="new@example.com",
            phone="555-0000"
        )

        assert result["success"] is True
        assert "contact" in result

    @patch("gmail_mcp.mcp.tools.contacts.get_config", mock_config)
    @patch("gmail_mcp.mcp.tools.contacts.get_credentials")
    @patch("gmail_mcp.mcp.tools.contacts.get_people_service")
    def test_update_contact_success(self, mock_people, mock_creds):
        """Test updating a contact."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_people.return_value = mock_service

        mock_service.people().get().execute.return_value = {
            "resourceName": "people/c123",
            "etag": "abc123",
            "names": [{"displayName": "Old Name"}],
        }

        mock_service.people().updateContact().execute.return_value = {
            "resourceName": "people/c123",
            "names": [{"displayName": "New Name"}],
        }

        update_contact = get_tool("update_contact")
        result = update_contact(
            resource_name="people/c123",
            name="New Name"
        )

        assert result["success"] is True

    @patch("gmail_mcp.mcp.tools.contacts.get_config", mock_config)
    @patch("gmail_mcp.mcp.tools.contacts.get_credentials")
    @patch("gmail_mcp.mcp.tools.contacts.get_people_service")
    def test_delete_contact_success(self, mock_people, mock_creds):
        """Test deleting a contact."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_people.return_value = mock_service

        mock_service.people().deleteContact().execute.return_value = {}

        delete_contact = get_tool("delete_contact")
        result = delete_contact(resource_name="people/c123")

        assert result["success"] is True

    @patch("gmail_mcp.mcp.tools.contacts.get_credentials")
    def test_create_contact_not_authenticated(self, mock_creds):
        """Test unauthenticated request."""
        mock_creds.return_value = None

        create_contact = get_tool("create_contact")
        result = create_contact(name="Test")

        assert result["success"] is False


class TestContactGroups:
    """Tests for contact group operations."""

    @patch("gmail_mcp.mcp.tools.contacts.get_config", mock_config)
    @patch("gmail_mcp.mcp.tools.contacts.get_credentials")
    @patch("gmail_mcp.mcp.tools.contacts.get_people_service")
    def test_list_contact_groups_success(self, mock_people, mock_creds):
        """Test listing contact groups."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_people.return_value = mock_service

        mock_service.contactGroups().list().execute.return_value = {
            "contactGroups": [
                {"resourceName": "contactGroups/123", "name": "Work"},
                {"resourceName": "contactGroups/456", "name": "Family"},
            ]
        }

        list_contact_groups = get_tool("list_contact_groups")
        result = list_contact_groups()

        assert result["success"] is True
        assert len(result["groups"]) == 2

    @patch("gmail_mcp.mcp.tools.contacts.get_config", mock_config)
    @patch("gmail_mcp.mcp.tools.contacts.get_credentials")
    @patch("gmail_mcp.mcp.tools.contacts.get_people_service")
    def test_create_contact_group_success(self, mock_people, mock_creds):
        """Test creating a contact group."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_people.return_value = mock_service

        mock_service.contactGroups().create().execute.return_value = {
            "resourceName": "contactGroups/789",
            "name": "New Group",
        }

        create_contact_group = get_tool("create_contact_group")
        result = create_contact_group(name="New Group")

        assert result["success"] is True
        assert result["group"]["name"] == "New Group"

    @patch("gmail_mcp.mcp.tools.contacts.get_credentials")
    def test_list_groups_not_authenticated(self, mock_creds):
        """Test unauthenticated request."""
        mock_creds.return_value = None

        list_contact_groups = get_tool("list_contact_groups")
        result = list_contact_groups()

        assert result["success"] is False


class TestMergeContacts:
    """Tests for merge_contacts tool."""

    @patch("gmail_mcp.mcp.tools.contacts.get_config", mock_config)
    @patch("gmail_mcp.mcp.tools.contacts.get_credentials")
    @patch("gmail_mcp.mcp.tools.contacts.get_people_service")
    def test_merge_contacts_dry_run(self, mock_people, mock_creds):
        """Test merge contacts in dry run mode."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_people.return_value = mock_service

        # Mock getting contacts to merge
        def get_side_effect(resourceName, personFields):
            mock_response = MagicMock()
            if 'c1' in resourceName:
                mock_response.execute.return_value = {
                    "resourceName": "people/c1",
                    "etag": "etag1",
                    "names": [{"displayName": "John Doe"}],
                    "emailAddresses": [{"value": "john@example.com"}],
                }
            else:
                mock_response.execute.return_value = {
                    "resourceName": "people/c2",
                    "etag": "etag2",
                    "names": [{"displayName": "Johnny D"}],
                    "phoneNumbers": [{"value": "555-1234"}],
                }
            return mock_response

        mock_service.people().get.side_effect = get_side_effect

        merge_contacts = get_tool("merge_contacts")
        result = merge_contacts(
            resource_names=["people/c1", "people/c2"],
            dry_run=True
        )

        assert result["success"] is True
        assert result["dry_run"] is True
        assert "merged_preview" in result

    @patch("gmail_mcp.mcp.tools.contacts.get_credentials")
    def test_merge_contacts_not_authenticated(self, mock_creds):
        """Test unauthenticated request."""
        mock_creds.return_value = None

        merge_contacts = get_tool("merge_contacts")
        result = merge_contacts(resource_names=["people/c1", "people/c2"])

        assert result["success"] is False
