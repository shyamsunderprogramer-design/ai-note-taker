"""Route module for AI agents, shadow agent, collaboration, and meeting templates."""
import asyncio
import json
import logging
import uuid
from typing import Dict, Optional

from fastapi import APIRouter, Body, Depends, Query, Request
from fastapi.responses import StreamingResponse

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


logger = logging.getLogger("routes.agents")

# Agent framework availability
try:
    from modules.agents.orchestrator import orchestrator
    from modules.agents.session import session_manager
    AGENTS_AVAILABLE = True
except ImportError as e:
    AGENTS_AVAILABLE = False
    logger.warning(f"[Agents] Agent framework not available: {e}")

# Shadow agent availability
try:
    from shadow_agent import (
        shadow_agent,
        start_shadow_session,
        process_transcript_segment,
        get_shadow_suggestions,
        accept_suggestion_by_id,
        end_shadow_session,
        get_shadow_stats
    )
    SHADOW_AGENT_AVAILABLE = True
except ImportError as e:
    SHADOW_AGENT_AVAILABLE = False

# Collaboration availability
try:
    from collaboration_mode import (
        collaboration_manager,
        create_collaboration_session,
        join_collaboration,
        send_collaboration_message,
        get_collaboration_messages,
        get_collaboration_status,
        end_collaboration
    )
    COLLABORATION_AVAILABLE = True
except ImportError as e:
    COLLABORATION_AVAILABLE = False

# Meeting templates availability
try:
    from meeting_templates import (
        templates_manager,
        get_all_templates,
        get_template,
        get_categories,
        create_template,
        update_template,
        delete_template,
        search_templates,
        generate_notes
    )
    MEETING_TEMPLATES_AVAILABLE = True
except ImportError as e:
    MEETING_TEMPLATES_AVAILABLE = False

# Ingestion results cache
_ingestion_results: Dict = {}

router = APIRouter()


# --- Agent Framework Endpoints ---

@router.post("/agents/sessions")
async def create_agent_session(
    session_type: str = Query("meeting", description="Session type: interview, sales_call, meeting"),
    company: str = Query(None, description="Company name"),
    role: str = Query(None, description="Role/position"),
    stage: str = Query(None, description="Interview or sales stage"),
    active_agents: str = Query("interview_coach,meeting,sales_coach", description="Comma-separated agent types"),
    provider: str = Query("ollama", description="AI provider preference"),
):
    """Create a new AI agent session with specified active agents."""
    if not AGENTS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Agent framework not available", status_code=503)

    try:
        agents_list = [a.strip() for a in active_agents.split(",") if a.strip()]
        config = {"provider": provider}
        session = await session_manager.create_session(
            user_id="default",
            session_type=session_type,
            active_agents=agents_list,
            config=config,
            company=company,
            role=role,
            stage=stage,
        )
        return session
    except Exception as e:
        logger.error(f"[Agents] Create session error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/agents/sessions/{session_id}")
async def get_agent_session(session_id: str):
    """Get agent session state."""
    if not AGENTS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Agent framework not available", status_code=503)

    session = await session_manager.get_session(session_id)
    if not session:
        return error_response(ErrorCode.NOT_FOUND, "Session not found", status_code=404)
    return session


@router.post("/agents/sessions/{session_id}/end")
async def end_agent_session(session_id: str):
    """End an agent session."""
    if not AGENTS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Agent framework not available", status_code=503)

    session = await session_manager.end_session(session_id)
    if not session:
        return error_response(ErrorCode.NOT_FOUND, "Session not found", status_code=404)
    return session


@router.post("/agents/sessions/{session_id}/segment")
async def process_agent_segment(
    session_id: str,
    text: str = Query(..., description="Transcript text"),
    speaker: str = Query(..., description="Speaker: user, interviewer, other, Speaker 1, SPEAKER_00, etc."),
):
    """Process a transcript segment through all active agents. Returns JSON (polling mode)."""
    if not AGENTS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Agent framework not available", status_code=503)

    try:
        result = await orchestrator.process_segment(session_id, text, speaker)
        return result
    except Exception as e:
        logger.error(f"[Agents] Segment processing error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/agents/sessions/{session_id}/stream")
