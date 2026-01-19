"""
Gmail MCP Type Definitions

This module provides TypedDict definitions for all tool return types,
enabling better IDE support and type checking.
"""

import sys
from typing import TypedDict, List, Optional, Any, Union

# NotRequired is available in typing from Python 3.11+
if sys.version_info >= (3, 11):
    from typing import NotRequired
else:
    try:
        from typing_extensions import NotRequired
    except ImportError:
        # Fallback: define NotRequired as identity for older Python without typing_extensions
        from typing import TypeVar
        T = TypeVar('T')
        NotRequired = Optional  # type: ignore


# =============================================================================
# Common Types
# =============================================================================

class ErrorResponse(TypedDict):
    """Standard error response from tools."""
    error: str


# =============================================================================
# Email Types
# =============================================================================

class EmailInfo(TypedDict):
    """Basic email information returned by list/search operations."""
    id: str
    thread_id: str
    subject: str
    from_: str  # Note: 'from' is reserved keyword
    to: str
    cc: str
    date: str
    snippet: str
    labels: List[str]
    email_link: str


class EmailDetail(EmailInfo):
    """Full email details including body content."""
    body: str


class EmailCountResponse(TypedDict):
    """Response from get_email_count."""
    email: str
    total_messages: int
    inbox_messages: int
    next_page_token: NotRequired[Optional[str]]


class ListEmailsResponse(TypedDict):
    """Response from list_emails."""
    emails: List[EmailInfo]
    next_page_token: NotRequired[Optional[str]]


class SearchEmailsResponse(TypedDict):
    """Response from search_emails."""
    query: str
    emails: List[EmailInfo]
    next_page_token: NotRequired[Optional[str]]


class EmailOverviewCounts(TypedDict):
    """Email counts by label."""
    inbox: int
    unread: int
    sent: int
    draft: int
    spam: int
    trash: int


class EmailOverviewAccount(TypedDict):
    """Account information in email overview."""
    email: str
    total_messages: int
    total_threads: int


class EmailOverviewResponse(TypedDict):
    """Response from get_email_overview."""
    account: EmailOverviewAccount
    counts: EmailOverviewCounts
    recent_emails: List[EmailInfo]
    unread_count: int


# =============================================================================
# Email Send Types
# =============================================================================

class DraftCreatedResponse(TypedDict):
    """Response when a draft is created."""
    success: bool
    message: str
    draft_id: str
    confirmation_required: bool


class EmailSentResponse(TypedDict):
    """Response when an email is sent."""
    success: bool
    message: str
    email_id: NotRequired[str]


class ComposeEmailResponse(DraftCreatedResponse):
    """Response from compose_email."""
    pass


class ForwardEmailResponse(DraftCreatedResponse):
    """Response from forward_email."""
    pass


# =============================================================================
# Email Reply Context Types
# =============================================================================

class ThreadContext(TypedDict):
    """Thread context for email replies."""
    id: str
    subject: str
    message_count: int
    participants: List[str]
    summary: str


class SenderContext(TypedDict):
    """Sender context for email replies."""
    email: str
    name: str
    message_count: int
    first_contact: NotRequired[Optional[str]]
    last_contact: NotRequired[Optional[str]]


class CommunicationPatterns(TypedDict):
    """Communication pattern analysis."""
    message_count: int
    communication_exists: bool
    avg_response_time_hours: NotRequired[Optional[float]]
    frequency: NotRequired[Optional[str]]


class ExtractedEntities(TypedDict):
    """Entities extracted from email content."""
    dates: List[str]
    times: List[str]
    phone_numbers: List[str]
    email_addresses: List[str]
    urls: List[str]
    action_items: List[str]


