# Product Spec — Job Application Agent
**Author:** Lalitha Pammi, Product Manager  
**Version:** 1.1  
**Status:** Agent 1 shipped · Agent 2 in progress · Multi-agent architecture planned  
**Last updated:** April 2026

---

## The Origin

Two things collided to spark this idea.

The first was a post by a tech executive describing how AI could be used to organize a desktop — not just search it, but actively structure it, name things, keep it clean. That idea stuck: what if AI didn't just answer questions but actively managed the artifacts of knowledge work?

The second was a pattern observed during job searching. Resume match scoring tools suggested keyword changes to improve match percentages. The result felt wrong — resumes started reading as inflated and generic rather than authentically representing real experience. The goal was AI that helps present genuine skills better, not game an algorithm. On top of that, every session customizing a resume and cover letter manually using Claude ended the same way — files in Downloads, no structure, no easy way to find what was sent where. The intentional approach was right, but the infrastructure to support it did not exist.

The insight: job seekers in 2026 are already using LLMs like Claude and ChatGPT to customize their resumes. That behavior is established. What nobody had built was the layer on top — something that captures those customized artifacts, organizes them, and manages the lifecycle automatically. No external service. No subscription. Full control.

---

## Problem Statement

### The job seeker's pain today

Most job seekers applying in 2026 face three distinct frustrations:

**1. Loss of control**
Auto-apply tools and resume inflation services apply on their behalf, often sending generic or keyword-stuffed resumes that don't represent them authentically. They have no visibility into what version of their resume went where.

There is a legitimate argument for auto-apply — in a competitive market, applying early increases visibility and some roles close within hours. This product does not dismiss that reality. However, it serves a different segment: job seekers who believe quality and authenticity outperform volume, particularly for mid-senior roles where recruiters scrutinize fit closely. For this user, applying with a tailored resume is a deliberate strategy, not a limitation.

**2. Disorganization**
Even job seekers who customize their own resumes end up with a chaotic file system — `resume_v3_final_FINAL_amazon.docx`, scattered cover letters, no way to quickly reference what they submitted for a specific role.

**3. Paying when there's no income**
Job search services charge monthly subscriptions regardless of whether the user is actively searching. When you're unemployed, paying $30-50/month for a tool you might not need next month is a real friction point.

---

## User Research

### Methodology
Informal interviews conducted at job seeker networking events in early 2026. Two personas emerged consistently.

---

### Persona 1 — The Intentional Applicant
**Role:** Mid-career Product Manager, actively job searching  
**Behavior:** Uses Claude to customize resume and cover letter for each application manually. Deliberately avoids auto-apply tools and keyword inflation services — believes the job seeker is responsible for what goes on their resume before it reaches a recruiter. Applies selectively and wants every application to authentically represent their experience.  
**Key quote:** *"I want to have control on when and what I update my resume to, instead of relying on external services."*  
**Pain points:**
- Paying for job search services with no guaranteed ROI when there is no income
- Manual file organization after every application eats time and creates confusion
- No single place to see everything applied to
- Keyword inflation tools produce resumes that feel unreal and don't represent the candidate honestly
- Existing AI resume tools push toward automation and volume — there is no tool built for the intentional, quality-first job seeker
- No guardrails around AI-generated content — tools rewrite resumes without the candidate's knowledge or consent

---

### Persona 2 — Melissa
**Role:** Fellow job seeker, mid-career professional  
**Behavior:** Uses AI tools to update her resume for each role. Attended job seeker networking events looking for better tools and strategies.  
**Key insights from conversation:**
- Already uses AI to update resume for every application — the workflow exists, it just needs structure
- Struggles to stay organized during the job search — loses track of which resume version went to which company
- Frustrated by auto-apply tools — feels they misrepresent her and remove her agency
- Wants more control over her applications — wants to know exactly what was sent, to whom, and when

**Validation:** Melissa's frustrations independently mirrored those of Persona 1 — discovered through separate conversations at different events. This was not an isolated experience — it was a consistent pattern across the target segment.

