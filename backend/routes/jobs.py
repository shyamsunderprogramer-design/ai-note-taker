"""Route module for job application tracker endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from security import ErrorCode, error_response
from security.auth import User

# Auth helpers (mirrored — will be consolidated)
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from security import get_current_user

security_bearer = HTTPBearer(auto_error=False)


async def get_token_from_request(credentials: HTTPAuthorizationCredentials = Depends(security_bearer)) -> str:
    if credentials:
        return credentials.credentials
    return None


async def require_authentication(token: str = Depends(get_token_from_request)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    return user


logger = logging.getLogger("routes.jobs")

# Job tracker availability
try:
    from job_tracker import job_tracker, track_application, get_applications
    JOB_TRACKER_AVAILABLE = True
except ImportError:
    JOB_TRACKER_AVAILABLE = False

router = APIRouter()


@router.post("/job-tracker/application")
async def create_job_application(
    user_id: str = Query("default", description="User ID"),
    company: str = Query(..., description="Company name"),
    role: str = Query(..., description="Job role"),
    location: str = Query(None, description="Job location"),
    salary_range: str = Query(None, description="Salary range"),
    job_url: str = Query(None, description="Job posting URL"),
    status: str = Query("saved", description="Application status"),
    priority: str = Query("medium", description="Priority level"),
    user: User = Depends(require_authentication)
):
    """Create a new job application."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        result = job_tracker.create_application(
            user_id=user_id,
            company=company,
            role=role,
            location=location,
            salary_range=salary_range,
            job_url=job_url,
            status=status,
            priority=priority
        )
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Create error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/job-tracker/applications")
async def get_job_applications(
    user_id: str = Query("default", description="User ID"),
    status: str = Query(None, description="Filter by status"),
    tags: str = Query(None, description="Filter by tags (comma-separated)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get all job applications for a user with optional filters and pagination."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available")

    try:
        tag_list = tags.split(",") if tags else None
        applications = job_tracker.get_user_applications(user_id, status, tag_list)
        total = len(applications)
        return {
            "user_id": user_id,
            "count": total,
            "total": total,
            "limit": limit,
            "offset": offset,
            "applications": applications[offset:offset + limit],
        }
    except Exception as e:
        logger.error(f"[JobTracker] Get applications error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e))


@router.get("/job-tracker/application/{app_id}")
async def get_job_application(app_id: str):
    """Get a single job application."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        application = job_tracker.get_application(app_id)
        if not application:
            return error_response(ErrorCode.NOT_FOUND, "Application not found", status_code=404)
        return application
    except Exception as e:
        logger.error(f"[JobTracker] Get application error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/job-tracker/application/{app_id}/status")
async def update_job_status(
    app_id: str,
    status: str = Query(..., description="New status"),
    notes: str = Query(None, description="Status change notes"),
    user: User = Depends(require_authentication)
):
    """Update application status."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        result = job_tracker.update_status(app_id, status, notes)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Update status error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/job-tracker/application/{app_id}/interview")
async def add_job_interview(
    app_id: str,
    interview_type: str = Query(..., description="Interview type"),
    scheduled_date: str = Query(..., description="ISO datetime"),
    duration_minutes: int = Query(60, description="Duration in minutes"),
    notes: str = Query(None, description="Notes")
):
    """Add an interview to a job application."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        result = job_tracker.add_interview(
            app_id, interview_type, scheduled_date, duration_minutes, notes=notes
        )
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Add interview error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/job-tracker/application/{app_id}/offer")
async def add_job_offer(
    app_id: str,
    salary: str = Query(..., description="Salary offer"),
    benefits: str = Query(..., description="Benefits (comma-separated)"),
    deadline: str = Query(None, description="Offer deadline")
):
    """Add offer details to a job application."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        benefits_list = benefits.split(",") if benefits else []
        result = job_tracker.add_offer(app_id, salary, benefits_list, deadline)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Add offer error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/job-tracker/stats")
async def get_job_tracker_stats(user_id: str = Query("default", description="User ID")):
    """Get job application pipeline statistics."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        stats = job_tracker.get_pipeline_stats(user_id)
        return stats
    except Exception as e:
        logger.error(f"[JobTracker] Stats error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/job-tracker/upcoming-interviews")
async def get_upcoming_job_interviews(
    user_id: str = Query("default", description="User ID"),
    days: int = Query(7, description="Number of days to look ahead")
):
    """Get upcoming interviews within specified days."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        interviews = job_tracker.get_upcoming_interviews(user_id, days)
        return {
            "user_id": user_id,
            "count": len(interviews),
            "interviews": interviews
        }
    except Exception as e:
        logger.error(f"[JobTracker] Upcoming interviews error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/job-tracker/company/{company}")
async def get_company_job_insights(company: str):
    """Get insights about a specific company from applications."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        insights = job_tracker.get_company_insights(company)
        return insights
    except Exception as e:
        logger.error(f"[JobTracker] Company insights error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.delete("/job-tracker/application/{app_id}")
async def delete_job_application(app_id: str, user: User = Depends(require_authentication)):
    """Delete a job application."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        result = job_tracker.delete_application(app_id)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Delete error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/job-tracker/duplicates")
async def find_job_duplicates(user_id: str = Query("default", description="User ID")):
    """Find duplicate applications (same company + role) for a user."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        duplicates = job_tracker.find_duplicates(user_id)
        return duplicates
    except Exception as e:
        logger.error(f"[JobTracker] Find duplicates error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/job-tracker/duplicates/remove")
async def remove_job_duplicates(
    user_id: str = Query("default", description="User ID"),
    keep: str = Query("latest", description="Which to keep: 'latest' or 'oldest'")
):
    """Remove duplicate applications, keeping either the latest or oldest."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    if keep not in ["latest", "oldest"]:
        return error_response(ErrorCode.VALIDATION_ERROR, "keep must be 'latest' or 'oldest'", status_code=422)

    try:
        result = job_tracker.remove_duplicates(user_id, keep)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Remove duplicates error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/job-tracker/application/{app_id}/details")
async def get_job_application_details(app_id: str):
    """Get detailed information about a specific application."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        details = job_tracker.get_application_details(app_id)
        if not details:
            return error_response(ErrorCode.NOT_FOUND, "Application not found", status_code=404)
        return details
    except Exception as e:
        logger.error(f"[JobTracker] Get details error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/job-tracker/application/{app_id}/recruiter")
async def add_recruiter_contact(
    app_id: str,
    name: str = Query(..., description="Recruiter name"),
    email: Optional[str] = Query(None, description="Recruiter email"),
    phone: Optional[str] = Query(None, description="Recruiter phone"),
    is_primary: bool = Query(True, description="Set as primary recruiter")
):
    """Add recruiter contact to an application."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        result = job_tracker.add_recruiter(app_id, name, email, phone, is_primary)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Add recruiter error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/job-tracker/application/{app_id}/communication")
