# Job Application Agent

An MCP (Model Context Protocol) server that automates your job application workflow inside Claude Desktop. Customize your resume and cover letter with AI, save everything organized by company and job ID — and automatically archive rejections when you delete the email.

---

## What It Does

**Agent 1 — Resume Workflow**
- Helps you tailor your resume and cover letter to a specific job description using preloaded prompts
- Saves your resume, cover letter and job description to a structured folder on your Desktop when you say "save now"
- Organizes files automatically: `Desktop/Job Applications/Company/Role-JobID/`
- Works with your existing company folders — won't overwrite anything
- Lists all your saved applications on demand

**Agent 2 — Rejection Watcher**
- Runs in the background every 4 hours
- Reads only your Outlook Deleted Items folder — never your full inbox
- When you delete a rejection email, the agent detects it, matches the Job ID to your saved folder, and archives it automatically
- Moves the folder to `_Rejected/` (soft delete — nothing is permanently removed)
- Logs every archival to `deletion_log.csv` so nothing is lost silently

---

## Quality & Evaluation

Agent 2's rejection classifier is evaluated against a curated test suite before any production deployment. The eval harness (`eval_classifier.py`) measures:

- **Precision** — of emails classified as rejections, how many actually were?
- **Recall** — of actual rejections, how many did we catch?
- **F1 score** — harmonic mean of precision and recall
- **Extraction accuracy** — when a rejection is correctly identified, did we extract the right Job ID and company?

### Severity-weighted failure analysis

Not all failures are equal. The eval assigns a severity tier to every test case based on the consequence of a wrong call:

| Severity | Example | Consequence |
|---|---|---|
| 🔴 Critical | Offer letter | Archives a folder the user must not lose |
| 🟠 High | Interview invite | Archives an active application |
| 🟡 Medium | Promotional email | Minor noise, recoverable |
| 🟢 Low | Clear rejection misclassified | Least harmful failure mode |

High and critical failures must be zero before deployment. Missing a rejection (false negative) is explicitly treated as less harmful than archiving something the user still needs.

### Confidence guardrail

The classifier returns a confidence level — `high`, `medium`, or `low` — alongside every decision. In production, `watcher.py` applies a minimum confidence threshold: low-confidence results are skipped and written to `review_needed.csv` for manual review rather than acted on automatically. This trades recall for safety — the agent does less rather than risk doing the wrong thing.

### Test coverage

The eval suite (`eval_data.json`) covers 15 test cases across 7 categories:

- Clear rejections with and without job IDs
- Informal recruiter rejections
- Interview invites (false positive risk)
- Offer letters (catastrophic false positive risk)
- Promotional emails from applied companies
- Newsletter emails that should never trigger
- Application confirmations (false positive risk)

To run the eval:
```bash
uv run eval_classifier.py
```

### Adding your own test cases

Add real emails from your own inbox to `eval_data.json` over time. Each entry follows this structure:

```json
{
  "id": "TC16",
  "category": "your_category",
  "subject": "Email subject line",
  "body": "Email body preview text",
  "expected": {
    "is_rejection": true,
    "job_id": "JR-123456",
    "company": "Company Name"
  },
  "severity_if_wrong": "high"
}
```

`severity_if_wrong` accepts: `critical`, `high`, `medium`, `low`

---

## Requirements