async def stream_agent_suggestions(
    session_id: str,
    text: str = Query(..., description="Transcript text"),
    speaker: str = Query(..., description="Speaker: user, interviewer, other, Speaker 1, SPEAKER_00, etc."),
):
    """SSE stream for real-time agent suggestion delivery."""
    if not AGENTS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Agent framework not available", status_code=503)

    from starlette.responses import StreamingResponse

    async def event_generator():
        async for event in orchestrator.process_segment_stream(session_id, text, speaker):
            yield event

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/agents/sessions/{session_id}/agents")
async def update_active_agents(
    session_id: str,
    active_agents: str = Query(..., description="Comma-separated agent types to activate"),
):
    """Update which agents are active for a session."""
    if not AGENTS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Agent framework not available", status_code=503)

    session = await session_manager.get_session(session_id)
    if not session:
        return error_response(ErrorCode.NOT_FOUND, "Session not found", status_code=404)

    agents_list = [a.strip() for a in active_agents.split(",") if a.strip()]
    session["active_agents"] = agents_list
    for agent_type in agents_list:
        if agent_type not in session.get("agent_states", {}):
            session.setdefault("agent_states", {})[agent_type] = {
                "last_suggestion_time": 0,
                "suggestions_made": 0,
                "suggestions_accepted": 0,
            }

    await session_manager.save_session(session)
    return {"session_id": session_id, "active_agents": agents_list}


@router.get("/agents/sessions/{session_id}/suggestions")
async def get_agent_suggestions(session_id: str):
    """Get all suggestions generated in a session."""
    if not AGENTS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Agent framework not available", status_code=503)

    session = await session_manager.get_session(session_id)
    if not session:
        return error_response(ErrorCode.NOT_FOUND, "Session not found", status_code=404)

    return {"suggestions": session.get("suggestions", [])}


@router.post("/agents/suggestions/{suggestion_id}/accept")
async def accept_agent_suggestion(suggestion_id: str):
    """Accept an agent suggestion and record feedback for self-learning."""
    if not AGENTS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Agent framework not available", status_code=503)

    for session_id, session in session_manager._memory_sessions.items():
        result = session_manager.accept_suggestion(session, suggestion_id)
        if result:
            await session_manager.save_session(session)

            try:
                from agents.learning import get_learner
                learner = get_learner()
                learner.record_acceptance(
                    suggestion_id=suggestion_id,
                    agent_type=result.get("agent_type", ""),
                    category=result.get("category", "general"),
                    content_preview=result.get("content", "")[:200],
                    confidence=result.get("confidence", 0.5),
                    question_hash=result.get("metadata", {}).get("question", "")[:100],
                )
                learner.save_to_session(session)
                await session_manager.save_session(session)
            except Exception as e:
                logger.warning(f"[Agents] Failed to record acceptance feedback: {e}")

            return {"status": "accepted", "suggestion": result}

    return error_response(ErrorCode.NOT_FOUND, "Suggestion not found", status_code=404)


@router.post("/agents/suggestions/{suggestion_id}/dismiss")
async def dismiss_agent_suggestion(suggestion_id: str):
    """Dismiss an agent suggestion and record feedback for self-learning."""
    if not AGENTS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Agent framework not available", status_code=503)

    for session_id, session in session_manager._memory_sessions.items():
        result = session_manager.dismiss_suggestion(session, suggestion_id)
        if result:
            await session_manager.save_session(session)

            try:
                from agents.learning import get_learner
                learner = get_learner()
                learner.record_dismissal(
                    suggestion_id=suggestion_id,
                    agent_type=result.get("agent_type", ""),
                    category=result.get("category", "general"),
                    content_preview=result.get("content", "")[:200],
                    confidence=result.get("confidence", 0.5),
                    question_hash=result.get("metadata", {}).get("question", "")[:100],
                )
                learner.save_to_session(session)
                await session_manager.save_session(session)
            except Exception as e:
                logger.warning(f"[Agents] Failed to record dismissal feedback: {e}")

            return {"status": "dismissed", "suggestion": result}

    return error_response(ErrorCode.NOT_FOUND, "Suggestion not found", status_code=404)


@router.get("/agents/available")
async def list_available_agents():
    """List all available agent types with descriptions."""
    if not AGENTS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Agent framework not available", status_code=503)

    return {"agents": orchestrator.get_available_agents()}


@router.get("/agents/sessions/{session_id}/stats")
async def get_agent_session_stats(session_id: str):
    """Get session statistics."""
    if not AGENTS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Agent framework not available", status_code=503)

    session = await session_manager.get_session(session_id)
    if not session:
        return error_response(ErrorCode.NOT_FOUND, "Session not found", status_code=404)

    return session_manager.get_stats(session)


@router.get("/agents/cache/stats")
async def get_cache_stats():
    """Get context cache statistics."""
    if not AGENTS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Agent framework not available", status_code=503)

    try:
        from agents.cache import get_cache
        return get_cache().get_stats()
    except ImportError:
        return {"error": "Cache module not available"}


