"""
cognitive_graph.py - Personal Cognitive Graph for AI Note Taker

Neo4j-based knowledge graph that stores user's interview history semantically.
Nodes: Interview, Question, Answer, Company, Role, Topic, Skill, User
Relationships: CONTAINS, ASKED_BY, ANSWERED_WITH, RELATED_TO, FOR_ROLE
"""

import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import json

logger = logging.getLogger("cognitive_graph")

# Neo4j driver (lazy import - only connect when needed)
_driver = None

def get_driver():
    """Get or create Neo4j driver"""
    global _driver
    if _driver is None:
        try:
            from neo4j import GraphDatabase
            import os

            # Default connection settings
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            user = os.getenv("NEO4J_USER", "neo4j")
            password = os.getenv("NEO4J_PASSWORD", "password")

            _driver = GraphDatabase.driver(uri, auth=(user, password))
            logger.info(f"[CognitiveGraph] Connected to Neo4j at {uri}")
        except ImportError:
            logger.error("[CognitiveGraph] neo4j Python package not installed. Run: pip install neo4j")
            return None
        except Exception as e:
            logger.error(f"[CognitiveGraph] Failed to connect: {e}")
            return None
    return _driver

@dataclass
class InterviewNode:
    """Represents an interview session"""
    id: str
    title: str
    timestamp: datetime
    duration_ms: int
    user_id: str

@dataclass
class QuestionNode:
    """Represents a question asked in an interview"""
    id: str
    text: str
    category: str  # technical, behavioral, system-design, etc.
    difficulty: Optional[str] = None
    company_id: Optional[str] = None

@dataclass
class AnswerNode:
    """Represents an answer given"""
    id: str
    text: str
    transcript: str  # Full transcript including thinking process
    confidence: float = 0.0

@dataclass
class CompanyNode:
    """Represents a company"""
    id: str
    name: str
    industry: Optional[str] = None
    size: Optional[str] = None

@dataclass
class RoleNode:
    """Represents a job role"""
    id: str
    title: str
    level: Optional[str] = None  # junior, mid, senior, staff, principal
    department: Optional[str] = None

@dataclass
class TopicNode:
    """Represents a technical topic"""
    id: str
    name: str
    category: str  # algorithm, database, system-design, etc.

@dataclass
class SkillNode:
    """Represents a skill mentioned or demonstrated"""
    id: str
    name: str
    proficiency: Optional[str] = None  # beginner, intermediate, expert

