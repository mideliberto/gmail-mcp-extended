# Google MCP - Project Instructions

> **Location:** ~/dev/google-mcp/
> **Language:** Python
> **Purpose:** Gmail, Calendar, Drive, Docs, Chat MCPs

---

## Development Logging

Every completed task MUST end with an append to DEVLOG.md:

```markdown
### [Task Title]
**Origin:** [Issue #X | Chat decision | Bug report]
**Task:** [One-line description]
**Changes:**
- [What was done]
**Commits:** [hash]
**Status:** Complete | Partial | Blocked
**Notes:** [Optional - gotchas, follow-up needed]
```

If DEVLOG.md doesn't exist, create it first using the template in the repo.

Commit changes to DEVLOG.md as part of the task commit, or immediately after if the main commit is already pushed.

---

## Project-Specific Notes

- Virtual environment: `.venv/`
- Run tests: `.venv/bin/python -m pytest tests/`
- Syntax check: `.venv/bin/python -m py_compile <file>`

---