---

## Why Now

Three conditions align in 2026 that make this the right moment:

**1. LLM adoption is mainstream for job seekers**
90% of active job seekers are using Claude, ChatGPT, or Copilot to customize their resumes. The behavior is already there — they just lack the infrastructure layer on top of it.

**2. MCP is emerging as the universal standard**
Anthropic's Model Context Protocol, now open-sourced under the Linux Foundation, allows AI agents to connect directly to local filesystems, email, and cloud storage. This makes a locally-run, platform-agnostic agent possible without building a SaaS product.

**3. The market gap is real**
Existing tools either charge recurring subscriptions, take control away from the user, or require uploading personal documents to third-party servers. There is no lightweight, AI-native, user-controlled solution that lives inside the tools job seekers already use.

---

## Solution

### Job Application Agent

An MCP server that lives inside Claude Desktop (and eventually ChatGPT and Copilot) and automates the job application lifecycle — from resume customization to organized file storage to human-confirmed rejection cleanup.

**Core philosophy:** Meet users where they already are. No new app to download, no new account to create, no subscription to pay for. The agent plugs into the LLM the user already uses and adds structure to a workflow they are already doing.

**Responsible AI philosophy:** The agent never acts without the user's knowledge. It does not rewrite resumes from scratch, invent experience, or apply on the user's behalf. Every AI action is transparent, reversible, and grounded in what the user has already written. The human stays in control at every step.

**Scalability philosophy:** The product is built on a single MCP server that grows over time. Each new agent capability is added as a new MCP tool — Claude Desktop connects to the server once and automatically gains access to every tool. This means adding a new agent does not require a new server, a new connection, or any reconfiguration. The server is the stable foundation. Agents and tools are layered on top of it as the product evolves.

---

## Architecture

### Agent 1 — Resume Workflow (shipped)
**Pattern: Human-in-the-loop** — the user controls every step. The agent assists and executes, but nothing happens without explicit user intent. The "save now" trigger is a deliberate confirmation, not an automatic action.

```
User pastes JD + resume into Claude Desktop
        ↓
Preloaded prompts guide the workflow
(review · rewrite · cover letter)
        ↓
User says "save now" ← human approval required
        ↓
MCP tool extracts company + role + Job ID from JD
Confirms Job ID with user before saving
        ↓
Creates folder: Desktop/Job Applications/Company/Role-JobID/
Saves: job_description.txt · resume.txt · cover_letter.txt
```

**MCP primitives used:**
- `save_application()` — tool
- `list_applications()` — tool
- `review_resume` — prompt
- `rewrite_resume` — prompt
- `write_cover_letter` — prompt
- `save_now` — prompt

**Key design decisions:**
- Job ID as the primary key — no database needed, folder name is the lookup key
- Prompt guards — all prompts check for JD and resume before proceeding
- Existing folders respected — agent checks before creating, never overwrites
- Responsible AI guardrails — rewrite prompt explicitly instructs Claude to use only experience already in the resume, never invent or inflate
- Authentic over optimized — prompts instruct Claude to preserve the user's voice, not keyword-optimize for ATS systems

---

### Agent 2 — Rejection Watcher (in progress)
**Pattern: Human-in-the-loop** — the agent perceives and reasons autonomously, but the archiving action requires explicit user confirmation inside Claude Desktop. Nothing is deleted without the user saying so.

```
Runs at 6am daily (Python scheduler)
        ↓
Reads Outlook via Microsoft Graph API (last 24 hours)
        ↓
Claude API classifies each email:
Is this a rejection? Which Job ID? Which company?
        ↓
Writes pending actions to pending_actions.json
{company, job_id, folder_path, detected_date}
        ↓
User opens Claude Desktop and asks "any rejections?"
        ↓
check_rejections() tool reads pending_actions.json
Shows user: "Amazon JR-123456 — archive folder? Yes/No"
        ↓
User confirms → archive_application() tool fires
Moves folder → Desktop/Job Applications/_Rejected/
Writes to deletion_log.csv · clears from pending
```

