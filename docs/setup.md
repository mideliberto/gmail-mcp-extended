# Gmail MCP Setup Guide

Complete guide to setting up Gmail MCP from scratch, including Google Cloud project configuration.

## Prerequisites

- Python 3.11+
- A Google account
- Claude Code or Claude Desktop installed

---

## Part 1: Google Cloud Project Setup

This is the most involved part of setup. Follow each step carefully.

### 1.1 Create a Google Cloud Project

**Step 1:** Go to [Google Cloud Console](https://console.cloud.google.com/)

If this is your first time, you may need to agree to Terms of Service.

**Step 2:** Create a new project

Look at the top-left of the page, next to "Google Cloud". You'll see either:
- "Select a project" (if you have no projects)
- A project name (if you have existing projects)

Click that dropdown, then:
1. In the popup, click **New Project** (top right of the popup)
2. **Project name:** Enter `gmail-mcp` (or any name you like)
3. **Organization:** Leave as "No organization" (unless you're using a work account)
4. **Location:** Leave as default
5. Click **Create**

**Step 3:** Wait for project creation (takes 10-30 seconds)

You'll see a notification in the top right. Once done, click **Select Project** in that notification, OR click the project dropdown again and select your new project.

**Verify:** The project dropdown should now show `gmail-mcp` (or your chosen name).

---

### 1.2 Enable Required APIs

You need to enable 3 APIs. This tells Google "this project is allowed to use these services."

**Step 1:** Navigate to the API Library

In the left sidebar:
1. Click **APIs & Services** (you may need to scroll or click the hamburger menu ☰)
2. Click **Library**

**Step 2:** Enable Gmail API

1. In the search box, type `Gmail API`
2. Click on **Gmail API** in the results (the one by Google)
3. Click the big blue **Enable** button
4. Wait for it to enable (a few seconds)

**Step 3:** Enable Google Calendar API

1. Click **← APIs & Services** in the top breadcrumb to go back to the library
2. Search for `Google Calendar API`
3. Click on **Google Calendar API**
4. Click **Enable**

**Step 4:** Enable People API

1. Go back to the library
2. Search for `People API`
3. Click on **People API** (also called "Google People API")
4. Click **Enable**

**Verify:** Go to **APIs & Services → Enabled APIs & services**. You should see all 3 APIs listed.

---

### 1.3 Configure OAuth Consent Screen

This is where you tell Google about your "app" - even though it's just for personal use.

**Step 1:** Navigate to OAuth consent screen

In the left sidebar:
1. Click **APIs & Services**
2. Click **OAuth consent screen**

**Step 2:** Choose user type

You'll see two options:
- **Internal:** Only for Google Workspace (company) accounts
- **External:** For personal Gmail accounts

Select **External** (even if you have Workspace, External works for everyone).

Click **Create**.

**Step 3:** Fill in App Information (Page 1 of 4)

Fill in these fields:

| Field | What to Enter |
|-------|---------------|
| **App name** | `Gmail MCP` (or anything you want) |
| **User support email** | Select your email from dropdown |
| **App logo** | Skip (optional) |
| **Application home page** | Skip (optional) |
| **Application privacy policy link** | Skip (optional) |
| **Application terms of service link** | Skip (optional) |
| **Authorized domains** | Skip (leave empty) |
| **Developer contact information** | Enter your email address |

Click **Save and Continue**.

---

### 1.4 Add OAuth Scopes (Page 2 of 4)

Scopes define what permissions your app requests. This is the trickiest part.

**Step 1:** Click **Add or Remove Scopes**

A sidebar panel will open on the right.

**Step 2:** Find the "Manually add scopes" section

Scroll down in the sidebar. You'll see:
- A table of common scopes (checkboxes)
- Below that: **"Manually add scopes"** with a text box

**Step 3:** Paste all scopes

Copy this entire block and paste it into the text box:

```
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.labels
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/gmail.settings.basic
https://www.googleapis.com/auth/calendar.readonly
https://www.googleapis.com/auth/calendar.events
https://www.googleapis.com/auth/contacts.readonly
https://www.googleapis.com/auth/contacts
https://www.googleapis.com/auth/userinfo.email
https://www.googleapis.com/auth/userinfo.profile
openid
```

**Step 4:** Click **Add to Table**

The scopes should appear in the table above.

**Step 5:** Click **Update** (bottom of sidebar)

**Step 6:** Verify scopes were added

You should see:
- "Your sensitive scopes" section with several scopes
- "Your restricted scopes" section with Gmail scopes

Don't worry about the "sensitive" and "restricted" warnings - this is expected for email/calendar access.

**Step 7:** Click **Save and Continue**

---

### 1.5 Add Test Users (Page 3 of 4)

**IMPORTANT:** While your app is in "Testing" mode, ONLY users you add here can authenticate. If you skip this, you'll get "Access denied" errors.

**Step 1:** Click **+ Add Users**

**Step 2:** Enter your email address

Type your full Gmail address (e.g., `yourname@gmail.com`).

If you want others to use this MCP (family members, etc.), add their emails too. You can add up to 100 test users.

**Step 3:** Click **Add**

**Step 4:** Click **Save and Continue**

---

### 1.6 Summary (Page 4 of 4)

Review your settings. You should see:
- App name: Gmail MCP
- User support email: your email
- Scopes: 12 scopes listed
- Test users: 1 user (you)

Click **Back to Dashboard**.

**Note:** Your app will show "Publishing status: Testing". This is correct! You do NOT need to publish the app. It works perfectly in Testing mode for personal use.

---

### 1.7 Create OAuth Credentials

Now you create the actual client ID and secret that the MCP uses.

**Step 1:** Navigate to Credentials

In the left sidebar:
1. Click **APIs & Services**
2. Click **Credentials**

**Step 2:** Create OAuth Client ID

1. Click **+ Create Credentials** (top of page)
2. Select **OAuth client ID**

**Step 3:** Choose application type

**IMPORTANT:** Select **Desktop app** (NOT "Web application")

Common mistake: Selecting "Web application" will cause authentication to fail.

**Step 4:** Name it

- **Name:** `Gmail MCP Desktop` (or anything you want)

**Step 5:** Click **Create**

**Step 6:** Save your credentials!

A popup will show:
- **Client ID:** Something like `185105316119-xxxxx.apps.googleusercontent.com`
- **Client Secret:** Something like `GOCSPX-xxxxxxxxxxxx`

**CRITICAL:** Save both of these somewhere secure right now! You can also:
- Click **Download JSON** to save as a file
- Click **OK** to close (you can view them later under Credentials)

**To view credentials later:** Go to Credentials → Click on your OAuth client → You'll see Client ID and can reveal Client Secret.

---

### 1.8 Summary: What You Should Have

After Part 1, you should have:

| Item | Example |
|------|---------|
| Project name | `gmail-mcp` |
| APIs enabled | Gmail API, Google Calendar API, People API |
| OAuth consent screen | Configured with 12 scopes |
| Test users | Your email added |
| Client ID | `123456789-xxx.apps.googleusercontent.com` |
| Client Secret | `GOCSPX-xxxxxxxxxx` |

Save the Client ID and Client Secret - you'll need them in Part 3.

---

## Part 2: Install Gmail MCP

### 2.1 Clone and Set Up

```bash
# Clone the repository
git clone https://github.com/yourusername/gmail-mcp.git
cd gmail-mcp

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
```

### 2.2 Generate Encryption Key

Generate a key to encrypt your OAuth tokens at rest:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Save this key - you'll need it for configuration.

---

## Part 3: Configure Claude Code / Claude Desktop

### 3.1 Claude Code Configuration

Edit `~/.claude/settings.json` (create if it doesn't exist):

```json
{
  "mcpServers": {
    "gmail-mcp": {
      "command": "/path/to/gmail-mcp/.venv/bin/mcp",
      "args": ["run", "/path/to/gmail-mcp/gmail_mcp/main.py:mcp"],
      "cwd": "/path/to/gmail-mcp",
      "env": {
        "PYTHONPATH": "/path/to/gmail-mcp",
        "CONFIG_FILE_PATH": "/path/to/gmail-mcp/config.yaml",
        "GOOGLE_CLIENT_ID": "your-client-id.apps.googleusercontent.com",
        "GOOGLE_CLIENT_SECRET": "GOCSPX-your-client-secret",
        "TOKEN_ENCRYPTION_KEY": "your-generated-encryption-key"
      }
    }
  }
}
```

Replace `/path/to/gmail-mcp` with your actual path (e.g., `/Users/yourname/gmail-mcp`).

### 3.2 Claude Desktop Configuration

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or equivalent:

```json
{
  "mcpServers": {
    "gmail-mcp": {
      "command": "/path/to/gmail-mcp/.venv/bin/mcp",
      "args": ["run", "/path/to/gmail-mcp/gmail_mcp/main.py:mcp"],
      "cwd": "/path/to/gmail-mcp",
      "env": {
        "PYTHONPATH": "/path/to/gmail-mcp",
        "CONFIG_FILE_PATH": "/path/to/gmail-mcp/config.yaml",
        "GOOGLE_CLIENT_ID": "your-client-id.apps.googleusercontent.com",
        "GOOGLE_CLIENT_SECRET": "GOCSPX-your-client-secret",
        "TOKEN_ENCRYPTION_KEY": "your-generated-encryption-key"
      }
    }
  }
}
```

---

## Part 4: First-Time Authentication

1. Start Claude Code or Claude Desktop
2. Ask Claude to check your email or calendar
3. Claude will use the `authenticate` tool, which opens a browser
4. Log in with your Google account and grant permissions
5. You'll be redirected to `localhost:8000/auth/callback`
6. Authentication complete! Tokens are stored encrypted in `~/gmail_mcp_tokens/`

---

## Configuration Files Reference

### Files in the Repository (Public)

| File | Purpose |
|------|---------|
| `config.yaml` | Server structure, scopes, defaults (NO secrets) |
| `config.yaml.example` | Template for reference |

### Files Outside Repository (Private)

| File | Purpose |
|------|---------|
| `~/.claude/settings.json` | Claude Code MCP config with secrets |
| `~/Library/Application Support/Claude/claude_desktop_config.json` | Claude Desktop config |
| `~/gmail_mcp_tokens/tokens.json` | Encrypted OAuth tokens |

---

## Updating OAuth Scopes

If you need to add new scopes (e.g., for new features):

1. **Google Cloud Console:** Add scope to OAuth consent screen
2. **config.yaml:** Add scope to `google.auth_scopes`
3. **Re-authenticate:**
   ```
   Ask Claude: "logout and re-authenticate"
   ```
   Or delete `~/gmail_mcp_tokens/tokens.json` and authenticate fresh

---

## Troubleshooting

### "Access blocked: This app's request is invalid"
- Make sure you're using **Desktop app** credentials, not Web application
- Check that redirect_uri in config.yaml matches: `http://localhost:8000/auth/callback`

### "This app isn't verified"
- Click **Advanced** → **Go to [app name] (unsafe)**
- This is expected for personal/test apps that aren't published

### "User not in test users list"
- Go to OAuth consent screen → Test users → Add your email

### "Token expired" or "Invalid credentials"
- Delete `~/gmail_mcp_tokens/tokens.json`
- Re-authenticate

### "contacts_api_enabled not found"
- Update config.yaml to include the contacts section (see config.yaml.example)

---

## Security Best Practices

1. **Never commit secrets to git** - Client ID, Client Secret, and Encryption Key stay in `~/.claude/settings.json`

2. **Rotate credentials if exposed** - If secrets are ever visible in logs/screenshots:
   - Google Cloud Console → Credentials → Delete old credential → Create new
   - Generate new encryption key
   - Update `~/.claude/settings.json`
   - Re-authenticate

3. **Use test mode** - No need to publish your OAuth app for personal use

4. **Backup your config privately** - See [Private Config Backup](#private-config-backup) below

---

## Private Config Backup

Your `~/.claude/settings.json` contains secrets and shouldn't be in a public repo. Options for backup:

### Option 1: Private Git Repo (Recommended)

```bash
# Create a private repo for dotfiles/configs
mkdir -p ~/dotfiles-private
cd ~/dotfiles-private
git init

# Copy your config
cp ~/.claude/settings.json ./claude-settings.json

# Create .gitignore in gmail-mcp that points here
echo "# Private config stored in ~/dotfiles-private" > ~/gmail-mcp/.env.example

# Commit to private repo
git add .
git commit -m "Claude MCP configuration"
git remote add origin git@github.com:yourusername/dotfiles-private.git
git push -u origin main
```

### Option 2: Encrypted Local Backup

```bash
# Encrypt your settings
tar -czf - ~/.claude/settings.json | openssl enc -aes-256-cbc -salt -out ~/claude-backup.enc

# To restore:
openssl enc -d -aes-256-cbc -in ~/claude-backup.enc | tar -xzf - -C /
```

### Option 3: Password Manager

Store the JSON contents in your password manager (1Password, Bitwarden, etc.) as a secure note.

---

## Quick Reference

| Task | Command/Location |
|------|------------------|
| Check auth status | Ask Claude: "check gmail auth status" |
| Re-authenticate | Ask Claude: "logout and authenticate" |
| View tokens location | `~/gmail_mcp_tokens/tokens.json` |
| View Claude Code config | `~/.claude/settings.json` |
| Run tests | `cd gmail-mcp && pytest tests/ -v` |
| View logs | Ask Claude: "what gmail MCP tools are available" |
