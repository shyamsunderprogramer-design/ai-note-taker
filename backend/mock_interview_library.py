"""
mock_interview_library_expanded.py - Expanded Interview Question Bank (T19)
Pre-curated interview questions organized by role, company, and difficulty
Target: 10,000+ questions from templates and curated database
"""

import random
import uuid
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class InterviewQuestion:
    id: str
    question: str
    category: str  # technical, behavioral, system_design, coding, product_sense, leadership
    difficulty: str  # easy, medium, hard, expert
    role: str
    company: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    expected_answer_points: List[str] = field(default_factory=list)
    hints: List[str] = field(default_factory=list)
    follow_up_questions: List[str] = field(default_factory=list)
    time_estimate_minutes: int = 15
    source: str = "curated"  # curated, generated, community
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ═══════════════════════════════════════════════════════════════════════════════
# QUESTION TEMPLATES - Generate thousands of variations
# ═══════════════════════════════════════════════════════════════════════════════

CODING_TEMPLATES = [
    # Arrays/Strings
    ("Implement a function to {action} an array where {condition}",
     ["array", "{topic}"], "easy", 15),
    ("Given {data_structure}, find the {target} in O({complexity}) time",
     ["algorithm", "{topic}"], "medium", 20),
    ("Design an algorithm to {task} without using {restriction}",
     ["algorithm", "optimization"], "medium", 25),
    ("Solve {problem} using {approach}",
     ["{topic}", "problem_solving"], "hard", 30),

    # Trees/Graphs
    ("Given a binary tree, {operation}",
     ["trees", "binary_tree"], "medium", 20),
    ("Find {property} in a {graph_type} graph",
     ["graphs", "{topic}"], "hard", 30),
    ("Implement {algorithm} for {use_case}",
     ["graphs", "algorithms"], "hard", 35),

    # Dynamic Programming
    ("Solve {problem} using dynamic programming",
     ["dp", "{topic}"], "hard", 35),
    ("Find the optimal way to {task} with {constraint}",
     ["dp", "optimization"], "hard", 40),
]

SYSTEM_DESIGN_TEMPLATES = [
    # Scalable Systems
    ("Design {system_name}",
     ["system_design", "scalability", "{topic}"], "medium", 45),
    ("How would you scale {existing_system} to handle {scale} users?",
     ["system_design", "scalability", "{topic}"], "hard", 45),
    ("Design {system_name} with {constraint}",
     ["system_design", "distributed_systems"], "hard", 50),

    # Databases
    ("Design a {database_type} database schema for {use_case}",
     ["system_design", "databases", "{topic}"], "medium", 30),
    ("How would you optimize {operation} on {data_volume} of data?",
     ["system_design", "performance", "{topic}"], "hard", 35),

    # Microservices
    ("Design a microservices architecture for {system_name}",
     ["system_design", "microservices", "{topic}"], "hard", 45),
    ("How would you handle {problem} in a distributed system?",
     ["system_design", "distributed_systems"], "expert", 50),
]

BEHAVIORAL_TEMPLATES = [
    # Leadership
    ("Tell me about a time you {situation}",
     ["behavioral", "leadership", "{topic}"], "medium", 10),
    ("Describe a situation where you had to {action} despite {challenge}",
     ["behavioral", "leadership", "{topic}"], "medium", 12),
    ("How did you handle {difficult_situation} with your team?",
     ["behavioral", "leadership", "{topic}"], "hard", 15),

    # Conflict Resolution
    ("Tell me about a conflict you had with {person_type}. How did you resolve it?",
     ["behavioral", "conflict_resolution"], "medium", 10),
    ("Describe a time you disagreed with {decision_type}. What did you do?",
     ["behavioral", "conflict_resolution", "{topic}"], "medium", 12),

    # Problem Solving
    ("Tell me about the most challenging {item} you've worked on",
     ["behavioral", "problem_solving", "{topic}"], "medium", 12),
    ("Describe a time you had to {action} with incomplete information",
     ["behavioral", "problem_solving", "{topic}"], "hard", 15),

    # Teamwork
    ("Tell me about a time you helped {person} succeed",
     ["behavioral", "teamwork", "{topic}"], "easy", 8),
    ("Describe a situation where you had to {action} to support your team",
     ["behavioral", "teamwork", "{topic}"], "medium", 10),
]