- Mac (Windows support coming soon)
- [Claude Desktop](https://claude.ai/download) installed
- [uv](https://astral.sh/uv) installed
- Python 3.10 or higher
- Outlook / Microsoft 365 account (for Agent 2)
- Azure app registration with `Mail.Read` scope (for Agent 2 — setup below)

---

## Installation

**1. Clone the repo**
```bash
git clone https://github.com/Lalitha23/job-application-agent-.git
cd job-application-agent-
```

**2. Install dependencies**
```bash
uv add "mcp[cli]" anthropic schedule msal requests
```

**3. Connect to Claude Desktop**

Open your Claude Desktop config file:
```bash
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Add the following inside the JSON (keep any existing preferences):
```json
{
  "mcpServers": {
    "job-application-agent": {
      "command": "/Users/YOUR_USERNAME/.local/bin/uv",
      "args": [
        "run",
        "--directory",
        "/Users/YOUR_USERNAME/Documents/GitHub/job-application-agent-",
        "server.py"
      ]
    }
  }
}
```

Replace `YOUR_USERNAME` with your Mac username. To find it run:
```bash
whoami
```

**4. Restart Claude Desktop**

Fully quit Claude Desktop and reopen it:
```bash
pkill -f Claude
```

Then reopen from your Applications folder.

**5. Verify connection**

Look for the hammer icon at the bottom of the Claude Desktop chat input. If you see it the agent is connected and ready.

---

## How to Use — Agent 1 (Resume Workflow)

### Step 1 — Paste your inputs
Start a new chat in Claude Desktop and paste both:
- Your job description
- Your current resume

### Step 2 — Use the prompts
Click the **+** icon next to the hammer to access preloaded prompts:

| Prompt | What it does |
|---|---|
| `review_resume` | Identifies top 5 gaps between your resume and the JD |
| `rewrite_resume` | Rewrites your resume tailored to the JD |
| `write_cover_letter` | Writes a 3 paragraph cover letter |
| `save_now` | Saves all 3 artifacts to your Desktop |

> Note: All prompts will ask you to paste the job description and resume first if they are not already in the conversation.

### Step 3 — Save your application
When you are happy with your resume and cover letter, click the **+** icon and select `save_now`.

The agent will:
1. Extract the company name and role from the JD
2. Look for a Job ID (e.g. JR-123456) and confirm it with you
3. Ask for the Job ID if it cannot find one — type `NONE` to use today's date instead
4. Save all 3 files to your Desktop

### Folder structure
```
Desktop/
└── Job Applications/
    ├── Amazon/
    │   └── Senior-PM-JR-123456/
    │       ├── job_description.txt
    │       ├── resume.docx
    │       └── cover_letter.docx
    ├── Microsoft/
    │   └── PM-REQ-789/
    │       ├── job_description.txt
    │       ├── resume.docx
    │       └── cover_letter.docx
    ├── _Rejected/
    │   └── Senior-PM-JR-111111/   ← archived by Agent 2
    └── deletion_log.csv
```

### List your applications
Ask Claude anytime: `"list my applications"` and the agent will show all saved applications with dates.

---

## How to Use — Agent 2 (Rejection Watcher)

Agent 2 runs separately from Claude Desktop as a background Python process. It watches your Outlook Deleted Items folder and automatically archives job folders when you delete a rejection email.

### How it works

You don't need to do anything special. The workflow is:

1. A rejection email arrives in Outlook
2. You read it and delete it as you normally would
3. Agent 2 picks it up from Deleted Items, verifies it's a rejection, matches the Job ID to your saved folder, and moves the folder to `_Rejected/`

The agent runs every 4 hours and looks back 48 hours — so it will catch deletions even if it wasn't running when you deleted the email.

### Step 1 — Create an Azure app registration

Agent 2 needs OAuth access to your Outlook Deleted Items. You'll set this up once in Azure.

1. Go to [portal.azure.com](https://portal.azure.com) and sign in with your Microsoft account
2. Search for **App registrations** and click **New registration**
3. Name it something like `job-application-agent`
4. Under **Supported account types** select **Personal Microsoft accounts only**
5. Under **Redirect URI** select **Public client/native** and enter `http://localhost`
6. Click **Register**
7. Copy the **Application (client) ID** — you'll need this
8. Go to **Certificates & secrets** → **New client secret** → copy the secret value
9. Go to **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated** → add `Mail.Read`
10. Click **Grant admin consent**

### Step 2 — Set environment variables

Add these to your shell profile (`.zshrc` or `.bash_profile`):

```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export MICROSOFT_CLIENT_ID="your-azure-app-client-id"
export MICROSOFT_CLIENT_SECRET="your-azure-app-client-secret"
```

Then reload:
```bash
source ~/.zshrc
```

### Step 3 — Run the watcher

```bash
cd /Users/YOUR_USERNAME/Documents/GitHub/job-application-agent-
uv run watcher.py
```

The first run will open a browser window asking you to sign in to your Microsoft account and grant the `Mail.Read` permission. After that, authentication is cached and runs silently.

You should see:
```
Rejection watcher started.
Runs every 4 hours. Looks back 48 hours.
Reads Deleted Items only — inbox is never accessed.
Press Ctrl+C to stop.
```

### What gets logged

Every archived folder is recorded in `Desktop/Job Applications/deletion_log.csv`:

| company | role_job_id | date_archived | original_path |
|---|---|---|---|
| Amazon | Senior-PM-JR-123456 | 2026-04-01 08:30 | /Users/.../Amazon/Senior-PM-JR-123456 |

Nothing is permanently deleted. Folders move to `_Rejected/` and the log is your audit trail.

---

## Troubleshooting

**Hammer icon not showing in Claude Desktop**
- Make sure you fully quit Claude Desktop (`pkill -f Claude`) and reopen it
- Check the config file path and username are correct
- Run `which uv` in terminal and make sure the path matches what is in the config

**Folder created with no name**
- Make sure the company name and role in the JD don't contain only special characters
- The agent sanitizes names so symbols are stripped — plain text works best

**Agent 1 server not starting**

Check Claude Desktop logs:
```bash
tail -50 ~/Library/Logs/Claude/mcp.log
```

**Agent 2 authentication failing**
- Make sure `MICROSOFT_CLIENT_ID` and `MICROSOFT_CLIENT_SECRET` are set correctly in your environment
- Check that the redirect URI in Azure is set to `http://localhost` under Public client/native
- Make sure `Mail.Read` permission has been granted in Azure

**Agent 2 not finding matching folders**
- The agent matches by Job ID first. Make sure the rejection email contains the same Job ID that was used when saving the application
- If no Job ID is found in the email, the agent falls back to matching by company name
- Check `deletion_log.csv` to see what was processed

**Agent 2 stops when terminal closes**

To keep it running in the background after closing your terminal:
```bash
nohup uv run watcher.py > watcher.log 2>&1 &
```

---

## Privacy

Agent 2 reads **only your Deleted Items folder** — never your full inbox. The OAuth scope is `Mail.Read` but the implementation explicitly calls only the `deleteditems` endpoint. The code is open source and auditable. The agent only processes emails you have already chosen to delete.

---

## License

MIT
