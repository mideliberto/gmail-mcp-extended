"""
MCP Tools Package

This package contains modular tool definitions for the Gmail MCP server.
Each module handles a specific domain of functionality.

Tools are organized into the following modules:
- auth: Authentication (login, logout, check_auth_status)
- email_read: Reading emails (list, search, get, overview)
- email_send: Sending emails (compose, reply, forward, confirm_send)
- email_manage: Managing emails (archive, trash, delete, star, read/unread)
- email_thread: Thread/conversation view (get_thread, get_thread_summary)
- email_drafts: Draft management (list, get, update, delete)
- email_retention: Retention policy enforcement (setup_labels, enforce_policies, get_status)
- labels: Label management (list, create, delete, apply, remove, Claude review labels)
- attachments: Attachment handling (list, download)
- bulk: Bulk operations (bulk_archive, bulk_label, bulk_trash, cleanup_old_emails)
- calendar: Calendar operations (create, list, update, delete, suggest times, detect events)
- filters: Gmail filter management (list, create, delete, Claude review filters)
- vault: Obsidian vault integration (save_email_to_vault, batch_save)
- conflict: Multi-calendar conflict detection (list_calendars, check_conflicts, find_free_time)
- contacts: Google Contacts lookup (list_contacts, search_contacts, get_contact)
- email_settings: Gmail settings (vacation responder)
"""

from mcp.server.fastmcp import FastMCP

from gmail_mcp.mcp.tools.auth import setup_auth_tools
from gmail_mcp.mcp.tools.email_read import setup_email_read_tools
from gmail_mcp.mcp.tools.email_send import setup_email_send_tools
from gmail_mcp.mcp.tools.email_manage import setup_email_manage_tools
from gmail_mcp.mcp.tools.email_thread import setup_email_thread_tools
from gmail_mcp.mcp.tools.email_drafts import setup_email_draft_tools
from gmail_mcp.mcp.tools.email_retention import setup_email_retention_tools
from gmail_mcp.mcp.tools.labels import setup_label_tools
from gmail_mcp.mcp.tools.attachments import setup_attachment_tools
from gmail_mcp.mcp.tools.bulk import setup_bulk_tools
from gmail_mcp.mcp.tools.calendar import setup_calendar_tools
from gmail_mcp.mcp.tools.filters import setup_filter_tools
from gmail_mcp.mcp.tools.vault import setup_vault_tools
from gmail_mcp.mcp.tools.conflict import setup_conflict_tools
from gmail_mcp.mcp.tools.contacts import setup_contact_tools
from gmail_mcp.mcp.tools.email_settings import setup_email_settings_tools


def setup_tools(mcp: FastMCP) -> None:
    """
    Set up all MCP tools on the FastMCP application.

    Args:
        mcp (FastMCP): The FastMCP application.
    """
    setup_auth_tools(mcp)
    setup_email_read_tools(mcp)
    setup_email_send_tools(mcp)
    setup_email_manage_tools(mcp)
    setup_email_thread_tools(mcp)
    setup_email_draft_tools(mcp)
    setup_email_retention_tools(mcp)
    setup_label_tools(mcp)
    setup_attachment_tools(mcp)
    setup_bulk_tools(mcp)
    setup_calendar_tools(mcp)
    setup_filter_tools(mcp)
    setup_vault_tools(mcp)
    setup_conflict_tools(mcp)
    setup_contact_tools(mcp)
    setup_email_settings_tools(mcp)


__all__ = [
    "setup_tools",
    "setup_auth_tools",
    "setup_email_read_tools",
    "setup_email_send_tools",
    "setup_email_manage_tools",
    "setup_email_thread_tools",
    "setup_email_draft_tools",
    "setup_email_retention_tools",
    "setup_label_tools",
    "setup_attachment_tools",
    "setup_bulk_tools",
    "setup_calendar_tools",
    "setup_filter_tools",
    "setup_vault_tools",
    "setup_conflict_tools",
    "setup_contact_tools",
    "setup_email_settings_tools",
]
