"""
study_plan_generator.py - Personalized Study Plan Generator

Phase 2 Task #33: Adaptive study plans based on cognitive graph data

Features:
- Weak area identification from graph analysis
- Spaced repetition scheduling (SM-2 algorithm)
- Resource recommendations (LeetCode, System Design Primer, etc.)
- Progress tracking with milestones
- Adaptive difficulty adjustment
- Study session generation

Usage:
    from study_plan_generator import study_planner
    plan = study_planner.generate_plan(user_id, days=30)
"""

import logging
import random  # nosec B311 — used for study plan randomization, not security
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json

logger = logging.getLogger("study_plan_generator")


@dataclass
class StudyTask:
    """Individual study task"""
    id: str
    title: str
    description: str
    category: str  # "algorithms", "system_design", "behavioral", "language", "devops", "cloud", etc.
    difficulty: str  # "easy", "medium", "hard"
    estimated_minutes: int
    resources: List[Dict]
    prerequisites: List[str] = field(default_factory=list)
    completed: bool = False
    scheduled_date: Optional[datetime] = None
    confidence_target: float = 0.8
    parent_area: str = ""       # Which weak area this task belongs to
    is_focus: bool = False      # Primary task for the day
    is_stretch: bool = False   # Optional stretch goal


@dataclass
class StudySession:
    """A study session with multiple tasks"""
    date: datetime
    tasks: List[StudyTask]
    total_minutes: int
    theme: str  # e.g., "Graph Algorithms", "System Design Fundamentals"
    day_number: int = 0                  # 1-based day number
    focus_task_id: Optional[str] = None   # Primary task ID
    stretch_task_id: Optional[str] = None  # Optional stretch goal ID


@dataclass
class StudyPlan:
    """Complete study plan"""
    user_id: str
    created_at: datetime
    duration_days: int
    sessions: List[StudySession]
    weak_areas: List[Dict]
    strong_areas: List[Dict]
    milestones: List[Dict]
    total_tasks: int
    completed_tasks: int
    progress_percentage: float
    # Personalization fields
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    skill_gaps: Optional[List[Dict]] = None
    plan_type: str = "generic"  # "personalized" or "generic"
    personalization_context: Optional[Dict] = None  # Metadata about plan sources


class SpacedRepetitionScheduler:
    """SM-2 Algorithm implementation for spaced repetition scheduling."""

    def __init__(self):
        self.intervals = [1, 3, 7, 14, 30, 60, 120]
        self.easiness_factor = 2.5

    def calculate_next_review(
        self,
        current_confidence: float,
        review_count: int,
        last_interval: int = 1
    ) -> Tuple[int, float]:
        quality = int(current_confidence * 5)
        if quality < 3:
            return 1, max(1.3, self.easiness_factor - 0.2)
        new_ef = self.easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ef = max(1.3, new_ef)
        if review_count == 0:
            next_interval = 1
        elif review_count == 1:
            next_interval = 6
        else:
            next_interval = int(last_interval * new_ef)
        return min(next_interval, 365), new_ef

    def generate_review_schedule(
        self,
        tasks: List[StudyTask],
        start_date: datetime,
        days: int
    ) -> List[Tuple[datetime, StudyTask]]:
        schedule = []
        current_date = start_date
        for task in tasks:
            schedule.append((current_date, task))
            review_date = current_date
            interval = 1
            ef = 2.5
            for review_num in range(1, 6):
                interval, ef = self.calculate_next_review(
                    current_confidence=0.7,
                    review_count=review_num,
                    last_interval=interval
                )
                review_date += timedelta(days=interval)
                if review_date < start_date + timedelta(days=days):
                    schedule.append((review_date, task))
        schedule.sort(key=lambda x: x[0])
        return schedule


class JDAnalyzer:
    """Extract skills and keywords from job descriptions"""

    # Keyword maps for skill categorization
    TECHNICAL_KEYWORDS = {
        "algorithms": ["algorithms", "data structures", "complexity", "big o",
                       "sorting", "searching", "dynamic programming", "recursion",
                       "greedy", "binary search", "graph theory", "hash table",
                       "linked list", "tree traversal", "backtracking", "sliding window"],
        "system_design": ["system design", "distributed systems", "scalability",
                         "microservices", "load balancing", "caching", "sharding",
                         "replication", "consistency", "availability", "partition tolerance",
                         "message queue", "api design", "database design"],
        "python": ["python", "django", "flask", "fastapi", "pandas", "numpy",
                   "scipy", "pytest", "celery", "sqlalchemy"],
        "javascript": ["javascript", "js", "react", "angular", "vue", "node",
                       "typescript", "next.js", "express", "webpack"],
        "java": ["java", "spring", "spring boot", "kotlin", "maven", "gradle",
                 "jvm", "hibernate", "jpa"],
        "go": ["go", "golang", "goroutines", "channels", "gin"],
        "devops": ["docker", "kubernetes", "k8s", "ci/cd", "terraform", "ansible",
                   "jenkins", "github actions", "gitlab ci", "argocd", "helm"],
        "cloud": ["aws", "gcp", "azure", "cloud", "serverless", "lambda",
                  "s3", "ec2", "rds", "cloudfront", "cloudformation"],
        "databases": ["sql", "postgresql", "mysql", "mongodb", "redis", "dynamodb",
                     "cassandra", "elasticsearch", "neo4j", "sqlite"],
        "ml": ["machine learning", "deep learning", "nlp", "pytorch", "tensorflow",
               "scikit-learn", "neural network", "transformer", "llm"],
        "security": ["security", "authentication", "encryption", "oauth", "saml",
                    "ssl", "tls", "penetration testing", "owasp"],
        "api": ["rest", "graphql", "grpc", "api", "microservices", "websockets",
                "openapi", "swagger"],
    }

    # Section markers that indicate requirements
    REQUIREMENT_MARKERS = ["required", "must have", "requirements", "qualifications",
                          "essential", "mandatory", "you will need"]
    PREFERRED_MARKERS = ["preferred", "nice to have", "bonus", "desired", "plus"]

    # Map skill keywords to specific sub-topics for richer task generation
    SUB_TOPIC_MAP = {
        "ci/cd": ["Jenkins Pipeline Configuration", "GitHub Actions Workflows", "ArgoCD GitOps Deployment", "Pipeline Security & Secrets Management"],
        "docker": ["Dockerfile Best Practices", "Multi-stage Builds", "Docker Compose Networking", "Container Registry Management"],
        "kubernetes": ["Pod & Deployment Configuration", "Helm Charts & Releases", "K8s Networking (CNI/Service Mesh)", "Cluster Autoscaling & HPA"],
        "terraform": ["Terraform Modules & State", "Workspaces & Environment Management", "Terraform Testing Strategies", "Provider & Resource Patterns"],
        "ansible": ["Ansible Playbooks & Roles", "Inventory Management", "Ansible Vault for Secrets", "Idempotent Task Design"],
        "aws": ["AWS VPC & IAM Setup", "EC2 & Auto Scaling", "S3 & CloudFront CDN", "RDS & DynamoDB"],
        "gcp": ["GCP Compute Engine & Cloud Run", "BigQuery & Cloud Storage", "GCP IAM & Service Accounts", "GKE Cluster Management"],
        "azure": ["Azure Virtual Machines & Scale Sets", "Azure Blob & CDN", "Azure AD & RBAC", "Azure Kubernetes Service"],
        "python": ["Python Type Hints & Generics", "Async/Await Patterns", "Context Managers & Decorators", "Python Package Management"],
        "javascript": ["JS Event Loop & Promises", "Closures & Scope Chains", "ES6+ Features & Modules", "Node.js Streams & Buffers"],
        "react": ["React Hooks Deep Dive", "State Management (Redux/Zustand)", "React Performance Optimization", "Server Components (RSC)"],
        "sql": ["SQL Window Functions", "Query Optimization & EXPLAIN", "Indexing Strategies", "Transaction Isolation Levels"],
        "redis": ["Redis Data Structures", "Caching Patterns (Cache-Aside)", "Redis Pub/Sub & Streams", "Redis Cluster & Sentinel"],
        "security": ["OWASP Top 10 Deep Dive", "OAuth2/OIDC Implementation", "Container Image Scanning", "Network Policies & Firewalls"],
        "system design": ["Load Balancer Strategies", "Caching Patterns (LRU/Write-Through)", "Database Sharding & Replication", "Message Queue Architecture"],
        "monitoring": ["Prometheus & Grafana Setup", "Distributed Tracing (Jaeger)", "Log Aggregation (ELK Stack)", "SLO/SLI Definition & Alerting"],
        "git": ["Git Branching Strategies", "Interactive Rebase & Cherry-Pick", "Git Hooks & CI Integration", "Monorepo Management"],
        "linux": ["Linux Process Management", "Shell Scripting & Automation", "File System & Permissions", "Networking & Troubleshooting"],
        "networking": ["TCP/IP & DNS Deep Dive", "HTTP/2 & HTTP/3", "Load Balancer Types", "CDN Configuration & Edge Caching"],
        "testing": ["Unit Testing Best Practices", "Integration Testing Patterns", "E2E Testing with Cypress/Playwright", "Test Doubles & Mocking"],
    }

    def extract_skills(self, jd_text: str) -> List[Dict]:
        """Extract skills from job description text with relevance weighting"""
        if not jd_text:
            return []

        text_lower = jd_text.lower()
        found_skills = []

        # Detect if text has a "requirements" section (higher weight)
        has_requirements = any(marker in text_lower for marker in self.REQUIREMENT_MARKERS)

        for category, keywords in self.TECHNICAL_KEYWORDS.items():
            for keyword in keywords:
                count = text_lower.count(keyword.lower())
                if count > 0:
                    # Weight: base 0.3, boosted by frequency and requirements section
                    weight = 0.3 + min(count * 0.08, 0.4)
                    if has_requirements:
                        weight += 0.1

                    # Invert: high relevance = low confidence = high-priority weak area
                    confidence = max(0.1, 1.0 - weight)

                    found_skills.append({
                        "name": keyword.title() if len(keyword) > 3 else keyword.upper(),
                        "category": category,
                        "confidence": confidence,
                        "source": "job_description",
                        "mentions": count,
                        "sub_topics": self.SUB_TOPIC_MAP.get(keyword.lower(), []),
                    })

        # Deduplicate: keep highest-weight (lowest confidence) entry per category+name
        seen = {}
        for skill in found_skills:
            key = (skill["category"], skill["name"])
            if key not in seen or skill["confidence"] < seen[key]["confidence"]:
                seen[key] = skill

        # Sort by confidence ascending (weakest first)
        skills = sorted(seen.values(), key=lambda x: x["confidence"])
        return skills[:25]  # Cap at 25 skills from JD