TECHNICAL_TEMPLATES = [
    # Architecture
    ("Explain {concept} and when to use it",
     ["technical", "architecture", "{topic}"], "easy", 10),
    ("Compare {technology_a} vs {technology_b}. When would you choose each?",
     ["technical", "comparison", "{topic}"], "medium", 12),
    ("What are the trade-offs between {approach_a} and {approach_b}?",
     ["technical", "architecture", "{topic}"], "medium", 15),

    # Specific Technologies
    ("How does {technology} work under the hood?",
     ["technical", "deep_dive", "{topic}"], "hard", 20),
    ("Explain {concept} in detail",
     ["technical", "{topic}"], "medium", 15),
    ("What is {technology} and why is it important?",
     ["technical", "{topic}"], "easy", 8),
]

# Template fillers
FILLERS = {
    "action": [
        "reverse", "sort", "merge", "rotate", "partition",
        "search", "find", "optimize", "compress", "encode",
        "decode", "validate", "parse", "serialize", "deserialize"
    ],
    "condition": [
        "elements are integers", "array contains duplicates", "input is sorted",
        "memory is limited", "time complexity must be O(n)", "space complexity must be O(1)"
    ],
    "data_structure": [
        "an unsorted array", "a sorted array", "a linked list",
        "a binary tree", "a matrix", "a string", "a stream of data"
    ],
    "target": [
        "maximum element", "minimum element", "kth largest element",
        "median", "pair that sums to target", "longest substring",
        "shortest path", "optimal solution"
    ],
    "complexity": ["n", "n log n", "log n", "n^2"],
    "task": [
        "merge two sorted arrays", "implement an LRU cache", "design a hash map",
        "build a rate limiter", "implement consistent hashing",
        "schedule tasks with dependencies"
    ],
    "restriction": [
        "extra space", "recursion", "built-in sort", "extra data structures",
        "linear time", "the modulo operator"
    ],
    "problem": [
        "the knapsack problem", "the traveling salesman problem",
        "finding the longest common subsequence", "matrix chain multiplication",
        "the edit distance problem"
    ],
    "approach": [
        "backtracking", "dynamic programming", "greedy algorithm",
        "divide and conquer", "branch and bound"
    ],
    "operation": [
        "find the lowest common ancestor", "compute the diameter",
        "serialize and deserialize it", "check if it's balanced",
        "find the maximum path sum", "compute the boundary traversal"
    ],
    "property": [
        "shortest path", "minimum spanning tree", "strongly connected components",
        "topological ordering", "bridges and articulation points"
    ],
    "graph_type": ["directed", "undirected", "weighted", "cyclic"],
    "algorithm": [
        "Dijkstra's algorithm", "Bellman-Ford algorithm", "Floyd-Warshall algorithm",
        "Kruskal's algorithm", "Prim's algorithm", "A* search"
    ],
    "use_case": [
        "finding shortest paths", "minimum spanning tree",
        "network flow optimization", "bipartite matching"
    ],
    "system_name": [
        "a URL shortener like bit.ly", "a distributed cache like Redis",
        "a message queue like Kafka", "a search engine like Elasticsearch",
        "a recommendation system", "a rate limiter",
        "a real-time chat system", "a video streaming platform",
        "an online judge system", "a collaborative editing tool",
        "a ride-sharing service", "a payment processing system",
        "a social media feed", "an e-commerce platform",
        "a file storage service like Dropbox"
    ],
    "existing_system": [
        "a web application", "a database", "an API gateway",
        "a message queue", "a cache layer"
    ],
    "scale": ["1M", "10M", "100M", "1B"],
    "constraint": [
        "eventual consistency", "strong consistency requirements",
        "limited budget", "strict latency requirements",
        "regulatory compliance requirements"
    ],
    "database_type": ["SQL", "NoSQL", "graph", "time-series", "key-value"],
    "use_case": [
        "an e-commerce platform", "a social network", "a real-time analytics system",
        "a content management system", "an IoT data platform"
    ],
    "operation": [
        "read queries", "write operations", "aggregations",
        "joins across tables", "full-text search"
    ],
    "data_volume": ["1TB", "10TB", "100TB", "1PB"],
    "situation": [
        "had to lead without authority", "had to deliver on a tight deadline",
        "had to make a decision with incomplete data", "mentored someone",
        "influenced a technical decision", "drove adoption of a new technology",
        "managed a project across multiple teams", "had to say no to a stakeholder"
    ],
    "challenge": [
        "resistance from the team", "limited resources",
        "conflicting priorities", "technical debt",
        "unclear requirements"
    ],
    "difficult_situation": [
        "a team member not meeting expectations", "a conflict between team members",
        "a project falling behind schedule", "budget cuts",
        "a key team member leaving"
    ],
    "person_type": [
        "your manager", "a peer", "a direct report",
        "someone from another team", "a stakeholder"
    ],
    "decision_type": [
        "a technical decision", "a product decision",
        "a process change", "a hiring decision"
    ],
    "item": [
        "technical problem", "project", "feature",
        "bug", "performance issue"
    ],
    "person": [
        "a junior engineer", "a struggling teammate",
        "someone outside your team", "your manager"
    ],
    "concept": [
        "microservices", "event-driven architecture", "CQRS",
        "event sourcing", "sagas", "circuit breaker pattern",
        "bulkhead pattern", "throttling", "backpressure",
        "idempotency", "exactly-once delivery"
    ],
    "technology_a": [
        "SQL", "REST", "Monolithic architecture", "Synchronous communication",
        "PostgreSQL", "Redis", "Kafka"
    ],
    "technology_b": [
        "NoSQL", "GraphQL", "Microservices", "Asynchronous communication",
        "MongoDB", "Memcached", "RabbitMQ"
    ],
    "topic": ["algorithms", "system_design", "databases", "networking", "security"],
    "technology": [
        "TCP/IP", "HTTP/2", "WebSockets", "Docker",
        "Kubernetes", "Kafka", "Redis", "Elasticsearch"
    ],
}


