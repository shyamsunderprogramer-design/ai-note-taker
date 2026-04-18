"""Route module for interview simulator, mock interview library, resume review, and complexity analysis."""
import io
import logging
import re
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse

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


logger = logging.getLogger("routes.interview")

# Interview simulator
try:
    from interview_simulator import (
        interview_simulator,
        create_interview,
        get_question,
        submit_response,
        finish_interview
    )
    INTERVIEW_SIMULATOR_AVAILABLE = True
except ImportError:
    INTERVIEW_SIMULATOR_AVAILABLE = False

# Mock interview library
try:
    from mock_interview_library import (
        mock_library,
        get_all_questions,
        get_questions_by_role,
        get_questions_by_company,
        get_random_question,
        get_practice_set,
        get_library_stats,
        search_questions
    )
    MOCK_LIBRARY_AVAILABLE = True
except ImportError as e:
    MOCK_LIBRARY_AVAILABLE = False

# Resume review
try:
    from resume_review import resume_reviewer, analyze_resume
    RESUME_REVIEW_AVAILABLE = True
except ImportError:
    RESUME_REVIEW_AVAILABLE = False

# Job tracker for resume comparison
try:
    from job_tracker import job_tracker
    JOB_TRACKER_AVAILABLE = True
except ImportError:
    JOB_TRACKER_AVAILABLE = False

# Resume review V2
RESUME_REVIEW_V2_AVAILABLE = False
resume_reviewer_v2 = None
try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "modules" / "interview"))
    from resume_review_v2 import ResumeReviewerV2, analyze_resume as analyze_resume_v2_func
    resume_reviewer_v2 = ResumeReviewerV2()
    RESUME_REVIEW_V2_AVAILABLE = True
