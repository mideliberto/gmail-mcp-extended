# Development Log

> **Purpose:** Durable record of development tasks, decisions, and outcomes.
> **Maintainer:** Appended by Claude Code after each task completion.
> **Format:** Reverse chronological (newest first within each date).

---

## 2026-02-23

### Add file_path parameter to create_drive_file and update_drive_file
**Origin:** Chat decision
**Task:** Add file_path parameter for large file uploads that bypass MCP parameter size limits
**Changes:**
- Added `file_path` parameter to `create_drive_file` and `update_drive_file` tool definitions
- Changed `mime_type` default to `None` with auto-detection from file extension
- Added mutual exclusivity validation (content vs file_path)
- Added `create_file_from_path()` and `update_file_from_path()` to DriveProcessor using MediaFileUpload
- Files modified: `drive_mcp/mcp/tools/__init__.py`, `drive_mcp/drive/processor.py`, `CHANGELOG.md`
**Commits:** (see below)
**Status:** Complete
**Notes:** MediaFileUpload was already imported but unused. Existing content-based code paths unchanged.

---

## 2026-02-09

### Fix labelIds KeyError on empty/missing labels
**Origin:** Bug report - get_email fails on scheduled sends
**Task:** Replace unsafe msg["labelIds"] with msg.get("labelIds", [])
**Changes:**
- gmail_mcp/mcp/tools/email_read.py:208 - changed to safe .get() access
**Commits:** [this commit]
**Status:** Complete
**Notes:** Only one unsafe access found; other labelIds references already used .get()

### Shared file search and text export for Drive MCP
**Origin:** Chat spec - PWP workflow requirements
**Task:** Add shared_with_me parameter to search and export_format parameter to read
**Changes:**
- processor.py: Added shared_with_me parameter to search_files(), appends sharedWithMe = true to query
- processor.py: Added export_format parameter to read_file(), returns correct export mime type for text detection
- tools/__init__.py: Added shared_with_me to search_drive_files with docstring
- tools/__init__.py: Added export_format to read_drive_file with full docstring for formats
**Commits:** 01dc39e
**Status:** Complete
**Notes:** Critical fix - mime_type now set to export mime (e.g., text/plain) so tool layer text detection works

---

## 2026-02-01

### Hierarchical CLAUDE.md structure
**Origin:** Chat decision - standardize project instructions
**Task:** Create ~/dev/CLAUDE.md with universal standards, slim down per-repo files
**Changes:**
- Created ~/dev/CLAUDE.md with roles, directives, error handling, DEVLOG requirement
- Replaced per-repo CLAUDE.md with project-specific content only
- Per-repo files now reference ~/dev/CLAUDE.md
**Commits:** 645d1f3
**Status:** Complete
**Notes:** ~/dev/CLAUDE.md is not in a git repo; it's a standalone file read by Claude Code

### CLAUDE.md and DEVLOG requirement
**Origin:** Chat decision - development logging practice
**Task:** Create project CLAUDE.md with DEVLOG requirement
**Changes:**
- Created CLAUDE.md with project info and DEVLOG requirement
- Added this entry to DEVLOG.md
**Commits:** [this commit]
**Status:** Complete
**Notes:** None

### rsvp_event calendar_id parameter
**Origin:** Consistency fix (found during calendar_id work)
**Task:** Add calendar_id parameter to rsvp_event for full consistency
**Changes:**
- Added calendar_id: str = "primary" to rsvp_event
- Updated API calls at lines 902, 917
**Commits:** 1204a52
**Status:** Complete
**Notes:** Commit also included pending changes from 2026-01-31 session (timezone fixes, doc deletions)

### calendar_id parameter consistency (Issue #12)
**Origin:** Issue #12
**Task:** Add calendar_id parameter to all calendar tools
**Changes:**
- Added calendar_id to: create_calendar_event, create_recurring_event, list_calendar_events, update_calendar_event, delete_calendar_event, add_travel_buffer
- Updated docs/gmail-mcp.md with parameter documentation and examples
**Commits:** 8679109, a1d08b6
**Status:** Complete
**Notes:** None

---

## 2026-01-31

### Documentation cleanup and reorganization
**Origin:** Chat design session - MCP standardization
**Task:** Consolidate and clean up documentation structure
**Changes:**
- Deleted obsolete docs: overview.md, structure.md, setup.md, google-docs-api-lists.md
- Content merged into README.md and per-server docs
- Updated tool counts and removed references to deleted code
**Commits:** (included in 1204a52)
**Status:** Complete
**Notes:** Changes were staged but not committed separately; picked up in next day's commit

### Dead code removal
**Origin:** Code review findings
**Task:** Remove harmful and dead code identified in review
**Changes:**
- Deleted detect_events_from_email (created garbage calendar invites)
- Deleted create_formatted_doc, debug_doc_structure, test_gdocs_render from drive_mcp
- Deleted gdocs_builder.py, gdocs_test.py, test_docs_formatter.py
- Deleted duplicate find_unsubscribe_link from bulk.py
**Commits:** (included in 1204a52)
**Status:** Complete
**Notes:** Should have been committed same day; got bundled into later commit

---

