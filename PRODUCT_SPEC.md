# Product Spec — Job Application Agent
**Author:** Lalitha Pammi, Product Manager  
**Version:** 1.0  
**Status:** Agent 1 shipped · Agent 2 in progress  
**Last updated:** March 2026

---

## The Origin

Two things collided to spark this idea.

The first was a post by a Microsoft executive describing how AI could be used to organize your desktop — not just search it, but actively structure it, name things, keep it clean. That idea stuck: what if AI didn't just answer questions but actively managed the artifacts of your life?

The second was personal frustration. While job searching, I tried resume match scoring tools that suggested keyword changes to improve my match percentage. The result felt wrong — my resume started reading as inflated and generic rather than authentically representing my experience. I stopped using them. I wanted AI to help me present my genuine skills better, not game an algorithm. On top of that, every time I customized a resume and cover letter manually using Claude, I was left with a mess of files on my desktop — no structure, no easy way to find what I had sent where. I was doing the right thing by being intentional, but the organization was completely on me with no support.

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

---

### Persona 2 — Melissa
**Role:** Fellow job seeker, mid-career professional  
**Behavior:** Uses AI tools to update her resume for each role. Attended job seeker networking events looking for better tools and strategies.  
**Key insights from conversation:**
- Already uses AI to update resume for every application — the workflow exists, it just needs structure
- Struggles to stay organized during the job search — loses track of which resume version went to which company
- Frustrated by auto-apply tools — feels they misrepresent her and remove her agency
- Wants more control over her applications — wants to know exactly what was sent, to whom, and when

**Validation:** Melissa's frustrations independently matched mine. This was not a unique problem — it was a pattern.

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

An MCP server that lives inside Claude Desktop (and eventually ChatGPT and Copilot) and automates the job application lifecycle — from resume customization to organized file storage to automatic rejection cleanup.

**Core philosophy:** Meet users where they already are. No new app to download, no new account to create, no subscription to pay for. The agent plugs into the LLM the user already uses and adds structure to a workflow they are already doing.

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

---

### Agent 2 — Rejection Watcher (in progress)
**Pattern: Fully autonomous** — runs entirely without user input. The agent perceives (email), reasons (is this a rejection? which role?), and acts (archive folder, write log) on its own schedule. The user never needs to trigger it.

```
Runs at 6am daily (Python scheduler)
        ↓
Reads Gmail/Outlook via OAuth (last 24 hours)
        ↓
Claude API classifies each email:
Is this a rejection? Which Job ID?
        ↓
Matches Job ID to folder name on Desktop
        ↓
Archives folder → Desktop/Job Applications/_Rejected/
Writes to deletion_log.csv: company · role · Job ID · date
```

**Key design decisions:**
- Job ID matching — rejection emails from most ATS systems include the Job ID
- Soft delete — moves to `_Rejected/` folder, never permanently deletes
- Audit log — every deletion is recorded so nothing is lost silently

---

## Tech Stack

| Layer | Technology |
|---|---|
| MCP server | Python + FastMCP |
| Package management | uv |
| LLM platform | Claude Desktop (v1) |
| Email reading | Gmail API + OAuth |
| Email classification | Anthropic Claude API |
| Background scheduler | Python `schedule` library |
| File storage | Local filesystem (v1) |
| Memory | Folder name as key (no DB) |

---

## Product Roadmap

### v1 — shipped
- Agent 1 fully working in Claude Desktop
- 4 preloaded prompts
- Folder creation with Job ID naming
- Error handling and input validation

### v2 — Agent 2 + storage choice
- Agent 2 rejection watcher (Gmail + Outlook)
- User chooses storage location at setup:
  - Local Desktop
  - SharePoint
- Deletion log and audit trail

### v3 — expanded lifecycle
- Status tracking: applied → interviewing → offer → rejected
- Interview prep prompts
- Application analytics: response rate by company type, role level, industry
- Export to job tracker spreadsheet

### v4 — multi-platform (future)
- ChatGPT Custom GPT support
- Microsoft Copilot agent support
- Single MCP server works across all three platforms
- Install once, use everywhere

---

## Open Questions for v2

- How do we handle rejection emails that do not include a Job ID?
- Should the rejection watcher run as a background process or be triggered manually?
- What is the right default storage location for non-technical users?
- Should we add a simple onboarding flow for first-time setup?