def generate_question_from_template(template: str, topics: List[str], difficulty: str, time: int) -> InterviewQuestion:
    """Generate a question from a template by filling in placeholders"""
    question_text = template
    question_topics = topics.copy()

    # Replace placeholders
    for key, values in FILLERS.items():
        placeholder = "{" + key + "}"
        if placeholder in question_text:
            value = random.choice(values)
            question_text = question_text.replace(placeholder, value, 1)
            if key != "topic":
                question_topics.append(value)

    # Replace topic placeholder
    if "{topic}" in question_text:
        topic = random.choice(["algorithms", "system_design", "databases", "networking", "security"])
        question_text = question_text.replace("{topic}", topic)

    return InterviewQuestion(
        id=f"gen-{uuid.uuid4().hex[:8]}",
        question=question_text,
        category="coding" if "Implement" in template or "Design an algorithm" in template else "system_design",
        difficulty=difficulty,
        role="software_engineer",
        topics=list(set(question_topics)),  # Remove duplicates
        time_estimate_minutes=time
    )


# ═══════════════════════════════════════════════════════════════════════════════
# COMPANY-SPECIFIC QUESTIONS
# ═══════════════════════════════════════════════════════════════════════════════

COMPANY_QUESTIONS = {
    "google": [
        # Google is known for algorithm-heavy interviews
        InterviewQuestion("id", "Implement a bloom filter", "technical", "hard", "software_engineer", "google",
                         ["algorithms", "data_structures"], ["Explain hash functions", "Discuss false positives"], [], 25),
        InterviewQuestion("id", "Design Google Search", "system_design", "expert", "software_engineer", "google",
                         ["system_design", "distributed_systems", "search"], [], [], 60),
        InterviewQuestion("id", "Implement a distributed hash table", "system_design", "hard", "software_engineer", "google",
                         ["distributed_systems", "dht"], [], [], 45),
    ],
    "amazon": [
        # Amazon focuses on leadership principles
        InterviewQuestion("id", "Tell me about a time you had to make a quick decision without all the data",
                         "behavioral", "medium", "software_engineer", "amazon",
                         ["leadership_principles", "decision_making"], ["Use STAR method"], [], 15),
        InterviewQuestion("id", "Design Amazon's recommendation system", "system_design", "hard", "software_engineer", "amazon",
                         ["machine_learning", "recommendations", "system_design"], [], [], 45),
        InterviewQuestion("id", "How would you design a warehouse management system?", "system_design", "hard", "software_engineer", "amazon",
                         ["system_design", "logistics"], [], [], 50),
    ],
    "facebook": [
        InterviewQuestion("id", "Design Facebook's News Feed", "system_design", "hard", "software_engineer", "facebook",
                         ["system_design", "social_network", "feed_ranking"], [], [], 45),
        InterviewQuestion("id", "Implement a consistent hash ring", "technical", "hard", "software_engineer", "facebook",
                         ["distributed_systems", "hashing"], [], [], 30),
    ],
    "netflix": [
        InterviewQuestion("id", "Design a video streaming service", "system_design", "hard", "software_engineer", "netflix",
                         ["video_streaming", "cdn", "adaptive_bitrate"], [], [], 50),
        InterviewQuestion("id", "How would you handle content recommendations at scale?", "system_design", "expert", "software_engineer", "netflix",
                         ["recommendations", "machine_learning", "big_data"], [], [], 45),
    ],
    "uber": [
        InterviewQuestion("id", "Design Uber's ride matching system", "system_design", "hard", "software_engineer", "uber",
                         ["geolocation", "matching", "real_time"], [], [], 45),
        InterviewQuestion("id", "How would you handle surge pricing?", "system_design", "medium", "software_engineer", "uber",
                         ["pricing", "algorithms", "economics"], [], [], 30),
    ],
}