class SpacedRepetitionPlanner:
    """
    SM-2 Algorithm implementation for spaced repetition scheduling.
    Optimizes review intervals based on performance.
    """

    # NOTE: This class was previously named StudyPlanGenerator. It was renamed
    # to avoid shadowing the main StudyPlanGenerator at line 609.
    # See CodeQL alert #828/#829.

    def __init__(self):
        # Default intervals in days
        self.intervals = [1, 3, 7, 14, 30, 60, 120]
        self.easiness_factor = 2.5

    def calculate_next_review(
        self,
        current_confidence: float,
        review_count: int,
        last_interval: int = 1
    ) -> Tuple[int, float]:
        """
        Calculate next review interval and new easiness factor.

        Args:
            current_confidence: 0.0 to 1.0 (1.0 = perfect recall)
            review_count: Number of previous reviews
            last_interval: Previous interval in days

        Returns:
            (next_interval_days, new_easiness_factor)
        """
        # SM-2 quality rating (0-5)
        quality = int(current_confidence * 5)

        if quality < 3:
            # Reset interval if performance was poor
            return 1, max(1.3, self.easiness_factor - 0.2)

        # Calculate new easiness factor
        new_ef = self.easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ef = max(1.3, new_ef)  # Minimum EF is 1.3

        # Calculate next interval
        if review_count == 0:
            next_interval = 1
        elif review_count == 1:
            next_interval = 6
        else:
            next_interval = int(last_interval * new_ef)

        return min(next_interval, 365), new_ef  # Cap at 1 year

    def generate_review_schedule(
        self,
        tasks: List[StudyTask],
        start_date: datetime,
        days: int
    ) -> List[Tuple[datetime, StudyTask]]:
        """Generate review schedule for tasks"""
        schedule = []
        current_date = start_date

        for task in tasks:
            # Initial learning
            schedule.append((current_date, task))

            # Review schedule
            review_date = current_date
            interval = 1
            ef = 2.5  # lgtm[py/multiple-definition] — initial value before loop reassigns it

            for review_num in range(1, 6):  # 5 reviews over the period
                interval, ef = self.calculate_next_review(
                    current_confidence=0.7,  # Assume decent initial recall
                    review_count=review_num,
                    last_interval=interval
                )
                review_date += timedelta(days=interval)

                if review_date < start_date + timedelta(days=days):
                    schedule.append((review_date, task))

        # Sort by date
        schedule.sort(key=lambda x: x[0])
        return schedule


