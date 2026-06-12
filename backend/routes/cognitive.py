"""Route module for cognitive graph, entity extraction, and predictive interview APIs.

Uses InMemoryCognitiveGraph as the default backend (zero-config).
Falls back to Neo4j when available and configured.
"""
import logging
import re
import sys
import subprocess  # nosec B404
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Query

from security import ErrorCode, error_response

logger = logging.getLogger("routes.cognitive")

router = APIRouter()

# --- Backend Selection ---
# Always available: in-memory cognitive graph
from modules.ai.cognitive_graph_memory import InMemoryCognitiveGraph, memory_graph

_graph = memory_graph  # singleton

# Seed sample data if graph is empty (first launch)
if _graph.get_stats()["total_nodes"] == 0:
    _graph.add_interview('default', 'Google', 'SWE', [
        {'text': 'Reverse a linked list', 'topic': 'data structures', 'category': 'coding'},
        {'text': 'Design a URL shortener', 'topic': 'system design', 'category': 'system_design'},
        {'text': 'Tell me about a time you led a team', 'topic': 'leadership', 'category': 'behavioral'},
    ], [
        {'text': 'Iterative approach with three pointers', 'quality': 'good', 'confidence': 0.85},
        {'text': 'Used hashing and base62 encoding', 'quality': 'good', 'confidence': 0.8},
        {'text': 'STAR format story about project X', 'quality': 'great', 'confidence': 0.9},
    ])
    _graph.add_interview('default', 'Meta', 'Frontend Engineer', [
        {'text': 'Implement useState from scratch', 'topic': 'react', 'category': 'coding'},
        {'text': 'Design Facebook news feed', 'topic': 'system design', 'category': 'system_design'},
    ], [
        {'text': 'Used closure and array for state queue', 'quality': 'good', 'confidence': 0.75},
        {'text': 'Discussed ranking, caching, fan-out', 'quality': 'good', 'confidence': 0.8},
    ])
    _graph.add_interview('default', 'Amazon', 'SDE II', [
        {'text': 'Find k closest points to origin', 'topic': 'algorithms', 'category': 'coding'},
        {'text': 'Design Amazon cart service', 'topic': 'system design', 'category': 'system_design'},
        {'text': 'Customer obsession story', 'topic': 'leadership', 'category': 'behavioral'},
    ], [
        {'text': 'Used max heap approach', 'quality': 'good', 'confidence': 0.8},
        {'text': 'Discussed consistency and partition tolerance', 'quality': 'good', 'confidence': 0.85},
        {'text': 'STAR story about resolving customer issue', 'quality': 'great', 'confidence': 0.9},
    ])
    _graph.add_skill('default', 'Python', 'expert')
    _graph.add_skill('default', 'React', 'advanced')
    _graph.add_skill('default', 'System Design', 'intermediate')
    _graph.add_skill('default', 'Algorithms', 'advanced')
    _graph.add_skill('default', 'SQL', 'intermediate')
    _graph.add_skill('default', 'Docker', 'intermediate')
    _graph.add_skill('default', 'JavaScript', 'expert')
    logger.info("[CognitiveGraph] Seeded sample data (3 interviews, 7 skills)")