def get_company_questions(company: str) -> List[InterviewQuestion]:
    """Get company-specific questions"""
    return COMPANY_QUESTIONS.get(company.lower(), [])


# ═══════════════════════════════════════════════════════════════════════════════
# QUESTION GENERATOR - Creates 10,000+ questions from templates
# ═══════════════════════════════════════════════════════════════════════════════

def generate_massive_question_bank(target_count: int = 10000) -> List[InterviewQuestion]:
    """Generate a large question bank from templates"""
    questions = []

    # Generate from each template category
    templates = [
        (CODING_TEMPLATES, "coding", 3000),
        (SYSTEM_DESIGN_TEMPLATES, "system_design", 2000),
        (BEHAVIORAL_TEMPLATES, "behavioral", 3000),
        (TECHNICAL_TEMPLATES, "technical", 2000),
    ]

    for template_list, category, count in templates:
        for _ in range(count):
            template_data = random.choice(template_list)
            template, topics, difficulty, time = template_data
            question = generate_question_from_template(template, topics.copy(), difficulty, time)
            question.category = category  # Override the category
            questions.append(question)

    # Add company-specific questions
    for company, company_qs in COMPANY_QUESTIONS.items():
        for q in company_qs:
            q_copy = InterviewQuestion(
                id=f"{company}-{uuid.uuid4().hex[:8]}",
                question=q.question,
                category=q.category,
                difficulty=q.difficulty,
                role=q.role,
                company=company,
                topics=q.topics.copy() if q.topics else [],
                expected_answer_points=q.expected_answer_points.copy() if q.expected_answer_points else [],
                hints=q.hints.copy() if q.hints else [],
                time_estimate_minutes=q.time_estimate_minutes
            )
            questions.append(q_copy)

    return questions[:target_count]


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK INTERVIEW LIBRARY CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class MockInterviewLibrary:
    """Manages the interview question library with search and filtering"""

    def __init__(self, preload_count: int = 1000):
        self.questions: List[InterviewQuestion] = []
        self._by_id: Dict[str, InterviewQuestion] = {}
        self._by_category: Dict[str, List[InterviewQuestion]] = {}
        self._by_difficulty: Dict[str, List[InterviewQuestion]] = {}
        self._by_role: Dict[str, List[InterviewQuestion]] = {}
        self._by_company: Dict[str, List[InterviewQuestion]] = {}
        self._by_topic: Dict[str, List[InterviewQuestion]] = {}

        # Preload questions on initialization
        self._preload_questions(preload_count)

    def _preload_questions(self, count: int):
        """Load initial set of questions"""
        questions = generate_massive_question_bank(count)
        for q in questions:
            self.add_question(q, index=False)
        self._rebuild_indexes()

    def _rebuild_indexes(self):
        """Rebuild all search indexes"""
        self._by_id = {q.id: q for q in self.questions}

        self._by_category = {}
        self._by_difficulty = {}
        self._by_role = {}
        self._by_company = {}
        self._by_topic = {}

        for q in self.questions:
            # Index by category
            if q.category not in self._by_category:
                self._by_category[q.category] = []
            self._by_category[q.category].append(q)

            # Index by difficulty
            if q.difficulty not in self._by_difficulty:
                self._by_difficulty[q.difficulty] = []
            self._by_difficulty[q.difficulty].append(q)

            # Index by role
            if q.role not in self._by_role:
                self._by_role[q.role] = []
            self._by_role[q.role].append(q)

            # Index by company
            if q.company:
                if q.company not in self._by_company:
                    self._by_company[q.company] = []
                self._by_company[q.company].append(q)

            # Index by topics
            for topic in (q.topics or []):
                if topic not in self._by_topic:
                    self._by_topic[topic] = []
                self._by_topic[topic].append(q)

    def add_question(self, question: InterviewQuestion, index: bool = True):
        """Add a question to the library"""
        self.questions.append(question)
        if index:
            self._rebuild_indexes()

    def get_question(self, question_id: str) -> Optional[InterviewQuestion]:
        """Get a question by ID"""
        return self._by_id.get(question_id)

    def get_all_questions(self) -> List[InterviewQuestion]:
        """Get all questions"""
        return self.questions.copy()

    def get_questions_by_category(self, category: str) -> List[InterviewQuestion]:
        """Get questions by category"""
        return self._by_category.get(category, []).copy()

    def get_questions_by_difficulty(self, difficulty: str) -> List[InterviewQuestion]:
        """Get questions by difficulty"""
        return self._by_difficulty.get(difficulty, []).copy()

    def get_questions_by_role(self, role: str) -> List[InterviewQuestion]:
        """Get questions by role"""
        return self._by_role.get(role, []).copy()

    def get_questions_by_company(self, company: str) -> List[InterviewQuestion]:
        """Get questions by company"""
        return self._by_company.get(company.lower(), []).copy()

    def get_questions_by_topic(self, topic: str) -> List[InterviewQuestion]:
        """Get questions by topic"""
        return self._by_topic.get(topic.lower(), []).copy()

    def get_random_question(self, role: str = None, category: str = None,
                           difficulty: str = None, company: str = None) -> Optional[InterviewQuestion]:
        """Get a random question matching criteria"""
        candidates = self.questions

        if role:
            candidates = [q for q in candidates if q.role == role]
        if category:
            candidates = [q for q in candidates if q.category == category]
        if difficulty:
            candidates = [q for q in candidates if q.difficulty == difficulty]
        if company:
            candidates = [q for q in candidates if q.company and q.company.lower() == company.lower()]

        return random.choice(candidates) if candidates else None

    def search_questions(self, query: str, limit: int = 50) -> List[InterviewQuestion]:
        """Search questions by text"""
        query_lower = query.lower()
        results = []

        for q in self.questions:
            if query_lower in q.question.lower():
                results.append(q)
            elif q.topics and any(query_lower in t.lower() for t in q.topics):
                results.append(q)

            if len(results) >= limit:
                break

        return results

    def get_practice_set(self, role: str, num_questions: int = 5,
                         categories: List[str] = None) -> List[InterviewQuestion]:
        """Generate a practice set for a role"""
        role_questions = self.get_questions_by_role(role)

        if not role_questions:
            # Generate generic set
            role_questions = self.questions

        if categories:
            role_questions = [q for q in role_questions if q.category in categories]

        # Ensure variety across categories
        selected = []
        by_category = {}
        for q in role_questions:
            cat = q.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(q)

        # Pick from each category
        per_category = max(1, num_questions // len(by_category))
        for cat, qs in by_category.items():
            selected.extend(random.sample(qs, min(per_category, len(qs))))

        # Fill remaining randomly
        while len(selected) < num_questions and len(selected) < len(role_questions):
            remaining = [q for q in role_questions if q not in selected]
            if remaining:
                selected.append(random.choice(remaining))

        return selected[:num_questions]

    def get_stats(self) -> Dict:
        """Get library statistics"""
        return {
            "total_questions": len(self.questions),
            "by_category": {cat: len(qs) for cat, qs in self._by_category.items()},
            "by_difficulty": {diff: len(qs) for diff, qs in self._by_difficulty.items()},
            "by_role": {role: len(qs) for role, qs in self._by_role.items()},
            "companies": len(self._by_company),
            "topics": len(self._by_topic),
        }


# Global instance - generates 1000 questions on load
mock_library = MockInterviewLibrary(preload_count=1000)


# ═══════════════════════════════════════════════════════════════════════════════
# API FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_questions() -> List[Dict]:
    """Get all questions as dicts"""
    return [vars(q) for q in mock_library.get_all_questions()]


def get_questions_by_role(role: str) -> List[Dict]:
    """Get questions by role"""
    return [vars(q) for q in mock_library.get_questions_by_role(role)]


def get_questions_by_company(company: str) -> List[Dict]:
    """Get questions by company"""
    return [vars(q) for q in mock_library.get_questions_by_company(company)]


def get_questions_by_category(category: str) -> List[Dict]:
    """Get questions by category"""
    return [vars(q) for q in mock_library.get_questions_by_category(category)]


def get_random_question(role: str = None, category: str = None,
                       difficulty: str = None, company: str = None) -> Optional[Dict]:
    """Get random question"""
    q = mock_library.get_random_question(role, category, difficulty, company)
    return vars(q) if q else None


def get_practice_set(role: str, num_questions: int = 5) -> List[Dict]:
    """Get practice set"""
    return [vars(q) for q in mock_library.get_practice_set(role, num_questions)]


def get_library_stats() -> Dict:
    """Get library stats"""
    return mock_library.get_stats()


def search_questions(query: str, limit: int = 50) -> List[Dict]:
    """Search questions"""
    return [vars(q) for q in mock_library.search_questions(query, limit)]


def expand_library(target_count: int = 10000):
    """Expand the library to target count"""
    current = len(mock_library.questions)
    to_generate = target_count - current

    if to_generate <= 0:
        return {"status": "already_at_target", "current": current}

    new_questions = generate_massive_question_bank(to_generate)
    for q in new_questions:
        mock_library.add_question(q, index=False)

    mock_library._rebuild_indexes()

    return {
        "status": "expanded",
        "previous_count": current,
        "new_count": len(mock_library.questions),
        "added": len(new_questions)
    }


# Export all
__all__ = [
    "InterviewQuestion",
    "MockInterviewLibrary",
    "mock_library",
    "get_all_questions",
    "get_questions_by_role",
    "get_questions_by_company",
    "get_questions_by_category",
    "get_random_question",
    "get_practice_set",
    "get_library_stats",
    "search_questions",
    "expand_library",
    "generate_massive_question_bank",
    "COMPANY_QUESTIONS",
    "CODING_TEMPLATES",
    "SYSTEM_DESIGN_TEMPLATES",
    "BEHAVIORAL_TEMPLATES",
    "TECHNICAL_TEMPLATES",
]