@router.post("/agents/cache/cleanup")
async def cleanup_cache():
    """Remove expired entries from the context cache."""
    if not AGENTS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Agent framework not available", status_code=503)

    try:
        from agents.cache import get_cache
        removed = get_cache().cleanup_expired()
        return {"removed": removed}
    except ImportError:
        return {"error": "Cache module not available"}


@router.get("/agents/learning/stats")
async def get_learning_stats(agent_type: Optional[str] = None):
    """Get self-learning performance statistics."""
    if not AGENTS_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Agent framework not available", status_code=503)

    try:
        from agents.learning import get_learner
        return get_learner().get_performance_stats(agent_type)
    except ImportError:
        return {"error": "Learning module not available"}


# --- Ingestion Endpoints ---

@router.post("/agents/ingestion")
async def trigger_ingestion(request: Request):
    """Trigger data ingestion from GitHub repos or local directories."""
    try:
        from agents.ingestion.pipeline import IngestionPipeline
    except ImportError:
        try:
            from modules.agents.ingestion.pipeline import IngestionPipeline
        except ImportError:
            return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Ingestion pipeline not available", status_code=503)

    body = await request.json()
    mode = body.get("mode", "full")
    dry_run = body.get("dry_run", False)
    repo_urls = body.get("repos", [])
    local_paths = body.get("local_paths", [])

    if mode not in ("full", "graph_only", "rag_only"):
        return error_response(ErrorCode.INVALID_INPUT, f"Invalid mode: {mode}", status_code=400)

    if not repo_urls and not local_paths:
        return error_response(ErrorCode.INVALID_INPUT, "Provide 'repos' or 'local_paths'", status_code=400)

    task_id = str(uuid.uuid4())[:8]
    _ingestion_results[task_id] = {"status": "running", "progress": "Starting..."}

    pipeline = IngestionPipeline()

    def _run():
        try:
            if local_paths:
                stats = pipeline.ingest_from_local(local_paths, mode=mode, dry_run=dry_run)
            else:
                stats = pipeline.ingest_from_github(repo_urls, mode=mode, dry_run=dry_run)
            _ingestion_results[task_id] = {"status": "completed", "result": stats.to_dict()}
        except Exception as e:
            logger.error(f"[Ingestion] Background task failed: {e}")
            _ingestion_results[task_id] = {"status": "failed", "error": str(e)}

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run)

    return {"task_id": task_id, "status": "running"}


@router.get("/agents/ingestion/status")
async def get_ingestion_status(task_id: Optional[str] = None):
    """Get ingestion pipeline status, or poll a running task by task_id."""
    if task_id and task_id in _ingestion_results:
        return _ingestion_results[task_id]

    result = {
        "pipeline": "available",
        "agents_available": AGENTS_AVAILABLE,
        "modules": {},
    }

    try:
        from agents.ingestion.markdown_parser import MarkdownQAParser
        result["modules"]["markdown_parser"] = "available"
    except ImportError:
        result["modules"]["markdown_parser"] = "unavailable"

    try:
        from agents.ingestion.pdf_processor import PDFProcessor
        result["modules"]["pdf_processor"] = "available"
    except ImportError:
        result["modules"]["pdf_processor"] = "unavailable"

    try:
        from agents.ingestion.graph_loader import GraphLoader
        gl = GraphLoader()
        result["modules"]["graph_loader"] = "available"
        result["neo4j_available"] = gl._check_neo4j()
    except ImportError:
        result["modules"]["graph_loader"] = "unavailable"
        result["neo4j_available"] = False

    try:
        from agents.ingestion.rag_loader import RAGLoader
        rl = RAGLoader()
        result["modules"]["rag_loader"] = "available"
        ds = rl.doc_store
        result["rag_documents"] = len(ds.list_documents()) if ds else 0
    except ImportError:
        result["modules"]["rag_loader"] = "unavailable"
        result["rag_documents"] = 0

    return result


# --- Shadow Agent Endpoints ---

@router.post("/shadow/start")
async def start_shadow_interview(
    company: str = Query(..., description="Company name"),
    role: str = Query(..., description="Role being interviewed for"),
    stage: str = Query("", description="Interview stage")
):
    """Start a shadow interview session. Redirects to new agent framework when available."""
    if AGENTS_AVAILABLE:
        try:
            session = await session_manager.create_session(
                user_id="default",
                session_type="interview",
                active_agents=["interview_coach"],
                config={"company": company, "role": role, "stage": stage},
                company=company, role=role, stage=stage,
            )
            return {
                "status": "started",
                "session_id": session["id"],
                "company": company,
                "role": role,
                "message": "Shadow agent (LLM-powered) is listening. Press Ctrl+~ to toggle overlay.",
                "agent_framework": "v2",
            }
        except Exception as e:
            logger.warning(f"[ShadowAgent] Fallback to old agent: {e}")

    if not SHADOW_AGENT_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Shadow agent not available", status_code=503)

    try:
        return start_shadow_session(company, role, stage)
    except Exception as e:
        logger.error(f"[ShadowAgent] Start error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/shadow/process")
