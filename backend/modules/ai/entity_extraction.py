"""
entity_extraction.py - NLP entity extraction for interview transcripts

Extracts:
- Companies (Google, Meta, Amazon, etc.)
- Technical topics (algorithms, databases, system design, etc.)
- Skills (Python, React, Kubernetes, etc.)
- Roles (Software Engineer, Product Manager, etc.)
- Question categories (technical, behavioral, system design)

Uses rule-based extraction (lightweight, no ML model required)
Can be enhanced with spaCy NER for better accuracy.
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger("entity_extraction")

@dataclass
class ExtractedEntity:
    """Represents an extracted entity"""
    text: str
    label: str
    confidence: float = 1.0
    start: int = 0
    end: int = 0

# Known entities for interview contexts
COMPANY_NAMES = {
    # FAANG + major tech
    "google", "alphabet", "meta", "facebook", "amazon", "apple", "netflix",
    "microsoft", "linkedin", "twitter", "x", "uber", "lyft", "airbnb", "stripe",
    "square", "coinbase", "robinhood", "doordash", "instacart", "shopify",
    "spotify", "dropbox", "slack", "zoom", "notion", "figma", "canva",
    "openai", "anthropic", "cohere", "huggingface", "stability ai",
    "nvidia", "intel", "amd", "qualcomm", "broadcom", "cisco", "oracle",
    "salesforce", "sap", "adobe", "autodesk", "intuit", "workday",
    "snowflake", "databricks", "palantir", "datadog", "splunk", "elastic",
    "cloudflare", "fastly", "akamai", "verizon", "at&t", "t-mobile",
    "tiktok", "bytedance", "snapchat", "snap", "pinterest", "reddit",
    "quora", "stack overflow", "github", "gitlab", "bitbucket",
}

TECHNICAL_TOPICS = {
    # Algorithms
    "algorithm", "data structure", "big o", "complexity", "time complexity",
    "space complexity", "dynamic programming", "dp", "recursion", "iteration",
    "graph", "tree", "binary tree", "bst", "heap", "hash table", "hash map",
    "array", "linked list", "stack", "queue", "deque", "priority queue",
    "sorting", "searching", "binary search", "bfs", "dfs", "dijkstra",
    "a*", "a star", "backtracking", "greedy", "divide and conquer",

    # System Design
    "system design", "distributed system", "microservices", "monolith",
    "load balancer", "cdn", "cache", "caching", "redis", "memcached",
    "database", "sql", "nosql", "postgres", "mysql", "mongodb", "dynamodb",
    "cassandra", "cockroachdb", "tidb", "sharding", "replication", "partitioning",
    "api", "rest", "graphql", "grpc", "websocket", "http", "https",
    "message queue", "kafka", "rabbitmq", "sqs", "pubsub", "event driven",
    "cap theorem", "consistency", "availability", "partition tolerance",
    "rate limiting", "circuit breaker", "bulkhead", "throttling",
    "docker", "kubernetes", "k8s", "container", "orchestration",
    "aws", "gcp", "azure", "cloud", "serverless", "lambda", "ec2", "s3",

    # Frontend
    "frontend", "backend", "fullstack", "react", "vue", "angular", "svelte",
    "html", "css", "javascript", "typescript", "jsx", "tsx", "dom", "virtual dom",
    "webpack", "vite", "rollup", "parcel", "esbuild", "babel", "polyfill",
    "responsive", "accessibility", "a11y", "seo", "progressive web app", "pwa",

    # DevOps
    "ci/cd", "jenkins", "github actions", "gitlab ci", "travis", "circleci",
    "terraform", "ansible", "puppet", "chef", "infrastructure as code",
    "monitoring", "prometheus", "grafana", "elk", "logging", "tracing",
}

SKILLS = {
    # Programming languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "clojure", "erlang",
    "elixir", "haskell", "ocaml", "lua", "perl", "r", "matlab", "julia",

    # Frameworks & Libraries
    "django", "flask", "fastapi", "spring", "spring boot", "node.js", "nodejs",
    "express", "nestjs", "ruby on rails", "laravel", "symfony", "asp.net",
    "react", "vue", "angular", "svelte", "next.js", "nuxt", "gatsby",
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
    "spark", "hadoop", "kafka", "airflow", "dbt",

    # Tools & Platforms
    "git", "github", "gitlab", "bitbucket", "jira", "confluence", "notion",
    "docker", "kubernetes", "terraform", "aws", "gcp", "azure", "linux",
    "bash", "shell", "powershell", "vim", "vscode", "intellij",

    # Methodologies
    "agile", "scrum", "kanban", "tdd", "bdd", "ddd", "solid", "design patterns",
    "microservices", "event sourcing", "cqrs", "clean architecture",
}

ROLES = {
    "software engineer", "senior software engineer", "staff engineer",
    "principal engineer", "engineering manager", "tech lead", "cto", "vp of engineering",
    "product manager", "pm", "program manager", "product owner", "scrum master",
    "data scientist", "data engineer", "ml engineer", "ai engineer", "research scientist",
    "devops engineer", "sre", "site reliability engineer", "platform engineer",
    "frontend engineer", "backend engineer", "fullstack engineer", "mobile engineer",
    "ios developer", "android developer", "security engineer", "qa engineer",
    "ux designer", "ui designer", "product designer", "ux researcher",
}

QUESTION_CATEGORIES = {
    "technical": [
        "algorithm", "data structure", "coding", "implementation", "function",
        "optimize", "complexity", "time complexity", "space complexity",
    ],
    "system_design": [
        "design", "system", "architecture", "scale", "distributed", "database",
        "microservices", "api design", "service", "component",
    ],
    "behavioral": [
        "tell me about", "describe a time", "give an example", "situation",
        "conflict", "challenge", "team", "collaboration", "leadership",
        "strength", "weakness", "failure", "success", "experience",
    ],
    "knowledge": [
        "what is", "how does", "explain", "difference between", "compare",
        "pros and cons", "advantages", "disadvantages", "when to use",
    ],
}

DIFFICULTY_KEYWORDS = {
    "easy": ["simple", "basic", "beginner", "easy", "fundamental"],
    "medium": ["moderate", "typical", "standard", "medium", "average"],
    "hard": ["difficult", "complex", "advanced", "hard", "challenging", "tricky"],
}


class EntityExtractor:
    """Extract entities from interview text"""

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for faster matching"""
        # Company patterns
        self.company_patterns = [
            re.compile(r'\b' + re.escape(company) + r'\b', re.IGNORECASE)
            for company in COMPANY_NAMES
        ]

        # Role patterns
        self.role_patterns = [
            re.compile(r'\b' + re.escape(role) + r'\b', re.IGNORECASE)
            for role in ROLES
        ]

    def extract_companies(self, text: str) -> List[ExtractedEntity]:
        """Extract company names from text"""
        companies = []
        text_lower = text.lower()

        for company in COMPANY_NAMES:
            for match in re.finditer(r'\b' + re.escape(company) + r'\b', text_lower):
                companies.append(ExtractedEntity(
                    text=match.group(),
                    label="COMPANY",
                    confidence=0.9,
                    start=match.start(),
                    end=match.end()
                ))

        return companies

    def extract_topics(self, text: str) -> List[ExtractedEntity]:
        """Extract technical topics from text"""
        topics = []
        text_lower = text.lower()

        for topic in TECHNICAL_TOPICS:
            for match in re.finditer(r'\b' + re.escape(topic) + r'\b', text_lower):
                topics.append(ExtractedEntity(
                    text=match.group(),
                    label="TOPIC",
                    confidence=0.85,
                    start=match.start(),
                    end=match.end()
                ))

        return topics

    def extract_skills(self, text: str) -> List[ExtractedEntity]:
        """Extract skills from text"""
        skills = []
        text_lower = text.lower()

        for skill in SKILLS:
            for match in re.finditer(r'\b' + re.escape(skill) + r'\b', text_lower):
                skills.append(ExtractedEntity(
                    text=match.group(),
                    label="SKILL",
                    confidence=0.9,
                    start=match.start(),
                    end=match.end()
                ))

        return skills

    def extract_roles(self, text: str) -> List[ExtractedEntity]:
        """Extract job roles from text"""
        roles = []
        text_lower = text.lower()

        for role in ROLES:
            for match in re.finditer(r'\b' + re.escape(role) + r'\b', text_lower):
                roles.append(ExtractedEntity(
                    text=match.group(),
                    label="ROLE",
                    confidence=0.85,
                    start=match.start(),
                    end=match.end()
                ))

        return roles

    def categorize_question(self, text: str) -> Tuple[str, float]:
        """Categorize a question (technical, behavioral, system_design, knowledge)"""
        # Try SmartClassifier first if available
        try:
            from modules.ai.smart_classifier import get_classifier, CLASSIFIER_AVAILABLE
            if CLASSIFIER_AVAILABLE:
                classifier = get_classifier()
                if classifier:
                    return classifier.classify_question(text)
        except Exception:
            pass  # nosec B110

        # Fallback: keyword-based classification
        text_lower = text.lower()
        scores = {}

        for category, keywords in QUESTION_CATEGORIES.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            scores[category] = score

        if not scores or max(scores.values()) == 0:
            return "general", 0.5

        best_category = max(scores, key=scores.get)
        confidence = min(0.5 + (scores[best_category] * 0.1), 1.0)
        return best_category, confidence

    def estimate_difficulty(self, text: str) -> Tuple[Optional[str], float]:
        """Estimate question difficulty"""
        # Try SmartClassifier first if available
        try:
            from modules.ai.smart_classifier import get_classifier, CLASSIFIER_AVAILABLE
            if CLASSIFIER_AVAILABLE:
                classifier = get_classifier()
                if classifier:
                    return classifier.classify_difficulty(text)
        except Exception:
            pass  # nosec B110

        # Fallback: keyword-based difficulty estimation
        text_lower = text.lower()

        for difficulty, keywords in DIFFICULTY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return difficulty, 0.7

        # Check for difficulty indicators
        if any(word in text_lower for word in ["optimize", "trade-off", "distributed", "scale"]):
            return "hard", 0.6

        return None, 0.0

    def extract_all(self, text: str) -> Dict:
        """Extract all entities from text"""
        companies = self.extract_companies(text)
        topics = self.extract_topics(text)
        skills = self.extract_skills(text)
        roles = self.extract_roles(text)
        category, cat_confidence = self.categorize_question(text)
        difficulty, diff_confidence = self.estimate_difficulty(text)

        return {
            "companies": [{"text": e.text, "confidence": e.confidence} for e in companies],
            "topics": [{"text": e.text, "confidence": e.confidence} for e in topics],
            "skills": [{"text": e.text, "confidence": e.confidence} for e in skills],
            "roles": [{"text": e.text, "confidence": e.confidence} for e in roles],
            "category": {"label": category, "confidence": cat_confidence},
            "difficulty": {"label": difficulty, "confidence": diff_confidence} if difficulty else None,
            "entities_found": len(companies) + len(topics) + len(skills) + len(roles)
        }

    def process_transcript(self, transcript: str) -> List[Dict]:
        """Process a transcript and extract Q&A pairs"""
        # Simple Q&A extraction - split on common question patterns
        qa_pairs = []

        # Split transcript into segments
        lines = transcript.split('\n')
        current_q = None
        current_a = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect questions (ends with ? or starts with question words)
            is_question = line.endswith('?') or any(
                line.lower().startswith(word) for word in ['what', 'how', 'why', 'when', 'where', 'who', 'can', 'could', 'would', 'tell me', 'explain', 'describe']
            )

            if is_question:
                # Save previous Q&A pair
                if current_q and current_a:
                    qa_pairs.append({
                        'question': current_q,
                        'answer': ' '.join(current_a),
                        'entities': self.extract_all(current_q + ' ' + ' '.join(current_a))
                    })
                current_q = line
                current_a = []
            else:
                current_a.append(line)

        # Save last pair
        if current_q and current_a:
            qa_pairs.append({
                'question': current_q,
                'answer': ' '.join(current_a),
                'entities': self.extract_all(current_q + ' ' + ' '.join(current_a))
            })

        return qa_pairs


# Global instance
entity_extractor = EntityExtractor()


def extract_entities(text: str) -> Dict:
    """Extract entities from text - convenience function"""
    return entity_extractor.extract_all(text)


def process_transcript(transcript: str) -> List[Dict]:
    """Process transcript into Q&A pairs with entities - convenience function"""
    return entity_extractor.process_transcript(transcript)


# Phase 2: Try to use hybrid extractor if available
def extract_entities_hybrid(text: str) -> Dict:
    """Extract entities using hybrid ML + rule approach (Phase 2)"""
    try:
        from hybrid_entity_extraction import hybrid_extractor
        return hybrid_extractor.extract_all(text)
    except ImportError:
        # Fall back to rule-based
        return entity_extractor.extract_all(text)
