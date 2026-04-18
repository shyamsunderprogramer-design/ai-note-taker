"""
cognitive_graph.py - Personal Cognitive Graph for AI Note Taker

Neo4j-based knowledge graph that stores user's interview history semantically.
Nodes: Interview, Question, Answer, Company, Role, Topic, Skill, User
Relationships: CONTAINS, ASKED_BY, ANSWERED_WITH, RELATED_TO, FOR_ROLE
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
import uuid

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

            # T4: Neo4j security — always use auth, require strong password
            uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
            user = os.getenv("NEO4J_USER", "neo4j")
            password = os.getenv("NEO4J_PASSWORD", "")

            if not password:
                logger.error("[CognitiveGraph] NEO4J_PASSWORD environment variable is required. "
                             "Set a strong password before connecting. "
                             "Example: NEO4J_PASSWORD=your_secure_password")
                return None

            # Warn if using default/weak password
            if password in ("password", "neo4j", "admin", "123456"):
                logger.warning("[CognitiveGraph] WARNING: Neo4j password is weak/default. "
                               "Please set a strong password via NEO4J_PASSWORD env var.")

            # Always use authentication (T4: removed auth-disabled mode)
            _driver = GraphDatabase.driver(uri, auth=(user, password))

            # Verify connection works
            with _driver.session() as session:
                session.run("RETURN 1")

            logger.info(f"[CognitiveGraph] Connected to Neo4j at {uri} (auth enabled)")
        except ImportError:
            logger.error("[CognitiveGraph] neo4j Python package not installed. Run: pip install neo4j")
            return None
        except Exception as e:
            logger.error("[CognitiveGraph] Failed to connect to Neo4j: %s", str(e))
            logger.info("[CognitiveGraph] Make sure Neo4j is running and NEO4J_PASSWORD is set correctly.")
            _driver = None
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
        self._semantic = None  # Lazy-initialized SemanticSearchMixin

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
                        logger.warning("[CognitiveGraph] Constraint creation skipped: %s", str(e))

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
                        logger.warning("[CognitiveGraph] Index creation skipped: %s", str(e))

            self._initialized = True
            logger.info("[CognitiveGraph] Schema initialized successfully")
            return True

        except Exception as e:
            logger.error("[CognitiveGraph] Schema initialization failed: %s", str(e))
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
            logger.error("[CognitiveGraph] Failed to add interview: %s", str(e))
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
            logger.error("[CognitiveGraph] Failed to add Q&A: %s", str(e))
            return False

        # Index new nodes for semantic search
        try:
            if self._semantic is not None:
                self._semantic._index_node("Question", question.id, question.text)
                self._semantic._index_node("Answer", answer.id, answer.text)
                if company:
                    self._semantic._index_node("Company", company.id, company.name)
        except Exception as e:
            logger.debug("[CognitiveGraph] Failed to index node for semantic search: %s", str(e))

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
            logger.error("[CognitiveGraph] Failed to add topics: %s", str(e))
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
            logger.error("[CognitiveGraph] Failed to add skills: %s", str(e))
            return False

    def semantic_search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for related questions/answers by concept with fuzzy matching.

        Uses embedding-based semantic search when available, falls back to
        Cypher CONTAINS keyword search otherwise.
        """
        # Try semantic (embedding) search first
        if self._try_init_semantic():
            results = self._semantic.semantic_search(query, limit, driver=self.driver)
            if results:
                return results

        # Fallback to keyword-based Cypher search
        return self._legacy_keyword_search(query, limit)

    def _try_init_semantic(self):
        """Lazily initialize the SemanticSearchMixin."""
        if self._semantic is not None:
            return True

        try:
            from modules.ai.semantic_search import SemanticSearchMixin
            from modules.ai.embedding_service import EMBEDDING_AVAILABLE
            if EMBEDDING_AVAILABLE:
                self._semantic = SemanticSearchMixin(neo4j_driver=self.driver)
                return True
        except Exception as e:
            logger.debug("[CognitiveGraph] Semantic search unavailable: %s", str(e))

        return False

    def _legacy_keyword_search(self, query: str, limit: int = 10) -> List[Dict]:
        """Original Cypher CONTAINS-based keyword search (fallback)."""
        if not self.driver:
            return []

        # Enhanced search with multiple strategies
        # Strategy 1: Exact match on text content
        # Strategy 2: Match on related topics
        # Strategy 3: Match on skills demonstrated
        # Strategy 4: Match on company name

        cypher = """
        // Search across multiple fields with scoring
        CALL {
            // Search in question text
            MATCH (q:Question)-[:ANSWERED_WITH]->(a:Answer)
            WHERE q.text CONTAINS $keyword
            WITH q, a, 10 as score
            RETURN q, a, score
            UNION
            // Search in answer text
            MATCH (q:Question)-[:ANSWERED_WITH]->(a:Answer)
            WHERE a.text CONTAINS $keyword
            WITH q, a, 8 as score
            RETURN q, a, score
            UNION
            // Search in transcript
            MATCH (q:Question)-[:ANSWERED_WITH]->(a:Answer)
            WHERE a.transcript CONTAINS $keyword
            WITH q, a, 6 as score
            RETURN q, a, score
            UNION
            // Search by topic
            MATCH (t:Topic)
            WHERE t.name CONTAINS $keyword
            MATCH (t)<-[:RELATED_TO]-(q:Question)-[:ANSWERED_WITH]->(a:Answer)
            WITH q, a, 9 as score
            RETURN q, a, score
            UNION
            // Search by company
            MATCH (c:Company)
            WHERE c.name CONTAINS $keyword
            MATCH (c)<-[:ASKED_BY]-(q:Question)-[:ANSWERED_WITH]->(a:Answer)
            WITH q, a, 7 as score
            RETURN q, a, score
            UNION
            // Search by skill
            MATCH (s:Skill)
            WHERE s.name CONTAINS $keyword
            MATCH (s)<-[:DEMONSTRATES]-(a:Answer)<-[:ANSWERED_WITH]-(q:Question)
            WITH q, a, 8 as score
            RETURN q, a, score
        }
        WITH q, a, max(score) as relevance
        ORDER BY relevance DESC
        LIMIT $limit
        OPTIONAL MATCH (q)-[:RELATED_TO]->(t:Topic)
        OPTIONAL MATCH (q)-[:ASKED_BY]->(c:Company)
        OPTIONAL MATCH (i:Interview)-[:CONTAINS]->(q)
        RETURN DISTINCT q.id as question_id,
               q.text as question,
               a.text as answer,
               q.category as category,
               q.difficulty as difficulty,
               collect(DISTINCT t.name) as topics,
               c.name as company,
               i.timestamp as date,
               relevance
        ORDER BY relevance DESC
        """

        try:
            with self.driver.session() as session:
                result = session.run(cypher, keyword=query.lower(), limit=limit)
                return [dict(record) for record in result]
        except Exception as e:
            logger.error("[CognitiveGraph] Search failed: %s", str(e))
            return []

    def advanced_search(
        self,
        query: str = None,
        company: str = None,
        topic: str = None,
        category: str = None,
        difficulty: str = None,
        date_from: str = None,
        date_to: str = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Advanced search with multiple filters.

        Args:
            query: Text to search for
            company: Filter by company name
            topic: Filter by topic
            category: Filter by question category
            difficulty: Filter by difficulty (easy/medium/hard)
            date_from: Filter from date (ISO format)
            date_to: Filter to date (ISO format)
            limit: Max results
        """
        if not self.driver:
            return []

        # Build dynamic query
        conditions = []
        params = {"limit": limit}

        if query:
            conditions.append("(q.text CONTAINS $query OR a.text CONTAINS $query)")
            params["query"] = query.lower()

        if company:
            conditions.append("c.name = $company")
            params["company"] = company

        if topic:
            conditions.append("t.name = $topic")
            params["topic"] = topic

        if category:
            conditions.append("q.category = $category")
            params["category"] = category

        if difficulty:
            conditions.append("q.difficulty = $difficulty")
            params["difficulty"] = difficulty

        if date_from:
            conditions.append("i.timestamp >= datetime($date_from)")
            params["date_from"] = date_from

        if date_to:
            conditions.append("i.timestamp <= datetime($date_to)")
            params["date_to"] = date_to

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        cypher = f"""
        MATCH (q:Question)-[:ANSWERED_WITH]->(a:Answer)
        OPTIONAL MATCH (q)-[:ASKED_BY]->(c:Company)
        OPTIONAL MATCH (q)-[:RELATED_TO]->(t:Topic)
        OPTIONAL MATCH (i:Interview)-[:CONTAINS]->(q)
        {where_clause}
        RETURN q.id as question_id,
               q.text as question,
               a.text as answer,
               q.category as category,
               q.difficulty as difficulty,
               collect(DISTINCT t.name) as topics,
               c.name as company,
               i.timestamp as date
        ORDER BY i.timestamp DESC
        LIMIT $limit
        """

        try:
            with self.driver.session() as session:
                result = session.run(cypher, **params)
                return [dict(record) for record in result]
        except Exception as e:
            logger.error("[CognitiveGraph] Advanced search failed: %s", str(e))
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
            logger.error("[CognitiveGraph] History query failed: %s", str(e))
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
            logger.error("[CognitiveGraph] Company insights failed: %s", str(e))
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
            logger.error("[CognitiveGraph] Skill progression failed: %s", str(e))
            return []

    def get_user_skills(self, user_id: str) -> List[Dict]:
        """Get all skills for a user with their confidence levels"""
        if not self.driver:
            return []

        cypher = """
        MATCH (i:Interview {user_id: $user_id})-[:CONTAINS]->(q:Question)
              -[:ANSWERED_WITH]->(a:Answer)-[:DEMONSTRATES]->(s:Skill)
        RETURN s.name as name,
               avg(a.confidence) as confidence,
               count(a) as mentions
        ORDER BY confidence ASC
        """

        try:
            with self.driver.session() as session:
                result = session.run(cypher, user_id=user_id)
                return [dict(record) for record in result]
        except Exception as e:
            logger.error("[CognitiveGraph] Get user skills failed: %s", str(e))
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
    """Ingest a conversation into the graph with full Q&A parsing"""
    try:
        from entity_extraction import entity_extractor
        import uuid

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
        qa_pairs = []
        current_question = None

        for msg in messages:
            content = msg.get('content', msg.get('text', ''))
            role = msg.get('role', '').lower()

            # Detect questions (interviewer or ends with ?)
            if role == 'interviewer' or '?' in content:
                # Save previous Q&A pair
                if current_question and qa_pairs:
                    qa_pairs[-1]['answer'] = current_question.get('answer', '')

                # Start new question
                current_question = {
                    'question': content,
                    'answer': ''
                }
                qa_pairs.append(current_question)
            elif current_question:
                # This is an answer
                current_question['answer'] += ' ' + content

        # Process each Q&A pair
        for idx, qa in enumerate(qa_pairs):
            if not qa.get('question'):
                continue

            # Extract entities
            full_text = qa['question'] + ' ' + qa.get('answer', '')
            entities = entity_extractor.extract_all(full_text)

            # Create question node
            q_id = f"{conversation_id}-q{idx}"
            question = QuestionNode(
                id=q_id,
                text=qa['question'],
                category=entities.get('category', {}).get('label', 'general'),
                difficulty=entities.get('difficulty', {}).get('label') if entities.get('difficulty') else None
            )

            # Create answer node
            a_id = f"{conversation_id}-a{idx}"
            answer = AnswerNode(
                id=a_id,
                text=qa.get('answer', ''),
                transcript=qa.get('answer', ''),
                confidence=0.7  # Default confidence
            )

            # Add to graph
            cognitive_graph.add_question_answer(
                conversation_id,
                question,
                answer,
                None  # Company extracted below
            )

            # Add topics
            if entities.get('topics'):
                topics = [
                    TopicNode(id=f"{q_id}-t{tid}", name=t['text'], category='technical')
                    for tid, t in enumerate(entities['topics'])
                ]
                cognitive_graph.add_topics_to_question(q_id, topics)

            # Add skills
            if entities.get('skills'):
                skills = [
                    SkillNode(id=f"{a_id}-s{sid}", name=s['text'])
                    for sid, s in enumerate(entities['skills'])
                ]
                cognitive_graph.add_skills_to_answer(a_id, skills)

            # Add companies
            if entities.get('companies'):
                for comp in entities['companies']:
                    company = CompanyNode(
                        id=f"comp-{comp['text']}",
                        name=comp['text'].capitalize()
                    )
                    # Re-link question to company
                    if cognitive_graph.driver:
                        with cognitive_graph.driver.session() as session:
                            session.run("""
                                MATCH (q:Question {id: $q_id})
                                MERGE (c:Company {id: $c_id, name: $c_name})
                                MERGE (q)-[:ASKED_BY]->(c)
                            """, q_id=q_id, c_id=company.id, c_name=company.name)

        logger.info(f"[CognitiveGraph] Ingested conversation {conversation_id} with {len(qa_pairs)} Q&A pairs")
        return True
    except Exception as e:
        logger.error("[CognitiveGraph] Ingestion failed: %s", str(e))
        import traceback
        logger.error(traceback.format_exc())
        return False

def query_graph(query: str) -> List[Dict]:
    """Query the cognitive graph"""
    return cognitive_graph.semantic_search(query)
