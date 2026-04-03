import os
import csv
import shutil
import schedule
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import msal
import requests
from anthropic import Anthropic

# --- Config ---
BASE_DIR = Path.home() / "Desktop" / "Job Applications"
REJECTED_DIR = BASE_DIR / "_Rejected"
LOG_FILE = BASE_DIR / "deletion_log.csv"

CLIENT_ID = os.environ["MICROSOFT_CLIENT_ID"]
CLIENT_SECRET = os.environ["MICROSOFT_CLIENT_SECRET"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# Scoped to Mail.Read — but implementation only ever calls
# the Deleted Items endpoint. Never reads the full inbox.
SCOPES = ["https://graph.microsoft.com/Mail.Read"]
GRAPH_API = "https://graph.microsoft.com/v1.0"

# Only read emails deleted in the last 48 hours
LOOKBACK_HOURS = 48

anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)


# --- Auth ---
def get_access_token() -> str:
    """Authenticate with Microsoft personal account and return access token."""
    app = msal.PublicClientApplication(
        client_id=CLIENT_ID,
        authority="https://login.microsoftonline.com/consumers"
    )

    # Try silent auth first (uses cached token)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            return result["access_token"]

    # Fall back to interactive login (opens browser once)
    result = app.acquire_token_interactive(scopes=SCOPES)

    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception(f"Authentication failed: {result.get('error_description')}")


# --- Email reading ---
def get_deleted_emails(token: str) -> list:
    """
    Fetch recently deleted emails from Deleted Items folder only.
    Never reads the full inbox — only what the user has chosen to discard.
    """
    since = (datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "$filter": f"receivedDateTime ge {since}",
        "$select": "subject,bodyPreview,from,receivedDateTime",
        "$top": 50,
        "$orderby": "receivedDateTime desc"
    }

    # Explicitly call Deleted Items endpoint only
    response = requests.get(
        f"{GRAPH_API}/me/mailFolders/deleteditems/messages",
        headers=headers,
        params=params
    )
    response.raise_for_status()
    return response.json().get("value", [])


# --- Classification ---
def classify_email(subject: str, body: str) -> dict:
    """
    Use Claude API as a safety check to verify this is a job rejection
    and extract the Job ID and company name.
    The human already signalled intent by deleting the email —
    this is a verification step, not the primary decision.
    """
    prompt = (
        f"Analyze this email and determine if it is a job application rejection.\n\n"
        f"Subject: {subject}\n"
        f"Body: {body}\n\n"
        f"Respond in this exact format:\n"
        f"IS_REJECTION: yes or no\n"
        f"JOB_ID: the job ID if found (e.g. JR-123456, REQ-789) or NONE if not found\n"
        f"COMPANY: the company name or NONE if not found"
    )

    message = anthropic.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}]
    )

    response = message.content[0].text
    lines = response.strip().split("\n")
    result = {}
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()

    return {
        "is_rejection": result.get("IS_REJECTION", "no").lower() == "yes",
        "job_id": result.get("JOB_ID", "NONE").strip(),
        "company": result.get("COMPANY", "NONE").strip()
    }


# --- Folder matching ---
def find_matching_folder(job_id: str, company: str) -> Path | None:
    """
    Find a job folder matching the Job ID or company name.
    Job ID is the primary key — matches folder name directly.
    Company name is a fallback if Job ID is not found.
    """
    if not BASE_DIR.exists():
        return None

    for company_folder in BASE_DIR.iterdir():
        if not company_folder.is_dir() or company_folder.name.startswith("_"):
            continue
        for job_folder in company_folder.iterdir():
            if not job_folder.is_dir():
                continue
            # Match by Job ID first — primary key
            if job_id != "NONE" and job_id.lower() in job_folder.name.lower():
                return job_folder
            # Fallback: match by company name
            if company != "NONE" and company.lower() in company_folder.name.lower():
                return job_folder

    return None


# --- Archive ---
def archive_folder(folder_path: Path, company: str, job_id: str) -> None:
    """
    Move folder to _Rejected/ and write to deletion log.
    Soft delete only — nothing is permanently removed.
    Every archival is logged so nothing is lost silently.
    """
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)

    destination = REJECTED_DIR / folder_path.name
    shutil.move(str(folder_path), str(destination))

    # Write to audit log
    log_exists = LOG_FILE.exists()
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not log_exists:
            writer.writerow(["company", "role_job_id", "date_archived", "original_path"])
        writer.writerow([
            company,
            folder_path.name,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            str(folder_path)
        ])

    print(f"Archived: {folder_path.name} → _Rejected/")


# --- Main job ---
def run_rejection_watcher() -> None:
    """
    Main function — reads Deleted Items, runs safety check,
    archives matching job folders.

    Design: human-triggered autonomous.
    The user signals intent by deleting the rejection email.
    This agent handles the cleanup automatically.
    Only Deleted Items folder is read — inbox is never accessed.
    """
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Running rejection watcher...")

    try:
        token = get_access_token()
        emails = get_deleted_emails(token)
        print(f"Found {len(emails)} deleted emails in the last {LOOKBACK_HOURS} hours")

        archived_count = 0
        for email in emails:
            subject = email.get("subject", "")
            body = email.get("bodyPreview", "")

            # Safety check — verify this is actually a rejection
            result = classify_email(subject, body)

            if result["is_rejection"]:
                print(f"Rejection confirmed: {subject}")
                folder = find_matching_folder(result["job_id"], result["company"])

                if folder:
                    archive_folder(folder, result["company"], result["job_id"])
                    archived_count += 1
                else:
                    print(f"No matching folder found — Job ID: {result['job_id']} Company: {result['company']}")

        print(f"Done. {archived_count} folder(s) archived.")

    except Exception as e:
        print(f"Error: {str(e)}")


# --- Scheduler ---
if __name__ == "__main__":
    print("Rejection watcher started.")
    print(f"Runs every 4 hours. Looks back {LOOKBACK_HOURS} hours.")
    print("Reads Deleted Items only — inbox is never accessed.")
    print("Press Ctrl+C to stop.\n")

    # Run every 4 hours
    schedule.every(4).hours.do(run_rejection_watcher)

    # Run immediately on start
    run_rejection_watcher()

    while True:
        schedule.run_pending()
        time.sleep(60)