except ImportError as e:
    logger.warning("[ResumeReviewV2] Module not available: %s", str(e))


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes"""
    text = []
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            text.append(page.extract_text() or '')
        return '\n'.join(text)
    except Exception:
        pass  # nosec B110

    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text.append(page.extract_text() or '')
            return '\n'.join(text)
    except Exception:
        pass  # nosec B110

    text = pdf_bytes.decode('latin-1', errors='ignore')
    text = ''.join(c if c.isprintable() or c in '\n\t' else ' ' for c in text)
    return text[:10000]


def extract_text_from_docx(docx_bytes: bytes) -> str:
    """Extract text from DOCX bytes"""
    try:
        from docx import Document
        doc = Document(io.BytesIO(docx_bytes))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return '\n'.join(paragraphs)
    except Exception as e:
        logger.warning("[ResumeReview] DOCX extraction error: %s", str(e))
        return ""


def extract_complexity_from_text(text: str) -> Dict:
    """Extract Big-O complexity notation from text"""
    text_lower = text.lower()

    patterns = {
        'time_complexity': [
            r'o\(1\)', r'o\(log\s*n\)', r'o\(n\)', r'o\(n\s*log\s*n\)',
            r'o\(n\^2\)', r'o\(n\^3\)', r'o\(2\^n\)', r'o\(n!\)',
            r'constant\s*time', r'linear\s*time', r'quadratic\s*time', r'exponential\s*time',
        ],
        'space_complexity': [
            r'o\(1\)\s*space', r'o\(n\)\s*space', r'o\(log\s*n\)\s*space',
            r'constant\s*space', r'linear\s*space',
        ],
        'algorithm_patterns': [
            r'dynamic\s*programming', r'divide\s*and\s*conquer', r'greedy\s*algorithm',
            r'brute\s*force', r'binary\s*search', r'depth\s*first\s*search',
            r'breadth\s*first\s*search', r'recursion', r'iteration',
        ]
    }

    results = {
        'time_complexity': [],
        'space_complexity': [],
        'algorithm_types': [],
        'detected': False
    }

    for key, pats in patterns.items():
        for pattern in pats:
            matches = re.findall(pattern, text_lower)
            if matches:
                results[key].extend(matches)

    results['detected'] = bool(
        results['time_complexity'] or results['space_complexity'] or results['algorithm_types']
    )

    return results


router = APIRouter()


# --- Interview Simulator Endpoints ---

@router.post("/interview-simulator/create")
async def interview_simulator_create(
    company: str = Query(..., description="Target company name"),
    role: str = Query(None, description="Job role"),
    num_questions: int = Query(5, description="Number of questions"),
    difficulty: str = Query(None, description="Filter by difficulty (easy/medium/hard)"),
    user_id: str = Query("default", description="User ID")
):
    """Create a new interview simulation session."""
    if not INTERVIEW_SIMULATOR_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Interview simulator not available", status_code=503)

    try:
        result = interview_simulator.create_session(company, role, num_questions, user_id, difficulty)
        return result
    except Exception as e:
        logger.error("[InterviewSimulator] Create error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/interview-simulator/{session_id}/question")
async def interview_simulator_get_question(session_id: str):
    """Get the next question in the interview session."""
    if not INTERVIEW_SIMULATOR_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Interview simulator not available", status_code=503)

    try:
        question = interview_simulator.get_next_question(session_id)
        if question is None:
            return {"status": "complete", "message": "Interview complete"}
        return question
    except Exception as e:
        logger.error("[InterviewSimulator] Get question error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.post("/interview-simulator/{session_id}/answer")
async def interview_simulator_submit_answer(
    session_id: str,
    transcript: str = Query(..., description="User's answer transcript"),
    duration_ms: int = Query(0, description="Answer duration in milliseconds")
):
    """Submit an answer and get AI evaluation."""
    if not INTERVIEW_SIMULATOR_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Interview simulator not available", status_code=503)

    try:
        result = interview_simulator.submit_answer(session_id, transcript, duration_ms)
        return result
    except Exception as e:
        logger.error("[InterviewSimulator] Submit answer error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/interview-simulator/{session_id}/status")
async def interview_simulator_status(session_id: str):
    """Get current session status."""
    if not INTERVIEW_SIMULATOR_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Interview simulator not available", status_code=503)

    try:
        s = interview_simulator.get_session_status(session_id)
        if s is None:
            return error_response(ErrorCode.NOT_FOUND, "Session not found", status_code=404)
        return s
    except Exception as e:
        logger.error("[InterviewSimulator] Status error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.post("/interview-simulator/{session_id}/finish")
async def interview_simulator_finish(session_id: str):
    """Complete the interview and save to cognitive graph."""
    if not INTERVIEW_SIMULATOR_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Interview simulator not available", status_code=503)

    try:
        result = finish_interview(session_id)
        return result
    except Exception as e:
        logger.error("[InterviewSimulator] Finish error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


# --- Mock Interview Library Endpoints ---

@router.get("/mock-interview/questions")
async def get_mock_questions(
    role: str = Query(None, description="Filter by role"),
    category: str = Query(None, description="Filter by category"),
    difficulty: str = Query(None, description="Filter by difficulty"),
    company: str = Query(None, description="Filter by company"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get mock interview questions with optional filtering."""
    if not MOCK_LIBRARY_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Mock interview library not available", status_code=503)

    try:
        questions = mock_library.get_all_questions()

        if role:
            questions = [q for q in questions if q.role == role]
        if category:
            questions = [q for q in questions if q.category == category]
        if difficulty:
            questions = [q for q in questions if q.difficulty == difficulty]
        if company:
            questions = [q for q in questions if q.company and q.company.lower() == company.lower()]

        total = len(questions)
        result = [vars(q) for q in questions[offset:offset + limit]]

        return {
            "questions": result,
            "total": total,
            "limit": limit,
            "offset": offset,
            "filters": {"role": role, "category": category, "difficulty": difficulty, "company": company}
        }
    except Exception as e:
        logger.error("[MockLibrary] Error getting questions: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/mock-interview/question/random")
async def get_random_mock_question(
    role: str = Query(None, description="Filter by role"),
    category: str = Query(None, description="Filter by category"),
    difficulty: str = Query(None, description="Filter by difficulty")
):
    """Get a random question matching criteria."""
    if not MOCK_LIBRARY_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Mock interview library not available", status_code=503)

    try:
        question = mock_library.get_random_question(role, category, difficulty)
        if question:
            return {"question": vars(question)}
        return error_response(ErrorCode.NOT_FOUND, "No questions found matching criteria", status_code=404)
    except Exception as e:
        logger.error("[MockLibrary] Error getting random question: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/mock-interview/practice-set")