class PrepareReplyResponse(TypedDict):
    """Response from prepare_email_reply."""
    original_email: EmailDetail
    thread_context: NotRequired[Optional[ThreadContext]]
    sender_context: NotRequired[Optional[SenderContext]]
    communication_patterns: NotRequired[Optional[CommunicationPatterns]]
    entities: NotRequired[Optional[ExtractedEntities]]
    related_emails: NotRequired[Optional[List[EmailInfo]]]


# =============================================================================
# Email Management Types
# =============================================================================

class SimpleSuccessResponse(TypedDict):
    """Simple success/failure response."""
    success: bool
    message: str


class ArchiveEmailResponse(SimpleSuccessResponse):
    """Response from archive_email."""
    pass


class TrashEmailResponse(SimpleSuccessResponse):
    """Response from trash_email."""
    pass


class DeleteEmailResponse(SimpleSuccessResponse):
    """Response from delete_email."""
    pass


class MarkReadResponse(SimpleSuccessResponse):
    """Response from mark_as_read."""
    pass


class MarkUnreadResponse(SimpleSuccessResponse):
    """Response from mark_as_unread."""
    pass


class StarEmailResponse(SimpleSuccessResponse):
    """Response from star_email."""
    pass


class UnstarEmailResponse(SimpleSuccessResponse):
    """Response from unstar_email."""
    pass


# =============================================================================
# Label Types
# =============================================================================

class LabelInfo(TypedDict):
    """Information about a Gmail label."""
    id: str
    name: str
    type: str
    messageListVisibility: NotRequired[Optional[str]]
    labelListVisibility: NotRequired[Optional[str]]


class LabelColor(TypedDict):
    """Label color configuration."""
    backgroundColor: str
    textColor: str


class LabelDetail(LabelInfo):
    """Detailed label information."""
    color: NotRequired[Optional[LabelColor]]
    messagesTotal: NotRequired[Optional[int]]
    messagesUnread: NotRequired[Optional[int]]


class ListLabelsResponse(TypedDict):
    """Response from list_labels."""
    labels: List[LabelInfo]


class CreateLabelResponse(TypedDict):
    """Response from create_label."""
    success: bool
    message: str
    label: NotRequired[LabelDetail]


class ApplyLabelResponse(SimpleSuccessResponse):
    """Response from apply_label."""
    pass


class RemoveLabelResponse(SimpleSuccessResponse):
    """Response from remove_label."""
    pass


class ClaudeReviewLabelConfig(TypedDict):
    """Configuration for a Claude review label."""
    name: str
    color: str


class SetupClaudeReviewLabelsResponse(TypedDict):
    """Response from setup_claude_review_labels."""
    success: bool
    message: str
    created_labels: List[str]
    existing_labels: List[str]


class GetEmailsForClaudeReviewResponse(TypedDict):
    """Response from get_emails_for_claude_review."""
    label: str
    emails: List[EmailInfo]
    count: int


# =============================================================================
# Attachment Types
# =============================================================================

class AttachmentInfo(TypedDict):
    """Information about an email attachment."""
    id: str
    filename: str
    mimeType: str
    size: int


class GetAttachmentsResponse(TypedDict):
    """Response from get_attachments."""
    email_id: str
    attachments: List[AttachmentInfo]


class DownloadAttachmentResponse(TypedDict):
    """Response from download_attachment."""
    success: bool
    message: str
    file_path: NotRequired[str]


# =============================================================================
# Bulk Operation Types
# =============================================================================

class BulkOperationResponse(TypedDict):
    """Response from bulk operations."""
    success: bool
    message: str
    processed: int
    failed: int
    total: int


class BulkArchiveResponse(BulkOperationResponse):
    """Response from bulk_archive."""
    pass


class BulkLabelResponse(BulkOperationResponse):
    """Response from bulk_label."""
    pass


class BulkTrashResponse(BulkOperationResponse):
    """Response from bulk_trash."""
    pass


class CleanupOldEmailsResponse(BulkOperationResponse):
    """Response from cleanup_old_emails."""
    pass


# =============================================================================
# Filter Types
# =============================================================================