async def add_communication_log(
    app_id: str,
    comm_type: str = Query(..., description="Communication type: email, phone, message"),
    sender: str = Query(..., description="Sender name/email"),
    content: str = Query(..., description="Message content/summary"),
    direction: str = Query("inbound", description="inbound or outbound"),
    notes: Optional[str] = Query(None, description="Additional notes")
):
    """Log a communication (email, phone call, message) for an application."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        result = job_tracker.add_communication(app_id, comm_type, sender, content, direction, notes)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Add communication error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/job-tracker/application/{app_id}/background-check")
async def update_background_check_status(
    app_id: str,
    status: str = Query(..., description="Status: initiated, in_progress, completed, failed"),
    provider: Optional[str] = Query(None, description="Background check provider"),
    notes: Optional[str] = Query(None, description="Notes")
):
    """Update background check status for an application."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        result = job_tracker.update_background_check(app_id, status, provider, notes)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Background check error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/job-tracker/application/{app_id}/drug-test")
async def update_drug_test_status(
    app_id: str,
    status: str = Query(..., description="Status: scheduled, completed, passed, failed"),
    test_date: Optional[str] = Query(None, description="Test date (YYYY-MM-DD)"),
    location: Optional[str] = Query(None, description="Test location"),
    notes: Optional[str] = Query(None, description="Notes")
):
    """Update drug test status for an application."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        result = job_tracker.update_drug_test(app_id, status, test_date, location, notes)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Drug test error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/job-tracker/application/{app_id}/onboarding")
async def add_onboarding_info(
    app_id: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    documents: Optional[str] = Query(None, description="Comma-separated document names"),
    notes: Optional[str] = Query(None, description="Notes")
):
    """Add onboarding details for accepted offer."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        docs_list = [d.strip() for d in documents.split(",")] if documents else []
        result = job_tracker.add_onboarding_details(app_id, start_date, docs_list, notes)
        return result
    except Exception as e:
        logger.error(f"[JobTracker] Onboarding error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/job-tracker/search")
async def search_job_applications(
    user_id: str = Query("default", description="User ID"),
    query: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Search applications by company, role, or notes."""
    if not JOB_TRACKER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Job tracker not available", status_code=503)

    try:
        results = job_tracker.search_applications(user_id, query)
        total = len(results)
        return {"results": results[offset:offset + limit], "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        logger.error(f"[JobTracker] Search error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)