async def process_shadow_transcript(
    text: str = Query(..., description="Transcript text"),
    speaker: str = Query(..., description="Speaker (user/interviewer/other)")
):
    """Process transcript and generate suggestions. Redirects to agent framework when available."""
    if AGENTS_AVAILABLE:
        for sid, session in reversed(list(session_manager._memory_sessions.items())):
            if session.get("session_type") == "interview" and session.get("state") == "listening":
                try:
                    result = await orchestrator.process_segment(sid, text, speaker)
                    suggestions = result.get("suggestions", [])
                    if suggestions:
                        old_format = {
                            "detected": "question",
                            "question": text,
                            "suggestions": [
                                {
                                    "id": s["id"],
                                    "text": s["content"],
                                    "confidence": s["confidence"],
                                    "hotkey": s.get("metadata", {}).get("hotkey", f"Ctrl+{i+1}"),
                                    "category": s["category"],
                                }
                                for i, s in enumerate(suggestions[:3])
                            ],
                            "agent_framework": "v2",
                        }
                        return old_format
                    return {"detected": False}
                except Exception as e:
                    logger.warning(f"[ShadowAgent] Agent framework error, falling back: {e}")
                    break

    if not SHADOW_AGENT_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Shadow agent not available", status_code=503)

    try:
        result = process_transcript_segment(text, speaker)
        return result or {"detected": False}
    except Exception as e:
        logger.error(f"[ShadowAgent] Process error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/shadow/suggestions")
async def get_shadow_suggestions_list():
    """Get current shadow agent suggestions."""
    if not SHADOW_AGENT_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Shadow agent not available", status_code=503)

    try:
        return {"suggestions": get_shadow_suggestions()}
    except Exception as e:
        logger.error(f"[ShadowAgent] Suggestions error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/shadow/accept")
async def accept_shadow_suggestion(suggestion_id: str = Query(...)):
    """Accept a suggestion."""
    if not SHADOW_AGENT_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Shadow agent not available", status_code=503)

    try:
        text = accept_suggestion_by_id(suggestion_id)
        return {"text": text} if text else {"error": "Suggestion not found"}
    except Exception as e:
        logger.error(f"[ShadowAgent] Accept error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/shadow/end")
async def end_shadow_interview():
    """End shadow interview session."""
    if not SHADOW_AGENT_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Shadow agent not available", status_code=503)

    try:
        return end_shadow_session()
    except Exception as e:
        logger.error(f"[ShadowAgent] End error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/shadow/stats")