class FilterCriteria(TypedDict):
    """Gmail filter criteria."""
    from_: NotRequired[Optional[str]]
    to: NotRequired[Optional[str]]
    subject: NotRequired[Optional[str]]
    query: NotRequired[Optional[str]]
    hasAttachment: NotRequired[Optional[bool]]
    excludeChats: NotRequired[Optional[bool]]
    size: NotRequired[Optional[int]]
    sizeComparison: NotRequired[Optional[str]]


class FilterAction(TypedDict):
    """Gmail filter actions."""
    addLabelIds: NotRequired[Optional[List[str]]]
    removeLabelIds: NotRequired[Optional[List[str]]]
    forward: NotRequired[Optional[str]]


class FilterInfo(TypedDict):
    """Information about a Gmail filter."""
    id: str
    criteria: FilterCriteria
    action: FilterAction


class ListFiltersResponse(TypedDict):
    """Response from list_filters."""
    filters: List[FilterInfo]


class CreateFilterResponse(TypedDict):
    """Response from create_filter."""
    success: bool
    message: str
    filter_id: NotRequired[str]
    filter: NotRequired[FilterInfo]


class DeleteFilterResponse(SimpleSuccessResponse):
    """Response from delete_filter."""
    pass


class GetFilterResponse(TypedDict):
    """Response from get_filter."""
    success: bool
    filter: NotRequired[FilterInfo]
    message: NotRequired[str]


class CreateClaudeReviewFilterResponse(TypedDict):
    """Response from create_claude_review_filter."""
    success: bool
    message: str
    filter_id: NotRequired[str]


# =============================================================================
# Calendar Types
# =============================================================================

class CalendarEventTime(TypedDict):
    """Event time with optional timezone."""
    dateTime: NotRequired[Optional[str]]
    date: NotRequired[Optional[str]]
    timeZone: NotRequired[Optional[str]]


class CalendarAttendee(TypedDict):
    """Calendar event attendee."""
    email: str
    responseStatus: NotRequired[Optional[str]]
    displayName: NotRequired[Optional[str]]


class CalendarEvent(TypedDict):
    """Calendar event information."""
    id: str
    summary: str
    description: NotRequired[Optional[str]]
    location: NotRequired[Optional[str]]
    start: CalendarEventTime
    end: CalendarEventTime
    attendees: NotRequired[Optional[List[CalendarAttendee]]]
    htmlLink: NotRequired[Optional[str]]
    status: NotRequired[Optional[str]]


class CreateCalendarEventResponse(TypedDict):
    """Response from create_calendar_event."""
    success: bool
    message: str
    event_id: NotRequired[str]
    event_link: NotRequired[str]
    missing_info: NotRequired[List[str]]


class ListCalendarEventsResponse(TypedDict):
    """Response from list_calendar_events."""
    events: List[CalendarEvent]
    next_page_token: NotRequired[Optional[str]]


class UpdateCalendarEventResponse(TypedDict):
    """Response from update_calendar_event."""
    success: bool
    message: str
    event: NotRequired[CalendarEvent]


class DeleteCalendarEventResponse(SimpleSuccessResponse):
    """Response from delete_calendar_event."""
    pass


class RSVPEventResponse(SimpleSuccessResponse):
    """Response from rsvp_event."""
    pass


class MeetingTimeSuggestion(TypedDict):
    """A suggested meeting time."""
    start: str
    end: str
    formatted: str


class SuggestMeetingTimesResponse(TypedDict):
    """Response from suggest_meeting_times."""
    success: bool
    message: str
    suggestions: List[MeetingTimeSuggestion]


class DetectedEvent(TypedDict):
    """Event detected from email content."""
    title: str
    start_time: NotRequired[Optional[str]]
    end_time: NotRequired[Optional[str]]
    location: NotRequired[Optional[str]]
    description: NotRequired[Optional[str]]
    confidence: float


