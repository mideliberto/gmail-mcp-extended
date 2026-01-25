# Gmail MCP Authentication Guide

## Architecture

Auth is handled in `gmail_mcp/auth/oauth.py`. Key functions:

| Function | Purpose |
|----------|---------|
| `login(scope_override)` | Generates OAuth URL, stores state |
| `process_auth_code(code, state)` | Exchanges auth code for tokens |
| `start_oauth_process(timeout, scope_override)` | Full flow with callback server |
| `get_credentials()` | Returns valid credentials, auto-refreshes if expired |
| `get_scopes(scope_override)` | Builds scope list from config or override |

## Critical: Multi-Account Scope Isolation

**Issue #11 fix** - In `login()`, the `include_granted_scopes` parameter **MUST be `"false"`**:

```python
auth_url, state = flow.authorization_url(
    access_type="offline",
    include_granted_scopes="false",  # CRITICAL - prevents scope pollution
    prompt="consent",
)
```

### Why This Matters

Setting `include_granted_scopes="true"` causes Google to merge scopes from ALL previous authorizations across different accounts/apps. This breaks multi-account setups (e.g., personal + work MCP instances) because `oauthlib` sees mismatched scopes and rejects the token with:

```
Scope has changed from "https://www.googleapis.com/auth/gmail.modify ..."
to "https://www.googleapis.com/auth/chat.memberships.readonly ..."
```

### If Users Hit This Error

1. Go to https://myaccount.google.com/permissions
2. Revoke access for the OAuth app
3. Clear browser cookies for accounts.google.com
4. Re-authenticate

## Scope Configuration

Scopes are built dynamically from `config.yaml` based on enabled APIs:

- `gmail_api_scopes` - always included
- `calendar_api_enabled` + `calendar_api_scopes`
- `contacts_api_enabled`
- `drive_api_enabled` + `drive_api_scopes`
- `chat_api_enabled` + `chat_api_scopes`

User info scopes (`userinfo.email`, `userinfo.profile`, `openid`) are always appended.

### Scope Override

Both `login()` and `start_oauth_process()` accept a `scope_override` parameter to request specific scopes instead of building from config:

```python
# Request only Gmail read access
login(scope_override=["https://www.googleapis.com/auth/gmail.readonly"])
```

## Token Storage

Tokens are managed by `TokenManager` in `gmail_mcp/auth/token_manager.py`:

- Encrypted at rest using PBKDF2-derived key
- Key sourced from `GMAIL_MCP_ENCRYPTION_KEY` env var
- Stored in `~/.gmail-mcp/tokens/` by default

## MCP Tools for Auth

| Tool | Purpose |
|------|---------|
| `authenticate(services)` | Starts browser-based OAuth flow. Optional `services` param filters scopes (e.g., `"gmail,calendar"`). |
| `check_auth_status` | Verifies current auth state and token validity |
| `logout` | Clears stored tokens |

## Security Notes

- State parameter is verified to prevent CSRF attacks
- Tokens auto-refresh when expired
- `prompt="consent"` ensures user always sees the consent screen (required for refresh tokens)
