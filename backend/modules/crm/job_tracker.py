"""
job_tracker.py - Job Application Tracker

Track job applications, interviews, and offers.
Integrates with cognitive graph and interview simulator.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import uuid

logger = logging.getLogger("job_tracker")


class ApplicationStatus(Enum):
    # Initial stages
    SAVED = "saved"                    # Job saved but not applied
    APPLIED = "applied"                # Application submitted

    # Communication stages
    RECRUITER_CONTACT = "recruiter_contact"    # Recruiter reached out
    AVAILABILITY_REQUESTED = "availability_requested"  # Asking for availability

    # Interview stages
    PHONE_SCREEN = "phone_screen"      # Initial recruiter call
    FIRST_ROUND = "first_round"        # First technical/HR interview
    SECOND_ROUND = "second_round"      # Second interview
    THIRD_ROUND = "third_round"        # Third/final interview
    TECHNICAL = "technical"            # Technical interview (legacy)
    ONSITE = "onsite"                  # Onsite interview (legacy)

    # Pre-employment stages
    BACKGROUND_CHECK = "background_check"        # Background verification
    DRUG_TEST = "drug_test"            # Drug screening
    REFERENCE_CHECK = "reference_check"        # Reference verification

    # Offer stages
    OFFER = "offer"                    # Offer received
    OFFER_NEGOTIATION = "offer_negotiation"    # Negotiating terms
    OFFER_ACCEPTED = "offer_accepted"  # Offer accepted
    OFFER_DECLINED = "offer_declined"  # Offer declined

    # Final stages
    ONBOARDING = "onboarding"          # Onboarding process
    HIRED = "hired"                    # Successfully hired

    # Negative outcomes
    REJECTED = "rejected"              # Application rejected
    WITHDRAWN = "withdrawn"            # Candidate withdrew
    GHOSTED = "ghosted"                # No response >30 days


@dataclass
class JobApplication:
    """Represents a job application with full workflow tracking"""
    # Basic Info
    id: str
    user_id: str
    company: str
    role: str
    location: Optional[str]
    salary_range: Optional[str]
    job_url: Optional[str]
    job_description: Optional[str]  # Full job description snapshot

    # Status
    status: str
    applied_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # Application Details
    notes: List[Dict]
    contacts: List[Dict]  # Recruiters, hiring managers
    interviews: List[Dict]
    communications: List[Dict]  # Email threads
    documents: List[Dict]  # Uploaded documents

    # Offer Details
    offer_details: Optional[Dict]

    # Documents
    resume_version: Optional[str]
    cover_letter: Optional[str]
    resume_file: Optional[str]  # Path to uploaded resume
    cover_letter_file: Optional[str]  # Path to cover letter

    # Application Metadata
    application_confirmation: Optional[str]  # Confirmation number
    application_portal: Optional[str]  # LinkedIn, Indeed, Company website
    application_method: Optional[str]  # Easy Apply, Email, Portal
    application_screenshot: Optional[str]  # Screenshot of submission

    # Recruiter Info
    recruiter_name: Optional[str]
    recruiter_email: Optional[str]
    recruiter_phone: Optional[str]
    hiring_manager: Optional[str]

    # Interview Coordination
    availability_slots: List[Dict]  # Provided availability
    preferred_interview_times: List[Dict]

    # Pre-employment
    background_check: Optional[Dict]
    drug_test: Optional[Dict]
    reference_checks: List[Dict]

    # Onboarding
    onboarding_details: Optional[Dict]
    start_date: Optional[str]

    # Organization
    tags: List[str]
    priority: str  # high, medium, low

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "company": self.company,
            "role": self.role,
            "location": self.location,
            "salary_range": self.salary_range,
            "job_url": self.job_url,
            "job_description": self.job_description,
            "status": self.status,
            "applied_date": self.applied_date.isoformat() if self.applied_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "notes": self.notes,
            "contacts": self.contacts,
            "interviews": self.interviews,
            "communications": self.communications,
            "documents": self.documents,
            "offer_details": self.offer_details,
            "resume_version": self.resume_version,
            "cover_letter": self.cover_letter,
            "resume_file": self.resume_file,
            "cover_letter_file": self.cover_letter_file,
            "application_confirmation": self.application_confirmation,
            "application_portal": self.application_portal,
            "application_method": self.application_method,
            "application_screenshot": self.application_screenshot,
            "recruiter_name": self.recruiter_name,
            "recruiter_email": self.recruiter_email,
            "recruiter_phone": self.recruiter_phone,
            "hiring_manager": self.hiring_manager,
            "availability_slots": self.availability_slots,
            "preferred_interview_times": self.preferred_interview_times,
            "background_check": self.background_check,
            "drug_test": self.drug_test,
            "reference_checks": self.reference_checks,
            "onboarding_details": self.onboarding_details,
            "start_date": self.start_date,
            "tags": self.tags,
            "priority": self.priority
        }


class JobTracker:
    """Job Application Tracker"""

    def __init__(self):
        self.applications: Dict[str, JobApplication] = {}
        self.cognitive_graph = None
        self._load_dependencies()

    def _load_dependencies(self):
        try:
            from cognitive_graph import cognitive_graph
            self.cognitive_graph = cognitive_graph
        except ImportError:
            pass

    def create_application(
        self,
        user_id: str,
        company: str,
        role: str,
        **kwargs
    ) -> Dict:
        """Create a new job application with full workflow tracking"""
        app_id = str(uuid.uuid4())
        now = datetime.now()

        application = JobApplication(
            id=app_id,
            user_id=user_id,
            company=company,
            role=role,
            location=kwargs.get('location'),
            salary_range=kwargs.get('salary_range'),
            job_url=kwargs.get('job_url'),
            job_description=kwargs.get('job_description'),
            status=kwargs.get('status', 'saved'),
            applied_date=datetime.fromisoformat(kwargs['applied_date']) if kwargs.get('applied_date') else None,
            created_at=now,
            updated_at=now,
            notes=kwargs.get('notes', []),
            contacts=kwargs.get('contacts', []),
            interviews=kwargs.get('interviews', []),
            communications=kwargs.get('communications', []),
            documents=kwargs.get('documents', []),
            offer_details=kwargs.get('offer_details'),
            resume_version=kwargs.get('resume_version'),
            cover_letter=kwargs.get('cover_letter'),
            resume_file=kwargs.get('resume_file'),
            cover_letter_file=kwargs.get('cover_letter_file'),
            application_confirmation=kwargs.get('application_confirmation'),
            application_portal=kwargs.get('application_portal'),
            application_method=kwargs.get('application_method'),
            application_screenshot=kwargs.get('application_screenshot'),
            recruiter_name=kwargs.get('recruiter_name'),
            recruiter_email=kwargs.get('recruiter_email'),
            recruiter_phone=kwargs.get('recruiter_phone'),
            hiring_manager=kwargs.get('hiring_manager'),
            availability_slots=kwargs.get('availability_slots', []),
            preferred_interview_times=kwargs.get('preferred_interview_times', []),
            background_check=kwargs.get('background_check'),
            drug_test=kwargs.get('drug_test'),
            reference_checks=kwargs.get('reference_checks', []),
            onboarding_details=kwargs.get('onboarding_details'),
            start_date=kwargs.get('start_date'),
            tags=kwargs.get('tags', []),
            priority=kwargs.get('priority', 'medium')
        )

        self.applications[app_id] = application

        logger.info(f"[JobTracker] Created application {app_id} for {company} {role}")

        return {
            "success": True,
            "application": application.to_dict(),
            "message": "Application created successfully"
        }

    def get_application(self, app_id: str) -> Optional[Dict]:
        """Get a single application"""
        app = self.applications.get(app_id)
        return app.to_dict() if app else None

    def get_user_applications(
        self,
        user_id: str,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict]:
        """Get all applications for a user with optional filters"""
        apps = [a for a in self.applications.values() if a.user_id == user_id]

        if status:
            apps = [a for a in apps if a.status == status]

        if tags:
            apps = [a for a in apps if any(t in a.tags for t in tags)]

        # Sort by updated_at desc
        apps.sort(key=lambda x: x.updated_at, reverse=True)

        return [a.to_dict() for a in apps]

    def update_status(
        self,
        app_id: str,
        new_status: str,
        notes: Optional[str] = None
    ) -> Dict:
        """Update application status"""
        app = self.applications.get(app_id)
        if not app:
            return {"error": "Application not found"}

        old_status = app.status
        app.status = new_status
        app.updated_at = datetime.now()

        # Add status change note
        if notes:
            app.notes.append({
                "type": "status_change",
                "from": old_status,
                "to": new_status,
                "note": notes,
                "timestamp": datetime.now().isoformat()
            })

        # Auto-update applied_date if moving to applied
        if new_status == 'applied' and not app.applied_date:
            app.applied_date = datetime.now()

        logger.info(f"[JobTracker] Updated {app_id} from {old_status} to {new_status}")

        return {
            "success": True,
            "application": app.to_dict()
        }

    def add_interview(
        self,
        app_id: str,
        interview_type: str,
        scheduled_date: str,
        duration_minutes: int = 60,
        interviewer_names: Optional[List[str]] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """Add an interview to an application"""
        app = self.applications.get(app_id)
        if not app:
            return {"error": "Application not found"}

        interview = {
            "id": str(uuid.uuid4()),
            "type": interview_type,
            "scheduled_date": scheduled_date,
            "duration_minutes": duration_minutes,
            "interviewer_names": interviewer_names or [],
            "notes": notes,
            "status": "scheduled",
            "created_at": datetime.now().isoformat()
        }

        app.interviews.append(interview)
        app.updated_at = datetime.now()

        # Update application status if needed
        status_map = {
            'phone_screen': 'phone_screen',
            'technical': 'technical',
            'onsite': 'onsite',
            'final': 'onsite'
        }
        if interview_type in status_map:
            app.status = status_map[interview_type]

        return {
            "success": True,
            "interview": interview,
            "application": app.to_dict()
        }

    def add_offer(
        self,
        app_id: str,
        salary: str,
        benefits: List[str],
        deadline: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """Add offer details to an application"""
        app = self.applications.get(app_id)
        if not app:
            return {"error": "Application not found"}

        app.offer_details = {
            "salary": salary,
            "benefits": benefits,
            "deadline": deadline,
            "notes": notes,
            "received_date": datetime.now().isoformat()
        }
        app.status = 'offer'
        app.updated_at = datetime.now()

        return {
            "success": True,
            "application": app.to_dict()
        }

    def add_communication(
        self,
        app_id: str,
        comm_type: str,  # email, phone, message
        sender: str,
        content: str,
        direction: str = "inbound",  # inbound, outbound
        notes: Optional[str] = None
    ) -> Dict:
        """Add communication log to application"""
        app = self.applications.get(app_id)
        if not app:
            return {"error": "Application not found"}

        communication = {
            "id": str(uuid.uuid4()),
            "type": comm_type,
            "sender": sender,
            "content": content,
            "direction": direction,
            "notes": notes,
            "timestamp": datetime.now().isoformat()
        }

        app.communications.append(communication)
        app.updated_at = datetime.now()

        return {
            "success": True,
            "communication": communication,
            "application": app.to_dict()
        }

    def add_recruiter(
        self,
        app_id: str,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        is_primary: bool = False
    ) -> Dict:
        """Add recruiter contact to application"""
        app = self.applications.get(app_id)
        if not app:
            return {"error": "Application not found"}

        recruiter = {
            "id": str(uuid.uuid4()),
            "name": name,
            "email": email,
            "phone": phone,
            "type": "recruiter",
            "is_primary": is_primary,
            "added_at": datetime.now().isoformat()
        }

        app.contacts.append(recruiter)
        if is_primary:
            app.recruiter_name = name
            app.recruiter_email = email
            app.recruiter_phone = phone

        app.updated_at = datetime.now()

        return {
            "success": True,
            "recruiter": recruiter,
            "application": app.to_dict()
        }

    def update_background_check(
        self,
        app_id: str,
        status: str,  # initiated, in_progress, completed, failed
        provider: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """Update background check status"""
        app = self.applications.get(app_id)
        if not app:
            return {"error": "Application not found"}

        if not app.background_check:
            app.background_check = {}

        app.background_check.update({
            "status": status,
            "provider": provider or app.background_check.get("provider"),
            "notes": notes,
            "updated_at": datetime.now().isoformat()
        })

        if status == "initiated":
            app.status = "background_check"

        app.updated_at = datetime.now()

        return {
            "success": True,
            "background_check": app.background_check,
            "application": app.to_dict()
        }

    def update_drug_test(
        self,
        app_id: str,
        status: str,  # scheduled, completed, passed, failed
        test_date: Optional[str] = None,
        location: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """Update drug test status"""
        app = self.applications.get(app_id)
        if not app:
            return {"error": "Application not found"}

        if not app.drug_test:
            app.drug_test = {}

        app.drug_test.update({
            "status": status,
            "test_date": test_date,
            "location": location,
            "notes": notes,
            "updated_at": datetime.now().isoformat()
        })

        if status == "scheduled":
            app.status = "drug_test"

        app.updated_at = datetime.now()

        return {
            "success": True,
            "drug_test": app.drug_test,
            "application": app.to_dict()
        }

    def add_onboarding_details(
        self,
        app_id: str,
        start_date: str,
        documents: Optional[List[str]] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """Add onboarding details"""
        app = self.applications.get(app_id)
        if not app:
            return {"error": "Application not found"}

        app.onboarding_details = {
            "start_date": start_date,
            "documents": documents or [],
            "notes": notes,
            "updated_at": datetime.now().isoformat()
        }
        app.start_date = start_date
        app.status = "onboarding"
        app.updated_at = datetime.now()

        return {
            "success": True,
            "onboarding": app.onboarding_details,
            "application": app.to_dict()
        }

    def get_pipeline_stats(self, user_id: str) -> Dict:
        """Get application pipeline statistics"""
        apps = self.get_user_applications(user_id)

        # Count by status
        status_counts = {}
        for app in apps:
            status = app['status']
            status_counts[status] = status_counts.get(status, 0) + 1

        # Calculate response rate
        total_applied = len([a for a in apps if a['status'] != 'saved'])
        total_responses = len([a for a in apps if a['status'] not in ['saved', 'applied']])
        response_rate = (total_responses / total_applied * 100) if total_applied > 0 else 0

        # Calculate conversion rates
        pipeline = {
            'applied': status_counts.get('applied', 0),
            'phone_screen': status_counts.get('phone_screen', 0),
            'technical': status_counts.get('technical', 0),
            'onsite': status_counts.get('onsite', 0),
            'offer': status_counts.get('offer', 0),
            'accepted': status_counts.get('accepted', 0)
        }

        # Time to response (average)
        response_times = []
        for app in apps:
            if app['applied_date'] and len(app['interviews']) > 0:
                applied = datetime.fromisoformat(app['applied_date'])
                first_interview = datetime.fromisoformat(app['interviews'][0]['created_at'])
                days = (first_interview - applied).days
                if days >= 0:
                    response_times.append(days)

        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        return {
            "total_applications": len(apps),
            "total_saved": status_counts.get('saved', 0),
            "total_applied": total_applied,
            "total_offers": status_counts.get('offer', 0) + status_counts.get('accepted', 0),
            "response_rate": round(response_rate, 1),
            "pipeline": pipeline,
            "avg_response_time_days": round(avg_response_time, 1),
            "conversion_rates": {
                "applied_to_phone": self._calc_rate(pipeline['phone_screen'], pipeline['applied']),
                "phone_to_technical": self._calc_rate(pipeline['technical'], pipeline['phone_screen']),
                "technical_to_onsite": self._calc_rate(pipeline['onsite'], pipeline['technical']),
                "onsite_to_offer": self._calc_rate(pipeline['offer'], pipeline['onsite'])
            }
        }

    def _calc_rate(self, numerator: int, denominator: int) -> float:
        """Calculate percentage rate"""
        return round((numerator / denominator * 100), 1) if denominator > 0 else 0

    def get_upcoming_interviews(self, user_id: str, days: int = 7) -> List[Dict]:
        """Get upcoming interviews within N days"""
        apps = self.get_user_applications(user_id)
        upcoming = []
        now = datetime.now()
        cutoff = now + timedelta(days=days)

        for app in apps:
            for interview in app.get('interviews', []):
                if interview.get('scheduled_date'):
                    interview_date = datetime.fromisoformat(interview['scheduled_date'])
                    if now <= interview_date <= cutoff and interview.get('status') == 'scheduled':
                        upcoming.append({
                            "application_id": app['id'],
                            "company": app['company'],
                            "role": app['role'],
                            **interview
                        })

        upcoming.sort(key=lambda x: x['scheduled_date'])
        return upcoming

    def delete_application(self, app_id: str) -> Dict:
        """Delete an application"""
        if app_id in self.applications:
            del self.applications[app_id]
            return {"success": True, "message": "Application deleted"}
        return {"error": "Application not found"}

    def get_company_insights(self, company: str) -> Dict:
        """Get insights about a company from applications"""
        company_apps = [a for a in self.applications.values()
                       if a.company.lower() == company.lower()]

        if not company_apps:
            return {"message": "No applications found for this company"}

        # Calculate success rate
        total = len(company_apps)
        offers = len([a for a in company_apps if a.status in ['offer', 'accepted']])
        rejected = len([a for a in company_apps if a.status == 'rejected'])

        # Common roles
        from collections import Counter
        roles = Counter([a.role for a in company_apps]).most_common(5)

        # Average time in pipeline
        days_in_pipeline = []
        for app in company_apps:
            if app.applied_date and app.interviews:
                days = (datetime.now() - app.applied_date).days
                days_in_pipeline.append(days)

        return {
            "company": company,
            "total_applications": total,
            "offer_rate": round((offers / total * 100), 1) if total > 0 else 0,
            "rejection_rate": round((rejected / total * 100), 1) if total > 0 else 0,
            "common_roles": roles,
            "avg_days_in_pipeline": round(sum(days_in_pipeline) / len(days_in_pipeline), 1) if days_in_pipeline else 0,
            "status_breakdown": dict(Counter([a.status for a in company_apps]))
        }

    def find_duplicates(self, user_id: str) -> Dict:
        """Find duplicate applications (same company + role) for a user"""
        apps = self.get_user_applications(user_id)

        # Group by company+role
        grouped = {}
        for app in apps:
            key = (app['company'].lower().strip(), app['role'].lower().strip())
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(app)

        # Find duplicates (groups with more than 1)
        duplicates = {k: v for k, v in grouped.items() if len(v) > 1}

        return {
            "total_applications": len(apps),
            "duplicate_groups": len(duplicates),
            "duplicates": [
                {
                    "company": company,
                    "role": role,
                    "count": len(items),
                    "applications": sorted(items, key=lambda x: x['updated_at'], reverse=True)
                }
                for (company, role), items in duplicates.items()
            ]
        }

    def remove_duplicates(self, user_id: str, keep: str = "latest") -> Dict:
        """Remove duplicate applications, keeping either 'latest' or 'oldest'"""
        duplicates = self.find_duplicates(user_id)

        removed = []
        kept = []

        for group in duplicates.get('duplicates', []):
            apps = group['applications']

            if keep == "oldest":
                # Keep first (oldest), remove rest
                to_keep = apps[-1]  # Oldest (earliest created)
                to_remove = apps[:-1]
            else:
                # Keep latest (most recent), remove rest
                to_keep = apps[0]  # Latest (most recently updated)
                to_remove = apps[1:]

            kept.append(to_keep['id'])

            for app in to_remove:
                result = self.delete_application(app['id'])
                if result.get('success'):
                    removed.append({
                        "id": app['id'],
                        "company": app['company'],
                        "role": app['role'],
                        "status": app['status']
                    })

        return {
            "success": True,
            "removed": removed,
            "kept": kept,
            "removed_count": len(removed),
            "message": f"Removed {len(removed)} duplicates, kept {len(kept)} applications"
        }

    def get_application_details(self, app_id: str) -> Optional[Dict]:
        """Get detailed information about a specific application with computed fields"""
        app = self.get_application(app_id)
        if not app:
            return None

        # Add computed fields
        days_in_pipeline = 0
        if app.get('applied_date'):
            applied = datetime.fromisoformat(app['applied_date'])
            days_in_pipeline = (datetime.now() - applied).days

        # Get company insights
        company_insights = self.get_company_insights(app['company'])

        return {
            **app,
            "days_in_pipeline": days_in_pipeline,
            "company_insights": company_insights if 'total_applications' in company_insights else None,
            "interview_count": len(app.get('interviews', [])),
            "has_offer": app.get('offer_details') is not None,
            "is_active": app['status'] not in ['rejected', 'withdrawn', 'ghosted', 'accepted']
        }

    def search_applications(self, user_id: str, query: str) -> List[Dict]:
        """Search applications by company, role, or notes"""
        apps = self.get_user_applications(user_id)
        query_lower = query.lower()

        results = []
        for app in apps:
            searchable_text = f"{app['company']} {app['role']} {' '.join([n.get('note', '') for n in app.get('notes', [])])}"
            if query_lower in searchable_text.lower():
                results.append(app)

        return results


# Global instance
job_tracker = JobTracker()


# Convenience functions
def track_application(user_id: str, company: str, role: str, **kwargs) -> Dict:
    """Quick function to track a new application"""
    return job_tracker.create_application(user_id, company, role, **kwargs)


def get_applications(user_id: str, **filters) -> List[Dict]:
    """Get applications for a user"""
    return job_tracker.get_user_applications(user_id, **filters)


def update_application_status(app_id: str, status: str, notes: str = None) -> Dict:
    """Update application status"""
    return job_tracker.update_status(app_id, status, notes)


def get_dashboard_stats(user_id: str) -> Dict:
    """Get dashboard statistics"""
    return job_tracker.get_pipeline_stats(user_id)


def find_duplicate_applications(user_id: str) -> Dict:
    """Find duplicate applications for a user"""
    return job_tracker.find_duplicates(user_id)


def remove_duplicate_applications(user_id: str, keep: str = "latest") -> Dict:
    """Remove duplicate applications"""
    return job_tracker.remove_duplicates(user_id, keep)


def get_application_details(app_id: str) -> Optional[Dict]:
    """Get detailed information about an application"""
    return job_tracker.get_application_details(app_id)


def search_applications(user_id: str, query: str) -> List[Dict]:
    """Search applications by company, role, or notes"""
    return job_tracker.search_applications(user_id, query)