class DetectEventsFromEmailResponse(TypedDict):
    """Response from detect_events_from_email."""
    success: bool
    events: List[DetectedEvent]
    email_link: str


# =============================================================================
# Conflict Detection Types
# =============================================================================

class CalendarInfo(TypedDict):
    """Information about a calendar."""
    id: str
    summary: str
    description: NotRequired[Optional[str]]
    primary: NotRequired[Optional[bool]]
    accessRole: str
    backgroundColor: NotRequired[Optional[str]]
    foregroundColor: NotRequired[Optional[str]]


class ListCalendarsResponse(TypedDict):
    """Response from list_calendars."""
    success: bool
    calendars: List[CalendarInfo]


class ConflictInfo(TypedDict):
    """Information about a scheduling conflict."""
    time_slot: str
    events: List[CalendarEvent]
    calendars: List[str]
    severity: str


class CheckConflictsResponse(TypedDict):
    """Response from check_conflicts."""
    success: bool
    conflicts: List[ConflictInfo]
    message: str


class FreeTimeSlot(TypedDict):
    """A free time slot."""
    start: str
    end: str
    duration_minutes: int
    formatted: str


class FindFreeTimeResponse(TypedDict):
    """Response from find_free_time."""
    success: bool
    free_slots: List[FreeTimeSlot]
    message: str


class DailyAgendaEvent(TypedDict):
    """Event in daily agenda."""
    calendar: str
    calendar_id: str
    event: CalendarEvent


class GetDailyAgendaResponse(TypedDict):
    """Response from get_daily_agenda."""
    success: bool
    date: str
    events: List[DailyAgendaEvent]
    conflict_count: int
    message: str


# =============================================================================
# Vault Integration Types
# =============================================================================

class SaveEmailToVaultResponse(TypedDict):
    """Response from save_email_to_vault."""
    success: bool
    message: str
    file_path: NotRequired[str]
    attachments_saved: NotRequired[List[str]]


class BatchSaveEmailsToVaultResponse(TypedDict):
    """Response from batch_save_emails_to_vault."""
    success: bool
    message: str
    saved: int
    failed: int
    file_paths: List[str]


# =============================================================================
# Authentication Types
# =============================================================================

class AuthStatusResponse(TypedDict):
    """Response from check_auth_status."""
    authenticated: bool
    email: NotRequired[Optional[str]]
    message: NotRequired[str]


class AuthenticateResponse(TypedDict):
    """Response from authenticate."""
    success: bool
    message: str


class LogoutResponse(TypedDict):
    """Response from logout."""
    success: bool
    message: str


# =============================================================================
# Unsubscribe Types
# =============================================================================

class FindUnsubscribeLinkResponse(TypedDict):
    """Response from find_unsubscribe_link."""
    success: bool
    unsubscribe_link: NotRequired[Optional[str]]
    message: str


# =============================================================================
# Type Aliases for Return Type Unions
# =============================================================================

# Common return type pattern: success response or error
EmailCountResult = Union[EmailCountResponse, ErrorResponse]
ListEmailsResult = Union[ListEmailsResponse, ErrorResponse]
SearchEmailsResult = Union[SearchEmailsResponse, ErrorResponse]
EmailOverviewResult = Union[EmailOverviewResponse, ErrorResponse]
EmailDetailResult = Union[EmailDetail, ErrorResponse]
DraftCreatedResult = Union[DraftCreatedResponse, ErrorResponse]
SimpleResult = Union[SimpleSuccessResponse, ErrorResponse]
ListLabelsResult = Union[ListLabelsResponse, ErrorResponse]
BulkOperationResult = Union[BulkOperationResponse, ErrorResponse]
ListFiltersResult = Union[ListFiltersResponse, ErrorResponse]
CalendarEventResult = Union[CreateCalendarEventResponse, ErrorResponse]
ListCalendarEventsResult = Union[ListCalendarEventsResponse, ErrorResponse]
