"""Route module for cognitive graph, entity extraction, and predictive interview APIs."""
import logging
import subprocess
import sys
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from security import ErrorCode, error_response

logger = logging.getLogger("routes.cognitive")

# Cognitive graph
try:
    from cognitive_graph import (
        cognitive_graph,
        initialize_graph,
        ingest_conversation,
        query_graph,
        InterviewNode,
        QuestionNode,
        AnswerNode,
        CompanyNode,
        TopicNode,
        SkillNode
    )
    COGNITIVE_GRAPH_AVAILABLE = True
except ImportError:
    COGNITIVE_GRAPH_AVAILABLE = False

# Entity extraction
try:
    from entity_extraction import extract_entities, process_transcript, entity_extractor
    ENTITY_EXTRACTION_AVAILABLE = True
except ImportError:
    ENTITY_EXTRACTION_AVAILABLE = False

# Predictive interview
try:
    from predictive_interview import (
        predictive_interview,
        get_predictions,
        get_checklist
    )
    PREDICTIVE_AVAILABLE = True
except ImportError:
    PREDICTIVE_AVAILABLE = False
    logger.warning("[Predictive] Module not available")

router = APIRouter()


# --- Cognitive Graph Endpoints ---

@router.get("/cognitive-graph/status")
async def cognitive_graph_status():
    """Check if Neo4j cognitive graph is available"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return {"available": False, "error": "Cognitive graph module not installed"}

    try:
        from cognitive_graph import get_driver
        driver = get_driver()
        if not driver:
            return {"available": True, "connected": False, "error": "Neo4j not connected"}
        try:
            with driver.session() as session:
                session.run("RETURN 1")
            return {"available": True, "connected": True}
        except Exception:
            return {"available": True, "connected": False, "error": "Neo4j connection failed"}
    except Exception as e:
        return {"available": True, "connected": False, "error": str(e)}


@router.post("/cognitive-graph/initialize")
async def cognitive_graph_initialize():
    """Initialize the cognitive graph schema"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    success = initialize_graph()
    return {"initialized": success}


@router.get("/cognitive-graph/search")
async def cognitive_graph_search(q: str = Query(...), limit: int = Query(10)):
    """Semantic search across interview history"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    results = query_graph(q)
    return {"query": q, "results": results, "count": len(results)}


@router.get("/cognitive-graph/history/{user_id}")
async def cognitive_graph_history(user_id: str, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    """Get user's interview history from graph (paginated)."""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    history = cognitive_graph.get_interview_history(user_id, limit + offset)
    total = len(history) if history else 0
    paginated = history[offset:offset + limit] if history else []
    return {"user_id": user_id, "interviews": paginated, "total": total, "limit": limit, "offset": offset}


@router.get("/cognitive-graph/company/{company_name}")
async def cognitive_graph_company_insights(company_name: str):
    """Get insights about a company"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    insights = cognitive_graph.get_company_insights(company_name)
    return {"company": company_name, "insights": insights}


@router.get("/cognitive-graph/skill/{user_id}/{skill_name}")
async def cognitive_graph_skill_progression(user_id: str, skill_name: str):
    """Track user's progression on a specific skill"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    progression = cognitive_graph.get_skill_progression(user_id, skill_name)
    return {"user_id": user_id, "skill": skill_name, "progression": progression}


@router.post("/cognitive-graph/ingest/{conversation_id}")
async def cognitive_graph_ingest(conversation_id: str, body: dict):
    """Ingest a conversation into the cognitive graph"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    success = ingest_conversation(conversation_id, body)
    return {"ingested": success, "conversation_id": conversation_id}


@router.post("/cognitive-graph/interview")
async def cognitive_graph_add_interview(body: dict):
    """Add an interview to the cognitive graph"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    interview = InterviewNode(
        id=body.get("id", ""),
        title=body.get("title", "Untitled"),
        timestamp=datetime.fromisoformat(body.get("timestamp", datetime.now().isoformat())),
        duration_ms=body.get("duration_ms", 0),
        user_id=body.get("user_id", "default")
    )

    success = cognitive_graph.add_interview(interview)
    return {"added": success, "interview_id": interview.id}