class ResourceLibrary:
    """Library of study resources organized by category and difficulty"""

    RESOURCES = {
        "algorithms": {
            "easy": [
                {"name": "Two Sum", "type": "leetcode", "url": "https://leetcode.com/problems/two-sum/", "description": "Hash map approach — O(n) time, fundamental for interview warm-ups"},
                {"name": "Valid Parentheses", "type": "leetcode", "url": "https://leetcode.com/problems/valid-parentheses/", "description": "Stack-based solution — teaches stack intuition for parsing problems"},
                {"name": "Merge Two Sorted Lists", "type": "leetcode", "url": "https://leetcode.com/problems/merge-two-sorted-lists/", "description": "Linked list manipulation — pointer-based reasoning"},
                {"name": "Best Time to Buy and Sell Stock", "type": "leetcode", "url": "https://leetcode.com/problems/best-time-to-buy-and-sell-stock/", "description": "One-pass greedy — sliding window foundation"},
                {"name": "Palindrome Number", "type": "leetcode", "url": "https://leetcode.com/problems/palindrome-number/", "description": "Math reversal technique — number manipulation basics"},
            ],
            "medium": [
                {"name": "Binary Tree Level Order Traversal", "type": "leetcode", "url": "https://leetcode.com/problems/binary-tree-level-order-traversal/", "description": "BFS with queue — tree traversal pattern used in many problems"},
                {"name": "3Sum", "type": "leetcode", "url": "https://leetcode.com/problems/3sum/", "description": "Two-pointer technique after sorting — classic interview question"},
                {"name": "Word Break", "type": "leetcode", "url": "https://leetcode.com/problems/word-break/", "description": "Dynamic programming with string segmentation — shows DP on strings"},
                {"name": "Coin Change", "type": "leetcode", "url": "https://leetcode.com/problems/coin-change/", "description": "Classic DP — bottom-up tabulation, essential for unbounded knapsack variants"},
                {"name": "Number of Islands", "type": "leetcode", "url": "https://leetcode.com/problems/number-of-islands/", "description": "DFS/BFS on grid — graph traversal on 2D matrix"},
                {"name": "Group Anagrams", "type": "leetcode", "url": "https://leetcode.com/problems/group-anagrams/", "description": "Hash map with sorted keys — grouping pattern"},
                {"name": "Top K Frequent Elements", "type": "leetcode", "url": "https://leetcode.com/problems/top-k-frequent-elements/", "description": "Heap or bucket sort — frequency counting pattern"},
            ],
            "hard": [
                {"name": "Merge k Sorted Lists", "type": "leetcode", "url": "https://leetcode.com/problems/merge-k-sorted-lists/", "description": "Min-heap or divide-and-conquer — merging pattern with priority queue"},
                {"name": "LRU Cache", "type": "leetcode", "url": "https://leetcode.com/problems/lru-cache/", "description": "Hash map + doubly linked list — O(1) get/put, system design essential"},
                {"name": "Trapping Rain Water", "type": "leetcode", "url": "https://leetcode.com/problems/trapping-rain-water/", "description": "Two-pointer with min-height — spatial reasoning and optimization"},
                {"name": "Word Search II", "type": "leetcode", "url": "https://leetcode.com/problems/word-search-ii/", "description": "Trie + DFS backtracking — combines data structure with search"},
                {"name": "Median of Two Sorted Arrays", "type": "leetcode", "url": "https://leetcode.com/problems/median-of-two-sorted-arrays/", "description": "Binary search on partition — advanced divide and conquer"},
            ],
        },
        "system_design": {
            "easy": [
                {"name": "Design URL Shortener", "type": "system_design", "url": "https://github.com/donnemartin/system-design-primer", "description": "Hash-based shortening, base62 encoding, database sharding fundamentals"},
                {"name": "Design Key-Value Store", "type": "system_design", "url": "https://github.com/donnemartin/system-design-primer", "description": "CAP theorem, consistency patterns, write-ahead log"},
                {"name": "Design Pastebin", "type": "system_design", "url": "https://github.com/donnemartin/system-design-primer", "description": "Object storage, rate limiting, expiration policies"},
            ],
            "medium": [
                {"name": "Design News Feed", "type": "system_design", "url": "https://github.com/donnemartin/system-design-primer", "description": "Fan-out on write vs read, caching strategies, ranking algorithms"},
                {"name": "Design Rate Limiter", "type": "system_design", "url": "https://github.com/donnemartin/system-design-primer", "description": "Token bucket, sliding window, distributed rate limiting with Redis"},
                {"name": "Design Chat System", "type": "system_design", "url": "https://github.com/donnemartin/system-design-primer", "description": "WebSocket vs polling, message ordering, delivery guarantees"},
                {"name": "Design Notification System", "type": "system_design", "url": "https://github.com/donnemartin/system-design-primer", "description": "Multi-channel dispatch, priority queues, deduplication"},
            ],
            "hard": [
                {"name": "Design Distributed Message Queue", "type": "system_design", "url": "https://github.com/donnemartin/system-design-primer", "description": "Kafka-like architecture, partitioning, consumer groups, exactly-once delivery"},
                {"name": "Design Web Crawler", "type": "system_design", "url": "https://github.com/donnemartin/system-design-primer", "description": "Distributed crawling, politeness, URL frontier, deduplication"},
                {"name": "Design YouTube/Video Streaming", "type": "system_design", "url": "https://github.com/donnemartin/system-design-primer", "description": "CDN, adaptive bitrate, transcoding pipeline, metadata storage"},
                {"name": "Design Google Drive", "type": "system_design", "url": "https://github.com/donnemartin/system-design-primer", "description": "File sync, conflict resolution, chunked upload, delta encoding"},
            ],
        },
        "devops": {
            "easy": [
                {"name": "Docker Getting Started", "type": "tutorial", "url": "https://docs.docker.com/get-started/", "description": "Hands-on Docker basics — images, containers, Dockerfile, and docker-compose"},
                {"name": "GitHub Actions Quickstart", "type": "tutorial", "url": "https://docs.github.com/en/actions/quickstart", "description": "CI/CD pipeline basics — workflows, runners, and actions"},
                {"name": "Terraform Basics", "type": "tutorial", "url": "https://developer.hashicorp.com/terraform/tutorials", "description": "IaC fundamentals — providers, resources, state, and modules"},
                {"name": "Kubectl Cheat Sheet", "type": "reference", "url": "https://kubernetes.io/docs/reference/kubectl/cheatsheet/", "description": "Essential kubectl commands for pod, deployment, and service management"},
            ],
            "medium": [
                {"name": "Jenkins Pipeline Tutorial", "type": "tutorial", "url": "https://www.jenkins.io/doc/pipeline/tour/", "description": "Declarative and scripted pipelines — stages, agents, shared libraries"},
                {"name": "ArgoCD Getting Started", "type": "tutorial", "url": "https://argo-cd.readthedocs.io/en/stable/getting_started/", "description": "GitOps continuous delivery — app-of-apps, sync waves, and health checks"},
                {"name": "Helm Charts Guide", "type": "tutorial", "url": "https://helm.sh/docs/topics/charts/", "description": "Chart structure, templates, values, and release management for K8s"},
                {"name": "Prometheus + Grafana Setup", "type": "tutorial", "url": "https://prometheus.io/docs/tutorials/", "description": "Metrics collection, PromQL queries, Grafana dashboards, and alerting rules"},
                {"name": "Ansible Best Practices", "type": "tutorial", "url": "https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html", "description": "Role structure, inventory management, vault encryption, and idempotent tasks"},
            ],
            "hard": [
                {"name": "Kubernetes the Hard Way", "type": "tutorial", "url": "https://github.com/kelseyhightower/kubernetes-the-hard-way", "description": "Bootstrap K8s from scratch — understand every component, certs, and networking"},
                {"name": "Terraform Module Design", "type": "tutorial", "url": "https://developer.hashicorp.com/terraform/language/modules/develop", "description": "Production module patterns — interfaces, testing, versioning, and registry publishing"},
                {"name": "Service Mesh with Istio", "type": "tutorial", "url": "https://istio.io/latest/docs/setup/getting-started/", "description": "Traffic management, mutual TLS, observability, and canary deployments"},
            ],
        },
        "cloud": {
            "easy": [
                {"name": "AWS Free Tier Setup", "type": "tutorial", "url": "https://aws.amazon.com/free/", "description": "Getting started with AWS — EC2, S3, IAM basics with free tier"},
                {"name": "GCP Cloud Run Quickstart", "type": "tutorial", "url": "https://cloud.google.com/run/docs/quickstarts", "description": "Serverless containers — deploy and scale without managing infrastructure"},
                {"name": "Azure Fundamentals", "type": "tutorial", "url": "https://learn.microsoft.com/en-us/training/paths/microsoft-azure-fundamentals/", "description": "Core Azure concepts — compute, storage, networking, and identity"},
            ],
            "medium": [
                {"name": "AWS Well-Architected Framework", "type": "reference", "url": "https://aws.amazon.com/architecture/well-architected/", "description": "5 pillars — operational excellence, security, reliability, performance, cost optimization"},
                {"name": "GCP Kubernetes Engine", "type": "tutorial", "url": "https://cloud.google.com/kubernetes-engine/docs/how-to", "description": "GKE cluster management — node pools, autoscaling, and workload identity"},
                {"name": "AWS VPC Design", "type": "tutorial", "url": "https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html", "description": "Subnets, NACLs, route tables, and transit gateway for multi-VPC architectures"},
                {"name": "Cloud Cost Optimization", "type": "guide", "url": "https://aws.amazon.com/aws-cost-management/", "description": "Reserved instances, spot instances, right-sizing, and budget alerts"},
            ],
            "hard": [
                {"name": "Multi-Region Failover Architecture", "type": "guide", "url": "https://aws.amazon.com/solutions/implementations/multi-region-application/", "description": "Active-active deployment, global load balancing, and data replication strategies"},
                {"name": "AWS Security Best Practices", "type": "guide", "url": "https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html", "description": "Zero trust, least privilege IAM, encryption at rest/transit, and compliance automation"},
            ],
        },
        "databases": {
            "easy": [
                {"name": "SQLBolt Interactive SQL", "type": "tutorial", "url": "https://sqlbolt.com/", "description": "Interactive SQL lessons — SELECT, JOINs, aggregations, and subqueries"},
                {"name": "MongoDB University Basics", "type": "tutorial", "url": "https://university.mongodb.com/", "description": "Document model, CRUD operations, indexing basics, and aggregation pipeline"},
                {"name": "Redis.io Commands", "type": "reference", "url": "https://redis.io/commands/", "description": "String, hash, list, set, sorted set operations and patterns"},
            ],
            "medium": [
                {"name": "Use The Index, Luke", "type": "tutorial", "url": "https://use-the-index-luke.com/", "description": "Database indexing explained — B-tree, hash, partial, and composite indexes"},
                {"name": "PostgreSQL Performance", "type": "guide", "url": "https://www.postgresql.org/docs/current/performance-tips.html", "description": "EXPLAIN ANALYZE, query planning, vacuum, and connection pooling with PgBouncer"},
                {"name": "Redis University", "type": "tutorial", "url": "https://university.redis.com/", "description": "Caching patterns, pub/sub, streams, and Redis clustering"},
                {"name": "Database Sharding Patterns", "type": "article", "url": "https://medium.com/system-design-blog/database-sharding", "description": "Hash-based vs range-based sharding, resharding, and hotspot mitigation"},
            ],
            "hard": [
                {"name": "Designing Data-Intensive Applications", "type": "book", "description": "Martin Kleppmann's definitive guide — transactions, replication, partitioning, and consensus"},
                {"name": "Jepsen.io Analyses", "type": "reference", "url": "https://jepsen.io/", "description": "Distributed systems correctness analysis — partition tolerance, consistency models, and failure modes"},
            ],
        },
        "security": {
            "easy": [
                {"name": "OWASP Top 10", "type": "reference", "url": "https://owasp.org/www-project-top-ten/", "description": "Top 10 web application security risks — injection, XSS, broken auth, and misconfig"},
                {"name": "CIS Benchmarks", "type": "reference", "url": "https://www.cisecurity.org/cis-benchmarks", "description": "Security configuration benchmarks for OS, cloud, and applications"},
            ],
            "medium": [
                {"name": "OWASP Web Security Testing Guide", "type": "tutorial", "url": "https://owasp.org/www-project-web-security-testing-guide/", "description": "Systematic web app testing — authentication, authorization, injection, and session management"},
                {"name": "OWASP API Security Top 10", "type": "reference", "url": "https://owasp.org/www-project-api-security/", "description": "API-specific risks — broken object-level auth, mass assignment, and rate limiting"},
                {"name": "Container Security Best Practices", "type": "guide", "url": "https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html", "description": "Image scanning, least privilege, network policies, and runtime security"},
            ],
            "hard": [
                {"name": "Threat Modeling with STRIDE", "type": "guide", "url": "https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats", "description": "Systematic threat identification — spoofing, tampering, repudiation, info disclosure, DoS, elevation"},
                {"name": "NIST Cybersecurity Framework", "type": "reference", "url": "https://www.nist.gov/cyberframework", "description": "Identify, protect, detect, respond, recover — enterprise security governance"},
            ],
        },
        "api": {
            "easy": [
                {"name": "RESTful API Design", "type": "guide", "url": "https://restfulapi.net/", "description": "REST principles — resources, verbs, status codes, and HATEOAS"},
                {"name": "OpenAPI Specification", "type": "reference", "url": "https://swagger.io/specification/", "description": "API description standard — schema, paths, parameters, and responses"},
            ],
            "medium": [
                {"name": "GraphQL Best Practices", "type": "guide", "url": "https://graphql.org/learn/best-practices/", "description": "Schema design, resolver patterns, N+1 problem, and pagination with connections"},
                {"name": "API Versioning Strategies", "type": "article", "url": "https://www.postman.com/api-platform/api-versioning/", "description": "URL path, header, query param versioning — tradeoffs and migration approaches"},
                {"name": "gRPC Fundamentals", "type": "tutorial", "url": "https://grpc.io/docs/what-is-grpc/", "description": "Protocol buffers, streaming, interceptors, and service definitions"},
            ],
            "hard": [
                {"name": "Designing Event-Driven APIs", "type": "guide", "url": "https://microservices.io/patterns/data/event-sourcing.html", "description": "Event sourcing, CQRS, saga patterns, and eventual consistency in distributed systems"},
                {"name": "API Gateway Patterns", "type": "article", "url": "https://microservices.io/patterns/apigateway.html", "description": "Request routing, composition, rate limiting, and authentication at the edge"},
            ],
        },
        "behavioral": {
            "easy": [
                {"name": "Tell me about yourself", "type": "behavioral", "description": "2-minute pitch with key achievements — present, past, future framework"},
                {"name": "Why this company?", "type": "behavioral", "description": "Research company values, mission, recent news — connect to your career goals"},
                {"name": "Greatest strength", "type": "behavioral", "description": "Pick 2-3 relevant strengths with specific evidence — avoid generic answers"},
            ],
            "medium": [
                {"name": "Describe a conflict", "type": "behavioral", "description": "STAR method — focus on resolution, compromise, and what you learned about collaboration"},
                {"name": "Tell me about a failure", "type": "behavioral", "description": "Emphasize learning and growth — show self-awareness and how you changed your approach"},
                {"name": "Describe a challenging project", "type": "behavioral", "description": "Technical depth + business impact — walk through decisions, tradeoffs, and outcomes"},
                {"name": "How do you handle deadlines?", "type": "behavioral", "description": "Prioritization frameworks, communication, and trade-off decisions under pressure"},
            ],
            "hard": [
                {"name": "Describe leading without authority", "type": "behavioral", "description": "Influence through expertise and relationships — building consensus across teams"},
                {"name": "Tell me about a system you built", "type": "behavioral", "description": "Technical depth + business impact — architecture decisions, scaling challenges, and lessons"},
                {"name": "Describe a disagreement with your manager", "type": "behavioral", "description": "Professional pushback — data-driven arguments, understanding their perspective, and resolution"},
            ],
        },
        "python": {
            "easy": [
                {"name": "Python Context Managers", "type": "concept", "description": "with statements, __enter__/__exit__, contextlib utilities for resource management"},
                {"name": "Python Generators", "type": "concept", "description": "yield, generator expressions, memory-efficient data processing pipelines"},
                {"name": "Python Decorators", "type": "concept", "description": "@syntax, higher-order functions, functools.wraps, and common patterns"},
            ],
            "medium": [
                {"name": "Python Async/Await", "type": "concept", "description": "asyncio, event loop, coroutines, and concurrent task patterns"},
                {"name": "Python Type System", "type": "concept", "description": "Type hints, generics, Protocol, TypeVar, and runtime type checking"},
                {"name": "Python Testing", "type": "concept", "description": "pytest, fixtures, parametrize, mocking, and test organization patterns"},
            ],
            "hard": [
                {"name": "Python Metaclasses", "type": "concept", "description": "Class creation hooks, __new__ vs __init__, and metaclass conflicts"},
                {"name": "Python Concurrency", "type": "concept", "description": "threading vs multiprocessing vs asyncio — GIL implications and when to use each"},
            ],
        },
        "javascript": {
            "easy": [
                {"name": "JS Promises & Async/Await", "type": "concept", "description": "Event loop, microtasks vs macrotasks, and error handling patterns"},
                {"name": "JS Closures", "type": "concept", "description": "Lexical scoping, factory functions, and memory implications"},
                {"name": "JS Prototypes", "type": "concept", "description": "Prototype chain, inheritance, and __proto__ vs prototype"},
            ],
            "medium": [
                {"name": "React Hooks", "type": "concept", "description": "useState, useEffect, useCallback, useMemo, and custom hooks patterns"},
                {"name": "TypeScript Generics", "type": "concept", "description": "Generic functions, constraints, conditional types, and mapped types"},
                {"name": "Node.js Streams", "type": "concept", "description": "Readable, writable, transform streams, and backpressure handling"},
            ],
            "hard": [
                {"name": "JS Engine Internals", "type": "concept", "description": "V8 optimization, hidden classes, inline caching, and garbage collection"},
                {"name": "Webpack & Bundling", "type": "concept", "description": "Code splitting, tree shaking, lazy loading, and module federation"},
            ],
        },
        "go": {
            "easy": [
                {"name": "Go Concurrency", "type": "concept", "description": "Goroutines, channels, select statement, and concurrency patterns"},
                {"name": "Go Interfaces", "type": "concept", "description": "Implicit interfaces, composition, and the empty interface pattern"},
            ],
            "medium": [
                {"name": "Go Context Package", "type": "concept", "description": "Cancellation, timeouts, values — controlling goroutine lifecycles"},
                {"name": "Go Testing Patterns", "type": "concept", "description": "table-driven tests, benchmarks, test helpers, and race detection"},
            ],
            "hard": [
                {"name": "Go Memory Model", "type": "concept", "description": "Happens-before, memory ordering, and sync primitives guarantees"},
            ],
        },
        "java": {
            "easy": [
                {"name": "Java Collections Framework", "type": "concept", "description": "List, Set, Map implementations — choosing the right collection for the job"},
                {"name": "Java Streams API", "type": "concept", "description": "Stream operations, collectors, parallel streams, and common patterns"},
            ],
            "medium": [
                {"name": "Java Concurrency", "type": "concept", "description": "ExecutorService, CompletableFuture, concurrent collections, and thread safety"},
                {"name": "Spring Boot Fundamentals", "type": "concept", "description": "Auto-configuration, dependency injection, actuator, and testing"},
            ],
            "hard": [
                {"name": "JVM Internals", "type": "concept", "description": "Class loading, JIT compilation, garbage collection tuning, and memory model"},
            ],
        },
        "ml": {
            "easy": [
                {"name": "Scikit-learn Tutorials", "type": "tutorial", "url": "https://scikit-learn.org/stable/tutorial/", "description": "Supervised learning basics — classification, regression, and model evaluation"},
                {"name": "Google ML Crash Course", "type": "tutorial", "url": "https://developers.google.com/machine-learning/crash-course", "description": "Foundational ML concepts — loss functions, gradient descent, and regularization"},
            ],
            "medium": [
                {"name": "PyTorch Tutorials", "type": "tutorial", "url": "https://pytorch.org/tutorials/", "description": "Neural network fundamentals — tensors, autograd, training loops, and transfer learning"},
                {"name": "Feature Engineering", "type": "guide", "url": "https://www.featurerose.com/", "description": "Feature selection, transformation, encoding, and handling missing data"},
            ],
            "hard": [
                {"name": "Transformers from Scratch", "type": "tutorial", "url": "https://jalammar.github.io/illustrated-transformer/", "description": "Self-attention, positional encoding, multi-head attention, and encoder-decoder architecture"},
                {"name": "MLOps Practices", "type": "guide", "url": "https://ml-ops.org/", "description": "Model versioning, monitoring, A/B testing, and continuous training pipelines"},
            ],
        },
        "cpp": {
            "easy": [
                {"name": "C++ Smart Pointers", "type": "concept", "description": "unique_ptr, shared_ptr, weak_ptr — ownership semantics and RAII"},
                {"name": "C++ STL Containers", "type": "concept", "description": "vector, map, unordered_map — choosing the right container and complexity guarantees"},
            ],
            "medium": [
                {"name": "C++ Move Semantics", "type": "concept", "description": "rvalue references, std::move, perfect forwarding, and return value optimization"},
                {"name": "C++ Templates", "type": "concept", "description": "Function templates, class templates, SFINAE, and C++20 concepts"},
            ],
            "hard": [
                {"name": "C++ Memory Model", "type": "concept", "description": "Atomics, memory ordering, lock-free programming, and data race prevention"},
            ],
        },
        "rust": {
            "easy": [
                {"name": "Rust Ownership", "type": "concept", "description": "Ownership rules, borrowing, lifetimes — the core of Rust's memory safety"},
                {"name": "Rust Error Handling", "type": "concept", "description": "Result<T,E>, Option<T>, the ? operator, and error propagation patterns"},
            ],
            "medium": [
                {"name": "Rust Traits", "type": "concept", "description": "Trait definitions, implementations, trait objects, and trait bounds"},
                {"name": "Rust Concurrency", "type": "concept", "description": "Send/Sync traits, channels, async/await with tokio, and fearless concurrency"},
            ],
            "hard": [
                {"name": "Rust Unsafe", "type": "concept", "description": "Unsafe Rust — when you need it, raw pointers, and maintaining safety invariants"},
            ],
        },
    }

    @classmethod
    def get_resources(
        cls,
        category: str,
        difficulty: str,
        count: int = 3
    ) -> List[Dict]:
        """Get random resources for a category/difficulty"""
        cat_data = cls.RESOURCES.get(category, {})

        # Check if this category has difficulty-level structure (dict of lists)
        if isinstance(cat_data, dict) and difficulty in cat_data:
            resources = cat_data[difficulty]
        elif isinstance(cat_data, list):
            # Flat list (legacy language resources)
            resources = cat_data
        else:
            resources = []

        # Fallback: try any difficulty for this category
        if not resources and isinstance(cat_data, dict):
            for diff in ["easy", "medium", "hard"]:
                if diff in cat_data and cat_data[diff]:
                    resources = cat_data[diff]
                    break

        if not resources:
            return []

        if len(resources) <= count:
            return resources
        return random.sample(resources, count)