async def get_shadow_statistics():
    """Get shadow session statistics."""
    if not SHADOW_AGENT_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Shadow agent not available", status_code=503)

    try:
        return get_shadow_stats()
    except Exception as e:
        logger.error(f"[ShadowAgent] Stats error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


# --- Collaboration Endpoints ---

@router.post("/collaboration/create")
async def create_collaboration(
    host_name: str = Body(..., description="Host name"),
    context: Optional[dict] = Body(default=None, description="Session context"),
    user: User = Depends(require_authentication)
):
    """Create a new collaboration session."""
    if not COLLABORATION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Collaboration mode not available", status_code=503)

    try:
        return create_collaboration_session(host_name, context)
    except Exception as e:
        logger.error(f"[Collaboration] Create error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/collaboration/join")
async def join_collaboration_session(
    join_code: str = Query(..., description="6-digit join code"),
    name: str = Query(..., description="Your name")
):
    """Join a collaboration session."""
    if not COLLABORATION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Collaboration mode not available", status_code=503)

    try:
        return join_collaboration(join_code, name)
    except Exception as e:
        logger.error(f"[Collaboration] Join error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/collaboration/message")
async def send_collaboration_msg(
    session_id: str = Query(...),
    participant_id: str = Query(...),
    text: str = Query(...),
    msg_type: str = Query("suggestion"),
    is_private: bool = Query(False)
):
    """Send a message in collaboration session."""
    if not COLLABORATION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Collaboration mode not available", status_code=503)

    try:
        return send_collaboration_message(session_id, participant_id, text, msg_type, is_private)
    except Exception as e:
        logger.error(f"[Collaboration] Message error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/collaboration/messages")
async def get_collaboration_msgs(
    session_id: str = Query(...),
    participant_id: str = Query(...),
    since: float = Query(0),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Get messages for a session (paginated)."""
    if not COLLABORATION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Collaboration mode not available", status_code=503)

    try:
        msgs = get_collaboration_messages(session_id, participant_id, since)
        if isinstance(msgs, list):
            total = len(msgs)
            return {"messages": msgs[offset:offset + limit], "total": total, "limit": limit, "offset": offset}
        return {"messages": msgs}
    except Exception as e:
        logger.error(f"[Collaboration] Messages error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/collaboration/status")
async def get_collaboration_session_status(session_id: str = Query(...)):
    """Get collaboration session status."""
    if not COLLABORATION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Collaboration mode not available", status_code=503)

    try:
        s = get_collaboration_status(session_id)
        return s or {"error": "Session not found"}
    except Exception as e:
        logger.error(f"[Collaboration] Status error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/collaboration/end")
async def end_collaboration_session(
    session_id: str = Query(...),
    participant_id: str = Query(...)
):
    """End collaboration session."""
    if not COLLABORATION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Collaboration mode not available", status_code=503)

    try:
        return end_collaboration(session_id, participant_id)
    except Exception as e:
        logger.error(f"[Collaboration] End error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


# --- Meeting Templates Endpoints ---

@router.get("/meeting-templates")
async def list_meeting_templates(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    """Get all meeting templates with pagination."""
    if not MEETING_TEMPLATES_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Meeting templates not available")

    try:
        templates = get_all_templates()
        total = len(templates)
        return {
            "templates": templates[offset:offset + limit],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"[MeetingTemplates] List error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/meeting-templates/categories")
async def list_template_categories():
    """Get all template categories."""
    if not MEETING_TEMPLATES_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Meeting templates not available", status_code=503)

    try:
        categories = get_categories()
        return {"categories": categories}
    except Exception as e:
        logger.error(f"[MeetingTemplates] Categories error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/meeting-templates")
async def create_meeting_template(body: dict, user: User = Depends(require_authentication)):
    """Create a custom meeting template."""
    if not MEETING_TEMPLATES_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Meeting templates not available", status_code=503)

    try:
        template = create_template(body)
        return template
    except Exception as e:
        logger.error(f"[MeetingTemplates] Create error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/meeting-templates/{template_id}")
async def get_meeting_template(template_id: str):
    """Get a specific meeting template."""
    if not MEETING_TEMPLATES_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Meeting templates not available", status_code=503)

    try:
        template = get_template(template_id)
        if template:
            return template
        return error_response(ErrorCode.NOT_FOUND, "Template not found", status_code=404)
    except Exception as e:
        logger.error(f"[MeetingTemplates] Get error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.put("/meeting-templates/{template_id}")
async def update_meeting_template(template_id: str, body: dict):
    """Update a custom meeting template."""
    if not MEETING_TEMPLATES_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Meeting templates not available", status_code=503)

    try:
        template = update_template(template_id, body)
        if template:
            return template
        return error_response(ErrorCode.NOT_FOUND, "Template not found or cannot update default templates", status_code=404)
    except Exception as e:
        logger.error(f"[MeetingTemplates] Update error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.delete("/meeting-templates/{template_id}")
async def delete_meeting_template(template_id: str):
    """Delete a custom meeting template."""
    if not MEETING_TEMPLATES_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Meeting templates not available", status_code=503)

    try:
        success = delete_template(template_id)
        if success:
            return {"success": True}
        return error_response(ErrorCode.NOT_FOUND, "Template not found or cannot delete default templates", status_code=404)
    except Exception as e:
        logger.error(f"[MeetingTemplates] Delete error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/meeting-templates/search")
async def search_meeting_templates(query: str = Query(...)):
    """Search meeting templates."""
    if not MEETING_TEMPLATES_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Meeting templates not available", status_code=503)

    try:
        results = search_templates(query)
        return {"templates": results}
    except Exception as e:
        logger.error(f"[MeetingTemplates] Search error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.post("/meeting-templates/{template_id}/generate")
async def generate_meeting_notes(template_id: str, body: dict):
    """Generate meeting notes from template."""
    if not MEETING_TEMPLATES_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Meeting templates not available", status_code=503)

    try:
        notes = generate_notes(template_id, body)
        return {"notes": notes}
    except Exception as e:
        logger.error(f"[MeetingTemplates] Generate error: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)