# Gmail MCP Backlog

## Development Workflow

**Before any major work:**
1. `cd /Users/mike/gmail-mcp && source .venv/bin/activate`
2. `pytest tests/ -v --tb=short` - capture baseline (264 passed)
3. Plan the changes (update this file or create issue)
4. Implement changes
5. `pytest tests/ -v --tb=short` - compare output
6. Fix any regressions
7. Update docs (`README.md`, `docs/overview.md`)
8. Update `_claude/gmail-mcp-test-plan.md` if needed
9. Commit and push

---

## Priority Matrix

| Priority | Items |
|----------|-------|
| **High** | Contact Hygiene (#24-28) |
| **Medium** | Unsubscribe Management, Contact Bulk Ops (#29-32) |
| **Low** | Travel Time, DST Handling, Contact CRUD (#33-35) |
| **Future** | Google Drive Integration |

**Recently Completed (2026-01-21):** Scheduled Send (#13), Attendee Free/Busy (#15), Event Reminders (#16), Contact Lookup (#18), Vacation Responder (#14), Tests & Docs for all

---

## Bugs

### 20. ✅ FIXED - Bulk Operations Capped at 20 Emails (2026-01-19)
**Root cause:** HTTP batch request callback pattern was unreliable - only ~20% of callbacks were succeeding.

**Fix:** Switched from HTTP batch requests (`new_batch_http_request()`) to Gmail's native `batchModify` endpoint which handles up to 1000 IDs in a single API call.

**Changes:**
1. Added `_fetch_messages_with_pagination()` helper for fetching up to `max_emails`
2. Rewrote `_batch_modify_emails()` to use native `batchModify` endpoint
3. Simplified `_batch_trash_emails()` to call `_batch_modify_emails()` with TRASH label

All bulk operations now properly process up to `max_emails` (max 500):
- `bulk_trash(query, max_emails)`
- `bulk_archive(query, max_emails)`
- `bulk_label(query, label_id, max_emails)`
- `bulk_remove_label(query, label_id, max_emails)` - NEW
- `cleanup_old_emails(query, days_old, action, max_emails)`

**Files changed:**
- `gmail_mcp/mcp/tools/bulk.py` - pagination helper, native batchModify, bulk_remove_label

---

### 23. ✅ FIXED - Filter Creation OAuth Scope (2026-01-19)
Added `gmail.settings.basic` scope to `oauth.py`. User must re-auth after upgrade.

**Note discovered:** Gmail API limits filters to 1 user label each. Multiple labels require multiple filters.

---

## Email Features

### 11. ✅ IMPLEMENTED - Thread/Conversation View (2026-01-19)
Implemented full thread/conversation view support with three new tools:

**New tools:**
- `get_thread(thread_id)` - Returns full conversation with all messages
- `get_thread_summary(thread_id)` - Returns condensed view (original, timeline, recent messages)
- `get_email(email_id, include_thread=True)` - Option to include thread context

**Features:**
- Full message bodies extracted
- Participant extraction from from/to/cc fields
- Chronological message ordering
- Direct Gmail web links

**Files:**
- `gmail_mcp/mcp/tools/email_thread.py` (new - ~220 lines)
- `gmail_mcp/mcp/tools/email_read.py` (updated get_email with include_thread)
- `gmail_mcp/mcp/tools/__init__.py` (registered new module)
- `tests/test_email_thread.py` (new - 9 tests)

---

### 12. ✅ IMPLEMENTED - Draft Management (2026-01-21)
Full draft lifecycle management implemented.

**New tools:**
- `list_drafts(max_results=10)` - List all drafts with basic info
- `get_draft(draft_id)` - Get full draft content
- `update_draft(draft_id, to=None, subject=None, body=None, cc=None, bcc=None)` - Update existing draft
- `delete_draft(draft_id)` - Permanently delete a draft

**Features:**
- Preserves unchanged fields when updating (only specified fields change)
- Returns full draft details after update
- Pagination support for list_drafts

**Files:**
- `gmail_mcp/mcp/tools/email_drafts.py` (new - ~280 lines)
- `tests/test_email_drafts.py` (new - 11 tests)

---

### 13. ✅ IMPLEMENTED - Scheduled Send (2026-01-21)
Schedule emails to send later using draft + calendar reminder approach.

**New parameter on compose_email:**
```python
compose_email(to="...", subject="...", body="...", send_at="tomorrow 8am")
```

**How it works:**
1. Creates email as draft
2. Creates calendar event at scheduled time: "📧 Send email: [subject]"
3. Event description includes draft link and instructions
4. User receives reminder and sends manually (or Claude sends when reminded)

**Note:** Gmail API doesn't support native scheduled send - this is the workaround approach.

**Files:**
- `gmail_mcp/mcp/tools/email_send.py` (updated compose_email with send_at parameter)

---

### 21. ✅ IMPLEMENTED - Retention Labels & Automated Cleanup (2026-01-21)
Automated email retention policy enforcement.

**New tools:**
- `setup_retention_labels()` - Creates standard retention labels if they don't exist
- `enforce_retention_policies(dry_run=True, max_emails_per_label=100)` - Enforces retention policies
- `get_retention_status()` - Shows current status of all retention labels

**Features:**
- Dry run mode by default (safe preview before deletion)
- Supports 6 retention periods: 7-days, 30-days, 90-days, 6-months, 1-year, 3-years
- Per-label breakdown of expired email counts
- Graceful handling of missing labels

**Usage:**
```python
# Preview what would be deleted
enforce_retention_policies(dry_run=True)

# Actually delete expired emails
enforce_retention_policies(dry_run=False)

# Check retention status
get_retention_status()
```

**Files:**
- `gmail_mcp/mcp/tools/email_retention.py` (new - ~300 lines)
- `tests/test_email_retention.py` (new - 10 tests)

---

### 22. Unsubscribe Management
**Priority:** Medium
**Issue:** No systematic way to manage newsletters/subscriptions.

**Concept:**
1. Find emails with unsubscribe links (already have `find_unsubscribe_link`)
2. Create smart label for potential subscriptions
3. Workflow to triage: unsubscribe, junk, or retain

**Implementation:**

**Phase 1: Discovery**
```python
find_subscription_emails(max_results=100, unlabeled_only=True)
# Searches: has:unsubscribe -label:Subscription/*
# Returns list with sender, frequency, unsubscribe link

# Returns:
{
  "subscriptions": [
    {
      "from": "newsletter@techsite.com",
      "count": 15,
      "frequency": "daily",
      "unsubscribe_link": "https://...",
      "sample_subject": "Daily Tech Digest"
    },
    ...
  ]
}
```

**Phase 2: Triage Actions**
```python
# Option 1: Unsubscribe and archive existing
unsubscribe_and_cleanup(from_address="newsletter@spam.com")
# - Finds unsubscribe link
# - Returns link for user to click (or auto-request if simple)
# - Creates filter to auto-trash future emails
# - Archives existing emails from sender

# Option 2: Keep but organize
create_subscription_filter(
    from_address="newsletter@goodsite.com",
    action="retain",
    retention="30-days",  # Optional: auto-cleanup old ones
    skip_inbox=True
)
# Creates filter: apply Subscription/Retained label, archive

# Option 3: Mark as junk
mark_as_junk(from_address="spammer@bad.com")
# Creates filter to auto-trash
# Reports as spam
# Trashes existing emails
```

**Phase 3: Labels**
```python
setup_subscription_labels()
# Creates:
# - Subscription/Review (newly discovered)
# - Subscription/Retained (keeping)
# - Subscription/Unsubscribed (processed, filter created)
```

**Claude Workflow:**
- Weekly/monthly prompt: "Show me subscription emails I haven't triaged"
- For each: "Unsubscribe, junk, or keep? If keep, what retention?"

**Files:**
- `gmail_mcp/mcp/tools/email_subscriptions.py` (new)
- `tests/test_email_subscriptions.py` (new)

**Estimated scope:** ~200 lines code, ~80 lines tests

**Note:** Automatic unsubscription (HTTP request to unsubscribe link) is risky - some links confirm the email is active. Better to return the link for user to click manually.

---

### 14. ✅ IMPLEMENTED - Vacation Responder (2026-01-21)
Vacation responder / out of office auto-reply.

**New tools:**
- `set_vacation_responder(subject, message, start_date, end_date, contacts_only, domain_only)` - Enable vacation responder
- `get_vacation_responder()` - Check current status
- `disable_vacation_responder()` - Disable vacation responder

**Usage:**
```python
set_vacation_responder(
    subject="Out of Office",
    message="I'm away until Feb 7. For urgent matters, contact backup@co.com",
    start_date="tomorrow",
    end_date="next friday"
)
```

**Files:**
- `gmail_mcp/mcp/tools/email_settings.py` (new - ~200 lines)

---

## Calendar Features

### 15. ✅ IMPLEMENTED - Attendee Free/Busy Query (2026-01-21)
Check availability of multiple attendees and find common free times.

**New tool:**
```python
check_attendee_availability(
    attendees=["bob@company.com", "alice@company.com"],
    start_date="tomorrow",
    end_date="friday",
    duration="1 hour"
)
# Returns times when ALL attendees are free
```

**Features:**
- Uses Calendar API `freebusy.query()` for efficient batch lookup
- Finds common free slots within working hours
- Excludes weekends by default
- Shows individual availability breakdown

**Note:** Only works for attendees who share their calendar or are in same org.

**Files:**
- `gmail_mcp/mcp/tools/conflict.py` (added check_attendee_availability)

---

### 16. ✅ IMPLEMENTED - Event Reminders (2026-01-21)
Custom per-event reminders on calendar events.

**New `reminders` parameter on all calendar event functions:**
```python
create_calendar_event(
    summary="...",
    start_time="...",
    reminders=["30 minutes", "1 day before by email"]
)

# Also supports dict format:
create_calendar_event(
    summary="...",
    start_time="...",
    reminders=[{"method": "popup", "minutes": 30}, {"method": "email", "minutes": 1440}]
)
```

**Supported formats:**
- `"30 minutes"` or `"30 minutes before"` - popup reminder
- `"1 hour before by email"` - email reminder
- `"1 day"`, `"2 weeks"` - any time unit

**Works with:**
- `create_calendar_event()`
- `create_recurring_event()`
- `update_calendar_event()`

**Files:**
- `gmail_mcp/mcp/tools/calendar.py` (added _parse_reminder helper, updated all event functions)

---

### 17. Travel Time Buffer
**Priority:** Low
**Issue:** No automatic travel time between events with locations.

**Desired behavior:**
```python
create_calendar_event(
    summary="Meeting at Client Office",
    start_time="tomorrow 2pm",
    location="123 Main St, Chicago",
    add_travel_time=True,  # Auto-adds buffer event before
    travel_from="Home"  # Or previous event location
)
```

**Implementation:**
- Complex - requires:
  - Location geocoding (Google Maps API)
  - Travel time estimation
  - Creating blocking event before main event
- **Simpler alternative:** Manual travel buffer
  ```python
  add_travel_buffer(event_id="...", minutes=30, label="Travel to meeting")
  ```

**Recommendation:** Start with simple manual buffer, skip auto-calculation for now.

**Files:**
- `gmail_mcp/mcp/tools/calendar.py`

**Estimated scope:** ~40 lines (simple version)

---

## Contact Integration

### 18. ✅ IMPLEMENTED - Contact Lookup (2026-01-21)
Google Contacts access via People API.

**New tools:**
```python
list_contacts(max_results=50)  # List all contacts
search_contacts(query="Bob Smith")  # Find contacts by name, email, company
get_contact(email="bob@company.com")  # Get contact details by email
```

**Returns contact info:**
- name, given_name, family_name
- emails (list), primary email
- phones (list), primary phone
- organization, title, department
- addresses
- notes, photo_url

**Configuration:**
Requires `contacts_api_enabled: true` in config and re-authentication to grant scope.

**Files:**
- `gmail_mcp/utils/services.py` (added get_people_service)
- `gmail_mcp/mcp/tools/contacts.py` (new - ~250 lines)
- `gmail_mcp/auth/oauth.py` (added contacts scope when enabled)

---

## Contact Management

**Prerequisite:** Upgrade from `contacts.readonly` to `contacts` scope (full read/write).

### 24. Find Duplicate Contacts
**Priority:** High
**Status:** Planned

Detect contacts that may be duplicates based on name, email, or phone.

**Proposed tool:**
```python
find_duplicate_contacts(
    threshold: float = 0.8,  # Similarity threshold
    max_results: int = 50
) -> Dict[str, Any]

# Returns:
{
  "success": True,
  "duplicate_groups": [
    {
      "contacts": [
        {"resource_name": "people/c123", "name": "John Smith", "email": "john@example.com"},
        {"resource_name": "people/c456", "name": "John R Smith", "email": "john@example.com"}
      ],
      "match_reason": "Same email address",
      "confidence": 1.0
    },
    {
      "contacts": [...],
      "match_reason": "Similar name",
      "confidence": 0.85
    }
  ],
  "total_groups": 5
}
```

**Matching criteria (in order of confidence):**
1. Exact email match (confidence: 1.0)
2. Exact phone match (confidence: 1.0)
3. Very similar name + same domain (confidence: 0.9)
4. Similar name (Levenshtein distance) (confidence: 0.7-0.9)

**Implementation notes:**
- Use `contacts.readonly` scope (can implement now!)
- Fuzzy name matching with `difflib.SequenceMatcher` or `fuzzywuzzy`
- Group by highest-confidence match first

**Files:**
- `gmail_mcp/mcp/tools/contacts.py` (extend)

**Estimated scope:** ~100 lines

---

### 25. Merge Contacts
**Priority:** High
**Status:** Planned
**Requires:** `contacts` scope (read/write)

Combine two or more contacts into one, preserving all unique information.

**Proposed tool:**
```python
merge_contacts(
    resource_names: List[str],  # List of contact resource names to merge
    primary: str = None,  # Which contact to keep as primary (others deleted)
    dry_run: bool = True  # Preview merge without executing
) -> Dict[str, Any]

# Returns:
{
  "success": True,
  "merged_contact": {
    "resource_name": "people/c123",
    "name": "John Smith",
    "emails": ["john@work.com", "john@personal.com"],  # Combined
    "phones": ["+1-555-1234", "+1-555-5678"],  # Combined
    ...
  },
  "contacts_removed": ["people/c456", "people/c789"],
  "dry_run": True
}
```

**Merge logic:**
- Keep primary contact's name (or most complete name)
- Combine all unique emails, phones, addresses
- Combine notes (concatenate with separator)
- Keep most recent photo
- Preserve all organization info

**Files:**
- `gmail_mcp/mcp/tools/contacts.py` (extend)

**Estimated scope:** ~150 lines

---

### 26. Find Stale Contacts
**Priority:** High
**Status:** Planned

Find contacts you haven't emailed (sent or received) in N months.

**Proposed tool:**
```python
find_stale_contacts(
    months: int = 12,  # No email activity in this many months
    max_results: int = 100
) -> Dict[str, Any]

# Returns:
{
  "success": True,
  "stale_contacts": [
    {
      "resource_name": "people/c123",
      "name": "Old Colleague",
      "email": "old@company.com",
      "last_email_date": "2024-06-15",  # Last sent/received
      "months_inactive": 18
    },
    ...
  ],
  "total_stale": 45
}
```

**Implementation:**
1. Get all contacts with email addresses
2. For each, search Gmail: `from:{email} OR to:{email} after:{cutoff_date}`
3. Contacts with no results are stale

**Note:** Can use `contacts.readonly` scope + `gmail.readonly` - implementable now!

**Files:**
- `gmail_mcp/mcp/tools/contacts.py` (extend)

**Estimated scope:** ~80 lines

---

### 27. Enrich Contact from Email
**Priority:** High
**Status:** Planned

Extract contact details from email signatures and update contacts.

**Proposed tool:**
```python
enrich_contact_from_email(
    email_id: str,  # Email to extract signature from
    contact_email: str = None,  # Which contact to update (default: sender)
    dry_run: bool = True
) -> Dict[str, Any]

# Returns:
{
  "success": True,
  "extracted_info": {
    "phone": "+1-555-123-4567",
    "title": "Senior Engineer",
    "company": "Acme Corp",
    "address": "123 Main St, San Francisco, CA"
  },
  "contact_before": {...},
  "contact_after": {...},
  "fields_updated": ["phone", "title"],
  "dry_run": True
}
```

**Signature parsing patterns:**
- Phone: Various formats (+1, parentheses, dashes)
- Title/Company: "Title at Company" or "Title | Company"
- Address: Multi-line address patterns
- LinkedIn/Twitter URLs

**Files:**
- `gmail_mcp/mcp/tools/contacts.py` (extend)
- `gmail_mcp/utils/signature_parser.py` (new - regex patterns)

**Estimated scope:** ~200 lines (parsing is complex)

---

### 28. Find Incomplete Contacts
**Priority:** High
**Status:** Planned

Find contacts missing key information (email, phone, etc.).

**Proposed tool:**
```python
find_incomplete_contacts(
    require_email: bool = True,
    require_phone: bool = False,
    require_organization: bool = False,
    max_results: int = 100
) -> Dict[str, Any]

# Returns:
{
  "success": True,
  "incomplete_contacts": [
    {
      "resource_name": "people/c123",
      "name": "Bob Someone",
      "missing_fields": ["phone", "organization"],
      "has_email": True,
      "has_phone": False,
      "has_organization": False
    },
    ...
  ],
  "total_incomplete": 23
}
```

**Note:** Can use `contacts.readonly` scope - implementable now!

**Files:**
- `gmail_mcp/mcp/tools/contacts.py` (extend)

**Estimated scope:** ~50 lines

---

### 29. Bulk Update Contacts
**Priority:** Medium
**Status:** Planned
**Requires:** `contacts` scope (read/write)

Update a field across multiple contacts (e.g., company rename).

**Proposed tool:**
```python
bulk_update_contacts(
    resource_names: List[str] = None,  # Specific contacts, or...
    query: str = None,  # Search query to find contacts
    updates: Dict[str, str] = {},  # Fields to update
    dry_run: bool = True
) -> Dict[str, Any]

# Example: Company renamed
bulk_update_contacts(
    query="Acme Corp",  # Find all contacts at old company
    updates={"organization": "Acme Industries"},
    dry_run=False
)

# Returns:
{
  "success": True,
  "contacts_updated": 15,
  "contacts": [...],
  "dry_run": False
}
```

**Files:**
- `gmail_mcp/mcp/tools/contacts.py` (extend)

**Estimated scope:** ~80 lines

---

### 30. Import Contacts
**Priority:** Medium
**Status:** Planned
**Requires:** `contacts` scope (read/write)

Import contacts from CSV or vCard file.

**Proposed tool:**
```python
import_contacts(
    file_path: str,  # Path to CSV or vCard file
    format: str = "auto",  # "csv", "vcard", or "auto" (detect)
    dry_run: bool = True,
    skip_duplicates: bool = True  # Skip if email already exists
) -> Dict[str, Any]

# Returns:
{
  "success": True,
  "imported": 45,
  "skipped_duplicates": 3,
  "errors": [
    {"row": 12, "error": "Invalid email format"}
  ],
  "dry_run": True
}
```

**CSV format expected:**
```
Name,Email,Phone,Company,Title
John Smith,john@example.com,555-1234,Acme,Engineer
```

**Files:**
- `gmail_mcp/mcp/tools/contacts.py` (extend)
- May need `vobject` package for vCard parsing

**Estimated scope:** ~150 lines

---

### 31. Export Contacts
**Priority:** Medium
**Status:** Planned

Export contacts to CSV or vCard for backup.

**Proposed tool:**
```python
export_contacts(
    file_path: str,  # Where to save
    format: str = "csv",  # "csv" or "vcard"
    query: str = None,  # Optional filter
    max_results: int = 1000
) -> Dict[str, Any]

# Returns:
{
  "success": True,
  "exported": 156,
  "file_path": "/path/to/contacts.csv",
  "format": "csv"
}
```

**Note:** Can use `contacts.readonly` scope - implementable now!

**Files:**
- `gmail_mcp/mcp/tools/contacts.py` (extend)

**Estimated scope:** ~80 lines

---

### 32. Contact Groups (Labels)
**Priority:** Medium
**Status:** Planned
**Requires:** `contacts` scope (read/write)

Manage contact groups for organization.

**Proposed tools:**
```python
list_contact_groups() -> Dict[str, Any]
# Returns all contact groups with member counts

create_contact_group(name: str) -> Dict[str, Any]

add_contacts_to_group(
    group_resource_name: str,
    contact_resource_names: List[str]
) -> Dict[str, Any]

remove_contacts_from_group(
    group_resource_name: str,
    contact_resource_names: List[str]
) -> Dict[str, Any]

delete_contact_group(group_resource_name: str) -> Dict[str, Any]
```

**Files:**
- `gmail_mcp/mcp/tools/contacts.py` (extend)

**Estimated scope:** ~120 lines

---

### 33. Create Contact
**Priority:** Low
**Status:** Planned
**Requires:** `contacts` scope (read/write)

Create a new contact.

**Proposed tool:**
```python
create_contact(
    name: str,
    email: str = None,
    phone: str = None,
    organization: str = None,
    title: str = None,
    notes: str = None
) -> Dict[str, Any]

# Returns:
{
  "success": True,
  "contact": {
    "resource_name": "people/c123456",
    "name": "New Person",
    ...
  }
}
```

**Files:**
- `gmail_mcp/mcp/tools/contacts.py` (extend)

**Estimated scope:** ~50 lines

---

### 34. Update Contact
**Priority:** Low
**Status:** Planned
**Requires:** `contacts` scope (read/write)

Update an existing contact.

**Proposed tool:**
```python
update_contact(
    resource_name: str,  # Or email to lookup
    email: str = None,
    name: str = None,
    phone: str = None,
    organization: str = None,
    title: str = None,
    notes: str = None,
    append_notes: bool = False  # Append to existing notes vs replace
) -> Dict[str, Any]
```

**Files:**
- `gmail_mcp/mcp/tools/contacts.py` (extend)

**Estimated scope:** ~60 lines

---

### 35. Delete Contact
**Priority:** Low
**Status:** Planned
**Requires:** `contacts` scope (read/write)

Delete a contact.

**Proposed tool:**
```python
delete_contact(
    resource_name: str = None,
    email: str = None  # Lookup by email if resource_name not provided
) -> Dict[str, Any]
```

**Files:**
- `gmail_mcp/mcp/tools/contacts.py` (extend)

**Estimated scope:** ~30 lines

---

## Low Priority / Polish

### 3. DST Transition Handling
**Priority:** Low
**Status:** Documented, not implemented

Edge case handling for daylight saving time transitions. Only affects ~2 hours per year.

---

### 9. Relative Email Count
**Priority:** Low
**Status:** Skip unless requested

`list_emails(count="last 10")` - Claude handles this naturally.

---

## Google Drive Integration (Future)

### 19. Drive Integration - Full Spec

**Priority:** Future (separate phase)
**Scope:** Large - effectively doubles the MCP functionality

#### 19.1 Core File Operations

```python
# List and search
list_drive_files(folder_id=None, query=None, max_results=20)
search_drive(query="quarterly report", file_type="document")
get_file_info(file_id="...")

# Upload and download
upload_file(local_path="/path/to/file.pdf", folder_id=None, name=None)
download_file(file_id="...", local_path="/path/to/save")

# Management
create_folder(name="Project X", parent_id=None)
move_file(file_id="...", new_parent_id="...")
rename_file(file_id="...", new_name="...")
delete_file(file_id="...")  # Moves to trash
permanently_delete_file(file_id="...")

# Sharing
share_file(file_id="...", email="bob@co.com", role="reader|writer|commenter")
get_sharing_settings(file_id="...")
remove_sharing(file_id="...", email="bob@co.com")
get_shareable_link(file_id="...", anyone_with_link=False)
```

#### 19.2 Google Docs

```python
# Creation
create_doc(title="Meeting Notes", content=None, folder_id=None)
create_doc_from_template(template_id="...", title="...", replacements={"{{NAME}}": "Mike"})

# Reading
get_doc_content(doc_id="...")  # Returns markdown or plain text
get_doc_outline(doc_id="...")  # Returns headers/structure

# Editing
append_to_doc(doc_id="...", content="New paragraph here")
insert_in_doc(doc_id="...", content="...", index=0)  # Insert at position
replace_in_doc(doc_id="...", find="old text", replace="new text")
update_doc(doc_id="...", content="Full new content")  # Replace all

# Export
export_doc(doc_id="...", format="pdf|docx|md|txt", local_path="...")
```

#### 19.3 Google Sheets

```python
# Creation
create_sheet(title="Budget 2026", folder_id=None)
create_sheet_from_template(template_id="...", title="...")

# Reading
get_sheet_data(sheet_id="...", range="Sheet1!A1:D10")
get_sheet_info(sheet_id="...")  # Metadata, sheet names, etc.
get_all_sheets(sheet_id="...")  # List tabs in spreadsheet

# Writing
update_sheet_cells(sheet_id="...", range="A1:B2", values=[["a", "b"], ["c", "d"]])
append_sheet_row(sheet_id="...", sheet_name="Sheet1", values=["col1", "col2", "col3"])
insert_sheet_row(sheet_id="...", row_index=5, values=[...])
delete_sheet_rows(sheet_id="...", start_row=5, end_row=10)

# Sheet management
add_sheet_tab(sheet_id="...", title="New Tab")
delete_sheet_tab(sheet_id="...", tab_id=123)
rename_sheet_tab(sheet_id="...", tab_id=123, new_name="...")

# Formatting (limited)
format_sheet_range(sheet_id="...", range="A1:D1", bold=True, background_color="#cccccc")

# Export
export_sheet(sheet_id="...", format="xlsx|csv|pdf", local_path="...")
```

#### 19.4 Google Slides (Lower Priority)

```python
create_presentation(title="Q1 Review")
get_presentation_outline(presentation_id="...")
add_slide(presentation_id="...", layout="TITLE_AND_BODY")
update_slide_text(presentation_id="...", slide_index=0, placeholder="TITLE", text="...")
export_presentation(presentation_id="...", format="pptx|pdf", local_path="...")
```

#### 19.5 Integration Features

```python
# Email + Drive
attach_drive_file(email_draft_id="...", file_id="...")  # Attach Drive file to email
save_attachment_to_drive(email_id="...", attachment_id="...", folder_id="...")

# Calendar + Drive
attach_file_to_event(event_id="...", file_id="...")
create_meeting_notes(event_id="...")  # Creates doc linked to event

# Cross-service search
search_all(query="quarterly report")  # Search emails, drive, calendar
```

#### Implementation Plan

**Phase 1: Core Drive (Est. 400 lines)**
- File listing, search, upload, download
- Folder operations
- Basic sharing

**Phase 2: Docs (Est. 300 lines)**
- Create, read, append, export
- Template support

**Phase 3: Sheets (Est. 400 lines)**
- Create, read, write cells
- Append rows, basic formatting
- Export

**Phase 4: Integration (Est. 200 lines)**
- Email attachments ↔ Drive
- Calendar ↔ Drive linking

**Phase 5: Slides (Est. 150 lines)**
- Basic creation and export
- Lower priority

**Total estimated scope:** ~1,500 lines code, ~500 lines tests

**New dependencies:**
- `google-api-python-client` (already have)
- Additional OAuth scopes:
  - `https://www.googleapis.com/auth/drive`
  - `https://www.googleapis.com/auth/documents`
  - `https://www.googleapis.com/auth/spreadsheets`
  - `https://www.googleapis.com/auth/presentations`

**New files:**
```
gmail_mcp/
├── drive/
│   ├── __init__.py
│   ├── files.py       # Core file operations
│   ├── docs.py        # Google Docs
│   ├── sheets.py      # Google Sheets
│   └── slides.py      # Google Slides
├── mcp/tools/
│   ├── drive_files.py
│   ├── drive_docs.py
│   ├── drive_sheets.py
│   └── drive_slides.py
tests/
├── test_drive_files.py
├── test_drive_docs.py
├── test_drive_sheets.py
└── test_drive_slides.py
```

**Recommendation:** Drive integration should be a separate project phase. Current Gmail+Calendar MCP is solid. Drive is a significant expansion that should be planned and executed as its own sprint.

---

## Completed

### ✅ NLP Date Parsing (2026-01-19)
- Added `dateparser` dependency
- Created centralized `date_parser.py`
- Updated all calendar functions to use NLP
- Added `recurrence_pattern` NLP for recurring events
- 50+ unit tests
- Updated README and docs

### ✅ Backlog Items 1,2,5,6,7,8,10 (2026-01-19)
- **#1 Week Range Handling**: `parse_week_range()` for "this week", "next week", "last week", "past N days"
- **#2 Better Error Messages**: `DATE_PARSING_HINT` constant with helpful examples in all date errors
- **#5 Past Date Preference**: `detect_date_direction()` auto-detects past/future based on keywords
- **#6 Working Hours Parsing**: `parse_working_hours()` supports "9-17", "9am-5pm", "9am to 5pm"
- **#7 Duration Parsing**: `parse_duration()` supports "1 hour", "90 minutes", "half hour"
- **#8 Email Search Date NLP**: `search_emails()` now accepts `after`, `before`, `date_range` NLP parameters
- **#10 Label Fuzzy Matching**: `apply_label()` and `remove_label()` accept `label` name parameter with case-insensitive matching

---

## Test Baseline

As of 2026-01-21 (post-tests-and-docs):
```
349 passed, 5 warnings
```

Warnings are dateparser deprecation notices (upstream issue, not actionable).

**Test additions (2026-01-21):**
- `test_contacts.py` - 11 tests for contact lookup
- `test_email_settings.py` - 11 tests for vacation responder
- `test_tools.py` - 5 tests for scheduled send
- `test_calendar_tools.py` - 17 tests for reminder parsing
- `test_conflict.py` - 5 tests for attendee availability
