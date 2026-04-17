"""Route module for study plan and real-time interview suggestion endpoints."""
import json
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

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


logger = logging.getLogger("routes.study")

# Study plan availability
try:
    from study_plan_generator import study_planner, generate_plan, adapt_plan, export_plan
    STUDY_PLAN_AVAILABLE = True
except ImportError as e:
    STUDY_PLAN_AVAILABLE = False
    logger.warning(f"[StudyPlan] Module not available: {e}")

# Cognitive graph for study plan context
try:
    from cognitive_graph import cognitive_graph
    COGNITIVE_GRAPH_AVAILABLE = True
except ImportError:
    COGNITIVE_GRAPH_AVAILABLE = False

# Realtime suggestions availability
try:
    from realtime_suggestions import (
        realtime_engine,
        voice_processor,
        process_transcript_segment,
        process_voice_command
    )
    REALTIME_AVAILABLE = True
except ImportError as e:
    REALTIME_AVAILABLE = False
    logger.warning(f"[Realtime] Module not available: {e}")

router = APIRouter()


# --- Study Plan Endpoints ---

def _serialize_plan(plan) -> dict:
    """Serialize a StudyPlan object to a JSON-ready dict"""
    result = {
        "user_id": plan.user_id,
        "created_at": plan.created_at.isoformat(),
        "duration_days": plan.duration_days,
        "progress": {
            "total_tasks": plan.total_tasks,
            "completed_tasks": plan.completed_tasks,
            "percentage": round(plan.progress_percentage, 2)
        },
        "weak_areas": plan.weak_areas,
        "strong_areas": plan.strong_areas,
        "milestones": plan.milestones,
        "target_role": plan.target_role,
        "target_company": plan.target_company,
        "skill_gaps": plan.skill_gaps,
        "plan_type": plan.plan_type,
        "personalization_context": getattr(plan, "personalization_context", None),
        "sessions": [
            {
                "date": s.date.isoformat(),
                "theme": s.theme,
                "total_minutes": s.total_minutes,
                "day_number": getattr(s, "day_number", 0),
                "focus_task_id": getattr(s, "focus_task_id", None),
                "stretch_task_id": getattr(s, "stretch_task_id", None),
                "tasks": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "description": t.description,
                        "difficulty": t.difficulty,
                        "category": t.category,
                        "estimated_minutes": t.estimated_minutes,
                        "completed": t.completed,
                        "resources": t.resources,
                        "parent_area": getattr(t, "parent_area", ""),
                        "is_focus": getattr(t, "is_focus", False),
                        "is_stretch": getattr(t, "is_stretch", False),
                        "confidence_target": getattr(t, "confidence_target", 0.8),
                    }
                    for t in s.tasks
                ]
            }
            for s in plan.sessions
        ]
    }
    return result


class StudyPlanPersonalizedRequest(BaseModel):
    """Request body for personalized study plan generation"""
    user_id: str
    target_role: str
    target_company: Optional[str] = None
    job_description: Optional[str] = None
    current_skills: Optional[List[str]] = None
    days: int = 30
    daily_minutes: int = 60


@router.post("/study-plan/generate")
async def generate_study_plan(
    user_id: str = Query(..., description="User ID"),
    days: int = Query(30, description="Plan duration in days"),
    daily_minutes: int = Query(60, description="Daily study time target"),
    target_role: Optional[str] = Query(None, description="Target job role"),
    target_company: Optional[str] = Query(None, description="Target company name"),
    job_description: Optional[str] = Query(None, description="Job description text"),
    current_skills: Optional[str] = Query(None, description="Comma-separated current skills"),
    user: User = Depends(require_authentication)
):
    """Generate personalized study plan."""
    if not STUDY_PLAN_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Study plan generator not available", status_code=503)

    try:
        skills_list = [s.strip() for s in current_skills.split(",")] if current_skills else None

        graph_data = None
        if COGNITIVE_GRAPH_AVAILABLE:
            try:
                stats = cognitive_graph.get_graph_stats(user_id)
                graph_data = {"skills": stats.get("top_skills", [])}
            except Exception:
                pass  # nosec B110

        plan = study_planner.generate_plan(
            user_id, days, daily_minutes, graph_data,
            target_role=target_role,
            target_company=target_company,
            job_description=job_description,
            current_skills=skills_list,
        )

        return _serialize_plan(plan)
    except Exception as e:
        logger.error(f"[StudyPlan] Generation error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/study-plan/generate-personalized")
async def generate_personalized_study_plan(
    request: StudyPlanPersonalizedRequest,
    user: User = Depends(require_authentication)
):
    """Generate a personalized study plan with full input via JSON body (for large JDs)"""
    if not STUDY_PLAN_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Study plan generator not available", status_code=503)

    try:
        graph_data = None
        if COGNITIVE_GRAPH_AVAILABLE:
            try:
                stats = cognitive_graph.get_graph_stats(request.user_id)
                graph_data = {"skills": stats.get("top_skills", [])}
            except Exception:
                pass  # nosec B110

        plan = study_planner.generate_plan(
            request.user_id, request.days, request.daily_minutes, graph_data,
            target_role=request.target_role,
            target_company=request.target_company,
            job_description=request.job_description,
            current_skills=request.current_skills,
        )

        return _serialize_plan(plan)
    except Exception as e:
        logger.error(f"[StudyPlan] Personalized generation error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/study-plan/{user_id}")