**MCP primitives added:**
- `check_rejections()` — tool, reads pending_actions.json and presents to user
- `archive_application()` — tool, archives folder and writes to log on confirmation
- `check_pending` — prompt, natural language trigger to surface pending actions

**Key design decisions:**
- Human-in-the-loop — agent detects, human decides, agent executes
- Single MCP server — all tools live in server.py, no separate server needed
- pending_actions.json as the bridge between watcher.py and Claude Desktop
- Soft delete — moves to `_Rejected/` folder, never permanently deletes
- Audit log — every archival is recorded so nothing is lost silently
- Scalable tool pattern — new agent capabilities are new MCP tools, not new servers
- Responsible AI — no folder is ever deleted without explicit user confirmation, preventing irreversible mistakes

---

## Multi-Agent Scalability Vision

The product is designed around a single MCP server that hosts all tools. Agents are the reasoning workflows that use those tools. An orchestrator eventually routes between agents based on user intent.

```
Agents are the brains — they perceive, reason and decide
Tools are the hands — they execute specific actions
Orchestrator is the router — it decides which agent handles what
```

**Current state (v1 + v2) — 2 agents, 4 tools:**
```
Agent 1 — Resume Workflow
├── save_application()
└── list_applications()

Agent 2 — Rejection Watcher
├── check_rejections()
└── archive_application()
```

**Future state (v3+) — 5 agents, 10+ tools:**
```
Agent 1 — Resume Workflow
├── save_application()
└── list_applications()

Agent 2 — Rejection Watcher
├── check_rejections()
└── archive_application()

Agent 3 — Follow-up Agent
└── draft_followup()

Agent 4 — Interview Prep Agent
└── prep_interview()

Agent 5 — Status Tracker
└── track_status()

Orchestrator — routes between all agents
based on user intent and context
```

An orchestrator prompt will eventually route between these agents based on user intent — making Claude Desktop an AI-powered job search chief of staff for the intentional applicant.

---

## Tech Stack

| Layer | Technology |
|---|---|
| MCP server | Python + FastMCP |
| Package management | uv |
| LLM platform | Claude Desktop (v1) |
| Email reading | Microsoft Graph API + MSAL OAuth |
| Email classification | Anthropic Claude API |
| Background scheduler | Python `schedule` library |
| File storage | Local filesystem (v1) |
| Memory | Folder name as key (no DB) |
| Pending actions | pending_actions.json (lightweight bridge) |

---

## Product Roadmap

### v1 — shipped
- Agent 1 fully working in Claude Desktop
- 4 preloaded prompts
- Folder creation with Job ID naming
- Error handling and input validation
- Responsible AI guardrails — rewrites based only on existing resume, never invents experience
- Human-in-the-loop confirmation before every save action

### v2 — Agent 2 (in progress)
- Rejection watcher via Outlook OAuth
- Human-in-the-loop confirmation in Claude Desktop
- pending_actions.json as bridge between watcher and MCP server
- 2 new MCP tools: check_rejections() and archive_application()
- Deletion log and audit trail
- User chooses storage location at setup:
  - Local Desktop
  - SharePoint

### v3 — expanded lifecycle + multi-agent
- Orchestrator prompt routes between all agents
- Follow-up agent — detects emails needing a reply, drafts responses
- Interview prep agent — generates prep materials when interview is confirmed
- Status tracking: applied → interviewing → offer → rejected
- Application analytics: response rate by company type, role level, industry

### v4 — multi-platform (future)
- ChatGPT Custom GPT support
- Microsoft Copilot agent support
- Single MCP server works across all three platforms
- Install once, use everywhere

---

## Open Questions for v2

- How do we handle rejection emails that do not include a Job ID?
- What is the right default storage location for non-technical users?
- Should we add a simple onboarding flow for first-time setup?
- How do we handle the scheduler running when the machine is asleep at 6am?
- Should pending_actions.json have an expiry — what if the user never confirms?