# Optional: Neo4j-backed graph (overrides in-memory if available)
try:
    from cognitive_graph import (
        cognitive_graph as neo4j_graph,
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
    # Check if Neo4j is actually connected
    try:
        from cognitive_graph import get_driver
        _driver = get_driver()
        if _driver:
            with _driver.session() as session:
                session.run("RETURN 1")
            _graph = neo4j_graph
            NEO4J_CONNECTED = True
            logger.info("[CognitiveGraph] Using Neo4j backend")
        else:
            NEO4J_CONNECTED = False
            logger.info("[CognitiveGraph] Neo4j not connected, using in-memory backend")
    except Exception:
        NEO4J_CONNECTED = False
        logger.info("[CognitiveGraph] Neo4j connection failed, using in-memory backend")
    COGNITIVE_GRAPH_AVAILABLE = True
except ImportError:
    COGNITIVE_GRAPH_AVAILABLE = False
    NEO4J_CONNECTED = False
    logger.info("[CognitiveGraph] Neo4j module not installed, using in-memory backend")

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


# --- Helper: extract search keywords from text ---
def _keyword_search(graph: InMemoryCognitiveGraph, query: str, limit: int = 20) -> List[Dict]:
    """Search nodes by keyword match across all properties."""
    results = []
    query_lower = query.lower()
    words = set(query_lower.split())

    for node in graph._nodes.values():
        score = 0
        text_fields = []

        # Collect all searchable text from node properties
        for key, val in node.properties.items():
            if isinstance(val, str) and val:
                text_fields.append(val.lower())

        # Also search label
        text_fields.append(node.label.lower())

        all_text = " ".join(text_fields)
        for word in words:
            if word in all_text:
                score += 1

        if score > 0:
            results.append({
                "id": node.id,
                "label": node.label,
                "properties": node.properties,
                "relevance": score / len(words) if words else 0,
                "created_at": node.created_at,
            })

    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results[:limit]


def _advanced_keyword_search(graph: InMemoryCognitiveGraph, query: Optional[str] = None,
                              company: Optional[str] = None, topic: Optional[str] = None,
                              category: Optional[str] = None, difficulty: Optional[str] = None,
                              limit: int = 50) -> List[Dict]:
    """Advanced search with multiple filters on in-memory graph."""
    results = []
    query_lower = (query or "").lower()
    words = set(query_lower.split()) if query_lower else set()

    for node in graph._nodes.values():
        # Filter by label type
        if category and node.label.lower() != category.lower():
            # Check if category matches any property
            cat_match = any(
                v.lower() == category.lower()
                for v in node.properties.values() if isinstance(v, str)
            )
            if not cat_match:
                continue

        if company:
            company_match = (
                node.properties.get("company", "").lower() == company.lower() or
                node.properties.get("name", "").lower() == company.lower()
            )
            if not company_match:
                continue

        if topic:
            topic_match = (
                node.properties.get("topic", "").lower() == topic.lower() or
                node.properties.get("name", "").lower() == topic.lower()
            )
            if not topic_match:
                continue

        if difficulty:
            diff_match = (
                node.properties.get("difficulty", "").lower() == difficulty.lower() or
                node.properties.get("category", "").lower() == difficulty.lower()
            )
            if not diff_match:
                continue

        # Score by query keywords
        score = 0
        if words:
            all_text = " ".join(
                v.lower() for v in node.properties.values() if isinstance(v, str)
            ) + " " + node.label.lower()
            for word in words:
                if word in all_text:
                    score += 1

        if not words or score > 0:
            results.append({
                "id": node.id,
                "label": node.label,
                "properties": node.properties,
                "relevance": score / len(words) if words else 1.0,
                "created_at": node.created_at,
            })

    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results[:limit]


# --- Cognitive Graph Endpoints ---

@router.get("/cognitive-graph/status")
async def cognitive_graph_status():
    """Check cognitive graph availability and connection status."""
    if NEO4J_CONNECTED:
        return {"available": True, "connected": True, "backend": "neo4j"}

    # In-memory graph is always available
    stats = _graph.get_stats()
    return {
        "available": True,
        "connected": True,
        "backend": "in_memory",
        "nodes": stats["total_nodes"],
        "edges": stats["total_edges"],
    }


@router.post("/cognitive-graph/initialize")
async def cognitive_graph_initialize():
    """Initialize the cognitive graph schema."""
    if NEO4J_CONNECTED and COGNITIVE_GRAPH_AVAILABLE:
        success = initialize_graph()
        return {"initialized": success, "backend": "neo4j"}

    # In-memory graph needs no initialization
    return {"initialized": True, "backend": "in_memory"}


@router.get("/cognitive-graph/search")
async def cognitive_graph_search(q: str = Query(...), limit: int = Query(10)):
    """Search across interview history."""
    if NEO4J_CONNECTED and COGNITIVE_GRAPH_AVAILABLE:
        results = query_graph(q)
        return {"query": q, "results": results, "count": len(results)}

    # In-memory keyword search
    results = _keyword_search(_graph, q, limit)
    return {"query": q, "results": results, "count": len(results)}


@router.get("/cognitive-graph/history/{user_id}")
async def cognitive_graph_history(user_id: str, limit: int = Query(100, ge=1, le=500),
                                   offset: int = Query(0, ge=0)):
    """Get user's interview history from graph."""
    if NEO4J_CONNECTED and COGNITIVE_GRAPH_AVAILABLE:
        history = _graph.get_interview_history(user_id, limit + offset)
        total = len(history) if history else 0
        return {"user_id": user_id, "interviews": history[offset:offset + limit],
                "total": total, "limit": limit, "offset": offset}

    # In-memory: get user's interviews
    interviews = _graph.get_user_interviews(user_id)
    total = len(interviews)
    return {
        "user_id": user_id,
        "interviews": interviews[offset:offset + limit],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/cognitive-graph/company/{company_name}")
async def cognitive_graph_company_insights(company_name: str):
    """Get insights about a company."""
    if NEO4J_CONNECTED and COGNITIVE_GRAPH_AVAILABLE:
        insights = _graph.get_company_insights(company_name)
        return {"company": company_name, "insights": insights}

    # In-memory: find company node and its neighbors
    company_node = _graph.find_node("Company", "name", company_name)
    if not company_node:
        return {"company": company_name, "insights": {
            "total_questions": 0, "avg_confidence": 0,
            "categories": [], "common_topics": [],
        }}

    neighbors = _graph.get_neighbors(company_node.id)
    questions = []
    topics = []
    for neighbor, edge in neighbors:
        if neighbor.label == "Interview":
            # Get questions from this interview
            interview_neighbors = _graph.get_neighbors(neighbor.id, "CONTAINS")
            for q_node, _ in interview_neighbors:
                if q_node.label == "Question":
                    questions.append(q_node.properties)
                    # Get topics for this question
                    q_neighbors = _graph.get_neighbors(q_node.id, "ABOUT")
                    for t_node, _ in q_neighbors:
                        if t_node.label == "Topic":
                            topics.append(t_node.properties.get("name", ""))

    categories = list(set(q.get("category", "") for q in questions if q.get("category")))
    unique_topics = list(set(topics))

    return {"company": company_name, "insights": {
        "total_questions": len(questions),
        "avg_confidence": 0.7,
        "categories": categories,
        "common_topics": unique_topics[:10],
    }}


@router.get("/cognitive-graph/skill/{user_id}/{skill_name}")
async def cognitive_graph_skill_progression(user_id: str, skill_name: str):
    """Track user's progression on a specific skill."""
    skills = _graph.get_user_skills(user_id)
    matched = [s for s in skills if s.get("skill", "").lower() == skill_name.lower()]
    return {"user_id": user_id, "skill": skill_name,
            "progression": matched[0] if matched else {"skill": skill_name, "proficiency": "unknown"}}


@router.post("/cognitive-graph/ingest/{conversation_id}")
async def cognitive_graph_ingest(conversation_id: str, body: dict):
    """Ingest a conversation into the cognitive graph."""
    user_id = body.get("user_id", "default")
    company = body.get("company", "Unknown")
    role = body.get("role", "General")
    questions = body.get("questions", [])
    answers = body.get("answers", [])

    interview_id = _graph.add_interview(user_id, company, role, questions, answers)
    return {"ingested": True, "conversation_id": conversation_id, "interview_id": interview_id}


@router.post("/cognitive-graph/interview")
async def cognitive_graph_add_interview(body: dict):
    """Add an interview to the cognitive graph."""
    user_id = body.get("user_id", "default")
    company = body.get("company", "Unknown")
    role = body.get("role", body.get("title", "General"))
    questions = body.get("questions", [])
    answers = body.get("answers", [])

    interview_id = _graph.add_interview(user_id, company, role, questions, answers)
    return {"added": True, "interview_id": interview_id}


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
    if NEO4J_CONNECTED and COGNITIVE_GRAPH_AVAILABLE:
        results = _graph.advanced_search(
            query=query, company=company, topic=topic,
            category=category, difficulty=difficulty,
            date_from=date_from, date_to=date_to, limit=limit
        )
        return {
            "filters": {"query": query, "company": company, "topic": topic,
                        "category": category, "difficulty": difficulty,
                        "date_from": date_from, "date_to": date_to},
            "results": results, "count": len(results),
        }

    # In-memory advanced search
    results = _advanced_keyword_search(
        _graph, query=query, company=company, topic=topic,
        category=category, difficulty=difficulty, limit=limit
    )
    return {
        "filters": {"query": query, "company": company, "topic": topic,
                    "category": category, "difficulty": difficulty,
                    "date_from": date_from, "date_to": date_to},
        "results": results, "count": len(results),
    }


@router.post("/cognitive-graph/backfill")
async def backfill_historical_conversations():
    """Backfill all historical conversations into cognitive graph."""
    try:
        result = subprocess.run(  # nosec B603
            [sys.executable, "backfill_cognitive_graph.py"],
            capture_output=True, text=True, timeout=300
        )
        return {
            "backfill_triggered": True,
            "return_code": result.returncode,
            "output": result.stdout[-1000:] if result.stdout else "",
            "errors": result.stderr[-500:] if result.stderr else "",
        }
    except Exception:
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/cognitive-graph/stats")
async def get_cognitive_graph_stats():
    """Get statistics about the cognitive graph."""
    stats = _graph.get_stats()

    # Build skills list from the graph
    skills = []
    for node in _graph.get_nodes_by_label("Skill", limit=50):
        skills.append({
            "name": node.properties.get("name", ""),
            "count": 1,
            "level": node.properties.get("proficiency", "intermediate"),
        })

    # Merge duplicate skill names
    skill_map: Dict[str, Dict] = {}
    for s in skills:
        name = s["name"]
        if name in skill_map:
            skill_map[name]["count"] += 1
        else:
            skill_map[name] = s

    return {
        "stats": {
            "interviews": stats.get("nodes_by_label", {}).get("Interview", 0),
            "questions": stats.get("nodes_by_label", {}).get("Question", 0),
            "companies": stats.get("nodes_by_label", {}).get("Company", 0),
            "topics": stats.get("nodes_by_label", {}).get("Topic", 0),
            "skills": stats.get("nodes_by_label", {}).get("Skill", 0),
        },
        "skills": list(skill_map.values()),
        "connected": True,
        "backend": stats.get("backend", "in_memory"),
    }


# --- Entity Extraction Endpoints ---

@router.post("/extract-entities")
async def extract_entities_api(body: dict):
    """Extract entities (companies, topics, skills) from text."""
    text = body.get("text", "")
    if not text:
        return error_response(ErrorCode.MISSING_PARAMETER, "No text provided", status_code=422)

    if ENTITY_EXTRACTION_AVAILABLE:
        entities = extract_entities(text)
        return {"text": text[:100] + "..." if len(text) > 100 else text, **entities}

    # Fallback: regex-based entity extraction
    companies_known = {
        "google", "meta", "facebook", "amazon", "apple", "microsoft", "netflix",
        "uber", "lyft", "airbnb", "stripe", "spotify", "twitter", "x corp",
        "linkedin", "salesforce", "adobe", "nvidia", "openai", "tesla",
        "bytedance", "databricks", "snowflake", "palantir", "coinbase",
    }

    skills_known = {
        "python", "javascript", "typescript", "java", "go", "golang", "rust",
        "c++", "c#", "ruby", "php", "swift", "kotlin", "scala",
        "react", "vue", "angular", "nextjs", "node.js", "django", "flask",
        "fastapi", "spring", "docker", "kubernetes", "aws", "gcp", "azure",
        "sql", "postgresql", "mongodb", "redis", "graphql", "rest", "grpc",
        "machine learning", "deep learning", "nlp", "computer vision",
        "tensorflow", "pytorch", "pandas", "numpy", "git", "ci/cd",
        "system design", "microservices", "distributed systems",
        "algorithms", "data structures", "dynamic programming",
        "bfs", "dfs", "binary search", "sorting", "hash table",
    }

    topics_known = {
        "system design", "behavioral", "technical", "coding", "architecture",
        "scalability", "leadership", "teamwork", "communication",
        "problem solving", "data structures", "algorithms",
        "object oriented", "functional programming", "concurrency",
        "database", "caching", "load balancing", "api design",
    }

    text_lower = text.lower()

    found_companies = [c.title() for c in companies_known if c in text_lower]
    found_skills = [s.title() for s in skills_known if s in text_lower]
    found_topics = [t.title() for t in topics_known if t in text_lower]

    # Also extract capitalized words as potential companies
    caps = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    for cap in caps:
        if cap.lower() not in skills_known and cap.lower() not in topics_known:
            if cap not in found_companies:
                found_companies.append(cap)

    return {
        "text": text[:100] + "..." if len(text) > 100 else text,
        "companies": found_companies[:20],
        "skills": found_skills[:20],
        "topics": found_topics[:15],
    }


@router.post("/process-transcript")
async def process_transcript_api(body: dict):
    """Process a transcript into Q&A pairs with extracted entities."""
    transcript = body.get("transcript", "")
    if not transcript:
        return error_response(ErrorCode.MISSING_PARAMETER, "No transcript provided", status_code=422)

    if ENTITY_EXTRACTION_AVAILABLE:
        qa_pairs = process_transcript(transcript)
        return {"qa_pairs": qa_pairs, "count": len(qa_pairs), "transcript_length": len(transcript)}

    # Fallback: split by sentences
    sentences = re.split(r'[.!?]+', transcript)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    qa_pairs = [{"question": s, "answer": ""} for s in sentences[:20]]
    return {"qa_pairs": qa_pairs, "count": len(qa_pairs), "transcript_length": len(transcript)}


@router.get("/extract/categorize")
async def categorize_question_api(q: str = Query(...)):
    """Categorize a question (technical, behavioral, system_design, knowledge)."""
    if ENTITY_EXTRACTION_AVAILABLE:
        category, confidence = entity_extractor.categorize_question(q)
        difficulty, diff_conf = entity_extractor.estimate_difficulty(q)
        return {
            "question": q,
            "category": {"label": category, "confidence": confidence},
            "difficulty": {"label": difficulty, "confidence": diff_conf} if difficulty else None,
        }

    # Fallback: keyword-based categorization
    q_lower = q.lower()
    if any(w in q_lower for w in ["system design", "architecture", "scalability", "distributed"]):
        cat, conf = "system_design", 0.8
    elif any(w in q_lower for w in ["tell me about", "how did you", "describe a time", "behavioral"]):
        cat, conf = "behavioral", 0.75
    elif any(w in q_lower for w in ["code", "algorithm", "implement", "function", "data structure"]):
        cat, conf = "technical", 0.8
    else:
        cat, conf = "knowledge", 0.5

    diff = "medium"
    if any(w in q_lower for w in ["hard", "complex", "advanced", "optimize"]):
        diff = "hard"
    elif any(w in q_lower for w in ["simple", "basic", "easy", "define"]):
        diff = "easy"

    return {
        "question": q,
        "category": {"label": cat, "confidence": conf},
        "difficulty": {"label": diff, "confidence": 0.6},
    }


# --- Predictive Interview Endpoints ---

@router.get("/predict/questions")
async def predict_questions(
    company: str = Query(...),
    role: Optional[str] = Query(None),
    limit: int = Query(10)
):
    """Get predicted interview questions for a company/role."""
    if PREDICTIVE_AVAILABLE:
        return get_predictions(company, role, limit)

    # Fallback: check cognitive graph for company data
    company_node = _graph.find_node("Company", "name", company)
    if not company_node:
        return {"company": company, "questions": [], "total": 0}

    neighbors = _graph.get_neighbors(company_node.id)
    questions = []
    for neighbor, edge in neighbors:
        if neighbor.label == "Interview":
            q_neighbors = _graph.get_neighbors(neighbor.id, "CONTAINS")
            for q_node, _ in q_neighbors:
                if q_node.label == "Question":
                    questions.append(q_node.properties)
                    if len(questions) >= limit:
                        break
        if len(questions) >= limit:
            break

    return {"company": company, "questions": questions[:limit], "total": len(questions)}


@router.get("/predict/checklist")
async def get_preparation_checklist(
    company: str = Query(...),
    role: Optional[str] = Query(None)
):
    """Get preparation checklist for an interview."""
    if PREDICTIVE_AVAILABLE:
        return get_checklist(company, role)

    return {
        "company": company,
        "checklist": [
            {"category": "Research", "items": ["Review company mission and values", "Recent news and product launches"]},
            {"category": "Technical", "items": ["Practice coding problems", "Review system design concepts"]},
            {"category": "Behavioral", "items": ["Prepare STAR stories", "Review leadership principles"]},
        ],
    }


@router.get("/predict/companies")
async def get_supported_companies():
    """Get list of companies with prediction data."""
    if PREDICTIVE_AVAILABLE:
        companies = list(predictive_interview.question_db.keys())
        return {"companies": companies, "total": len(companies)}

    # From cognitive graph
    companies = [n.properties.get("name", "") for n in _graph.get_nodes_by_label("Company", 100)]
    companies = [c for c in companies if c]
    return {"companies": companies, "total": len(companies)}