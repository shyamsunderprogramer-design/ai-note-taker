"""Route module for analytics, conversation analysis, and performance insights."""
import logging
import time

from fastapi import APIRouter, Body, Depends, Query

from security import ErrorCode, error_response

logger = logging.getLogger("routes.analytics")

# Analytics store availability
try:
    from analytics import get_analytics_store
    ANALYTICS_STORE_AVAILABLE = True
except ImportError:
    ANALYTICS_STORE_AVAILABLE = False

# Analytics engine availability
try:
    from analytics_engine import analytics
    ANALYTICS_AVAILABLE = True
except ImportError as e:
    ANALYTICS_AVAILABLE = False
    logger.warning("[Analytics] Module not available: %s", str(e))

# Conversation analyzer availability
try:
    from conversation_analyzer import analyzer, analyze_conversation
    ANALYZER_AVAILABLE = True
except ImportError as e:
    ANALYZER_AVAILABLE = False
    logger.warning("[Analyzer] Module not available: %s", str(e))

# Performance analyzer availability
try:
    from performance_analyzer import analyzer as performance_analyzer
    PERFORMANCE_ANALYZER_AVAILABLE = True
except ImportError as e:
    PERFORMANCE_ANALYZER_AVAILABLE = False
    logger.warning("[PerformanceAnalyzer] Module not available: %s", str(e))

# Cognitive graph for performance checklists
try:
    from cognitive_graph import cognitive_graph
    COGNITIVE_GRAPH_AVAILABLE = True
except ImportError:
    COGNITIVE_GRAPH_AVAILABLE = False

# Auth helpers (mirrored — will be consolidated)
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from security import get_current_user
from security.auth import User

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


router = APIRouter()


# --- Analytics Store Endpoints ---

@router.post("/analytics/record")
async def record_analytics(body: dict, user: User = Depends(require_authentication)):
    """Record analytics for a conversation."""
    if not ANALYTICS_STORE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Analytics store not available", status_code=503)

    from datetime import datetime as _dt
    store = get_analytics_store()

    start_time = body.get("start_time") or time.time()
    end_time = body.get("end_time") or time.time()
    if isinstance(start_time, str):
        try:
            start_time = _dt.fromisoformat(start_time).timestamp()
        except ValueError:
            start_time = time.time()
    if isinstance(end_time, str):
        try:
            end_time = _dt.fromisoformat(end_time).timestamp()
        except ValueError:
            end_time = time.time()

    metrics = store.record_conversation(
        conversation_id=body.get("conversation_id"),
        messages=body.get("messages", []),
        start_time=float(start_time),
        end_time=float(end_time),
        models_used=body.get("models_used", [])
    )

    return {"status": "recorded", "metrics": {
        "duration_minutes": metrics.duration_minutes,
        "message_count": metrics.message_count
    }}


