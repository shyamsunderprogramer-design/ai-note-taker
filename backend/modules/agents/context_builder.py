"""
Context Builder — Shared data source queries for all agents.

Centralizes access to cognitive graph, document RAG, entity extraction,
company insights, and skill progression. Every function degrades gracefully:
if a data source is unavailable, it returns empty results instead of crashing.
"""

import logging
from typing import List, Dict

logger = logging.getLogger("agents.context_builder")


async def query_cognitive_graph(query: str, limit: int = 5) -> List[Dict]:
    """Query cognitive graph for similar past Q&A.
    Returns [] if Neo4j is unavailable."""
    try:
        from cognitive_graph import cognitive_graph
        if hasattr(cognitive_graph, 'driver') and cognitive_graph.driver:
            results = cognitive_graph.semantic_search(query, limit=limit)
            if results:
                return [
                    {
                        "question": r.get("question", ""),
                        "answer": r.get("answer", ""),
                        "company": r.get("company", ""),
                        "topics": r.get("topics", []),
                        "confidence": r.get("confidence", 0),
                        "relevance": r.get("relevance", 0),
                    }
                    for r in results
                ]
    except ImportError:
        logger.debug("[ContextBuilder] Cognitive graph module not available")
    except Exception as e:
        logger.warning("[ContextBuilder] Cognitive graph query failed: %s", str(e))
    return []


async def query_document_rag(query: str, top_k: int = 3) -> List[Dict]:
    """Query document RAG for relevant context chunks.
    Returns [] if no documents or store unavailable."""
    try:
        from document_store import get_document_store
        store = get_document_store()
        results = store.retrieve_context(query, top_k=top_k)
        if results:
            return [
                {
                    "text": r.get("text", ""),
                    "doc_name": r.get("doc_name", ""),
                    "similarity": r.get("similarity", 0),
                }
                for r in results
            ]
    except ImportError:
        logger.debug("[ContextBuilder] Document store module not available")
    except Exception as e:
        logger.warning("[ContextBuilder] Document RAG query failed: %s", str(e))
    return []


def extract_entities(text: str) -> Dict:
    """Extract entities from text (companies, topics, skills, roles).
    Returns {} if extractor unavailable."""
    try:
        from entity_extraction import entity_extractor
        result = entity_extractor.extract_all(text)
        if result:
            return {
                "companies": result.get("companies", []),
                "topics": result.get("topics", []),
                "skills": result.get("skills", []),
                "roles": result.get("roles", []),
                "categories": result.get("categories", []),
                "difficulty": result.get("difficulty", "unknown"),
            }
    except ImportError:
        logger.debug("[ContextBuilder] Entity extraction module not available")
    except Exception as e:
        logger.warning("[ContextBuilder] Entity extraction failed: %s", str(e))
    return {}


async def get_company_insights(company: str) -> Dict:
    """Get company-specific insights from cognitive graph.
    Returns {} if graph unavailable or company not found."""
    if not company:
        return {}
    try:
        from cognitive_graph import cognitive_graph
        if hasattr(cognitive_graph, 'driver') and cognitive_graph.driver:
            insights = cognitive_graph.get_company_insights(company)
            if insights:
                return {
                    "total_questions": insights.get("total_questions", 0),
                    "categories": insights.get("categories", {}),
                    "common_topics": insights.get("common_topics", []),
                    "avg_confidence": insights.get("avg_confidence", 0),
                }
    except ImportError:
        logger.debug("[ContextBuilder] Cognitive graph not available for company insights")
    except Exception as e:
        logger.warning("[ContextBuilder] Company insights failed: %s", str(e))
    return {}


async def get_skill_progression(user_id: str, skill: str = None) -> List[Dict]:
    """Get skill progression data from cognitive graph.
    Returns [] if graph unavailable."""
    if not user_id:
        return []
    try:
        from cognitive_graph import cognitive_graph
        if hasattr(cognitive_graph, 'driver') and cognitive_graph.driver:
            if skill:
                return cognitive_graph.get_skill_progression(user_id, skill)
            else:
                skills = cognitive_graph.get_user_skills(user_id)
                if skills:
                    return [
                        {"skill": s.get("name", ""), "confidence": s.get("avg_confidence", 0)}
                        for s in skills[:10]
                    ]
    except ImportError:
        logger.debug("[ContextBuilder] Cognitive graph not available for skill progression")
    except Exception as e:
        logger.warning("[ContextBuilder] Skill progression failed: %s", str(e))
    return []


def format_graph_results(results: List[Dict]) -> str:
    """Format cognitive graph results for prompt injection."""
    if not results:
        return "No similar past Q&A found."
    lines = []
    for i, r in enumerate(results[:5], 1):
        company_str = f" (at {r['company']})" if r.get("company") else ""
        lines.append(
            f"{i}. Q: {r.get('question', 'N/A')}{company_str}\n"
            f"   A: {r.get('answer', 'N/A')}"
        )
    return "\n".join(lines)


def format_rag_results(results: List[Dict]) -> str:
    """Format document RAG results for prompt injection."""
    if not results:
        return "No preparation materials found."
    lines = []
    for i, r in enumerate(results[:3], 1):
        doc = r.get("doc_name", "Unknown doc")
        sim = r.get("similarity", 0)
        lines.append(f"{i}. [From: {doc}, relevance: {sim:.2f}]\n   {r.get('text', '')}")
    return "\n".join(lines)


def format_company_insights(insights: Dict, company: str) -> str:
    """Format company insights for prompt injection."""
    if not insights:
        return f"No specific insights available for {company}."
    lines = [f"Company: {company}"]
    if insights.get("total_questions"):
        lines.append(f"  Total past questions: {insights['total_questions']}")
    if insights.get("categories"):
        cats = insights["categories"]
        top_cats = sorted(cats.items(), key=lambda x: x[1], reverse=True)[:3]
        lines.append(f"  Focus areas: {', '.join(c for c, _ in top_cats)}")
    if insights.get("common_topics"):
        topics = insights["common_topics"][:5]
        lines.append(f"  Common topics: {', '.join(str(t) for t in topics)}")
    if insights.get("avg_confidence"):
        lines.append(f"  Avg candidate confidence: {insights['avg_confidence']:.1%}")
    return "\n".join(lines)