class StudyPlanGenerator:
    """
    Generate personalized study plans based on cognitive graph data.
    """

    def __init__(self):
        self.scheduler = SpacedRepetitionScheduler()
        self.resource_lib = ResourceLibrary()
        self.jd_analyzer = JDAnalyzer()

    def generate_plan(
        self,
        user_id: str,
        days: int = 30,
        daily_minutes: int = 60,
        cognitive_graph_data: Optional[Dict] = None,
        target_role: Optional[str] = None,
        target_company: Optional[str] = None,
        job_description: Optional[str] = None,
        current_skills: Optional[List[str]] = None,
    ) -> StudyPlan:
        """
        Generate a complete study plan for a user.

        Args:
            user_id: User identifier
            days: Plan duration in days
            daily_minutes: Target study time per day
            cognitive_graph_data: Optional pre-fetched graph data
            target_role: Target job role (e.g., "Senior DevOps Engineer")
            target_company: Target company (e.g., "Google")
            job_description: Job description text for skill extraction
            current_skills: List of skills the user already has

        Returns:
            Complete StudyPlan object
        """
        start_date = datetime.now()

        # Determine if we're generating a personalized or generic plan
        is_personalized = bool(target_role or job_description or target_company)

        # Identify weak areas from all available sources
        weak_areas = self._identify_personalized_weak_areas(
            cognitive_graph_data=cognitive_graph_data,
            target_role=target_role,
            target_company=target_company,
            job_description=job_description,
            current_skills=current_skills or [],
        )
        strong_areas = self._identify_strong_areas(cognitive_graph_data)

        # Compute skill gaps from JD vs current skills
        skill_gaps = self._compute_skill_gaps(job_description, current_skills or [])

        # Get company-specific practice questions
        company_questions = self._get_company_questions(target_company, target_role)

        # Generate tasks based on weak areas and company questions
        tasks = self._generate_personalized_tasks(
            weak_areas, company_questions, days
        )

        # Distribute tasks into daily sessions (no more "Rest Day" on day 1)
        sessions = self._build_daily_sessions(tasks, start_date, days, daily_minutes)

        # Generate milestones with weekly goals
        milestones = self._generate_milestones(sessions, weak_areas)

        # Calculate totals
        total_tasks = len(tasks)

        # Track what data sources informed this plan
        personalization_context = {
            "sources": [],
            "weak_area_count": len(weak_areas),
            "skill_gap_count": len(skill_gaps),
            "task_count": total_tasks,
            "session_count": len(sessions),
        }
        if cognitive_graph_data:
            personalization_context["sources"].append("cognitive_graph")
        if target_role:
            personalization_context["sources"].append("target_role")
            personalization_context["role"] = target_role
        if job_description:
            personalization_context["sources"].append("job_description")
        if target_company:
            personalization_context["sources"].append("company_focus")
            personalization_context["company"] = target_company
        if current_skills:
            personalization_context["sources"].append("current_skills")
            personalization_context["known_skills_count"] = len(current_skills)
        if not personalization_context["sources"]:
            personalization_context["sources"].append("defaults")

        return StudyPlan(
            user_id=user_id,
            created_at=start_date,
            duration_days=days,
            sessions=sessions,
            weak_areas=weak_areas,
            strong_areas=strong_areas,
            milestones=milestones,
            total_tasks=total_tasks,
            completed_tasks=0,
            progress_percentage=0.0,
            target_role=target_role,
            target_company=target_company,
            skill_gaps=skill_gaps,
            plan_type="personalized" if is_personalized else "generic",
            personalization_context=personalization_context,
        )

    def _identify_weak_areas(
        self,
        graph_data: Optional[Dict]
    ) -> List[Dict]:
        """Identify weak areas from cognitive graph data"""
        weak_areas = []

        if graph_data and "skills" in graph_data:
            for skill in graph_data["skills"]:
                confidence = skill.get("confidence", 1.0)
                if confidence < 0.5:
                    weak_areas.append({
                        "name": skill.get("name"),
                        "confidence": confidence,
                        "mentions": skill.get("mentions", 0),
                        "category": self._categorize_skill(skill.get("name", ""))
                    })
        # If no graph data, return empty — role patterns or JD will fill in
        # (Generic defaults like "Dynamic Programming" aren't relevant to most roles)

        # Sort by confidence (lowest first)
        weak_areas.sort(key=lambda x: x["confidence"])
        return weak_areas

    def _identify_strong_areas(
        self,
        graph_data: Optional[Dict]
    ) -> List[Dict]:
        """Identify strong areas from cognitive graph data"""
        strong_areas = []

        if graph_data and "skills" in graph_data:
            for skill in graph_data["skills"]:
                confidence = skill.get("confidence", 0.0)
                if confidence >= 0.7:
                    strong_areas.append({
                        "name": skill.get("name"),
                        "confidence": confidence,
                        "mentions": skill.get("mentions", 0)
                    })

        return strong_areas

    def _identify_personalized_weak_areas(
        self,
        cognitive_graph_data: Optional[Dict],
        target_role: Optional[str] = None,
        target_company: Optional[str] = None,
        job_description: Optional[str] = None,
        current_skills: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Merge weak area data from multiple sources:
        1. Cognitive graph (if available)
        2. Skill gaps from JD vs current skills
        3. Company-specific focus areas
        4. Role-pattern defaults
        """
        all_weak_areas = []

        # Source 1: Cognitive graph (only if real data provided)
        graph_weak = self._identify_weak_areas(cognitive_graph_data)
        for area in graph_weak:
            area["source"] = area.get("source", "cognitive_graph")
            all_weak_areas.append(area)

        # Source 2: JD skill extraction + gap analysis
        if job_description:
            jd_skills = self.jd_analyzer.extract_skills(job_description)
            current_lower = [s.lower() for s in (current_skills or [])]
            for skill in jd_skills:
                skill_name_lower = skill["name"].lower()
                already_known = any(
                    cs in skill_name_lower or skill_name_lower in cs
                    for cs in current_lower
                ) if current_lower else False
                if already_known:
                    # Boost confidence for known skills (they're not weak)
                    skill["confidence"] = min(skill["confidence"] + 0.4, 0.95)
                    skill["status"] = "strengthen"
                else:
                    skill["status"] = "learn"
                skill["source"] = "job_description"
                all_weak_areas.append(skill)

        # Source 3: Role-pattern derived defaults — ALWAYS use when role is specified
        # This ensures role-relevant content even when JD is also provided
        if target_role:
            role_weak = self._get_role_weak_areas(target_role)
            all_weak_areas.extend(role_weak)

        # Source 4: Company-specific focus areas
        if target_company:
            company_focus = self._get_company_focus_areas(target_company)
            all_weak_areas.extend(company_focus)

        # If absolutely nothing, use generic defaults
        if not all_weak_areas:
            all_weak_areas = [
                {"name": "System Design", "confidence": 0.4, "category": "system_design", "source": "defaults"},
                {"name": "Algorithms", "confidence": 0.5, "category": "algorithms", "source": "defaults"},
                {"name": "Behavioral Questions", "confidence": 0.5, "category": "behavioral", "source": "defaults"},
            ]

        # Deduplicate: merge same-named skills, keep lowest confidence
        merged = self._merge_weak_areas(all_weak_areas)

        # Filter out skills the user already knows well (confidence >= 0.8)
        # These shouldn't consume study time
        merged = [a for a in merged if a.get("confidence", 0) < 0.8]

        # Sort by confidence (weakest first) and cap at 12
        merged.sort(key=lambda x: x.get("confidence", 0.5))
        return merged[:12]

    def _compute_skill_gaps(
        self,
        job_description: Optional[str],
        current_skills: List[str],
    ) -> List[Dict]:
        """Compare JD requirements against current skills to identify gaps"""
        if not job_description:
            return []

        jd_skills = self.jd_analyzer.extract_skills(job_description)
        current_lower = [s.lower() for s in current_skills]

        gaps = []
        for skill in jd_skills:
            skill_name_lower = skill["name"].lower()
            already_known = any(
                cs in skill_name_lower or skill_name_lower in cs
                for cs in current_lower
            ) if current_lower else False

            gap_score = 0.0 if already_known else skill.get("confidence", 0.5)

            gaps.append({
                "skill": skill["name"],
                "category": skill["category"],
                "required": True,
                "current_level": "known" if already_known else "gap",
                "gap_score": round(gap_score, 2),
                "gap_percentage": round(gap_score * 100) if not already_known else 0,
                "recommended_hours": round(gap_score * 20) if not already_known else 0,
                "priority": "high" if gap_score >= 0.7 else "medium" if gap_score >= 0.4 else "low",
                "proficiency": "intermediate" if already_known else "none",
                "source": "job_description",
            })

        # Sort by gap score (biggest gaps first)
        gaps.sort(key=lambda x: x["gap_score"], reverse=True)
        return gaps[:15]

    def _get_role_weak_areas(self, role: str) -> List[Dict]:
        """Generate default weak areas based on target role"""
        role_lower = role.lower()

        # Role-to-category mapping with sub_topics for richer task generation
        role_patterns = {
            "devops": [
                {"name": "CI/CD Pipelines", "confidence": 0.3, "category": "devops", "source": "role_pattern", "sub_topics": ["Jenkins Pipeline Configuration", "GitHub Actions Workflows", "ArgoCD GitOps Deployment", "Pipeline Security & Secrets"]},
                {"name": "Infrastructure as Code", "confidence": 0.35, "category": "devops", "source": "role_pattern", "sub_topics": ["Terraform Modules & State", "Ansible Playbooks", "CloudFormation Templates", "IaC Testing Strategies"]},
                {"name": "Container Orchestration", "confidence": 0.4, "category": "devops", "source": "role_pattern", "sub_topics": ["Kubernetes Pod & Deployment Config", "Helm Charts", "Container Networking (CNI)", "Cluster Autoscaling"]},
                {"name": "Monitoring & Observability", "confidence": 0.45, "category": "devops", "source": "role_pattern", "sub_topics": ["Prometheus & Grafana Setup", "Distributed Tracing (Jaeger)", "Log Aggregation (ELK Stack)", "SLO/SLI Definition"]},
                {"name": "Cloud Infrastructure", "confidence": 0.5, "category": "cloud", "source": "role_pattern", "sub_topics": ["AWS VPC & IAM", "GCP Compute & Storage", "Serverless Architecture", "Cost Optimization"]},
                {"name": "Security & Compliance", "confidence": 0.55, "category": "security", "source": "role_pattern", "sub_topics": ["RBAC & Secrets Management", "Container Image Scanning", "Network Policies & Firewalls", "Compliance Automation"]},
                {"name": "System Design for Scale", "confidence": 0.4, "category": "system_design", "source": "role_pattern", "sub_topics": ["Load Balancer Strategies", "Caching Patterns", "Database Sharding & Replication", "Message Queue Architecture"]},
                {"name": "Algorithms & Problem Solving", "confidence": 0.5, "category": "algorithms", "source": "role_pattern", "sub_topics": ["Graph Traversal (BFS/DFS)", "Heap & Priority Queue Patterns", "Dynamic Programming Fundamentals", "String Manipulation Patterns"]},
            ],
            "frontend": [
                {"name": "React/Vue Performance", "confidence": 0.3, "category": "javascript", "source": "role_pattern", "sub_topics": ["React Hooks Deep Dive", "State Management Patterns", "React Performance Optimization", "Server Components (RSC)"]},
                {"name": "CSS Architecture", "confidence": 0.35, "category": "javascript", "source": "role_pattern", "sub_topics": ["CSS Grid & Flexbox Mastery", "Responsive Design Patterns", "CSS Custom Properties & Theming", "Animation & Transitions"]},
                {"name": "Web Accessibility", "confidence": 0.4, "category": "javascript", "source": "role_pattern", "sub_topics": ["ARIA Labels & Roles", "Keyboard Navigation", "Screen Reader Compatibility", "WCAG 2.1 Guidelines"]},
                {"name": "State Management", "confidence": 0.45, "category": "javascript", "source": "role_pattern", "sub_topics": ["Redux/Zustand Patterns", "Context API Best Practices", "Server State vs Client State", "Optimistic Updates"]},
                {"name": "TypeScript Mastery", "confidence": 0.5, "category": "javascript", "source": "role_pattern", "sub_topics": ["Generics & Utility Types", "Type Guards & Narrowing", "Module Declaration Files", "Strict Mode Patterns"]},
                {"name": "Testing & Quality", "confidence": 0.5, "category": "javascript", "source": "role_pattern", "sub_topics": ["Jest Unit Testing", "Cypress E2E Testing", "Testing Library Patterns", "CI/CD for Frontend"]},
                {"name": "System Design for Frontend", "confidence": 0.4, "category": "system_design", "source": "role_pattern", "sub_topics": ["Component Architecture", "API Design for SPAs", "Caching Strategies (CDN/SW)", "Micro-Frontends"]},
                {"name": "Algorithms", "confidence": 0.5, "category": "algorithms", "source": "role_pattern", "sub_topics": ["Two Pointer Technique", "Sliding Window Pattern", "Tree Traversal", "Dynamic Programming Basics"]},
            ],
            "backend": [
                {"name": "System Design", "confidence": 0.3, "category": "system_design", "source": "role_pattern", "sub_topics": ["Load Balancing & Proxies", "Database Sharding", "Caching Strategies", "Microservices Communication"]},
                {"name": "Database Optimization", "confidence": 0.35, "category": "databases", "source": "role_pattern", "sub_topics": ["SQL Query Optimization & EXPLAIN", "Indexing Strategies", "Connection Pooling", "Transaction Isolation Levels"]},
                {"name": "API Design", "confidence": 0.4, "category": "api", "source": "role_pattern", "sub_topics": ["REST API Best Practices", "GraphQL Schema Design", "API Versioning Strategies", "Rate Limiting & Throttling"]},
                {"name": "Algorithms", "confidence": 0.45, "category": "algorithms", "source": "role_pattern", "sub_topics": ["Graph Traversal", "Dynamic Programming", "Binary Search Patterns", "Heap & Priority Queue"]},
                {"name": "Concurrency & Parallelism", "confidence": 0.5, "category": "algorithms", "source": "role_pattern", "sub_topics": ["Thread Safety & Locks", "Async Programming Patterns", "Race Conditions & Deadlocks", "Producer-Consumer Pattern"]},
                {"name": "Security Fundamentals", "confidence": 0.5, "category": "security", "source": "role_pattern", "sub_topics": ["Authentication Patterns (JWT/OAuth)", "Input Validation & Sanitization", "HTTPS & TLS", "OWASP Top 10 for APIs"]},
                {"name": "Caching & Performance", "confidence": 0.55, "category": "system_design", "source": "role_pattern", "sub_topics": ["Redis Patterns", "CDN Configuration", "Application-Level Caching", "Query Result Caching"]},
                {"name": "Behavioral Questions", "confidence": 0.5, "category": "behavioral", "source": "role_pattern", "sub_topics": ["System Design Tradeoffs", "Debugging Production Issues", "Technical Decision Making", "Cross-team Collaboration"]},
            ],
            "fullstack": [
                {"name": "System Design", "confidence": 0.3, "category": "system_design", "source": "role_pattern", "sub_topics": ["End-to-End Architecture", "Database Sharding & Replication", "Caching Layers", "API Gateway Patterns"]},
                {"name": "Algorithms", "confidence": 0.35, "category": "algorithms", "source": "role_pattern", "sub_topics": ["Array & String Patterns", "Tree & Graph Traversal", "Dynamic Programming", "Hash Map Techniques"]},
                {"name": "API Design", "confidence": 0.4, "category": "api", "source": "role_pattern", "sub_topics": ["REST Best Practices", "GraphQL vs REST", "Authentication & Authorization", "Error Handling Patterns"]},
                {"name": "Frontend Performance", "confidence": 0.45, "category": "javascript", "source": "role_pattern", "sub_topics": ["Bundle Optimization", "Lazy Loading & Code Splitting", "Web Vitals (LCP/FID/CLS)", "SSR vs CSR Tradeoffs"]},
                {"name": "Database Design", "confidence": 0.45, "category": "databases", "source": "role_pattern", "sub_topics": ["Schema Design", "Indexing Strategies", "Query Optimization", "Data Migration Patterns"]},
                {"name": "DevOps Basics", "confidence": 0.5, "category": "devops", "source": "role_pattern", "sub_topics": ["Docker Fundamentals", "CI/CD Pipeline Setup", "Basic Kubernetes", "Environment Configuration"]},
                {"name": "Behavioral Questions", "confidence": 0.5, "category": "behavioral", "source": "role_pattern", "sub_topics": ["STAR Method", "Technical Leadership", "Handling Ambiguity", "Cross-functional Communication"]},
            ],
            "data": [
                {"name": "SQL Optimization", "confidence": 0.3, "category": "databases", "source": "role_pattern", "sub_topics": ["Window Functions", "CTEs & Subqueries", "Query Optimization & EXPLAIN", "Indexing Strategies"]},
                {"name": "Statistical Analysis", "confidence": 0.35, "category": "ml", "source": "role_pattern", "sub_topics": ["Hypothesis Testing", "A/B Testing Frameworks", "Regression Analysis", "Probability Distributions"]},
                {"name": "Data Pipeline Design", "confidence": 0.4, "category": "system_design", "source": "role_pattern", "sub_topics": ["ETL vs ELT Patterns", "Stream Processing (Kafka)", "Data Warehouse Architecture", "Data Quality & Validation"]},
                {"name": "Python for Data", "confidence": 0.45, "category": "python", "source": "role_pattern", "sub_topics": ["Pandas & NumPy", "Data Visualization (Matplotlib/Seaborn)", "Jupyter Notebook Best Practices", "Async Data Processing"]},
                {"name": "Algorithms", "confidence": 0.5, "category": "algorithms", "source": "role_pattern", "sub_topics": ["Sorting & Searching", "Dynamic Programming", "Graph Algorithms", "Probability & Combinatorics"]},
                {"name": "Machine Learning Basics", "confidence": 0.5, "category": "ml", "source": "role_pattern", "sub_topics": ["Supervised vs Unsupervised Learning", "Model Evaluation (Precision/Recall)", "Feature Engineering", "Overfitting & Regularization"]},
            ],
            "security": [
                {"name": "OWASP Top 10", "confidence": 0.3, "category": "security", "source": "role_pattern", "sub_topics": ["Injection Attacks", "Broken Authentication", "XSS Prevention", "Security Misconfiguration"]},
                {"name": "Network Security", "confidence": 0.35, "category": "security", "source": "role_pattern", "sub_topics": ["TCP/IP Fundamentals", "Firewall Configuration", "VPN & Tunneling", "Network Monitoring"]},
                {"name": "Cryptography", "confidence": 0.4, "category": "security", "source": "role_pattern", "sub_topics": ["Symmetric vs Asymmetric Encryption", "Hashing & Salting", "TLS/SSL Handshake", "Key Management"]},
                {"name": "Authentication & Authorization", "confidence": 0.45, "category": "security", "source": "role_pattern", "sub_topics": ["OAuth2 & OIDC", "JWT Security", "RBAC vs ABAC", "Session Management"]},
                {"name": "Cloud Security", "confidence": 0.5, "category": "cloud", "source": "role_pattern", "sub_topics": ["AWS IAM Best Practices", "Cloud Security Posture Management", "Infrastructure Security", "Compliance Frameworks"]},
                {"name": "Incident Response", "confidence": 0.5, "category": "security", "source": "role_pattern", "sub_topics": ["Threat Modeling", "Forensic Analysis", "Incident Handling Process", "Security Monitoring & Alerting"]},
            ],
            "mobile": [
                {"name": "Mobile Architecture", "confidence": 0.3, "category": "system_design", "source": "role_pattern", "sub_topics": ["App Architecture Patterns (MVVM/MVI)", "Offline-First Design", "Push Notification Architecture", "Deep Linking"]},
                {"name": "Performance Optimization", "confidence": 0.35, "category": "algorithms", "source": "role_pattern", "sub_topics": ["Memory Management", "Battery Optimization", "Network Caching", "Startup Time Optimization"]},
                {"name": "Platform-Specific APIs", "confidence": 0.4, "category": "algorithms", "source": "role_pattern", "sub_topics": ["iOS UIKit / SwiftUI", "Android Jetpack Compose", "Platform Channels (Flutter)", "Native Module Integration"]},
                {"name": "Testing & CI/CD", "confidence": 0.45, "category": "devops", "source": "role_pattern", "sub_topics": ["Unit & Widget Testing", "Integration Testing", "Fastlane Deployment", "Mobile CI/CD Pipelines"]},
                {"name": "Behavioral Questions", "confidence": 0.5, "category": "behavioral", "source": "role_pattern", "sub_topics": ["Cross-functional Collaboration", "App Store Review Process", "Handling Technical Debt", "User-Centered Design Decisions"]},
            ],
        }

        # Find matching pattern
        for key, areas in role_patterns.items():
            if key in role_lower:
                return areas

        # Default: return backend pattern for unknown roles
        return [
            {"name": "System Design", "confidence": 0.3, "category": "system_design", "source": "role_pattern", "sub_topics": ["Load Balancing", "Caching Strategies", "Database Sharding", "Microservices Communication"]},
            {"name": "Algorithms", "confidence": 0.4, "category": "algorithms", "source": "role_pattern", "sub_topics": ["Two Pointer Technique", "Sliding Window", "BFS/DFS", "Dynamic Programming Basics"]},
            {"name": "Behavioral Questions", "confidence": 0.5, "category": "behavioral", "source": "role_pattern", "sub_topics": ["STAR Method Practice", "Leadership Examples", "Handling Failure Stories", "Technical Decision Making"]},
        ]

    def _get_company_focus_areas(self, company: str) -> List[Dict]:
        """Get company-specific focus areas from predictive interview data"""
        if not company:
            return []

        try:
            from predictive_interview import predictive_interview
            predictions = predictive_interview.get_company_predictions(company, num_questions=5)
            areas = []
            seen_categories = set()
            for pred in predictions.get("predictions", []):
                cat = pred.get("category", "behavioral")
                if cat not in seen_categories:
                    seen_categories.add(cat)
                    areas.append({
                        "name": f"{company} {cat.replace('_', ' ').title()}",
                        "confidence": 1.0 - pred.get("likelihood", 0.5),
                        "category": cat,
                        "source": "company_focus",
                        "company": company,
                    })
            return areas
        except (ImportError, Exception):
            logger.warning("[StudyPlan] Predictive interview module not available for company focus")
            return []

    def _get_company_questions(self, company: Optional[str], role: Optional[str]) -> List[Dict]:
        """Get company-specific practice questions from predictive interview module"""
        if not company:
            return []

        try:
            from predictive_interview import predictive_interview
            predictions = predictive_interview.get_company_predictions(company, num_questions=8)
            questions = []
            for pred in predictions.get("predictions", []):
                questions.append({
                    "question": pred.get("question", f"Practice {company} interview question"),
                    "category": pred.get("category", "behavioral"),
                    "difficulty": pred.get("difficulty", "medium"),
                    "likelihood": pred.get("likelihood", 0.5),
                    "source": "company_specific",
                    "company": company,
                })
            return questions
        except (ImportError, Exception):
            logger.warning("[StudyPlan] Predictive interview module not available for company questions")
            return []

    def _merge_weak_areas(self, areas: List[Dict]) -> List[Dict]:
        """Merge duplicate weak areas, keeping lowest confidence"""
        merged = {}
        for area in areas:
            key = (area.get("category", ""), area.get("name", "").lower())
            if key in merged:
                # Keep the one with lower confidence (weaker = higher priority)
                if area.get("confidence", 1.0) < merged[key].get("confidence", 1.0):
                    merged[key] = area
                # Merge mentions
                merged[key]["mentions"] = max(
                    merged[key].get("mentions", 0),
                    area.get("mentions", 0)
                )
            else:
                merged[key] = dict(area)
        return list(merged.values())

    DESCRIPTION_TEMPLATES = {
        "algorithms": {
            "easy": "Practice the {topic} pattern — start with 2-3 easy problems, focusing on identifying when to apply this technique.",
            "medium": "Deep-dive into {topic} — solve 3 medium problems, then explain the time/space tradeoffs for each solution.",
            "hard": "Master {topic} at interview level — tackle 2 hard problems combining this pattern with other techniques, then mock-explain your approach.",
        },
        "system_design": {
            "easy": "Study {topic} fundamentals — draw architecture diagrams and list the key components, tradeoffs, and failure modes.",
            "medium": "Design a system emphasizing {topic} — practice whiteboarding a system with this pattern, covering scaling from 1K to 10M users.",
            "hard": "Design a production-grade system centered on {topic} — address fault tolerance, data consistency, monitoring, and cost optimization.",
        },
        "devops": {
            "easy": "Set up a local {topic} environment — follow a hands-on tutorial, then document the key configuration decisions you made.",
            "medium": "Build a multi-stage {topic} pipeline — implement this in a side project with proper error handling and rollback strategies.",
            "hard": "Architect an enterprise {topic} solution — design for multi-team usage, security hardening, and disaster recovery.",
        },
        "cloud": {
            "easy": "Explore {topic} fundamentals — complete a hands-on lab, then summarize the key pricing and scaling considerations.",
            "medium": "Build a production-ready {topic} setup — implement monitoring, IAM policies, and cost alerts in a side project.",
            "hard": "Architect a multi-region {topic} deployment — address high availability, failover, and compliance requirements.",
        },
        "databases": {
            "easy": "Practice {topic} basics — write 5 queries, then verify execution plans using EXPLAIN.",
            "medium": "Optimize {topic} in a real scenario — design a schema, write queries, then benchmark and tune for performance.",
            "hard": "Design a {topic} strategy for a high-throughput system — handle sharding, replication lag, and failover.",
        },
        "security": {
            "easy": "Review {topic} concepts — study common attack vectors and list 3 mitigation strategies for each.",
            "medium": "Implement {topic} in a sample application — then run a vulnerability scan and fix all findings.",
            "hard": "Design a {topic} strategy for an enterprise system — cover threat modeling, detection, and incident response.",
        },
        "api": {
            "easy": "Study {topic} principles — build a simple API endpoint and test it with curl and a REST client.",
            "medium": "Design a {topic} for a multi-client application — handle versioning, pagination, error formats, and rate limiting.",
            "hard": "Architect a {topic} for a high-traffic platform — cover authentication, caching, throttling, and backwards compatibility.",
        },
        "behavioral": {
            "easy": "Prepare a STAR-format story demonstrating {topic} — write it out and practice telling it in under 2 minutes.",
            "medium": "Develop 2-3 stories around {topic} covering different scenarios — practice adapting them to different question phrasings.",
            "hard": "Mock-interview practice for {topic} — have a friend ask unexpected follow-ups and practice staying composed.",
        },
        "python": {
            "easy": "Practice {topic} in Python — write a small script or module, then review against Python best practices (PEP 8, type hints).",
            "medium": "Build a Python project using {topic} — add tests, error handling, and document design decisions.",
            "hard": "Design a production Python system centered on {topic} — address performance, testing, deployment, and observability.",
        },
        "javascript": {
            "easy": "Practice {topic} in JS — build a small component or utility, then review against modern ES6+ patterns.",
            "medium": "Build a JS project using {topic} — add unit tests, handle edge cases, and optimize for performance.",
            "hard": "Architect a production JS system centered on {topic} — cover bundling, testing, CI/CD, and monitoring.",
        },
    }

    def _generate_actionable_description(self, topic, category, difficulty, parent_area=None):
        """Generate a specific, actionable description for a study task."""
        templates = self.DESCRIPTION_TEMPLATES.get(category, self.DESCRIPTION_TEMPLATES.get("algorithms", {}))
        template = templates.get(difficulty, "Study {topic} at {difficulty} level — focus on understanding core concepts and practical application.")
        return template.format(topic=topic, difficulty=difficulty)

    def _generate_personalized_tasks(
        self,
        weak_areas: List[Dict],
        company_questions: List[Dict],
        days: int
    ) -> List[StudyTask]:
        """Generate personalized tasks with sub-topic decomposition and actionable descriptions"""
        tasks = []
        task_id = 0
        # Scale task count to plan duration: ~3 tasks/day for short plans, ~2/day for longer
        target_count = max(days * 3, 20)
        target_count = min(target_count, 150)  # Cap at 150

        # Part A: Weak area tasks with sub-topic decomposition
        for area in weak_areas[:12]:
            category = area["category"]
            confidence = area["confidence"]
            area_name = area.get("name", "Unknown")
            sub_topics = area.get("sub_topics", [])
            source_tag = ""
            if area.get("source") == "company_focus":
                source_tag = f" ({area.get('company', '')})"

            # Determine difficulty progression based on confidence
            if confidence < 0.3:
                diff_cycle = ["easy", "easy", "medium", "medium", "hard"]
            elif confidence < 0.5:
                diff_cycle = ["easy", "medium", "medium", "hard", "hard"]
            else:
                diff_cycle = ["medium", "medium", "hard", "hard", "hard"]

            if sub_topics:
                # One task per sub-topic, cycling difficulties
                for i, sub_topic in enumerate(sub_topics):
                    if len(tasks) >= target_count:
                        break
                    difficulty = diff_cycle[i % len(diff_cycle)]
                    task_id += 1
                    resources = self.resource_lib.get_resources(category, difficulty, 2)
                    description = self._generate_actionable_description(sub_topic, category, difficulty, area_name)

                    tasks.append(StudyTask(
                        id=f"task_{task_id:03d}",
                        title=f"{sub_topic}{source_tag}",
                        description=description,
                        category=category,
                        difficulty=difficulty,
                        estimated_minutes=self._estimate_time(difficulty),
                        resources=resources,
                        confidence_target=min(confidence + 0.2, 0.9),
                        parent_area=area_name,
                    ))
            else:
                # Fallback: generate 5 tasks with difficulty progression
                for difficulty in diff_cycle[:5]:
                    if len(tasks) >= target_count:
                        break
                    task_id += 1
                    resources = self.resource_lib.get_resources(category, difficulty, 2)
                    description = self._generate_actionable_description(area_name, category, difficulty)

                    tasks.append(StudyTask(
                        id=f"task_{task_id:03d}",
                        title=f"{area_name} - {difficulty.title()} Level{source_tag}",
                        description=description,
                        category=category,
                        difficulty=difficulty,
                        estimated_minutes=self._estimate_time(difficulty),
                        resources=resources,
                        confidence_target=min(confidence + 0.2, 0.9),
                        parent_area=area_name,
                    ))

        # Part B: Company-specific practice questions
        seen_questions = set()
        for q in company_questions[:8]:
            if len(tasks) >= target_count:
                break
            question_text = q.get("question", "")
            if question_text in seen_questions:
                continue
            seen_questions.add(question_text)
            task_id += 1
            difficulty = q.get("difficulty", "medium")
            category = q.get("category", "behavioral")

            tasks.append(StudyTask(
                id=f"task_{task_id:03d}",
                title=f"Practice: {question_text[:80]}{'...' if len(question_text) > 80 else ''}",
                description=f"Company-specific {category} question (likelihood: {q.get('likelihood', 0.5):.0%}). Prepare a structured answer using the STAR method.",
                category=category,
                difficulty=difficulty,
                estimated_minutes=self._estimate_time(difficulty),
                resources=[],
                confidence_target=0.8,
                parent_area=f"{q.get('company', 'Company')} Interview",
            ))

        # Part C: Supplemental tasks if below target — add practice tasks for role-relevant weak areas
        if len(tasks) < target_count:
            practice_types = ["Practice Problems", "Review & Recap", "Mock Interview Prep", "Hands-On Lab", "Deep Dive Reading"]
            # Only generate supplemental tasks for areas we actually need to study (low confidence)
            priority_areas = [a for a in weak_areas if a.get("confidence", 1.0) < 0.7]
            for area in priority_areas[:6]:
                if len(tasks) >= target_count:
                    break
                category = area["category"]
                area_name = area.get("name", "Unknown")
                sub_topics = area.get("sub_topics", [])
                # Use sub_topics for specific practice if available
                if sub_topics:
                    for st in sub_topics[:2]:
                        if len(tasks) >= target_count:
                            break
                        task_id += 1
                        difficulty = random.choice(["medium", "hard"])
                        description = self._generate_actionable_description(st, category, difficulty, area_name)
                        tasks.append(StudyTask(
                            id=f"task_{task_id:03d}",
                            title=f"{st} — Practice Session",
                            description=description,
                            category=category,
                            difficulty=difficulty,
                            estimated_minutes=self._estimate_time(difficulty),
                            resources=self.resource_lib.get_resources(category, difficulty, 1),
                            confidence_target=min(area.get("confidence", 0.5) + 0.3, 0.95),
                            parent_area=area_name,
                        ))
                else:
                    for pt in practice_types:
                        if len(tasks) >= target_count:
                            break
                        task_id += 1
                        difficulty = random.choice(["easy", "medium", "hard"])
                        description = self._generate_actionable_description(f"{area_name} {pt}", category, difficulty, area_name)
                        tasks.append(StudyTask(
                            id=f"task_{task_id:03d}",
                            title=f"{area_name}: {pt}",
                            description=description,
                            category=category,
                            difficulty=difficulty,
                            estimated_minutes=self._estimate_time(difficulty),
                            resources=self.resource_lib.get_resources(category, difficulty, 1),
                            confidence_target=min(area.get("confidence", 0.5) + 0.3, 0.95),
                            parent_area=area_name,
                        ))

        return tasks

    def _build_daily_sessions(
        self,
        tasks: List[StudyTask],
        start_date: datetime,
        days: int,
        daily_minutes: int = 60,
    ) -> List[StudySession]:
        """
        Distribute tasks across days sequentially, ensuring every day has content.
        Uses time-based budgeting to fit tasks within daily_minutes.
        """
        if not tasks:
            return []

        sessions = []
        total_tasks = len(tasks)
        task_idx = 0

        # Calculate how many tasks to aim for per day based on average task duration
        avg_task_minutes = sum(t.estimated_minutes for t in tasks) / max(total_tasks, 1)
        tasks_per_day = max(1, min(int(daily_minutes / max(avg_task_minutes, 20)), total_tasks // max(days, 1)))

        for day_num in range(1, days + 1):
            session_date = start_date + timedelta(days=day_num - 1)
            day_tasks = []
            total_minutes = 0

            # Add warm-up review from previous day's focus task (10 min)
            if day_num > 1 and sessions:
                prev_session = sessions[-1]
                if prev_session.tasks:
                    # Find the focus task from yesterday for review
                    review_orig = None
                    for t in prev_session.tasks:
                        if t.is_focus and not t.id.startswith("review_"):
                            review_orig = t
                            break
                    if not review_orig:
                        review_orig = [t for t in prev_session.tasks if not t.id.startswith("review_")]
                        review_orig = review_orig[0] if review_orig else prev_session.tasks[0]

                    review_task = StudyTask(
                        id=f"review_day{day_num:03d}",
                        title=f"Review: {review_orig.title}",
                        description=f"Warm-up review of yesterday's focus area — {review_orig.title}. Spend 5-10 min recalling key concepts without notes.",
                        category=review_orig.category,
                        difficulty="easy",
                        estimated_minutes=10,
                        resources=[],
                        parent_area=review_orig.parent_area,
                    )
                    day_tasks.append(review_task)
                    total_minutes += 10

            # Fill the day with tasks until we hit the time budget
            max_budget = daily_minutes * 1.5  # Allow 150% overflow to fit meaningful tasks
            has_real_task = any(not t.id.startswith("review_") for t in day_tasks)
            while task_idx < total_tasks:
                task = tasks[task_idx]
                proposed_minutes = total_minutes + task.estimated_minutes

                if proposed_minutes > max_budget:
                    # Allow ONE task over budget if the day would otherwise be empty
                    if not has_real_task:
                        has_real_task = True
                        # Add this one task and stop
                        task.scheduled_date = session_date
                        day_tasks.append(task)
                        total_minutes += task.estimated_minutes
                        task_idx += 1
                        break
                    else:
                        break

                task.scheduled_date = session_date
                day_tasks.append(task)
                total_minutes += task.estimated_minutes
                has_real_task = True
                task_idx += 1

            # Ensure day 1 ALWAYS has content
            if day_num == 1 and not day_tasks and tasks:
                first_task = tasks[0]
                first_task.scheduled_date = session_date
                day_tasks.append(first_task)
                total_minutes = first_task.estimated_minutes
                task_idx = 1

            if day_tasks:
                # Determine focus and stretch tasks
                focus_task = None
                stretch_task = None
                non_review_tasks = [t for t in day_tasks if not t.id.startswith("review_")]
                if non_review_tasks:
                    # Focus: the task with lowest confidence target (most challenging)
                    non_review_tasks.sort(key=lambda t: t.confidence_target)
                    focus_task = non_review_tasks[0]
                    focus_task.is_focus = True
                    # Stretch: the task with highest difficulty
                    hard_tasks = [t for t in non_review_tasks if t.difficulty == "hard"]
                    if hard_tasks and hard_tasks[0] != focus_task:
                        stretch_task = hard_tasks[0]
                        stretch_task.is_stretch = True

                theme = self._generate_rich_theme(day_num, non_review_tasks, session_date, days)

                session = StudySession(
                    date=session_date,
                    tasks=day_tasks,
                    total_minutes=total_minutes,
                    theme=theme,
                    day_number=day_num,
                    focus_task_id=focus_task.id if focus_task else None,
                    stretch_task_id=stretch_task.id if stretch_task else None,
                )
                sessions.append(session)

        # If there are remaining tasks that didn't fit, redistribute 1 per session
        # (only if there's room within the budget)
        remaining_idx = task_idx
        if remaining_idx < total_tasks and sessions:
            for s in sessions:
                if remaining_idx >= total_tasks:
                    break
                task = tasks[remaining_idx]
                if s.total_minutes + task.estimated_minutes <= daily_minutes * 2.0:
                    task.scheduled_date = s.date
                    s.tasks.append(task)
                    s.total_minutes += task.estimated_minutes
                    remaining_idx += 1

        return sessions

    def _generate_rich_theme(
        self,
        day_index: int,
        tasks: List[StudyTask],
        date: datetime,
        total_days: int,
    ) -> str:
        """Generate a descriptive session theme like 'Day 3: Container Orchestration Deep Dive — K8s'"""
        if not tasks:
            # Fallback themes by day region
            if day_index <= total_days * 0.25:
                return f"Day {day_index}: Foundation Building"
            elif day_index <= total_days * 0.5:
                return f"Day {day_index}: Core Concepts Review"
            elif day_index <= total_days * 0.75:
                return f"Day {day_index}: Intermediate Practice"
            else:
                return f"Day {day_index}: Advanced Topics & Review"

        # Get the primary category and parent areas
        categories = [t.category for t in tasks if not t.id.startswith("review_")]
        parent_areas = [t.parent_area for t in tasks if t.parent_area and not t.id.startswith("review_")]

        # Count categories
        cat_counts = defaultdict(int)
        for cat in categories:
            cat_counts[cat] += 1

        primary_cat = max(cat_counts, key=cat_counts.get) if cat_counts else "general"

        # Category display names
        cat_names = {
            "algorithms": "Algorithms",
            "system_design": "System Design",
            "behavioral": "Behavioral Prep",
            "python": "Python",
            "javascript": "JavaScript",
            "devops": "DevOps & Infrastructure",
            "cloud": "Cloud Platform",
            "databases": "Databases",
            "security": "Security",
            "api": "API Design",
            "ml": "Machine Learning",
            "go": "Go",
            "java": "Java",
            "cpp": "C++",
            "rust": "Rust",
        }

        # Build theme based on day position and focus
        cat_display = cat_names.get(primary_cat, primary_cat.title())

        if parent_areas:
            # Use the first parent area as the specific focus
            focus = parent_areas[0]
            if len(set(parent_areas)) > 1:
                # Multiple areas — show primary + count
                return f"Day {day_index}: {focus} + {cat_display}"
            else:
                return f"Day {day_index}: {focus} — {cat_display}"
        else:
            # Just category
            phase = "Foundation" if day_index <= total_days * 0.3 else "Deep Dive" if day_index <= total_days * 0.7 else "Mastery"
            return f"Day {day_index}: {cat_display} {phase}"

    def _categorize_skill(self, skill_name: str) -> str:
        """Categorize a skill name into a study category"""
        name_lower = skill_name.lower()

        algorithm_keywords = [
            "algorithm", "sorting", "searching", "tree", "graph",
            "dynamic programming", "dp", "recursion", "greedy",
            "binary", "heap", "stack", "queue", "hash"
        ]

        system_design_keywords = [
            "system design", "distributed", "scalability", "database",
            "cache", "microservice", "api", "load balancer", "sharding"
        ]

        language_keywords = {
            "python": ["python"],
            "javascript": ["javascript", "js", "react", "node"],
            "java": ["java"],
            "go": ["go", "golang"],
            "cpp": ["c++", "cpp"],
            "rust": ["rust"]
        }

        # Check categories
        if any(kw in name_lower for kw in algorithm_keywords):
            return "algorithms"

        if any(kw in name_lower for kw in system_design_keywords):
            return "system_design"

        for lang, keywords in language_keywords.items():
            if any(kw in name_lower for kw in keywords):
                return lang

        return "behavioral"  # Default

    def _generate_tasks(
        self,
        weak_areas: List[Dict],
        days: int
    ) -> List[StudyTask]:
        """Generate study tasks for weak areas"""
        tasks = []
        task_id = 0

        # Calculate tasks per weak area
        tasks_per_area = max(3, days // max(len(weak_areas), 1) // 3)

        for area in weak_areas[:5]:  # Focus on top 5 weak areas
            category = area["category"]
            confidence = area["confidence"]

            # Determine difficulty based on confidence
            if confidence < 0.3:
                difficulties = ["easy", "easy", "medium"]
            elif confidence < 0.5:
                difficulties = ["easy", "medium", "medium"]
            else:
                difficulties = ["medium", "medium", "hard"]

            for i, difficulty in enumerate(difficulties[:tasks_per_area]):
                task_id += 1
                resources = self.resource_lib.get_resources(category, difficulty, 2)

                task = StudyTask(
                    id=f"task_{task_id:03d}",
                    title=f"{area['name']} - {difficulty.title()} Level",
                    description=f"Improve {area['name']} skills at {difficulty} level",
                    category=category,
                    difficulty=difficulty,
                    estimated_minutes=self._estimate_time(difficulty),
                    resources=resources,
                    prerequisites=[],
                    confidence_target=min(area["confidence"] + 0.2, 0.9)
                )
                tasks.append(task)

        return tasks

    def _estimate_time(self, difficulty: str) -> int:
        """Estimate time needed based on difficulty"""
        return {
            "easy": 30,
            "medium": 45,
            "hard": 60
        }.get(difficulty, 45)

    def _create_sessions(
        self,
        schedule: List[Tuple[datetime, StudyTask]],
        daily_minutes: int
    ) -> List[StudySession]:
        """Group scheduled tasks into daily sessions"""
        sessions = []

        # Group by date
        by_date = defaultdict(list)
        for date, task in schedule:
            date_key = date.date()
            by_date[date_key].append(task)

        # Create sessions
        for date_key in sorted(by_date.keys()):
            day_tasks = by_date[date_key]

            # Filter tasks to fit within daily_minutes
            selected_tasks = []
            total_minutes = 0

            for task in day_tasks:
                if total_minutes + task.estimated_minutes <= daily_minutes:
                    task.scheduled_date = datetime.combine(date_key, datetime.min.time())
                    selected_tasks.append(task)
                    total_minutes += task.estimated_minutes

            if selected_tasks:
                # Determine theme from tasks
                categories = [t.category for t in selected_tasks]
                theme = self._generate_theme(categories)

                session = StudySession(
                    date=datetime.combine(date_key, datetime.min.time()),
                    tasks=selected_tasks,
                    total_minutes=total_minutes,
                    theme=theme
                )
                sessions.append(session)

        return sessions

    def _generate_theme(self, categories: List[str]) -> str:
        """Generate a session theme from categories"""
        category_counts = defaultdict(int)
        for cat in categories:
            category_counts[cat] += 1

        if not category_counts:
            return "Mixed Review"

        primary = max(category_counts, key=category_counts.get)

        themes = {
            "algorithms": [
                "Algorithm Fundamentals",
                "Data Structures Review",
                "Problem Solving Patterns"
            ],
            "system_design": [
                "System Design Principles",
                "Scalability Patterns",
                "Distributed Systems"
            ],
            "behavioral": [
                "STAR Method Practice",
                "Leadership Stories",
                "Communication Skills"
            ],
            "python": ["Python Deep Dive", "Python Patterns"],
            "javascript": ["JavaScript Concepts", "Async Programming"],
            "go": ["Go Concurrency", "Go Patterns"]
        }

        return random.choice(themes.get(primary, ["Mixed Review"]))

    def _generate_milestones(
        self,
        sessions: List[StudySession],
        weak_areas: List[Dict]
    ) -> List[Dict]:
        """Generate weekly milestone checkpoints with specific focus areas"""
        milestones = []

        if not sessions:
            return milestones

        total_sessions = len(sessions)
        days_total = total_sessions  # 1 session per day

        # Group sessions by week (7-day chunks)
        weeks = defaultdict(list)
        for s in sessions:
            week_num = (s.day_number - 1) // 7 + 1 if s.day_number else 0
            weeks[week_num].append(s)

        # Phase labels based on week position
        phase_labels = {
            1: "Foundation & Setup",
            2: "Core Skills Development",
            3: "Deep Dive & Practice",
            4: "Advanced Topics",
        }

        rewards = {
            1: "Build your study rhythm — you're on track!",
            2: "Schedule a mock interview with a friend",
            3: "You're interview-ready for most topics — keep pushing!",
            4: "Treat yourself — you've earned it!",
        }

        # Get top weak area names for focus descriptions
        top_areas = [a.get("name", "") for a in weak_areas[:4]]
        top_categories = [a.get("category", "") for a in weak_areas[:4]]

        for week_num, week_sessions in sorted(weeks.items()):
            if not week_sessions:
                continue

            # Determine focus areas for this week
            all_parent_areas = []
            all_categories = []
            for s in week_sessions:
                for t in s.tasks:
                    if t.parent_area and not t.id.startswith("review_"):
                        all_parent_areas.append(t.parent_area)
                    if t.category and not t.id.startswith("review_"):
                        all_categories.append(t.category)

            # Count and get top focus areas
            area_counts = defaultdict(int)
            for a in all_parent_areas:
                area_counts[a] += 1
            top_week_areas = sorted(area_counts, key=area_counts.get, reverse=True)[:3]

            cat_counts = defaultdict(int)
            for c in all_categories:
                cat_counts[c] += 1
            top_week_cats = sorted(cat_counts, key=cat_counts.get, reverse=True)[:2]

            # Phase label
            if week_num <= 4:
                phase = phase_labels.get(week_num, f"Week {week_num}")
            elif week_num <= 8:
                phase = f"Week {week_num}: Continued Practice"
            else:
                phase = f"Week {week_num}: Mastery & Review"

            focus_str = ", ".join(top_week_areas) if top_week_areas else ", ".join(top_week_cats) if top_week_cats else "Mixed Review"

            milestones.append({
                "name": f"{phase}",
                "description": f"Focus on {focus_str}. Complete {len(week_sessions)} sessions this week.",
                "focus_areas": top_week_areas[:3],
                "week": week_num,
                "target_date": week_sessions[0].date.isoformat(),
                "type": "weekly",
                "reward": rewards.get(week_num, "Keep going — consistency is key!"),
            })

        # Final completion milestone
        milestones.append({
            "name": "Study Plan Complete!",
            "description": f"All {total_sessions} days completed. You've covered {', '.join(top_areas[:3])} and are ready for your interview!",
            "focus_areas": [],
            "week": (total_sessions // 7) + 1,
            "target_date": sessions[-1].date.isoformat(),
            "type": "completion",
            "reward": "You're interview-ready! Go ace it!",
        })

        return milestones

    def adapt_plan(
        self,
        plan: StudyPlan,
        completed_task_id: str,
        performance_score: float
    ) -> StudyPlan:
        """
        Adapt plan based on task completion and performance.

        Args:
            plan: Current study plan
            completed_task_id: ID of completed task
            performance_score: 0.0 to 1.0 performance rating

        Returns:
            Updated StudyPlan
        """
        # Update task completion
        found = False
        for session in plan.sessions:
            for task in session.tasks:
                if task.id == completed_task_id and not found:
                    task.completed = True
                    plan.completed_tasks += 1
                    found = True
                    break
            if found:
                break

        # Recalculate progress
        plan.progress_percentage = (
            plan.completed_tasks / plan.total_tasks * 100
            if plan.total_tasks > 0 else 0
        )

        # If performance was excellent, skip next review
        if performance_score > 0.9:
            logger.info(f"Excellent performance on {completed_task_id}, advancing schedule")
            # Could add logic to skip redundant reviews here

        # If performance was poor, add remedial tasks
        if performance_score < 0.5:
            logger.info(f"Poor performance on {completed_task_id}, adding remedial practice")
            # Find the task and add easier follow-up
            for session in plan.sessions:
                for task in session.tasks:
                    if task.id == completed_task_id:
                        # Add remedial task in next session
                        next_session_idx = plan.sessions.index(session) + 1
                        if next_session_idx < len(plan.sessions):
                            remedial = StudyTask(
                                id=f"{task.id}_remedial",
                                title=f"{task.title} (Review)",
                                description=f"Additional practice for {task.title}",
                                category=task.category,
                                difficulty="easy",  # Easier version
                                estimated_minutes=20,
                                resources=self.resource_lib.get_resources(
                                    task.category, "easy", 2
                                ),
                                prerequisites=[task.id]
                            )
                            plan.sessions[next_session_idx].tasks.append(remedial)
                        break

        return plan

    def export_plan(self, plan: StudyPlan, format: str = "json") -> str:
        """Export study plan to various formats"""
        if format == "json":
            return self._to_json(plan)
        elif format == "ical":
            return self._to_ical(plan)
        elif format == "markdown":
            return self._to_markdown(plan)
        else:
            raise ValueError(f"Unknown format: {format}")

    def _to_json(self, plan: StudyPlan) -> str:
        """Convert plan to JSON"""
        data = {
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
            "sessions": [
                {
                    "date": s.date.isoformat(),
                    "theme": s.theme,
                    "total_minutes": s.total_minutes,
                    "tasks": [
                        {
                            "id": t.id,
                            "title": t.title,
                            "difficulty": t.difficulty,
                            "category": t.category,
                            "estimated_minutes": t.estimated_minutes,
                            "completed": t.completed,
                            "resources": t.resources
                        }
                        for t in s.tasks
                    ]
                }
                for s in plan.sessions
            ]
        }
        return json.dumps(data, indent=2)

    def _escape_ical_text(self, text: str) -> str:
        """Escape special characters for iCal format"""
        # Escape backslash, newline, comma, semicolon, colon
        return (text
                .replace("\\", "\\\\")
                .replace("\n", "\\n")
                .replace("\r", "")
                .replace(",", "\\,")
                .replace(";", "\\;")
                .replace(":", "\\:"))

    def _to_ical(self, plan: StudyPlan) -> str:
        """Convert plan to iCal format for calendar import"""
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//AI Note Taker//Study Plan//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH"
        ]

        for session in plan.sessions:
            for task in session.tasks:
                date_str = session.date.strftime("%Y%m%d")
                lines.extend([
                    "BEGIN:VEVENT",
                    f"UID:{task.id}@ainotetaker.local",
                    f"DTSTART;VALUE=DATE:{date_str}",
                    f"DTEND;VALUE=DATE:{date_str}",
                    f"SUMMARY:{self._escape_ical_text(task.title)}",
                    f"DESCRIPTION:{self._escape_ical_text(task.description)}",
                    f"CATEGORIES:{task.category}",
                    f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
                    "END:VEVENT"
                ])

        lines.append("END:VCALENDAR")
        return "\r\n".join(lines)

    def _to_markdown(self, plan: StudyPlan) -> str:
        """Convert plan to Markdown for documentation"""
        lines = [
            f"# Study Plan for {plan.user_id}",
            f"",
            f"**Created:** {plan.created_at.strftime('%Y-%m-%d')}  ",
            f"**Duration:** {plan.duration_days} days  ",
            f"**Progress:** {plan.completed_tasks}/{plan.total_tasks} tasks ({plan.progress_percentage:.1f}%)",
            f"",
            f"## Weak Areas to Focus On",
            ""
        ]

        for area in plan.weak_areas:
            lines.append(f"- **{area['name']}** (Confidence: {area['confidence']:.0%})")

        lines.extend(["", "## Milestones", ""])
        for milestone in plan.milestones:
            lines.append(f"### {milestone['name']}")
            lines.append(f"- Target: {milestone['target_date']}")
            lines.append(f"- {milestone['description']}")
            if 'reward' in milestone:
                lines.append(f"- Reward: {milestone['reward']}")
            lines.append("")

        lines.extend(["## Daily Schedule", ""])
        for session in plan.sessions:
            lines.append(f"### {session.date.strftime('%Y-%m-%d (%A)')} - {session.theme}")
            for task in session.tasks:
                status = "✅" if task.completed else "⬜"
                lines.append(f"- {status} [{task.difficulty[0].upper()}] {task.title} ({task.estimated_minutes}min)")
            lines.append("")

        return "\n".join(lines)


# Global instance
study_planner = StudyPlanGenerator()


def generate_plan(
    user_id: str,
    days: int = 30,
    daily_minutes: int = 60,
    graph_data: Optional[Dict] = None,
    target_role: Optional[str] = None,
    target_company: Optional[str] = None,
    job_description: Optional[str] = None,
    current_skills: Optional[List[str]] = None,
) -> StudyPlan:
    """Generate study plan - convenience function"""
    return study_planner.generate_plan(
        user_id, days, daily_minutes, graph_data,
        target_role=target_role,
        target_company=target_company,
        job_description=job_description,
        current_skills=current_skills,
    )


def adapt_plan(
    plan: StudyPlan,
    completed_task_id: str,
    performance_score: float
) -> StudyPlan:
    """Adapt plan based on performance - convenience function"""
    return study_planner.adapt_plan(plan, completed_task_id, performance_score)


def export_plan(plan: StudyPlan, format: str = "json") -> str:
    """Export plan - convenience function"""
    return study_planner.export_plan(plan, format)
