# Job Application Agent

An MCP (Model Context Protocol) server that automates your job application workflow inside Claude Desktop. Customize your resume and cover letter with AI, then save everything to your desktop with one command — organized by company and job ID automatically.

---

## What It Does

- Helps you tailor your resume and cover letter to a specific job description using preloaded prompts
- Saves your resume, cover letter and job description to a structured folder on your Desktop when you say "save now"
- Organizes files automatically: `Desktop/Job Applications/Company/Role-JobID/`
- Works with your existing company folders — won't overwrite anything
- Lists all your saved applications on demand

---

## Requirements

- Mac (Windows support coming soon)
- [Claude Desktop](https://claude.ai/download) installed
- [uv](https://astral.sh/uv) installed
- Python 3.10 or higher

---

## Installation

**1. Clone the repo**
```bash
git clone https://github.com/Lalitha23/job-application-agent-.git
cd job-application-agent-
```

**2. Install dependencies**
```bash
uv add "mcp[cli]" anthropic schedule
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

## How to Use

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
    │       ├── resume.txt
    │       └── cover_letter.txt
    └── Microsoft/
        └── PM-REQ-789/
            ├── job_description.txt
            ├── resume.txt
            └── cover_letter.txt
```

### List your applications
Ask Claude anytime: `"list my applications"` and the agent will show all saved applications with dates.

---

## Troubleshooting

**Hammer icon not showing in Claude Desktop**
- Make sure you fully quit Claude Desktop (`pkill -f Claude`) and reopen it
- Check the config file path and username are correct
- Run `which uv` in terminal and make sure the path matches what is in the config

**Folder created with no name**
- Make sure the company name and role in the JD don't contain only special characters
- The agent sanitizes names so symbols are stripped — plain text works best

**Server not starting**
Check Claude Desktop logs:
```bash
tail -50 ~/Library/Logs/Claude/mcp.log
```

---

## Coming Soon — Agent 2

A background agent that runs at 6am daily, reads your Gmail for auto-rejection emails, matches them to saved applications by Job ID, and automatically archives the folder.

---

## License

MIT