@router.get("/analytics/summary")
async def get_analytics_summary(days: int = 30, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    """Get analytics summary for the past N days (paginated)."""
    if not ANALYTICS_STORE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Analytics store not available", status_code=503)

    store = get_analytics_store()
    data = store.get_summary(days)
    if isinstance(data, list):
        total = len(data)
        return {"data": data[offset:offset + limit], "total": total, "limit": limit, "offset": offset}
    return data


@router.post("/analytics/export")
async def export_analytics(body: dict):
    """Export analytics data."""
    if not ANALYTICS_STORE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Analytics store not available", status_code=503)

    store = get_analytics_store()
    fmt = body.get("format", "json")
    return store.get_export_data(fmt)


# --- Analytics Engine Endpoints (Graph Dashboard) ---

@router.get("/analytics/skill-progression/{user_id}")
async def get_skill_progression_api(
    user_id: str,
    skill: str = Query(...),
    months: int = Query(6)
):
    """Get skill progression over time for charting"""
    if not ANALYTICS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Analytics engine not available", status_code=503)

    try:
        data = analytics.get_skill_progression(user_id, skill, months)
        return data
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.post("/analytics/company-comparison")
async def compare_companies(
    companies: List[str] = Query(...)
):
    """Compare interview patterns across companies (heatmap data)"""
    if not ANALYTICS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Analytics engine not available", status_code=503)

    try:
        data = analytics.get_company_comparison(companies)
        return data
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/analytics/topic-network/{user_id}")
async def get_topic_network_api(
    user_id: str,
    min_connections: int = Query(2)
):
    """Get topic co-occurrence network for D3.js visualization"""
    if not ANALYTICS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Analytics engine not available", status_code=503)

    try:
        data = analytics.get_topic_network(user_id, min_connections)
        return data
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/analytics/interview-calendar/{user_id}")
async def get_interview_calendar_api(
    user_id: str,
    months: int = Query(6)
):
    """Get interview frequency data for calendar heatmap"""
    if not ANALYTICS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Analytics engine not available", status_code=503)

    try:
        data = analytics.get_interview_calendar(user_id, months)
        return data
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/analytics/performance-trends/{user_id}")
async def get_performance_trends_api(
    user_id: str
):
    """Get overall performance trends (improving/declining/stable skills)"""
    if not ANALYTICS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Analytics engine not available", status_code=503)

    try:
        data = analytics.get_performance_trends(user_id)
        return data
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/analytics/dashboard/{user_id}")
async def get_dashboard_summary_api(
    user_id: str
):
    """Get dashboard summary with key metrics"""
    if not ANALYTICS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Analytics engine not available", status_code=503)

    try:
        data = analytics.get_dashboard_summary(user_id)
        return data
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


# --- Conversation Analyzer Endpoints ---

@router.post("/analyze/conversation")
async def analyze_conversation_api(
    conversation: Dict
):
    """Analyze a conversation for auto-tagging and quality metrics."""
    if not ANALYZER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Conversation analyzer not available", status_code=503)

    try:
        analysis = analyze_conversation(conversation)
        return analysis
    except Exception as e:
        logger.error("[Analyzer] Error analyzing conversation: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.post("/analyze/batch")
async def analyze_conversations_batch(
    conversations: List[Dict]
):
    """Analyze multiple conversations in batch"""
    if not ANALYZER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Conversation analyzer not available", status_code=503)

    try:
        results = []
        for conv in conversations:
            analysis = analyze_conversation(conv)
            results.append({
                "id": conv.get("id", "unknown"),
                "title": conv.get("title", ""),
                "tags": analysis["tags"],
                "quality_tier": analysis["tags"]["quality_tier"],
                "overall_score": analysis["quality_metrics"]["overall_score"]
            })

        return {
            "analyzed": len(results),
            "results": results
        }
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/analyze/types")
async def get_conversation_types():
    """Get list of supported conversation types"""
    if not ANALYZER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Conversation analyzer not available", status_code=503)

    try:
        return {
            "types": [
                {"id": "practice_session", "label": "Practice Session", "description": "Self-study or preparation"},
                {"id": "mock_interview", "label": "Mock Interview", "description": "Simulated interview with feedback"},
                {"id": "real_interview", "label": "Real Interview", "description": "Actual company interview"}
            ],
            "focus_areas": [
                {"id": "system_design_focus", "label": "System Design"},
                {"id": "algorithm_heavy", "label": "Algorithms"},
                {"id": "behavioral_only", "label": "Behavioral"},
                {"id": "frontend_focus", "label": "Frontend"},
                {"id": "backend_focus", "label": "Backend"},
                {"id": "fullstack_focus", "label": "Fullstack"}
            ]
        }
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


# --- Performance Analyzer Endpoints ---

@router.post("/performance/analyze")
async def analyze_answer_performance(
    answer_text: str = Query(..., description="The answer text to analyze"),
    question_type: str = Query("behavioral", description="Type: behavioral, technical, system_design")
):
    """Analyze an interview answer for STAR method, code quality, speaking patterns"""
    if not PERFORMANCE_ANALYZER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Performance analyzer not available", status_code=503)

    try:
        result = performance_analyzer.analyze_answer(answer_text, question_type)
        return result
    except Exception as e:
        logger.error("[PerformanceAnalyzer] Error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.post("/performance/analyze-batch")
async def analyze_batch_answers(
    answers: List[dict]
):
    """Analyze multiple answers in batch"""
    if not PERFORMANCE_ANALYZER_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Performance analyzer not available", status_code=503)

    try:
        results = [
            performance_analyzer.analyze_answer(
                a.get("text", ""),
                a.get("type", "behavioral")
            )
            for a in answers
        ]
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error("[PerformanceAnalyzer] Batch error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/performance/tiers")
async def get_quality_tiers():
    """Get quality tier thresholds and descriptions"""
    return {
        "excellent": {"min_score": 80, "description": "Excellent answer quality"},
        "good": {"min_score": 65, "description": "Good with minor improvements needed"},
        "average": {"min_score": 50, "description": "Average, significant improvements possible"},
        "needs_improvement": {"min_score": 0, "description": "Needs substantial improvement"}
    }


@router.get("/performance/checklist/{user_id}")
async def get_personalized_checklist(
    user_id: str,
    question_type: str = Query("behavioral")
):
    """Get personalized interview performance checklist based on cognitive graph"""
    if not PERFORMANCE_ANALYZER_AVAILABLE or not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Performance analyzer or cognitive graph not available", status_code=503)

    try:
        skill_data = cognitive_graph.get_user_skills(user_id)

        checklist = {
            "star_method": {
                "situation": "Set the context - describe the scenario clearly",
                "task": "Define your specific responsibility or challenge",
                "action": "Detail what YOU did (use 'I' not 'we')",
                "result": "Quantify outcomes (e.g., 'reduced latency by 40%')"
            },
            "speaking": {
                "pace": "Aim for 15-25 words per sentence",
                "fillers": "Minimize um, uh, like, you know",
                "clarity": "Pause between key points"
            },
            "technical": {
                "examples": "Provide concrete code examples",
                "complexity": "Discuss time/space complexity",
                "edge_cases": "Mention error handling and edge cases",
                "best_practices": "Reference testing, documentation"
            }
        }

        if skill_data:
            weak_areas = [s for s in skill_data if s.get("confidence", 1.0) < 0.5]
            checklist["focus_areas"] = [s.get("name") for s in weak_areas[:3]]

        return {"checklist": checklist, "user_id": user_id}
    except Exception as e:
        logger.error("[PerformanceAnalyzer] Checklist error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)