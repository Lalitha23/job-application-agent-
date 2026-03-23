import os
from pathlib import Path
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# --- Config ---
BASE_DIR = Path.home() / "Desktop" / "Job Applications"

# Initialize MCP server
mcp = FastMCP("Job Application Agent")


# --- Helper ---
def sanitize(name: str) -> str:
    """Remove characters that are unsafe in folder names."""
    return "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip()


# --- Tools ---

@mcp.tool()
def save_application(
    company: str,
    role: str,
    job_id: str,
    resume_content: str,
    job_description: str,
    cover_letter: str
) -> str:
    """
    Save a job application to the local filesystem.
    Call this when the user says 'save now'.
    Creates a folder structure: Desktop/Job Applications/Company/Role-JobID/
    Saves resume, job description and cover letter as text files.

    Args:
        company: Company name e.g. Amazon
        role: Job title e.g. Senior Product Manager
        job_id: Job ID from the posting e.g. JR-123456
        resume_content: The full customized resume text
        job_description: The full job description text
        cover_letter: The full cover letter text
    """
    try:
        # Validate required fields are not empty
        if not sanitize(company):
            return "Error: Company name is missing or invalid. Please provide a valid company name."
        if not sanitize(role):
            return "Error: Role title is missing or invalid. Please provide a valid role title."
        if not sanitize(job_id):
            return "Error: Job ID is missing or invalid. Please provide a valid job ID."
        if not resume_content.strip():
            return "Error: Resume content is empty. Please provide the resume before saving."
        if not job_description.strip():
            return "Error: Job description is empty. Please provide the job description before saving."
        if not cover_letter.strip():
            return "Error: Cover letter is empty. Please write a cover letter before saving."

        # Build folder path
        safe_company = sanitize(company)
        safe_role = sanitize(role)
        safe_job_id = sanitize(job_id)
        folder_name = f"{safe_role}-{safe_job_id}"
        folder_path = BASE_DIR / safe_company / folder_name

        # Create folders (handles existing company folders gracefully)
        folder_path.mkdir(parents=True, exist_ok=True)

        # Save the three files
        (folder_path / "job_description.txt").write_text(job_description, encoding="utf-8")
        (folder_path / "resume.txt").write_text(resume_content, encoding="utf-8")
        (folder_path / "cover_letter.txt").write_text(cover_letter, encoding="utf-8")

        return (
            f"Saved successfully!\n"
            f"Location: {folder_path}\n"
            f"Files saved:\n"
            f"  - job_description.txt\n"
            f"  - resume.txt\n"
            f"  - cover_letter.txt"
        )

    except Exception as e:
        return f"Error saving application: {str(e)}"


@mcp.tool()
def list_applications() -> str:
    """
    List all job applications saved on the desktop.
    Shows company, role, job ID and date saved.
    """
    try:
        if not BASE_DIR.exists():
            return "No applications found. No Job Applications folder exists yet."

        results = []
        for company_folder in sorted(BASE_DIR.iterdir()):
            if not company_folder.is_dir():
                continue
            for job_folder in sorted(company_folder.iterdir()):
                if not job_folder.is_dir():
                    continue
                # Get date from folder metadata
                created = datetime.fromtimestamp(
                    job_folder.stat().st_birthtime
                ).strftime("%Y-%m-%d")
                results.append(f"  {company_folder.name} | {job_folder.name} | saved {created}")

        if not results:
            return "No applications saved yet."

        return "Your saved applications:\n" + "\n".join(results)

    except Exception as e:
        return f"Error listing applications: {str(e)}"


# --- Prompts ---

@mcp.prompt()
def review_resume() -> str:
    """Review resume against the job description."""
    return (
        "Before proceeding, check that both a job description AND a resume have been "
        "provided in this conversation. If either is missing, stop and ask the user to "
        "paste the missing item before continuing.\n\n"
        "If both are present: please review my resume against the job description. "
        "Identify the top 5 gaps or mismatches, and suggest specific improvements "
        "to better align my resume with this role. Be direct and specific."
    )


@mcp.prompt()
def rewrite_resume() -> str:
    """Rewrite resume tailored to the job description."""
    return (
        "Before proceeding, check that both a job description AND a resume have been "
        "provided in this conversation. If either is missing, stop and ask the user to "
        "paste the missing item before continuing.\n\n"
        "If both are present: please rewrite my resume tailored specifically to this "
        "job description. Keep all my real experience and skills but reframe and reorder "
        "them to match what this role is looking for. Preserve my voice and keep it authentic."
    )


@mcp.prompt()
def write_cover_letter() -> str:
    """Write a cover letter for this role."""
    return (
        "Before proceeding, check that both a job description AND a resume have been "
        "provided in this conversation. If either is missing, stop and ask the user to "
        "paste the missing item before continuing.\n\n"
        "If both are present: please write a compelling cover letter for this role. "
        "Keep it to 3 paragraphs: why this company, why I am a strong fit, and a clear "
        "call to action. Keep it concise and genuine."
    )


@mcp.prompt()
def save_now() -> str:
    """Trigger to save the application artifacts."""
    return (
        "Before saving, check that all of the following are present in our conversation:\n"
        "  1. Job description\n"
        "  2. Customized resume\n"
        "  3. Cover letter\n\n"
        "If any are missing, stop and ask the user to provide them before saving.\n\n"
        "If all are present:\n"
        "  - Extract the company name and role title from the job description\n"
        "  - Look for a Job ID in the job description (e.g. JR-123456, REQ-789, #12345)\n"
        "  - If a Job ID is found, confirm it with the user before saving\n"
        "  - If no Job ID is found, ask the user: 'I could not find a Job ID in the job "
        "description. Could you provide it? If there is no Job ID just type NONE and I "
        "will use today's date instead.'\n\n"
        "Once confirmed, call save_application with the company, role, job ID "
        "(or today's date in YYYY-MM-DD format if NONE), and all three artifacts."
    )


# --- Run ---
if __name__ == "__main__":
    mcp.run()