async def get_practice_question_set(
    role: str = Query("software_engineer", description="Role for practice set"),
    num_questions: int = Query(5, description="Number of questions", ge=1, le=10)
):
    """Get a balanced practice set with mix of categories and difficulties."""
    if not MOCK_LIBRARY_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Mock interview library not available", status_code=503)

    try:
        questions = mock_library.get_practice_set(role, num_questions)
        return {
            "questions": [vars(q) for q in questions],
            "role": role,
            "total_time_estimate": sum(q.time_estimate_minutes for q in questions)
        }
    except Exception as e:
        logger.error("[MockLibrary] Error getting practice set: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/mock-interview/search")
async def search_mock_questions(
    query: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Search questions by text (paginated)."""
    if not MOCK_LIBRARY_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Mock interview library not available", status_code=503)

    try:
        questions = mock_library.search_questions(query)
        total = len(questions)
        return {
            "questions": [vars(q) for q in questions[offset:offset + limit]],
            "query": query,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error("[MockLibrary] Error searching questions: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/mock-interview/stats")
async def get_mock_library_stats():
    """Get library statistics."""
    if not MOCK_LIBRARY_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Mock interview library not available", status_code=503)

    try:
        return mock_library.get_stats()
    except Exception as e:
        logger.error("[MockLibrary] Error getting stats: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/mock-interview/companies")
async def get_companies_with_questions():
    """Get list of companies that have specific questions."""
    if not MOCK_LIBRARY_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Mock interview library not available", status_code=503)

    try:
        companies = set()
        for q in mock_library.get_all_questions():
            if q.company:
                companies.add(q.company)
        return {"companies": sorted(list(companies))}
    except Exception as e:
        logger.error("[MockLibrary] Error getting companies: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


# --- Resume Review Endpoints ---

@router.post("/resume/analyze")
async def analyze_resume_endpoint(
    resume_text: str = Query(..., description="Resume text content"),
    job_description: str = Query(None, description="Job description for comparison"),
    role_type: str = Query("software_engineer", description="Role type")
):
    """Analyze resume and provide feedback."""
    if not RESUME_REVIEW_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Resume review not available", status_code=503)

    try:
        result = resume_reviewer.analyze_resume(resume_text, job_description, role_type)
        return result
    except Exception as e:
        logger.error("[ResumeReview] Analyze error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.post("/resume/compare")
async def compare_resume_to_job(
    resume_text: str = Query(..., description="Resume text content"),
    job_description: str = Query(..., description="Job description"),
    company: str = Query(None, description="Company name"),
    role: str = Query(None, description="Role title")
):
    """Compare resume against a specific job posting."""
    if not RESUME_REVIEW_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Resume review not available", status_code=503)

    try:
        analysis = resume_reviewer.analyze_resume(resume_text, job_description)

        company_insights = None
        if company and JOB_TRACKER_AVAILABLE:
            company_insights = job_tracker.get_company_insights(company)

        return {
            "analysis": analysis.get("analysis", {}),
            "company_insights": company_insights,
            "recommendations": analysis.get("analysis", {}).get("tailored_suggestions", []),
            "match_score": analysis.get("analysis", {}).get("overall_score", 0)
        }
    except Exception as e:
        logger.error("[ResumeReview] Compare error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.post("/resume/upload")
async def upload_resume_file(
    file: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
    role_type: str = Form("software_engineer")
):
    """Upload and analyze a resume file (PDF, DOCX, TXT, MD)."""
    if not RESUME_REVIEW_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Resume review not available", status_code=503)

    try:
        filename = file.filename.lower()
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md', '.rtf'}

        if not any(filename.endswith(ext) for ext in allowed_extensions):
            return error_response(ErrorCode.INVALID_FORMAT, f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}", status_code=422)

        content = await file.read()

        if filename.endswith('.pdf'):
            resume_text = extract_text_from_pdf(content)
        elif filename.endswith('.docx') or filename.endswith('.doc'):
            resume_text = extract_text_from_docx(content)
        else:
            try:
                resume_text = content.decode('utf-8')
            except UnicodeDecodeError:
                resume_text = content.decode('latin-1', errors='ignore')

        if not resume_text or len(resume_text.strip()) < 50:
            return error_response(ErrorCode.VALIDATION_ERROR, "Could not extract meaningful text from file. Please paste text manually.", status_code=422)

        result = resume_reviewer.analyze_resume(resume_text, job_description, role_type)

        result['file_info'] = {
            'filename': file.filename,
            'size': len(content),
            'extracted_length': len(resume_text)
        }

        return result

    except Exception as e:
        logger.error("[ResumeReview] Upload error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.post("/resume/analyze-v2")
async def analyze_resume_v2_endpoint(
    resume_text: Optional[str] = Form(None, description="Resume text content"),
    job_description: Optional[str] = Form(None, description="Job description for tailoring"),
    role_type: str = Form("software_engineer", description="Type of role"),
    file: Optional[UploadFile] = File(None, description="Resume file (PDF, DOCX, TXT)")
):
    """Analyze resume with enhanced V2 features (FREE)."""
    if not RESUME_REVIEW_V2_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Resume review V2 not available", status_code=503)

    try:
        extracted_text = resume_text
        file_info = None

        if file:
            content = await file.read()
            file_ext = file.filename.lower().split('.')[-1]

            if file_ext == 'pdf':
                extracted_text = extract_text_from_pdf(content)
            elif file_ext in ['docx', 'doc']:
                extracted_text = extract_text_from_docx(content)
            elif file_ext in ['txt', 'md', 'rtf']:
                try:
                    extracted_text = content.decode('utf-8')
                except UnicodeDecodeError:
                    extracted_text = content.decode('latin-1', errors='ignore')

            file_info = {
                'filename': file.filename,
                'size': len(content),
                'extracted_length': len(extracted_text) if extracted_text else 0
            }

        if not extracted_text or len(extracted_text.strip()) < 50:
            return error_response(ErrorCode.VALIDATION_ERROR, "Could not extract meaningful text. Please paste text directly.", status_code=422)

        result = resume_reviewer_v2.analyze_resume(extracted_text, job_description, role_type)

        if file_info:
            result['file_info'] = file_info

        return result

    except Exception as e:
        logger.error("[ResumeReviewV2] Analyze error: %s", str(e), exc_info=True)
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.post("/resume/tailor-v2")
async def tailor_resume_v2(
    resume_text: str = Form(..., description="Resume text content"),
    job_description: str = Form(..., description="Job description"),
    focus_areas: Optional[str] = Form(None, description="Comma-separated focus areas")
):
    """Get tailored suggestions for specific job (FREE)."""
    if not RESUME_REVIEW_V2_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Resume review V2 not available", status_code=503)

    try:
        result = resume_reviewer_v2.analyze_resume(resume_text, job_description)

        tailored = result.get('analysis', {}).get('tailored_suggestions', [])
        rewrites = result.get('analysis', {}).get('rewrites', [])
        missing_keywords = result.get('analysis', {}).get('missing_keywords', [])

        return {
            "success": True,
            "suggestions": tailored[:5],
            "rewrites": rewrites[:3],
            "missing_keywords": missing_keywords[:10],
            "message": "Free tier: Limited to 5 suggestions, 3 rewrites. Upgrade to Pro for unlimited."
        }

    except Exception as e:
        logger.error("[ResumeReviewV2] Tailor error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


# --- Complexity Analysis Endpoint ---

@router.post("/analysis/complexity")
async def analyze_complexity(
    text: str = Query(..., description="Text to analyze for complexity")
):
    """Analyze text for Big-O complexity notation and algorithm patterns."""
    try:
        result = extract_complexity_from_text(text)

        badge = None
        if result['detected']:
            complexities = result['time_complexity']
            if any('n!' in c or '2^n' in c for c in complexities):
                badge = {"type": "exponential", "color": "#ef4444", "label": "O(n!)"}
            elif any('n^2' in c or 'n^3' in c for c in complexities):
                badge = {"type": "polynomial", "color": "#f59e0b", "label": "O(n^2)"}
            elif any('n log' in c for c in complexities):
                badge = {"type": "linearithmic", "color": "#3b82f6", "label": "O(n log n)"}
            elif any('n)' in c and 'log' not in c for c in complexities):
                badge = {"type": "linear", "color": "#10b981", "label": "O(n)"}
            elif any('log' in c for c in complexities):
                badge = {"type": "logarithmic", "color": "#8b5cf6", "label": "O(log n)"}
            elif any('constant' in c or 'o(1)' in c for c in complexities):
                badge = {"type": "constant", "color": "#10b981", "label": "O(1)"}

        return {
            "success": True,
            "analysis": result,
            "badge": badge,
            "suggestions": [
                "Consider time/space tradeoffs" if result['time_complexity'] and not result['space_complexity'] else None,
                "Space complexity not analyzed" if not result['space_complexity'] and result['time_complexity'] else None,
            ]
        }
    except Exception as e:
        logger.error("[Complexity] Analysis error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)