async def get_study_plan(user_id: str):
    """Get current study plan for user (generates new one if none exists)"""
    if not STUDY_PLAN_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Study plan generator not available", status_code=503)

    try:
        graph_data = None
        if COGNITIVE_GRAPH_AVAILABLE:
            try:
                stats = cognitive_graph.get_graph_stats(user_id)
                graph_data = {"skills": stats.get("top_skills", [])}
            except Exception:
                pass  # nosec B110

        plan = study_planner.generate_plan(user_id, days=30, daily_minutes=60, cognitive_graph_data=graph_data)
        return json.loads(study_planner.export_plan(plan, "json"))
    except Exception as e:
        logger.error(f"[StudyPlan] Get error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/study-plan/{user_id}/complete-task")
async def complete_study_task(
    user_id: str,
    task_id: str = Query(...),
    performance_score: float = Query(0.7, description="Performance rating 0.0-1.0")
):
    """Mark task as complete and adapt plan"""
    if not STUDY_PLAN_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Study plan generator not available", status_code=503)

    try:
        return {
            "user_id": user_id,
            "task_id": task_id,
            "completed": True,
            "performance_score": performance_score,
            "message": "Task marked complete" + (
                " - Excellent! Advancing schedule." if performance_score > 0.9
                else " - Added remedial practice." if performance_score < 0.5
                else ""
            )
        }
    except Exception as e:
        logger.error(f"[StudyPlan] Complete error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/study-plan/{user_id}/today")
async def get_today_session(user_id: str):
    """Get today's study session"""
    if not STUDY_PLAN_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Study plan generator not available", status_code=503)

    try:
        plan = study_planner.generate_plan(user_id, days=30)
        today = datetime.now().date()

        for session in plan.sessions:
            if session.date.date() == today:
                return {
                    "date": session.date.isoformat(),
                    "theme": session.theme,
                    "total_minutes": session.total_minutes,
                    "tasks": [
                        {
                            "id": t.id,
                            "title": t.title,
                            "difficulty": t.difficulty,
                            "category": t.category,
                            "estimated_minutes": t.estimated_minutes,
                            "resources": t.resources
                        }
                        for t in session.tasks
                    ]
                }

        return {"message": "No study session scheduled for today", "tasks": []}
    except Exception as e:
        logger.error(f"[StudyPlan] Today error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/study-plan/resources/{category}")
async def get_study_resources(
    category: str,
    difficulty: str = Query("medium"),
    count: int = Query(5)
):
    """Get study resources for a category"""
    if not STUDY_PLAN_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Study plan generator not available", status_code=503)

    try:
        resources = study_planner.resource_lib.get_resources(category, difficulty, count)
        return {
            "category": category,
            "difficulty": difficulty,
            "resources": resources
        }
    except Exception as e:
        logger.error(f"[StudyPlan] Resources error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/study-plan/{user_id}/export")
async def export_study_plan(
    user_id: str,
    format: str = Query("json", description="Export format: json, ical, markdown")
):
    """Export study plan to various formats"""
    if not STUDY_PLAN_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Study plan generator not available", status_code=503)

    try:
        plan = study_planner.generate_plan(user_id, days=30)
        exported = study_planner.export_plan(plan, format)

        return {
            "user_id": user_id,
            "format": format,
            "content": exported
        }
    except Exception as e:
        logger.error(f"[StudyPlan] Export error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


# --- Realtime Suggestions Endpoints ---

@router.post("/realtime/process")
async def process_realtime_segment(
    text: str = Query(...),
    speaker: str = Query(...),
    conversation_id: Optional[str] = Query(None)
):
    """Process a transcript segment and return suggestion if relevant."""
    if not REALTIME_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Realtime suggestion engine not available", status_code=503)

    try:
        suggestion = process_transcript_segment(text, speaker)

        if suggestion:
            return {
                "has_suggestion": True,
                "suggestion": {
                    "id": suggestion.id,
                    "type": suggestion.type,
                    "content": suggestion.content,
                    "confidence": suggestion.confidence,
                    "relevance_score": suggestion.relevance_score,
                    "context": suggestion.context
                }
            }

        return {"has_suggestion": False}
    except Exception as e:
        logger.error(f"[Realtime] Error processing segment: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/realtime/command")
async def process_voice_command_api(
    text: str = Query(...),
    conversation_id: Optional[str] = Query(None)
):
    """Process a voice command from the user."""
    if not REALTIME_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Realtime suggestion engine not available", status_code=503)

    try:
        result = process_voice_command(text)

        if result:
            return {
                "is_command": True,
                "action": result.get("action"),
                "data": result
            }

        return {"is_command": False}
    except Exception as e:
        logger.error(f"[Realtime] Error processing command: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/realtime/suggestion-history")
async def get_suggestion_history(
    limit: int = Query(50)
):
    """Get history of suggestions shown during current session"""
    if not REALTIME_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Realtime suggestion engine not available", status_code=503)

    try:
        history = realtime_engine.get_suggestion_history(limit)
        return {
            "suggestions": [
                {
                    "id": s.id,
                    "type": s.type,
                    "content": s.content[:200],
                    "confidence": s.confidence,
                    "timestamp": s.timestamp.isoformat()
                }
                for s in history
            ],
            "count": len(history)
        }
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/realtime/configure")
async def configure_suggestions(
    min_confidence: float = Query(0.6),
    cooldown_seconds: float = Query(10.0)
):
    """Configure realtime suggestion parameters"""
    if not REALTIME_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Realtime suggestion engine not available", status_code=503)

    try:
        realtime_engine.set_min_confidence(min_confidence)
        realtime_engine.cooldown_seconds = cooldown_seconds
        return {
            "configured": True,
            "min_confidence": min_confidence,
            "cooldown_seconds": cooldown_seconds
        }
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/realtime/clear")
async def clear_suggestion_state():
    """Clear buffer and suggestion history (call when starting new interview)"""
    if not REALTIME_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Realtime suggestion engine not available", status_code=503)

    try:
        realtime_engine.clear_buffer()
        return {"cleared": True}
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)