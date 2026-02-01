# Changelog

## 2026-02-01

**Fixed:**
- Removed auto-add organizer as attendee in `create_calendar_event` and `create_recurring_event` — was causing duplicate calendar entries

## 2026-01-31

**Code Cleanup:**
- Removed `detect_events_from_email` (harmful regex-based event detection)
- Removed `create_formatted_doc`, `debug_doc_structure`, `test_gdocs_render` (incomplete Google Docs formatting)
- Removed duplicate `find_unsubscribe_link` from bulk.py
- Fixed token/auth caching issues (#55-57)

## 2026-01-23 - Backlog Complete

**gmail-mcp - Calendar (2 new tools):**
- `get_calendar_event` - Get single event by ID
- `duplicate_calendar_event` - Copy an event to a new time

**drive-mcp - File Actions (2 new tools):**
- `star_drive_file` - Star a file for quick access
- `unstar_drive_file` - Remove star from file

**drive-mcp - Comments (3 new tools):**
- `list_drive_comments` - List comments on a file
- `add_drive_comment` - Add comment to a file
- `delete_drive_comment` - Delete a comment

**drive-mcp - Revisions (3 new tools):**
- `list_drive_revisions` - List file version history
- `get_drive_revision` - Get specific revision metadata
- `download_drive_revision` - Download a previous version

**drive-mcp - Shared Drives Admin (3 new tools):**
- `create_shared_drive` - Create a new shared drive (Workspace admin)
- `delete_shared_drive` - Delete a shared drive
- `update_shared_drive` - Update shared drive name/settings

**docs-mcp - PDF Advanced (5 new tools):**
- `rotate_pdf` - Rotate pages in a PDF
- `compress_pdf` - Reduce PDF file size
- `add_watermark` - Add watermark to PDF pages
- `encrypt_pdf` - Password-protect a PDF
- `decrypt_pdf` - Remove password from PDF

## 2026-01-22 - Contact Hygiene, Subscription Management, Travel Buffer

**Contact Hygiene (21 new tools):**
- `find_duplicate_contacts` - Find potential duplicate contacts with fuzzy matching
- `find_stale_contacts` - Find contacts with no email activity in N months
- `find_incomplete_contacts` - Find contacts missing required fields
- `merge_contacts` - Merge duplicate contacts (requires write scope)
- `enrich_contact_from_email` - Extract contact info from email signatures
- `export_contacts` - Export contacts to CSV
- `create_contact`, `update_contact`, `delete_contact` - Full CRUD operations
- `list_contact_groups`, `create_contact_group`, `delete_contact_group` - Contact group management
- `add_contacts_to_group`, `remove_contacts_from_group` - Group membership management

**Subscription Management (6 new tools):**
- `setup_subscription_labels` - Create Subscriptions/Review, Retained, Unsubscribed labels
- `find_subscription_emails` - Find newsletter/subscription senders with unsubscribe links
- `get_unsubscribe_link` - Extract unsubscribe link from email headers/body
- `unsubscribe_and_cleanup` - Full unsubscribe workflow
- `create_subscription_filter` - Create filter for subscription sender
- `mark_sender_as_junk` - Filter sender to trash + report spam

**Calendar (1 new tool):**
- `add_travel_buffer` - Add blocking travel time event before meetings

**drive-mcp (43 tools):** Full Google Drive integration
- File operations, folders, workspace files, sharing, shared drives, bulk ops, labels, OCR

**docs-mcp (27 tools):** Local document processing (no Google auth)
- Office reading/templates/export, PDF processing, local OCR, vault integration

## 2026-01-21 - Email & Calendar Features

- Scheduled Send: `compose_email(send_at="tomorrow 8am")`
- Attendee Free/Busy: `check_attendee_availability()`
- Event Reminders: `reminders` parameter on all calendar functions
- Contact Lookup: `list_contacts()`, `search_contacts()`, `get_contact()`
- Vacation Responder: `set_vacation_responder()`, `get_vacation_responder()`, `disable_vacation_responder()`
- Draft Management: `list_drafts()`, `get_draft()`, `update_draft()`, `delete_draft()`
- Retention Labels: `setup_retention_labels()`, `enforce_retention_policies()`, `get_retention_status()`

## 2026-01-19 - Foundation

- NLP Date Parsing: Full natural language date support across all tools
- Bulk Operations: Fixed HTTP batch to use native batchModify endpoint
- Thread/Conversation View: `get_thread()`, `get_thread_summary()`
- Filter OAuth Scope: Added `gmail.settings.basic` scope
