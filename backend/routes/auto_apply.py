"""Route module for auto-apply job application endpoints."""
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from security import ErrorCode, error_response, get_current_user
from security.auth import User

security_bearer = HTTPBearer(auto_error=False)


async def get_token(credentials: HTTPAuthorizationCredentials = Depends(security_bearer)):
    return credentials.credentials if credentials else None


async def require_authentication(token=Depends(get_token)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Auth required", headers={"WWW-Authenticate": "Bearer"})
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    return user


logger = logging.getLogger("routes.auto_apply")

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory storage
# ---------------------------------------------------------------------------
# Keyed by user_id -> list of session dicts
_auto_apply_sessions: Dict[str, List[dict]] = {}
# Keyed by session_id -> session dict
_sessions_by_id: Dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class UserPreferences(BaseModel):
    salary_min: Optional[int] = Field(None, description="Minimum salary requirement")
    locations: Optional[List[str]] = Field(default_factory=list, description="Preferred locations")
    job_types: Optional[List[str]] = Field(default_factory=list, description="Preferred job types (full-time, part-time, contract, internship)")


class StartSessionRequest(BaseModel):
    job_urls: List[str] = Field(..., min_length=1, description="List of job posting URLs to apply to")
    resume_text: str = Field(..., min_length=1, description="Resume text content")
    cover_letter_template: str = Field(..., min_length=1, description="Cover letter template with {job_title}, {company}, etc. placeholders")
    user_preferences: UserPreferences = Field(default_factory=UserPreferences)


class ApplyJobRequest(BaseModel):
    custom_cover_letter: Optional[str] = Field(None, description="Custom cover letter override for this job")
    answers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Answers to application questions")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_cover_letter(template: str, job_details: dict) -> str:
    """Fill cover letter template with job details."""
    result = template
    placeholders = {
        "job_title": job_details.get("title", "the position"),
        "company": job_details.get("company", "your company"),
        "location": job_details.get("location", "the listed location"),
        "salary": job_details.get("salary", "competitive"),
    }
    for key, value in placeholders.items():
        result = result.replace("{" + key + "}", value)
    # Remove any unresolved placeholders
    result = re.sub(r"\{[a-zA-Z_]+\}", "", result)
    return result


def _mock_extract_job_details(url: str) -> dict:
    """Simulate extracting job details from a URL (MVP — no real scraping)."""
    # Derive a plausible company name from the domain
    try:
        domain = url.split("//")[1].split("/")[0] if "//" in url else url.split("/")[0]
        company = domain.split(".")[0].capitalize()
    except (IndexError, ValueError):
        company = "Unknown Company"

    return {
        "job_id": str(uuid.uuid4()),
        "url": url,
        "title": "Software Engineer",
        "company": company,
        "location": "Remote",
        "salary": "$80,000 - $120,000",
        "description": f"Job posting at {company}. Full details would be scraped in production.",
        "job_type": "full-time",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }


def _user_matches_preferences(job_details: dict, preferences: UserPreferences) -> bool:
    """Check whether a job matches user preferences (soft filter for MVP)."""
    if preferences.job_types and job_details.get("job_type") not in preferences.job_types:
        return False
    return True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/auto-apply/start")
async def start_auto_apply_session(
    request: Request,
    user: User = Depends(require_authentication),
):
    """Start an auto-apply session for a list of job URLs."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body")

    # Validate required fields
    job_urls = body.get("job_urls", [])
    resume_text = body.get("resume_text", "")
    cover_letter_template = body.get("cover_letter_template", "")
    prefs_data = body.get("user_preferences", {})

    if not job_urls or not isinstance(job_urls, list):
        raise HTTPException(status_code=422, detail="job_urls must be a non-empty list")
    if not resume_text:
        raise HTTPException(status_code=422, detail="resume_text is required")
    if not cover_letter_template:
        raise HTTPException(status_code=422, detail="cover_letter_template is required")

    preferences = UserPreferences(**prefs_data) if prefs_data else UserPreferences()

    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Build job entries from URLs
    jobs: List[dict] = []
    for url in job_urls:
        job_details = _mock_extract_job_details(url)
        matches = _user_matches_preferences(job_details, preferences)
        jobs.append({
            "job_id": job_details["job_id"],
            "url": url,
            "status": "pending" if matches else "skipped",
            "job_details": job_details,
            "applied_at": None,
            "error": None,
        })

    session = {
        "session_id": session_id,
        "user_id": user.id,
        "resume_text": resume_text,
        "cover_letter_template": cover_letter_template,
        "user_preferences": preferences.model_dump(),
        "jobs": jobs,
        "jobs_found": len(jobs),
        "jobs_applied": 0,
        "jobs_failed": 0,
        "current_status": "active",
        "created_at": now,
        "stopped_at": None,
    }

    _sessions_by_id[session_id] = session
    _auto_apply_sessions.setdefault(user.id, []).append(session)

    logger.info("[AutoApply] Session %s started for user %s with %d jobs", session_id, user.id, len(jobs))

    return {
        "session_id": session_id,
        "jobs_found": session["jobs_found"],
        "current_status": "active",
        "created_at": now,
        "jobs": [
            {"job_id": j["job_id"], "url": j["url"], "status": j["status"]}
            for j in jobs
        ],
    }


@router.get("/auto-apply/status/{session_id}")
async def get_auto_apply_status(
    session_id: str,
    user: User = Depends(require_authentication),
):
    """Get the status of an auto-apply session."""
    session = _sessions_by_id.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this session")

    jobs_applied = sum(1 for j in session["jobs"] if j["status"] == "applied")
    jobs_failed = sum(1 for j in session["jobs"] if j["status"] == "failed")

    return {
        "session_id": session_id,
        "jobs_found": session["jobs_found"],
        "jobs_applied": jobs_applied,
        "jobs_failed": jobs_failed,
        "current_status": session["current_status"],
        "created_at": session["created_at"],
        "stopped_at": session["stopped_at"],
        "jobs": [
            {"job_id": j["job_id"], "url": j["url"], "status": j["status"], "error": j["error"]}
            for j in session["jobs"]
        ],
    }


@router.post("/auto-apply/apply/{session_id}/{job_id}")
async def apply_to_specific_job(
    session_id: str,
    job_id: str,
    request: Request,
    user: User = Depends(require_authentication),
):
    """Apply to a specific job within a session."""
    session = _sessions_by_id.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this session")
    if session["current_status"] != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    # Find the job in the session
    job_entry = None
    for j in session["jobs"]:
        if j["job_id"] == job_id:
            job_entry = j
            break
    if not job_entry:
        raise HTTPException(status_code=404, detail="Job not found in session")
    if job_entry["status"] == "applied":
        raise HTTPException(status_code=400, detail="Already applied to this job")

    # Parse request body
    try:
        body = await request.json()
    except Exception:
        body = {}  # nosec B110 — JSON parse fallback for optional body

    custom_cover_letter = body.get("custom_cover_letter")
    answers = body.get("answers", {})

    # Mark as applying
    job_entry["status"] = "applying"

    try:
        # Generate cover letter
        if custom_cover_letter:
            cover_letter = custom_cover_letter
        else:
            cover_letter = _generate_cover_letter(
                session["cover_letter_template"],
                job_entry["job_details"],
            )

        # MVP: Simulate application submission
        # In production, this would use browser automation to fill forms
        application_result = {
            "job_id": job_id,
            "status": "applied",
            "cover_letter_used": cover_letter[:200] + ("..." if len(cover_letter) > 200 else ""),
            "answers_submitted": list(answers.keys()) if answers else [],
            "applied_at": datetime.now(timezone.utc).isoformat(),
            "message": "Application submitted successfully (MVP simulated)",
        }

        job_entry["status"] = "applied"
        job_entry["applied_at"] = application_result["applied_at"]

        logger.info("[AutoApply] Applied to job %s in session %s", job_id, session_id)

        return application_result

    except Exception as e:
        job_entry["status"] = "failed"
        job_entry["error"] = str(e)
        logger.error("[AutoApply] Failed to apply to job %s: %s", job_id, str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, f"Application failed: {str(e)}", status_code=500)


@router.get("/auto-apply/history")
async def get_auto_apply_history(
    user: User = Depends(require_authentication),
):
    """Get auto-apply session history for the current user."""
    sessions = _auto_apply_sessions.get(user.id, [])
    return {
        "user_id": user.id,
        "total_sessions": len(sessions),
        "sessions": [
            {
                "session_id": s["session_id"],
                "jobs_found": s["jobs_found"],
                "jobs_applied": sum(1 for j in s["jobs"] if j["status"] == "applied"),
                "jobs_failed": sum(1 for j in s["jobs"] if j["status"] == "failed"),
                "current_status": s["current_status"],
                "created_at": s["created_at"],
                "stopped_at": s["stopped_at"],
            }
            for s in sessions
        ],
    }


@router.post("/auto-apply/stop/{session_id}")
async def stop_auto_apply_session(
    session_id: str,
    user: User = Depends(require_authentication),
):
    """Stop an active auto-apply session."""
    session = _sessions_by_id.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this session")
    if session["current_status"] != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    now = datetime.now(timezone.utc).isoformat()
    session["current_status"] = "stopped"
    session["stopped_at"] = now

    # Mark any remaining pending/applying jobs as skipped
    for job in session["jobs"]:
        if job["status"] in ("pending", "applying"):
            job["status"] = "skipped"
            job["error"] = "Session stopped before application"

    jobs_applied = sum(1 for j in session["jobs"] if j["status"] == "applied")
    jobs_failed = sum(1 for j in session["jobs"] if j["status"] == "failed")
    jobs_skipped = sum(1 for j in session["jobs"] if j["status"] == "skipped")

    logger.info("[AutoApply] Session %s stopped by user %s", session_id, user.id)

    return {
        "session_id": session_id,
        "current_status": "stopped",
        "stopped_at": now,
        "jobs_applied": jobs_applied,
        "jobs_failed": jobs_failed,
        "jobs_skipped": jobs_skipped,
    }