@router.get("/cognitive-graph/search/advanced")
async def cognitive_graph_advanced_search(
    query: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(50)
):
    """Advanced search with multiple filters."""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    results = cognitive_graph.advanced_search(
        query=query,
        company=company,
        topic=topic,
        category=category,
        difficulty=difficulty,
        date_from=date_from,
        date_to=date_to,
        limit=limit
    )

    return {
        "filters": {
            "query": query,
            "company": company,
            "topic": topic,
            "category": category,
            "difficulty": difficulty,
            "date_from": date_from,
            "date_to": date_to
        },
        "results": results,
        "count": len(results)
    }


@router.post("/cognitive-graph/backfill")
async def backfill_historical_conversations():
    """Backfill all historical conversations into cognitive graph."""
    try:
        result = subprocess.run(
            [sys.executable, "backfill_cognitive_graph.py"],
            capture_output=True,
            text=True,
            timeout=300
        )

        return {
            "backfill_triggered": True,
            "return_code": result.returncode,
            "output": result.stdout[-1000:] if result.stdout else "",
            "errors": result.stderr[-500:] if result.stderr else ""
        }
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/cognitive-graph/stats")
async def get_cognitive_graph_stats():
    """Get statistics about the cognitive graph"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Cognitive graph not available", status_code=503)

    try:
        stats = {}

        if cognitive_graph.driver:
            with cognitive_graph.driver.session() as session:
                result = session.run("MATCH (i:Interview) RETURN count(i) as count")
                stats['interviews'] = result.single()['count']

                result = session.run("MATCH (q:Question) RETURN count(q) as count")
                stats['questions'] = result.single()['count']

                result = session.run("MATCH (c:Company) RETURN count(c) as count")
                stats['companies'] = result.single()['count']

                result = session.run("MATCH (t:Topic) RETURN count(t) as count")
                stats['topics'] = result.single()['count']

                result = session.run("MATCH (s:Skill) RETURN count(s) as count")
                stats['skills'] = result.single()['count']

        return {"stats": stats, "connected": bool(cognitive_graph.driver)}
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


# --- Entity Extraction Endpoints ---

@router.post("/extract-entities")
async def extract_entities_api(body: dict):
    """Extract entities (companies, topics, skills) from text"""
    if not ENTITY_EXTRACTION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Entity extraction not available", status_code=503)

    text = body.get("text", "")
    if not text:
        return error_response(ErrorCode.MISSING_PARAMETER, "No text provided", status_code=422)

    entities = extract_entities(text)
    return {"text": text[:100] + "..." if len(text) > 100 else text, "entities": entities}


@router.post("/process-transcript")
async def process_transcript_api(body: dict):
    """Process a transcript into Q&A pairs with extracted entities"""
    if not ENTITY_EXTRACTION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Entity extraction not available", status_code=503)

    transcript = body.get("transcript", "")
    if not transcript:
        return error_response(ErrorCode.MISSING_PARAMETER, "No transcript provided", status_code=422)

    qa_pairs = process_transcript(transcript)
    return {
        "qa_pairs": qa_pairs,
        "count": len(qa_pairs),
        "transcript_length": len(transcript)
    }


@router.get("/extract/categorize")
async def categorize_question_api(q: str = Query(...)):
    """Categorize a question (technical, behavioral, system_design, knowledge)"""
    if not ENTITY_EXTRACTION_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Entity extraction not available", status_code=503)

    category, confidence = entity_extractor.categorize_question(q)
    difficulty, diff_conf = entity_extractor.estimate_difficulty(q)

    return {
        "question": q,
        "category": {"label": category, "confidence": confidence},
        "difficulty": {"label": difficulty, "confidence": diff_conf} if difficulty else None
    }


# --- Predictive Interview Endpoints ---

@router.get("/predict/questions")
async def predict_questions(
    company: str = Query(...),
    role: Optional[str] = Query(None),
    limit: int = Query(10)
):
    """Get predicted interview questions for a company/role"""
    if not PREDICTIVE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Predictive interview module not available", status_code=503)

    predictions = get_predictions(company, role, limit)
    return predictions


@router.get("/predict/checklist")
async def get_preparation_checklist(
    company: str = Query(...),
    role: Optional[str] = Query(None)
):
    """Get preparation checklist for an interview"""
    if not PREDICTIVE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Predictive interview module not available", status_code=503)

    checklist = get_checklist(company, role)
    return checklist


@router.get("/predict/companies")
async def get_supported_companies():
    """Get list of companies with prediction data"""
    if not PREDICTIVE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Predictive interview module not available", status_code=503)

    companies = list(predictive_interview.question_db.keys())
    return {
        "companies": companies,
        "total": len(companies)
    }