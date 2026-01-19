"""
Gmail MCP - Model Context Protocol server for Gmail integration.

This package provides a comprehensive MCP server for Gmail and Google Calendar
integration with Claude Desktop and other MCP clients.

Features:
- Email reading, sending, and management
- Label management with Claude review labels
- Gmail filter management
- Calendar event management
- Multi-calendar conflict detection
- Obsidian vault integration
- Batch operations for efficient bulk processing

Example:
    from gmail_mcp.mcp.tools import setup_tools
    from gmail_mcp.auth.oauth import get_credentials
    from gmail_mcp.utils.services import get_gmail_service
"""

__version__ = "2.0.0"
__author__ = "Gmail MCP Contributors"

# Re-export key types for convenient access
from gmail_mcp.types import (
    # Common types
    ErrorResponse,
    SimpleSuccessResponse,

    # Email types
    EmailInfo,
    EmailDetail,
    EmailCountResponse,
    ListEmailsResponse,
    SearchEmailsResponse,
    EmailOverviewResponse,

    # Email send types
    DraftCreatedResponse,
    EmailSentResponse,
    PrepareReplyResponse,

    # Label types
    LabelInfo,
    LabelDetail,
    ListLabelsResponse,
    CreateLabelResponse,

    # Attachment types
    AttachmentInfo,
    GetAttachmentsResponse,

    # Bulk operation types
    BulkOperationResponse,

    # Filter types
    FilterInfo,
    FilterCriteria,
    FilterAction,
    ListFiltersResponse,
    CreateFilterResponse,

    # Calendar types
    CalendarEvent,
    CreateCalendarEventResponse,
    ListCalendarEventsResponse,
    SuggestMeetingTimesResponse,
    DetectEventsFromEmailResponse,

    # Conflict detection types
    CalendarInfo,
    ListCalendarsResponse,
    CheckConflictsResponse,
    FindFreeTimeResponse,
    GetDailyAgendaResponse,

    # Vault types
    SaveEmailToVaultResponse,
    BatchSaveEmailsToVaultResponse,

    # Auth types
    AuthStatusResponse,
)

__all__ = [
    # Version info
    "__version__",
    "__author__",

    # Common types
    "ErrorResponse",
    "SimpleSuccessResponse",

    # Email types
    "EmailInfo",
    "EmailDetail",
    "EmailCountResponse",
    "ListEmailsResponse",
    "SearchEmailsResponse",
    "EmailOverviewResponse",

    # Email send types
    "DraftCreatedResponse",
    "EmailSentResponse",
    "PrepareReplyResponse",

    # Label types
    "LabelInfo",
    "LabelDetail",
    "ListLabelsResponse",
    "CreateLabelResponse",

    # Attachment types
    "AttachmentInfo",
    "GetAttachmentsResponse",

    # Bulk operation types
    "BulkOperationResponse",

    # Filter types
    "FilterInfo",
    "FilterCriteria",
    "FilterAction",
    "ListFiltersResponse",
    "CreateFilterResponse",

    # Calendar types
    "CalendarEvent",
    "CreateCalendarEventResponse",
    "ListCalendarEventsResponse",
    "SuggestMeetingTimesResponse",
    "DetectEventsFromEmailResponse",

    # Conflict detection types
    "CalendarInfo",
    "ListCalendarsResponse",
    "CheckConflictsResponse",
    "FindFreeTimeResponse",
    "GetDailyAgendaResponse",

    # Vault types
    "SaveEmailToVaultResponse",
    "BatchSaveEmailsToVaultResponse",

    # Auth types
    "AuthStatusResponse",
]
