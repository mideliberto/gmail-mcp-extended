# Gmail MCP Backlog

## Development Workflow

**Before any major work:**
1. `cd /Users/mike/gmail-mcp && source .venv/bin/activate`
2. `pytest tests/ -v --tb=short` - capture baseline (417 passed)
3. Plan the changes (update this file or create issue)
4. Implement changes
5. `pytest tests/ -v --tb=short` - compare output
6. Fix any regressions
7. Update docs (`README.md`, `docs/overview.md`)
8. Commit and push

---

## Current State (2026-01-23)

**Version:** 2.3.0 - Monorepo with 3 MCP servers (backlog complete)

| Server | Tools | Status |
|--------|-------|--------|
| gmail-mcp | 95 | Complete |
| drive-mcp | 54 | Complete |
| docs-mcp | 32 | Complete |
| chat-mcp | 24 | Active |
| **Total** | **205** | |

**Test baseline:** 417 passed, 5 warnings

---

## Priority Matrix

| Priority | Items | Status |
|----------|-------|--------|
| **P1 - High** | Google Docs formatting (#58) | ✅ Complete |
| **P1 - High** | Calendar get/duplicate (#47-48) | ✅ Complete |
| **P2 - Medium** | Professional doc styling (#59) | Open |
| **P2 - Medium** | Drive star/comments (#39-43) | ✅ Complete |
| **P3 - Low** | Drive shared drives admin (#36-38) | ✅ Complete |
| **P3 - Low** | Drive revisions (#44-46) | ✅ Complete |
| **P3 - Low** | PDF advanced (#49-53) | ✅ Complete |

---

## Bugs / Known Issues

### #55 - Token/Salt Mismatch on Re-auth (P2)
**Problem:** When re-authenticating, if a salt file exists but token doesn't (or vice versa), or if auth runs with wrong config path, the salt and token become mismatched. Token decryption fails with `InvalidToken`.

**Root cause:**
- Multiple config files (`config.yaml` vs `config-pwp.yaml`) with different token paths
- Singleton TokenManager caches salt in memory
- MCP servers cache credentials and don't reload after re-auth

**Workaround:** Delete both `tokens.json` AND `encryption_salt` from token dir, restart Claude Code, re-auth.

**Fix options:**
1. Add `reload_credentials` tool to force refresh without restart
2. Add startup check: if token exists but can't decrypt, delete both and prompt re-auth
3. Store salt inside encrypted token file (single file = no mismatch)

### #56 - MCP Servers Cache Credentials (P2)
**Problem:** After re-authenticating, MCP servers still use cached credentials. Must restart Claude Code.

**Fix:** Add `logout` or `reload_auth` tool that clears singleton caches and reloads from disk.

### #57 - Chat API: Return User Display Names (P2) [GitHub #10](https://github.com/mideliberto/gmail-mcp-extended/issues/10)
**Problem:** `list_chat_members` only returns user IDs (e.g., `users/106781799854903048523`), not display names. Have to infer participant names from message content.

**Fix:** Call People API or Directory API to resolve user IDs to display names. Cache results to avoid repeated lookups.

**Workaround:** Track participant names in vault `0-inbox/chat-tracking.md` after manual identification.

### #60 - docgen-mcp Auth Not Refreshed After Re-auth (P2)
**Problem:** docgen-mcp (in `/Users/mike/Vaults/TMA/docgen-mcp/`) shares tokens with gmail-mcp but doesn't pick up refreshed tokens after re-authentication. Even after running `authenticate` tool with `drive` scope, docgen-mcp still fails with "invalid authentication credentials".

**Root cause:**
- docgen-mcp caches OAuth2Client in memory (`cachedClient` in `google-auth.ts`)
- MCP server process must be restarted to reload tokens
- Related to #56 but separate codebase

**Workaround:** Restart Claude Code after re-authenticating.

**Fix options:**
1. Add `clear_credentials` function called before each API request if token is expired
2. Add a health check/reload mechanism to docgen-mcp
3. Share a reload signal between gmail-mcp and docgen-mcp

---

## Recently Completed

### 2026-01-23 - Backlog Complete

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

### 2026-01-22 - Contact Hygiene, Subscription Management, Travel Buffer

**Contact Hygiene (21 new tools):**
- `find_duplicate_contacts` - Find potential duplicate contacts with fuzzy matching
- `find_stale_contacts` - Find contacts with no email activity in N months
- `find_incomplete_contacts` - Find contacts missing required fields
- `merge_contacts` - Merge duplicate contacts (requires write scope)
- `enrich_contact_from_email` - Extract contact info from email signatures (requires write scope)
- `export_contacts` - Export contacts to CSV
- `create_contact`, `update_contact`, `delete_contact` - Full CRUD operations (requires write scope)
- `list_contact_groups`, `create_contact_group`, `delete_contact_group` - Contact group management
- `add_contacts_to_group`, `remove_contacts_from_group` - Group membership management

**Subscription Management (6 new tools):**
- `setup_subscription_labels` - Create Subscriptions/Review, Retained, Unsubscribed labels
- `find_subscription_emails` - Find newsletter/subscription senders with unsubscribe links
- `get_unsubscribe_link` - Extract unsubscribe link from email headers/body
- `unsubscribe_and_cleanup` - Full unsubscribe workflow (get link, create filter, archive)
- `create_subscription_filter` - Create filter for subscription sender
- `mark_sender_as_junk` - Filter sender to trash + report spam

**Calendar (1 new tool):**
- `add_travel_buffer` - Add blocking travel time event before meetings

### 2026-01-22 - Drive & Docs MCP Servers
- **drive-mcp (43 tools):** Full Google Drive integration
  - File operations (12): list, search, get, read, create, update, rename, move, copy, trash, restore, delete
  - Folders (3): create, tree, path
  - Workspace files (4): create doc/sheet/slides, export
  - Sharing (6): permissions, share, update, remove, transfer ownership, shortcuts
  - Shared Drives (3): list, get, members
  - Bulk ops (4): move, trash, delete, share
  - Activity & Quota (2)
  - Labels (6): list, get, file labels, set, remove, search
  - OCR (3): upload with OCR, OCR existing, PDF OCR

- **docs-mcp (27 tools):** Local document processing (no Google auth)
  - Office reading (3): DOCX, XLSX, PPTX
  - Office templates (6): fill and create from templates
  - Office export (3): to markdown/CSV
  - PDF (7): read, metadata, markdown, images, merge, split, forms
  - Local OCR (4): image, PDF, auto-detect, to vault
  - Vault integration (4): save text/file/batch, doc to vault

### 2026-01-21 - Email & Calendar Features
- Scheduled Send, Attendee Free/Busy, Event Reminders
- Contact Lookup, Vacation Responder
- Draft Management, Retention Labels

---

### Bugs / Missing

- [x] **#58 - drive-mcp: Professional Google Docs creation (P1)** - ✅ Fixed 2026-01-29. `create_formatted_doc(name, markdown_content, parent_id)` now properly converts markdown to formatted Google Docs. Supports headings (H1-H6), bold/italic, bullet/numbered lists, horizontal rules, and tables (rendered as formatted text with bold headers). Key fix: insert all text in single operation, then apply formatting in reverse index order.

- [ ] **#63 - drive-mcp: `create_formatted_doc` bold parsing broken (P2)** - Bold text mid-word or spanning formatted regions doesn't apply correctly. Example: "**Critical**" renders with bold at start and end but not middle. Likely an index calculation bug when applying `UpdateTextStyleRequest` - the start/end indices aren't capturing the full range.

- [x] **#64 - drive-mcp: `create_formatted_doc` numbered lists don't enumerate (P1)** - ✅ Fixed 2026-01-30.

  **Original issue:** Numbered lists rendered as "1. 1. 1." instead of "1. 2. 3." because each paragraph got a separate `listId`.

  **Root cause:** `insertText` and `createParagraphBullets` were in separate batchUpdate calls. When paragraphs exist before bullets are applied in a separate API call, each paragraph gets its own `listId`.

  **Fix:** Keep `createParagraphBullets` in the SAME batchUpdate as `insertText`. When all requests are in one batch, paragraphs share the same `listId` and enumerate correctly.

  **Key insight:** From [Kanshi Tanaike's article](https://medium.com/google-cloud/techniques-for-creating-nested-lists-on-google-documents-using-google-docs-api-e6bd2c1718d8):
  - Insert ALL text at once with `\n` separating paragraphs
  - Apply `createParagraphBullets` with single range covering all paragraphs
  - Both requests in the SAME batchUpdate

  **References:**
  - [Google Docs API: Work with lists](https://developers.google.com/workspace/docs/api/how-tos/lists)
  - [CreateParagraphBulletsRequest docs](https://developers.google.com/docs/api/reference/rest/v1/documents/request)

- [ ] **#60 - drive-mcp: Table cell styling API error (P2)** - `create_formatted_doc` fails on table cell styling with error: `oneof field 'cells' is already set. Cannot set 'tableRange'`. The API rejects requests that specify both fields. Tables are created but lack header styling. Fix: use either `cells` OR `tableRange` in `UpdateTableCellStyleRequest`, not both.

- [ ] **#59 - drive-mcp: Professional document styling (P2)** - `create_formatted_doc` produces structurally correct but visually basic documents (plain fonts, no colors, default spacing). Claude.ai artifacts look polished because they render HTML/CSS. Options:
  1. **Template-based:** Add `create_doc_from_template(template_id, replacements)` - clone a styled template, replace placeholder text
  2. **Style presets:** Add `style_preset` param to `create_formatted_doc` (e.g., "proposal", "memo", "report") that applies predefined colors/fonts/spacing via `UpdateParagraphStyleRequest` and `UpdateTextStyleRequest`
  3. **Full styling API:** Expose font, color, spacing params directly

  Recommend: Template approach is cleanest. User creates styled templates in Docs UI, MCP clones and populates.

- [ ] **#61 - drive-mcp: `create_drive_file` upload conversion control (P2)** - Uploading .docx files results in broken Google Docs (can't open). Drive tries to auto-convert but fails silently. Need `convert` parameter:
  - `convert=False` (default): Keep as .docx, opens in compatibility mode. Preserves formatting, better for external sharing.
  - `convert=True`: Force conversion to native Google Doc. Better for collaboration but may mangle formatting.

  **Implementation:** In `processor.py` `create_file()`, when `convert=True`, set file metadata `mimeType` to `application/vnd.google-apps.document` to trigger explicit conversion. When `convert=False`, upload as-is without conversion.

- [ ] **#62 - drive-mcp: Upload .docx with proper Google Doc conversion (P2)** - Related to #61. When user wants a native Google Doc from a .docx, provide reliable conversion path. Options:
  1. Use Google Drive API import endpoint with explicit target mimeType
  2. Add `upload_and_convert(file_path, target_format)` tool
  3. Document that `create_formatted_doc` is preferred for Drive-native docs

  **Workaround:** Use `create_formatted_doc` with markdown content for native Google Docs, or keep .docx as-is and download locally.

- [ ] **#54 - drive-mcp: `create_label` missing** - Labels (6) has list, get, set, remove, search but no create. User tried to create "Processed" label, got "No such tool available". Either add `create_label` tool or document that labels must be created via Drive UI first.
- [x] **#55 - gmail-mcp: `list_drafts` broken** - Fixed in 3aff5a2. Changed to format="full" instead of invalid metadataHeaders.

### Future Ideas (not planned)

- **Import Contacts** - Import from CSV/vCard (requires contacts write scope)
- **Bulk Update Contacts** - Batch update contact fields
- **Smart Inbox Categorization** - Auto-categorize emails with ML
- **Email Analytics** - Response time tracking, volume analysis

---

## Scope Requirements Summary

**Currently available (readonly):**
- All contact discovery tools (duplicates, stale, incomplete)
- Export contacts
- All subscription discovery tools
- Travel time buffer

**Requires contacts write scope (user must re-auth if not already granted):**
- Merge contacts
- Enrich contact from email
- Contact CRUD (create, update, delete)
- Contact group operations

---

## Archived / Completed

<details>
<summary>Click to expand completed items</summary>

### ✅ Backlog Complete (#36-53) - 2026-01-23
- Calendar get/duplicate: `get_calendar_event()`, `duplicate_calendar_event()`
- Drive star/unstar: `star_drive_file()`, `unstar_drive_file()`
- Drive comments: `list_drive_comments()`, `add_drive_comment()`, `delete_drive_comment()`
- Drive revisions: `list_drive_revisions()`, `get_drive_revision()`, `download_drive_revision()`
- Shared drives admin: `create_shared_drive()`, `delete_shared_drive()`, `update_shared_drive()`
- PDF advanced: `rotate_pdf()`, `compress_pdf()`, `add_watermark()`, `encrypt_pdf()`, `decrypt_pdf()`

### ✅ Contact Hygiene (#24-28) - 2026-01-22
- `find_duplicate_contacts()` - Fuzzy matching with configurable threshold
- `find_stale_contacts()` - Cross-references Gmail activity
- `find_incomplete_contacts()` - Configurable required fields
- `merge_contacts()` - Combines info, deletes non-primary
- `enrich_contact_from_email()` - Signature parsing

### ✅ Unsubscribe Management (#22) - 2026-01-22
- Full discovery, triage, and cleanup workflow
- Labels for tracking subscription status

### ✅ Contact Bulk Ops (#29-32) - 2026-01-22
- Export implemented
- Contact groups full CRUD
- Import deferred (manual process via Google Contacts preferred)

### ✅ Travel Time Buffer (#17) - 2026-01-22
- `add_travel_buffer()` creates blocking event before meetings

### ✅ Contact CRUD (#33-35) - 2026-01-22
- `create_contact()`, `update_contact()`, `delete_contact()`

### ✅ Google Drive Integration (#19) - 2026-01-22
Implemented as separate `drive-mcp` server with 43 tools.

### ✅ Thread/Conversation View (#11) - 2026-01-19
- `get_thread()`, `get_thread_summary()`, `get_email(include_thread=True)`

### ✅ Draft Management (#12) - 2026-01-21
- `list_drafts()`, `get_draft()`, `update_draft()`, `delete_draft()`

### ✅ Scheduled Send (#13) - 2026-01-21
- `compose_email(send_at="tomorrow 8am")` creates draft + calendar reminder

### ✅ Vacation Responder (#14) - 2026-01-21
- `set_vacation_responder()`, `get_vacation_responder()`, `disable_vacation_responder()`

### ✅ Attendee Free/Busy (#15) - 2026-01-21
- `check_attendee_availability()`

### ✅ Event Reminders (#16) - 2026-01-21
- `reminders` parameter on all calendar event functions

### ✅ Contact Lookup (#18) - 2026-01-21
- `list_contacts()`, `search_contacts()`, `get_contact()`

### ✅ Retention Labels (#21) - 2026-01-21
- `setup_retention_labels()`, `enforce_retention_policies()`, `get_retention_status()`

### ✅ NLP Date Parsing - 2026-01-19
- Full natural language date support across all tools

### ✅ Bulk Operations Fix (#20) - 2026-01-19
- Fixed HTTP batch to use native batchModify endpoint

### ✅ Filter OAuth Scope (#23) - 2026-01-19
- Added `gmail.settings.basic` scope

</details>