class CognitiveGraph:
    """Personal Cognitive Graph for interview history"""

    def __init__(self):
        self.driver = get_driver()
        self._initialized = False

    def initialize_schema(self) -> bool:
        """Create Neo4j schema (constraints and indexes)"""
        if not self.driver:
            logger.error("[CognitiveGraph] Cannot initialize - no Neo4j connection")
            return False

        try:
            with self.driver.session() as session:
                # Create constraints (unique IDs)
                constraints = [
                    "CREATE CONSTRAINT interview_id IF NOT EXISTS FOR (i:Interview) REQUIRE i.id IS UNIQUE",
                    "CREATE CONSTRAINT question_id IF NOT EXISTS FOR (q:Question) REQUIRE q.id IS UNIQUE",
                    "CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE",
                    "CREATE CONSTRAINT role_id IF NOT EXISTS FOR (r:Role) REQUIRE r.id IS UNIQUE",
                    "CREATE CONSTRAINT topic_id IF NOT EXISTS FOR (t:Topic) REQUIRE t.id IS UNIQUE",
                    "CREATE CONSTRAINT skill_id IF NOT EXISTS FOR (s:Skill) REQUIRE s.id IS UNIQUE",
                ]

                for constraint in constraints:
                    try:
                        session.run(constraint)
                    except Exception as e:
                        logger.warning(f"[CognitiveGraph] Constraint creation skipped: {e}")

                # Create indexes for faster queries
                indexes = [
                    "CREATE INDEX interview_timestamp IF NOT EXISTS FOR (i:Interview) ON (i.timestamp)",
                    "CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name)",
                    "CREATE INDEX topic_name IF NOT EXISTS FOR (t:Topic) ON (t.name)",
                    "CREATE INDEX skill_name IF NOT EXISTS FOR (s:Skill) ON (s.name)",
                ]

                for index in indexes:
                    try:
                        session.run(index)
                    except Exception as e:
                        logger.warning(f"[CognitiveGraph] Index creation skipped: {e}")

            self._initialized = True
            logger.info("[CognitiveGraph] Schema initialized successfully")
            return True

        except Exception as e:
            logger.error(f"[CognitiveGraph] Schema initialization failed: {e}")
            return False

    def add_interview(self, interview: InterviewNode) -> bool:
        """Add an interview session to the graph"""
        if not self.driver:
            return False

        query = """
        MERGE (i:Interview {id: $id})
        SET i.title = $title,
            i.timestamp = datetime($timestamp),
            i.duration_ms = $duration_ms,
            i.user_id = $user_id
        RETURN i
        """

        try:
            with self.driver.session() as session:
                session.run(query,
                    id=interview.id,
                    title=interview.title,
                    timestamp=interview.timestamp.isoformat(),
                    duration_ms=interview.duration_ms,
                    user_id=interview.user_id
                )
            return True
        except Exception as e:
            logger.error(f"[CognitiveGraph] Failed to add interview: {e}")
            return False

    def add_question_answer(self, interview_id: str, question: QuestionNode,
                           answer: AnswerNode, company: Optional[CompanyNode] = None) -> bool:
        """Add a Q&A pair to an interview"""
        if not self.driver:
            return False

        try:
            with self.driver.session() as session:
                # Add question
                q_query = """
                MERGE (q:Question {id: $q_id})
                SET q.text = $text,
                    q.category = $category,
                    q.difficulty = $difficulty
                """
                session.run(q_query,
                    q_id=question.id,
                    text=question.text,
                    category=question.category,
                    difficulty=question.difficulty
                )

                # Add answer
                a_query = """
                MERGE (a:Answer {id: $a_id})
                SET a.text = $text,
                    a.transcript = $transcript,
                    a.confidence = $confidence
                """
                session.run(a_query,
                    a_id=answer.id,
                    text=answer.text,
                    transcript=answer.transcript,
                    confidence=answer.confidence
                )

                # Link Q&A
                qa_link = """
                MATCH (q:Question {id: $q_id}), (a:Answer {id: $a_id})
                MERGE (q)-[:ANSWERED_WITH]->(a)
                """
                session.run(qa_link, q_id=question.id, a_id=answer.id)

                # Link to interview
                iq_link = """
                MATCH (i:Interview {id: $i_id}), (q:Question {id: $q_id})
                MERGE (i)-[:CONTAINS]->(q)
                """
                session.run(iq_link, i_id=interview_id, q_id=question.id)

                # Add company if provided
                if company:
                    c_query = """
                    MERGE (c:Company {id: $c_id})
                    SET c.name = $name,
                        c.industry = $industry,
                        c.size = $size
                    """
                    session.run(c_query,
                        c_id=company.id,
                        name=company.name,
                        industry=company.industry,
                        size=company.size
                    )

                    # Link question to company
                    cq_link = """
                    MATCH (q:Question {id: $q_id}), (c:Company {id: $c_id})
                    MERGE (q)-[:ASKED_BY]->(c)
                    """
                    session.run(cq_link, q_id=question.id, c_id=company.id)

            return True
        except Exception as e:
            logger.error(f"[CognitiveGraph] Failed to add Q&A: {e}")
            return False

    def add_topics_to_question(self, question_id: str, topics: List[TopicNode]) -> bool:
        """Link topics to a question"""
        if not self.driver:
            return False

        try:
            with self.driver.session() as session:
                for topic in topics:
                    # Add topic
                    t_query = """
                    MERGE (t:Topic {id: $t_id})
                    SET t.name = $name,
                        t.category = $category
                    """
                    session.run(t_query,
                        t_id=topic.id,
                        name=topic.name,
                        category=topic.category
                    )

                    # Link to question
                    qt_link = """
                    MATCH (q:Question {id: $q_id}), (t:Topic {id: $t_id})
                    MERGE (q)-[:RELATED_TO]->(t)
                    """
                    session.run(qt_link, q_id=question_id, t_id=topic.id)

            return True
        except Exception as e:
            logger.error(f"[CognitiveGraph] Failed to add topics: {e}")
            return False

    def add_skills_to_answer(self, answer_id: str, skills: List[SkillNode]) -> bool:
        """Link skills demonstrated in an answer"""
        if not self.driver:
            return False

        try:
            with self.driver.session() as session:
                for skill in skills:
                    # Add skill
                    s_query = """
                    MERGE (s:Skill {id: $s_id})
                    SET s.name = $name,
                        s.proficiency = $proficiency
                    """
                    session.run(s_query,
                        s_id=skill.id,
                        name=skill.name,
                        proficiency=skill.proficiency
                    )

                    # Link to answer
                    sa_link = """
                    MATCH (a:Answer {id: $a_id}), (s:Skill {id: $s_id})
                    MERGE (a)-[:DEMONSTRATES]->(s)
                    """
                    session.run(sa_link, a_id=answer_id, s_id=skill.id)

            return True
        except Exception as e:
            logger.error(f"[CognitiveGraph] Failed to add skills: {e}")
            return False

    def semantic_search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for related questions/answers by concept"""
        if not self.driver:
            return []

        # Simple keyword-based search (can be enhanced with embeddings)
        cypher = """
        MATCH (q:Question)-[:ANSWERED_WITH]->(a:Answer)
        WHERE q.text CONTAINS $keyword
           OR a.text CONTAINS $keyword
           OR a.transcript CONTAINS $keyword
        OPTIONAL MATCH (q)-[:RELATED_TO]->(t:Topic)
        OPTIONAL MATCH (q)-[:ASKED_BY]->(c:Company)
        RETURN q.id as question_id,
               q.text as question,
               a.text as answer,
               collect(DISTINCT t.name) as topics,
               c.name as company
        LIMIT $limit
        """

        try:
            with self.driver.session() as session:
                result = session.run(cypher, keyword=query, limit=limit)
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"[CognitiveGraph] Search failed: {e}")
            return []

    def get_interview_history(self, user_id: str, limit: int = 100) -> List[Dict]:
        """Get user's interview history"""
        if not self.driver:
            return []

        cypher = """
        MATCH (i:Interview {user_id: $user_id})
        OPTIONAL MATCH (i)-[:CONTAINS]->(q:Question)
        OPTIONAL MATCH (q)-[:ASKED_BY]->(c:Company)
        WITH i, count(q) as question_count, collect(DISTINCT c.name) as companies
        RETURN i.id as id,
               i.title as title,
               i.timestamp as timestamp,
               i.duration_ms as duration_ms,
               question_count,
               companies
        ORDER BY i.timestamp DESC
        LIMIT $limit
        """

        try:
            with self.driver.session() as session:
                result = session.run(cypher, user_id=user_id, limit=limit)
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"[CognitiveGraph] History query failed: {e}")
            return []

    def get_company_insights(self, company_name: str) -> Dict:
        """Get insights about questions asked by a company"""
        if not self.driver:
            return {}

        cypher = """
        MATCH (c:Company {name: $company})<-[:ASKED_BY]-(q:Question)
        OPTIONAL MATCH (q)-[:RELATED_TO]->(t:Topic)
        OPTIONAL MATCH (q)-[:ANSWERED_WITH]->(a:Answer)
        RETURN c.name as company,
               count(DISTINCT q) as total_questions,
               collect(DISTINCT q.category) as categories,
               collect(DISTINCT t.name) as common_topics,
               avg(a.confidence) as avg_confidence
        """

        try:
            with self.driver.session() as session:
                result = session.run(cypher, company=company_name)
                record = result.single()
                return dict(record) if record else {}
        except Exception as e:
            logger.error(f"[CognitiveGraph] Company insights failed: {e}")
            return {}

    def get_skill_progression(self, user_id: str, skill_name: str) -> List[Dict]:
        """Track user's progress on a specific skill over time"""
        if not self.driver:
            return []

        cypher = """
        MATCH (i:Interview {user_id: $user_id})-[:CONTAINS]->(q:Question)
              -[:ANSWERED_WITH]->(a:Answer)-[:DEMONSTRATES]->(s:Skill {name: $skill})
        RETURN i.timestamp as date,
               a.confidence as proficiency,
               q.text as context
        ORDER BY i.timestamp
        """

        try:
            with self.driver.session() as session:
                result = session.run(cypher, user_id=user_id, skill=skill_name)
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"[CognitiveGraph] Skill progression failed: {e}")
            return []

    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("[CognitiveGraph] Connection closed")

# Global instance
cognitive_graph = CognitiveGraph()

# Convenience functions
def initialize_graph() -> bool:
    """Initialize the cognitive graph schema"""
    return cognitive_graph.initialize_schema()

def ingest_conversation(conversation_id: str, conversation_data: Dict) -> bool:
    """Ingest a conversation into the graph"""
    try:
        # Create interview node
        interview = InterviewNode(
            id=conversation_id,
            title=conversation_data.get("title", "Untitled Interview"),
            timestamp=datetime.fromtimestamp(conversation_data.get("updatedAt", datetime.now().timestamp()) / 1000),
            duration_ms=conversation_data.get("duration_ms", 0),
            user_id=conversation_data.get("user_id", "default")
        )
        cognitive_graph.add_interview(interview)

        # Process messages for Q&A pairs
        messages = conversation_data.get("messages", [])
        # Simple extraction - can be enhanced with NLP

        logger.info(f"[CognitiveGraph] Ingested conversation {conversation_id}")
        return True
    except Exception as e:
        logger.error(f"[CognitiveGraph] Ingestion failed: {e}")
        return False

def query_graph(query: str) -> List[Dict]:
    """Query the cognitive graph"""
    return cognitive_graph.semantic_search(query)
