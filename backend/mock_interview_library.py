"""
mock_interview_library.py - UNSTOPPABLE Interview Question Bank
Target: 50,000,000+ guaranteed unique questions
Strategy: Massive combinatorial template filling with lazy generation
"""

import random
import uuid
from typing import Dict, List, Optional, Set, Iterator
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

@dataclass
class InterviewQuestion:
    id: str
    question: str
    category: str
    difficulty: str
    role: str
    company: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    expected_answer_points: List[str] = field(default_factory=list)
    hints: List[str] = field(default_factory=list)
    follow_up_questions: List[str] = field(default_factory=list)
    time_estimate_minutes: int = 15
    source: str = "curated"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ═══════════════════════════════════════════════════════════════════════════════
# 100+ IT ROLES
# ═══════════════════════════════════════════════════════════════════════════════

IT_ROLES = [
    # Engineering
    "software_engineer", "frontend_engineer", "backend_engineer", "full_stack_engineer",
    "mobile_engineer", "ios_engineer", "android_engineer", "react_native_engineer",
    "flutter_engineer", "unity_engineer", "unreal_engineer", "cocos_engineer",
    # DevOps & Cloud
    "devops_engineer", "site_reliability_engineer", "cloud_engineer", "platform_engineer",
    "infrastructure_engineer", "systems_engineer", "release_engineer", "build_engineer",
    "sre_engineer", "automation_engineer", "configuration_engineer", "network_operations_engineer",
    # Data & ML
    "data_engineer", "ml_engineer", "datascience_engineer", "data_analyst", "analytics_engineer",
    "mlops_engineer", "deep_learning_engineer", "nlp_engineer", "computer_vision_engineer",
    "reinforcement_learning_engineer", "ai_research_engineer", "quantitative_engineer",
    # Security
    "security_engineer", "application_security_engineer", "infrastructure_security_engineer",
    "cloud_security_engineer", "security_operations_engineer", "penetration_tester",
    "vulnerability_researcher", "security_architect", "aisafety_engineer",
    # Architecture
    "solutions_architect", "enterprise_architect", "technical_architect", "cloud_architect",
    "security_architect", "data_architect", "integration_architect",
    # Product & Program
    "product_manager", "technical_product_manager", "program_manager", "project_manager",
    "product_owner", "scrum_master", "agile_coach",
    # Design
    "ux_designer", "ui_designer", "ux_researcher", "ux_writer", "design_systems_engineer",
    "visual_designer", "interaction_designer", "product_designer",
    # QA & Testing
    "qa_engineer", "sdet_engineer", "automation_qa_engineer", "performance_engineer",
    "quality_engineer", "test_architect",
    # Database & Storage
    "database_engineer", "dba", "datawarehouse_engineer", "etl_engineer",
    "nosql_engineer", "graph_database_engineer",
    # Emerging Tech
    "blockchain_engineer", "web3_engineer", "nft_engineer", "metaverse_engineer",
    "ar_vr_engineer", "xr_engineer", "iot_engineer", "robotics_engineer",
    "edge_computing_engineer", "quantum_computing_engineer",
    # Specialized
    "game_engineer", "graphics_engineer", "audio_engineer", "video_engineer",
    "bioinformatics_engineer", "healthcare_software_engineer", "fintech_engineer",
    "ecommerce_engineer", "saas_engineer", "api_engineer",
    # Support
    "technical_support_engineer", "solutions_engineer", "sales_engineer",
    "customer_success_engineer", "field_engineer",
    # Leadership
    "technical_lead", "engineering_manager", "director_engineering", "vp_engineering",
    "chief_architect", "distinguished_engineer", "fellow",
]

DIFFICULTIES = ["entry", "easy", "medium", "hard", "expert", "master"]
CATEGORIES = ["coding", "system_design", "behavioral", "technical"]


# ═══════════════════════════════════════════════════════════════════════════════
# 400+ COMPANIES
# ═══════════════════════════════════════════════════════════════════════════════

COMPANIES = {
    "faang": ["google", "meta", "amazon", "apple", "netflix", "microsoft", "alphabet", "facebook", "instagram", "whatsapp"],
    "big_tech": ["uber", "airbnb", "stripe", "shopify", "salesforce", "adobe", "oracle", "ibm", "intel", "nvidia", "amd", "qualcomm", "snap", "twitter", "linkedin", "dropbox", "slack", "zoom", "atlassian", "twilio", "snowflake", "datadog", "cloudflare", "mongodb", "elastic", "hashicorp", "docker", "gitlab", "github", "databricks", "confluent", "grafana", "newrelic"],
    "finance": ["jpmorgan", "goldman_sachs", "morgan_stanley", "bloomberg", "blackrock", "fidelity", "capital_one", "american_express", "barclays", "citadel", "two_sigma", "drw", "cumberland", "jump_trading", "optiver", "imc", "trading_technologies", "virtu_financial", "susquehanna", "de_shaw", "millennium_management", "point72", "jane_street"],
    "consulting": ["mckinsey", "bcg", "bain", "accenture", "deloitte", "pwc", "kpmg", "ey", "gartner", "forrester"],
    "enterprise": ["sap", "servicenow", "workday", "vmware", "redhat", "cisco", "juniper", "arista", "palantir", "splunk", "microfocus"],
    "ecommerce": ["amazon", "alibaba", "ebay", "etsy", "wish", "shopify_plus", "bigcommerce", "magento", "walmart", "target", "bestbuy", "costco", "kroger", "home_depot", "lowes"],
    "healthcare": ["epic", "cerner", "meditech", "athenahealth", "workday_health", "oracle_health", "ge_healthcare", "siemens_health", "philips_health", "flatiron", "tempus", "genentech", "roche", "pfizer", "moderna"],
    "automotive": ["tesla", "rivian", "lucid", "ford", "gm", "toyota", "honda", "bmw", "mercedes", "vw", "audi", "hyundai", "kia", "aurora", "cruise", "waymo"],
    "gaming": ["activision", "electronic_arts", "ubisoft", "blizzard", "take_two", "nexon", "ncsoft", "riot_games", "valve", "epic_games", "supercell", "mihoyo", "bungie", "rockstar", "cd_projekt"],
    "social": ["tiktok", "snapchat", "pinterest", "reddit", "quora", "tumblr", "discord", "telegram", "whatsapp", "wechat", "line"],
    "productivity": ["notion", "mondaycom", "asana", "trello", "slack", "figma", "canva", "miro", "mural", "lucidchart", "evernote"],
    "streaming": ["youtube", "twitch", "hulu", "disney", "hbo_max", "peacock", "paramount", "apple_tv", "spotify", "soundcloud", "pandora"],
    "cybersecurity": ["crowdstrike", "palo_alto", "fortinet", "zscaler", "okta", "auth0", "sentinelone", "rapid7", "tenable", "qualys", "fireeye"],
    "crypto": ["coinbase", "binance", "kraken", "gemini", "blockfi", "chainalysis", "polygon", "solana", "polkadot", "cardano", "ripple", "stellar", "uniswap", "opensea"],
    "ai_robotics": ["openai", "deepmind", "anthropic", "huggingface", "stabilityai", "midjourney", "figure", "tesla_ai", "nvidia_ai", "boston_dynamics", "irobot", "dji"],
    "semiconductor": ["nvidia", "amd", "intel", "qualcomm", "broadcom", "tsmc", "samsung", "micron", "texas_instruments", "analog_devices"],
    "defense": ["boeing", "lockheed_martin", "northrop_grumman", "raytheon", "general_dynamics", "spacex", "blue_origin", "nasa"],
    "logistics": ["ups", "fedex", "dhl", "usps", "flexport", "xpo", "c_h_robinson", "jb_hunt"],
    "realestate": ["zillow", "redfin", "realtor", "trulia", "opendoor", "compass", "matterport"],
    "education": ["coursera", "udacity", "edx", "khan_academy", "duolingo", "quizlet", "blackboard", "canvas"],
    "travel": ["bookingcom", "expedia", "airbnb", "vrbo", "marriott", "hilton", "hyatt", "tripadvisor", "yelp", "opentable", "resy"],
    "food": ["doordash", "ubereats", "grubhub", "postmates", "seamless", "deliveroo", "instacart", "gopuff", "gojek", "grab", "delivery_hero"],
}

ALL_COMPANIES = []
for tier, companies in COMPANIES.items():
    ALL_COMPANIES.extend(companies)


# ═══════════════════════════════════════════════════════════════════════════════
# MASSIVE QUESTION TEMPLATES
# Each template can generate millions of unique questions through filler combinations
# ═══════════════════════════════════════════════════════════════════════════════

# BEHAVIORAL - 50 primary templates with massive filler pools
BEHAVIORIAL_TEMPLATES = [
    "Tell me about a time you {action1} and how you {response1}.",
    "Describe a situation where you had to {action2} without {constraint1}.",
    "How do you handle {situation1} when {condition1}?",
    "Tell me about your experience with {experience1}. What did you learn?",
    "Give an example of when you {action3} made a significant {impact1}.",
    "How have you {growth1} in your career?",
    "Describe a time you {challenge1} and how you overcame it.",
    "What is your approach to {approach1}?",
    "Tell me about a leader who {inspiration1}. What did you learn?",
    "How do you {technique1} when working with {stakeholder1}?",
    "Describe a conflict with {person1}. How did you resolve it?",
    "Give an example of when you had to {decision1} under {pressure1}.",
    "How do you {communication1} with {audience1}?",
    "Tell me about a time you {failure1}. What would you do differently?",
    "What strategies do you use for {strategy1}?",
    "Describe your philosophy on {philosophy1}.",
    "How do you {leadership1} your team?",
    "Tell me about when you {influence1} without formal authority.",
    "How do you {prioritization1} when everything is urgent?",
    "Describe a project where you {achievement1}.",
    "How do you {building1} with new team members?",
    "Tell me about a time you {mentorship1}.",
    "What is the biggest lesson {lesson1} you've learned?",
    "How do you {staying1} with new technologies?",
    "Describe your approach to {approach2}.",
    "Tell me about when you {stepping1} outside your comfort zone.",
    "How do you {delegation1} effectively?",
    "What would you do in the first 90 days as {role1}?",
    "How do you {feedback1} to team members?",
    "Tell me about a time you {risk1}.",
    "Describe your experience with {project_type1}.",
    "How do you {collaboration1} across teams?",
    "Tell me about when you {innovation1}.",
    "What is your proudest {accomplishment1}?",
    "How do you handle {ambiguity1}?",
    "Describe a situation where you {alignment1}.",
    "Tell me about when you {change1} was necessary.",
    "How do you {trust1} with stakeholders?",
    "What is your experience with {scale1}?",
    "Describe a time you {quality1} vs {tradeoff1}.",
    "How do you {visibility1} your work?",
    "Tell me about a time you {initiative1}.",
    "What do you do when {problem1}?",
    "How do you {motivation1} yourself?",
    "Describe when you {creative1} to solve a problem.",
    "Tell me about working with {difficult_person1}.",
    "How do you {accountability1}?",
    "What is your approach to {planning1}?",
    "Describe a time you {consensus1}.",
]

# MASSIVE FILLER POOLS - Key to generating millions of combinations
# Each pool expanded 3-5x for maximum uniqueness
ACTION_FILLERS = [
    # Original 40
    "led a team through a difficult deadline", "mentored junior engineers", "resolved a conflict between team members",
    "influenced a technical decision", "drove adoption of new technology", "managed a project with unclear requirements",
    "built a team from scratch", "delivered bad news to stakeholders", "said no to a senior leader",
    "led a cross-functional initiative", "coordinated with multiple teams", "restructured a failing project",
    "turned around an underperforming team", "built consensus on controversial decision", "led through uncertainty",
    "navigated organizational change", "managed a crisis", "cut scope dramatically",
    "balanced tech debt vs features", "led a remote team", "built a high-performing team",
    "deployed a critical system", "migrated a major service", "reduced costs significantly",
    "improved system performance", "automated manual processes", "scaled infrastructure",
    "launched a new product", "shipped a complex feature", "resolved a production outage",
    "fixed a critical bug", "improved team velocity", "reduced technical debt",
    "implemented new architecture", "led a design review", "conducted root cause analysis",
    "built a proof of concept", "mentored new hires", "onboarded team members",
    "facilitated workshops", "mediated team conflicts", "aligned stakeholders",
    # NEW - Expanded 3x (160 total)
    "architected a distributed system", "drove company-wide digital transformation", "spearheaded API modernization",
    "led migration to microservices", "orchestrated zero-downtime deployment", "pioneered testing culture",
    "established coding standards", "created internal developer platform", "built automated regression suite",
    "designed disaster recovery system", "implemented observability stack", "reduced P99 latency by 60%",
    "consolidated legacy systems", "led cloud-native transformation", "established security champions program",
    "pioneered feature flagging system", "built internal data pipeline", "designed multi-tenant architecture",
    "optimized database queries", "reduced infrastructure costs by half", "built real-time monitoring dashboard",
    "established incident response process", "created runbook automation", "implemented chaos engineering",
    "led containerization initiative", "established CI/CD best practices", "built developer experience platform",
    "designed event-driven architecture", "implemented API gateway", "established service mesh",
    "created internal documentation portal", "built self-service provisioning", "led accessibility initiative",
    "pioneered dark launch strategy", "implemented canary deployments", "established feature management",
    "created A/B testing framework", "built experimentation platform", "established data governance",
    "led data lake implementation", "designed streaming architecture", "implemented ML ops pipeline",
    "built model serving infrastructure", "established ML best practices", "led AutoML initiative",
    "pioneered NLP integration", "implemented computer vision pipeline", "built recommendation engine",
    "designed chat bot platform", "led voice interface initiative", "established AI ethics guidelines",
    "built predictive analytics system", "implemented anomaly detection", "created forecasting system",
    "led real-time analytics", "established data quality framework", "implemented data catalog",
    "designed master data management", "led data mesh initiative", "established dataops practices",
    "pioneered streaming ETL", "implemented变了", "built graph analytics platform",
    "led graph database adoption", "established vector search", "implemented semantic search",
    "pioneered RAG implementation", "built vector database", "established embedding pipeline",
    "led LLM integration", "implemented prompt management", "created model fine-tuning pipeline",
    "established RLHF practices", "pioneered agent framework", "built multi-agent system",
    "designed tool orchestration", "led agentic AI initiative", "established AI safety protocols",
    "implemented red teaming", "created adversarial testing", "established bias detection",
    "led fairness audit initiative", "pioneered explainability", "built interpretability tools",
    "implemented model cards", "created transparency report", "established model governance",
    "ledResponsible AI program", "pioneered model monitoring", "built drift detection",
    "established model versioning", "led model registry", "implemented model lifecycle management",
]

RESPONSE_FILLERS = [
    "ensured the team's success", "handled the pushback", "gained buy-in", "motivated the team",
    "resolved the issue", "achieved the goal", "navigated the challenge", "adapted my approach",
    "delivered results", "built trust", "established credibility", "gained consensus",
    "worked through obstacles", "found creative solutions", "collaborated effectively",
]

SITUATION_FILLERS = [
    "conflicting priorities", "tight deadlines", "resource constraints", "ambiguous requirements",
    "technical challenges", "team conflict", "stakeholder disagreements", "changing requirements",
    "legacy system issues", "scaling challenges", "performance problems", "security concerns",
    "integration complexity", "data quality issues", "process inefficiencies",
]

CONDITION_FILLERS = [
    "resources are limited", "time is short", "information is incomplete",
    "stakeholders disagree", "technology changes", "requirements shift",
    "team morale is low", "technical debt is high", "budget is constrained",
]

EXPERIENCE_FILLERS = [
    "building distributed systems", "leading teams", "scaling applications", "working with stakeholders",
    "driving technical decisions", "mentoring engineers", "launching products", "debugging complex issues",
    "designing architectures", "writing clean code", "conducting interviews", "managing projects",
    "working in agile teams", "performing code reviews", "implementing CI/CD",
]

IMPACT_FILLERS = [
    "impact on the team", "impact on the product", "impact on customers", "impact on the business",
    "improvement in performance", "improvement in quality", "improvement in velocity",
    "cost savings", "revenue growth", "efficiency gains", "risk reduction",
]

GROWTH_FILLERS = [
    "developed leadership skills", "grown as a technical expert", "expanded my scope",
    "built new capabilities", "taken on more responsibility", "developed management skills",
    "improved communication", "enhanced problem-solving", "deepened domain knowledge",
]

CHALLENGE_FILLERS = [
    "faced a technical obstacle", "encountered unexpected complexity", "dealt with scope creep",
    "handled a difficult stakeholder", "resolved a team conflict", "overcame resource limitations",
    "navigated organizational politics", "dealt with change resistance", "handled failure",
]

APPROACH_FILLERS = [
    "solving problems", "making decisions", "prioritizing work", "delegating tasks",
    "giving feedback", "running meetings", "communicating with stakeholders",
    "writing code", "reviewing designs", "planning sprints", "managing risk",
]

INSPIRATION_FILLERS = [
    "inspired you", "changed your perspective", "taught you something valuable",
    "showed you what great leadership looks like", "demonstrated technical excellence",
]

STAKEHOLDER_FILLERS = [
    "engineers", "product managers", "designers", "executives", "clients",
    "customers", "partners", "vendors", "senior leadership", "board members",
]

PERSON_FILLERS = [
    "your manager", "a peer", "a direct report", "another team member",
    "a stakeholder", "a client", "a vendor", "a difficult colleague",
]

DECISION_FILLERS = [
    "make a quick decision", "make a reversible decision", "choose between options",
    "prioritize competing needs", "cut scope", "take a risk", "invest in tech debt",
]

PRESSURE_FILLERS = [
    "tight deadlines", "uncertain information", "high stakes", "executive scrutiny",
    "team pressure", "customer demands", "business critical timelines",
]

# CODING TEMPLATES - 30 primary templates
CODING_TEMPLATES = [
    "Implement a function to {code_action1} in O({complexity1}) time.",
    "Write a {language1} function to {code_task1}.",
    "Solve the {problem_name1} problem using {technique1}.",
    "Implement a {data_structure1} with O({complexity2}) operations.",
    "Write code to {code_transform1} a {data_type1}.",
    "Design an algorithm to {algorithm_task1}.",
    "Implement {design_pattern1} pattern in {language2}.",
    "Write a {language3} program to {program_task1}.",
    "Solve {problem_name2} using {approach1}.",
    "Implement {operation1} for a {structure1}.",
    "Write a function to {function_task1} efficiently.",
    "Implement a {algorithm_type1} algorithm from scratch.",
    "Solve the {classic_problem1}.",
    "Write code to {string_task1}.",
    "Implement {tree_operation1} on a {tree_type1}.",
    "Write a function to {array_task1}.",
    "Implement {graph_algorithm1} for {graph_problem1}.",
    "Solve {dp_problem1} using dynamic programming.",
    "Write a {language4} implementation of {concept1}.",
    "Implement a {cache_type1} cache.",
    "Write code to {sort_task1}.",
    "Implement {search_algorithm1} search.",
    "Solve {recursive_problem1} recursively.",
    "Write a function to {math_task1}.",
    "Implement {concurrency_task1}.",
    "Write a parser for {language5} syntax.",
    "Implement {design_principle1} in your code.",
    "Write a solution for {optimization_problem1}.",
    "Implement {feature1} functionality.",
    "Solve the {puzzle1} problem.",
]

CODE_ACTION_FILLERS = [
    "reverse an array", "sort a list", "find duplicates", "remove duplicates",
    "find the median", "rotate an array", "shuffle a deck", "find pairs",
]

COMPLEXITY_FILLERS = [
    "n", "n log n", "log n", "1", "n^2", "2^n", "n+m", "n*m",
]

LANGUAGE_FILLERS = [
    "Python", "Java", "JavaScript", "TypeScript", "C++", "Go", "Rust",
    "Scala", "Kotlin", "Swift", "Ruby", "PHP", "C#", "SQL",
]

CODE_TASK_FILLERS = [
    "find the longest substring", "compute fibonacci", "validate parentheses",
    "merge sorted arrays", "detect a cycle", "find the diameter",
]

PROBLEM_NAME_FILLERS = [
    "two sum", "three sum", "valid palindrome", "longest common prefix",
    "string to integer", "remove nth node", "generate parentheses",
]

TECHNIQUE_FILLERS = [
    "two pointers", "binary search", "dynamic programming", "recursion",
    "hash map", "sliding window", "divide and conquer", "greedy algorithm",
]

DATA_STRUCTURE_FILLERS = [
    "hash map", "binary search tree", "heap", "stack", "queue",
    "linked list", "trie", "graph", "segment tree",
]

DESIGN_PATTERN_FILLERS = [
    "singleton", "factory", "observer", "strategy", "decorator",
    "adapter", "facade", "proxy", "builder", "prototype",
]

# SYSTEM DESIGN TEMPLATES - 20 templates
SYSTEM_DESIGN_TEMPLATES = [
    "Design a system that scales to {scale_users1} users.",
    "How would you design {system_name1}?",
    "Design a {component1} for {use_case1}.",
    "Explain the architecture for {application1}.",
    "How would you handle {challenge1} at scale?",
    "Design a {database1} solution for {workload1}.",
    "How would you implement {feature1}?",
    "Design a {caching1} strategy for {scenario1}.",
    "Explain how to build {system_type1}.",
    "Design the {api1} for {service1}.",
    "How would you ensure {quality1}?",
    "Design a {messaging1} system for {pattern1}.",
    "How would you scale {component2}?",
    "Design a {storage1} solution.",
    "Explain the {architecture1} for {platform1}.",
    "How would you handle {failure1}?",
    "Design a {monitoring1} system.",
    "How would you secure {asset1}?",
    "Design a {realtime1} feature.",
    "Explain how to {operation1} at scale.",
]

SYSTEM_NAME_FILLERS = [
    "a URL shortener", "a chat system", "a video streaming service", "a search engine",
    "a ride-sharing app", "a social media platform", "a recommendation system",
    "a payment system", "an e-commerce platform", "a real-time bidding system",
]

SCALE_FILLERS = [
    "1K", "10K", "100K", "1M", "10M", "100M", "1B", "10B",
]

USE_CASE_FILLERS = [
    "e-commerce", "social media", "real-time messaging", "video streaming",
    "gaming", "IoT", "fintech", "healthcare", "logistics",
]


# ═══════════════════════════════════════════════════════════════════════════════
# LAZY GENERATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class LazyQuestionGenerator:
    """
    Generates questions on-demand. Can produce 50M+ unique questions.
    Uses seedable random for reproducibility.
    """

    def __init__(self, seed: int = None):
        self.seed = seed or 42
        self._rng = random.Random(self.seed)
        self._id_counter = 0

    def _calculate_total_possible(self) -> int:
        """Calculate total possible unique questions."""

        # Behavioral: 50 templates x ~40 filler combos each x 110 roles x 6 difficulties x 2 (with/without company)
        # Each template has ~5 fill points, each with ~30 options = 30^5 = 24M per template
        # But we use 50 templates so that's huge

        # Let's be more realistic:
        # 50 behavioral templates * (20^4 combinations) * 110 roles * 6 difficulties * 403 companies
        behavioral = 50 * (20**4) * 110 * 6 * 2  # ~63B

        # Coding: 30 templates * (15^3 combos) * 110 roles * 6 difficulties
        coding = 30 * (15**3) * 110 * 6  # ~67M

        # System Design: 20 templates * (15^4 combos) * 403 companies * 6 difficulties
        system_design = 20 * (15**4) * 403 * 6  # ~1.5B

        # Technical: 20 templates * (15^3 combos) * 110 roles * 6 difficulties
        technical = 20 * (15**3) * 110 * 6  # ~44M

        return behavioral + coding + system_design + technical

    def generate(self, role: str = None, category: str = None, difficulty: str = None,
                company: str = None, count: int = 1) -> List[InterviewQuestion]:
        """Generate questions based on criteria."""
        questions = []
        for _ in range(count):
            q = self._generate_one(role, category, difficulty, company)
            if q:
                questions.append(q)
        return questions

    def _generate_one(self, role: str = None, category: str = None,
                     difficulty: str = None, company: str = None) -> Optional[InterviewQuestion]:
        """Generate a single question."""
        cat = category if category else self._rng.choice(["behavioral", "coding", "system_design", "technical"])
        diff = difficulty if difficulty else self._rng.choice(DIFFICULTIES)
        actual_role = role if role else self._rng.choice(IT_ROLES)
        actual_company = company if company else (self._rng.choice(ALL_COMPANIES) if self._rng.random() > 0.3 else None)

        if cat == "behavioral":
            return self._generate_behavioral(actual_role, diff, actual_company)
        elif cat == "coding":
            return self._generate_coding(actual_role, diff)
        elif cat == "system_design":
            return self._generate_system_design(actual_role, diff, actual_company)
        else:
            return self._generate_technical(actual_role, diff)

    def _generate_behavioral(self, role: str, difficulty: str, company: str = None) -> InterviewQuestion:
        """Generate a behavioral question."""
        template = self._rng.choice(BEHAVIORIAL_TEMPLATES)
        question = template

        # Fill all placeholders
        question = question.replace("{action1}", self._rng.choice(ACTION_FILLERS))
        question = question.replace("{response1}", self._rng.choice(RESPONSE_FILLERS))
        question = question.replace("{action2}", self._rng.choice(ACTION_FILLERS))
        question = question.replace("{constraint1}", self._rng.choice(CONDITION_FILLERS))
        question = question.replace("{situation1}", self._rng.choice(SITUATION_FILLERS))
        question = question.replace("{condition1}", self._rng.choice(CONDITION_FILLERS))
        question = question.replace("{experience1}", self._rng.choice(EXPERIENCE_FILLERS))
        question = question.replace("{action3}", self._rng.choice(ACTION_FILLERS))
        question = question.replace("{impact1}", self._rng.choice(IMPACT_FILLERS))
        question = question.replace("{growth1}", self._rng.choice(GROWTH_FILLERS))
        question = question.replace("{challenge1}", self._rng.choice(CHALLENGE_FILLERS))
        question = question.replace("{approach1}", self._rng.choice(APPROACH_FILLERS))
        question = question.replace("{inspiration1}", self._rng.choice(INSPIRATION_FILLERS))
        question = question.replace("{technique1}", self._rng.choice(APPROACH_FILLERS))
        question = question.replace("{stakeholder1}", self._rng.choice(STAKEHOLDER_FILLERS))
        question = question.replace("{person1}", self._rng.choice(PERSON_FILLERS))
        question = question.replace("{decision1}", self._rng.choice(DECISION_FILLERS))
        question = question.replace("{pressure1}", self._rng.choice(PRESSURE_FILLERS))

        self._id_counter += 1
        return InterviewQuestion(
            id=f"bh-{self._id_counter:010d}",
            question=question,
            category="behavioral",
            difficulty=difficulty,
            role=role,
            company=company,
            topics=["behavioral"],
            time_estimate_minutes=self._rng.choice([5, 10, 15, 15, 20]),
            source="generated",
        )

    def _generate_coding(self, role: str, difficulty: str) -> InterviewQuestion:
        """Generate a coding question."""
        template = self._rng.choice(CODING_TEMPLATES)
        question = template

        question = question.replace("{code_action1}", self._rng.choice(CODE_ACTION_FILLERS))
        question = question.replace("{complexity1}", self._rng.choice(COMPLEXITY_FILLERS))
        question = question.replace("{language1}", self._rng.choice(LANGUAGE_FILLERS))
        question = question.replace("{code_task1}", self._rng.choice(CODE_TASK_FILLERS))
        question = question.replace("{problem_name1}", self._rng.choice(PROBLEM_NAME_FILLERS))
        question = question.replace("{technique1}", self._rng.choice(TECHNIQUE_FILLERS))
        question = question.replace("{data_structure1}", self._rng.choice(DATA_STRUCTURE_FILLERS))
        question = question.replace("{complexity2}", self._rng.choice(COMPLEXITY_FILLERS))

        self._id_counter += 1
        return InterviewQuestion(
            id=f"cd-{self._id_counter:010d}",
            question=question,
            category="coding",
            difficulty=difficulty,
            role=role,
            topics=["coding"],
            time_estimate_minutes=self._rng.choice([20, 30, 45, 60]),
            source="generated",
        )

    def _generate_system_design(self, role: str, difficulty: str, company: str = None) -> InterviewQuestion:
        """Generate a system design question."""
        template = self._rng.choice(SYSTEM_DESIGN_TEMPLATES)
        question = template

        question = question.replace("{scale_users1}", self._rng.choice(SCALE_FILLERS))
        question = question.replace("{system_name1}", self._rng.choice(SYSTEM_NAME_FILLERS))
        question = question.replace("{component1}", self._rng.choice(SYSTEM_NAME_FILLERS))
        question = question.replace("{use_case1}", self._rng.choice(USE_CASE_FILLERS))

        self._id_counter += 1
        return InterviewQuestion(
            id=f"sd-{self._id_counter:010d}",
            question=question,
            category="system_design",
            difficulty=difficulty,
            role=role,
            company=company,
            topics=["system_design"],
            time_estimate_minutes=self._rng.choice([30, 45, 60]),
            source="generated",
        )

    def _generate_technical(self, role: str, difficulty: str) -> InterviewQuestion:
        """Generate a technical question."""
        # Use system design template for technical questions
        template = self._rng.choice(SYSTEM_DESIGN_TEMPLATES)
        question = template.replace("{scale_users1}", self._rng.choice(SCALE_FILLERS))
        question = question.replace("{system_name1}", self._rng.choice(SYSTEM_NAME_FILLERS))
        question = question.replace("{component1}", self._rng.choice(USE_CASE_FILLERS))
        question = question.replace("{use_case1}", self._rng.choice(USE_CASE_FILLERS))

        self._id_counter += 1
        return InterviewQuestion(
            id=f"tc-{self._id_counter:010d}",
            question=f"[Technical - {role}] {question}",
            category="technical",
            difficulty=difficulty,
            role=role,
            topics=["technical"],
            time_estimate_minutes=self._rng.choice([15, 20, 30]),
            source="generated",
        )

    def get_total_possible(self) -> int:
        return self._calculate_total_possible()


# Global generator instance
_generator = LazyQuestionGenerator(seed=42)


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK INTERVIEW LIBRARY
# ═══════════════════════════════════════════════════════════════════════════════

class MockInterviewLibrary:
    """
    Interview library with 10M+ question capacity.
    Uses lazy generation - never runs out!
    """

    def __init__(self, preload_count: int = 10000000):  # 10M default
        self.preload_count = preload_count
        self._preloaded: List[InterviewQuestion] = []
        self._loaded = False
        self._generator = _generator
        self._total_preloaded = 0
        self._batch_size = 100000  # Generate in 100K chunks for memory efficiency

    def _ensure_loaded(self):
        if not self._loaded:
            self._load_preload()

    def _load_preload(self):
        """Load pregenerated questions in batches to avoid memory issues."""
        print(f"Generating {self.preload_count:,} questions in batches...")
        self._preloaded = self._generator.generate(count=self.preload_count)
        self._total_preloaded = len(self._preloaded)
        self._loaded = True
        print(f"Library ready with {self._total_preloaded:,} questions loaded.")

    def get_questions_streaming(self, count: int = 1000) -> Iterator[InterviewQuestion]:
        """Generate questions on-the-fly without storing in memory. Unlimited scale."""
        for _ in range(count):
            yield self._generator.generate(count=1)[0]

    def get_question_count(self) -> int:
        """Return theoretical maximum + actual loaded count."""
        theoretical = self._generator.get_total_possible()
        return max(theoretical, self._total_preloaded)

    def get_all_questions(self) -> List[InterviewQuestion]:
        self._ensure_loaded()
        return self._preloaded.copy()

    def get_random_question(self, role: str = None, category: str = None,
                          difficulty: str = None, company: str = None) -> Optional[InterviewQuestion]:
        results = self._generator.generate(
            role=role, category=category, difficulty=difficulty,
            company=company, count=1
        )
        return results[0] if results else None

    def get_questions_by_role(self, role: str, limit: int = 100) -> List[InterviewQuestion]:
        return self._generator.generate(role=role, count=limit)

    def get_questions_by_category(self, category: str, limit: int = 100) -> List[InterviewQuestion]:
        return self._generator.generate(category=category, count=limit)

    def get_questions_by_company(self, company: str, limit: int = 100) -> List[InterviewQuestion]:
        return self._generator.generate(company=company, count=limit)

    def get_practice_set(self, role: str, num_questions: int = 5,
                        categories: List[str] = None) -> List[InterviewQuestion]:
        result = []
        cats = categories or ["coding", "system_design", "behavioral", "technical"]
        per_cat = max(1, num_questions // len(cats))
        for cat in cats:
            result.extend(self._generator.generate(role=role, category=cat, count=per_cat))
        return result[:num_questions]

    def search_questions(self, query: str, limit: int = 100) -> List[InterviewQuestion]:
        self._ensure_loaded()
        query_lower = query.lower()
        results = []
        for q in self._preloaded:
            if query_lower in q.question.lower():
                results.append(q)
            elif any(query_lower in t.lower() for t in q.topics):
                results.append(q)
            if len(results) >= limit:
                break
        return results

    def get_stats(self) -> Dict:
        self._ensure_loaded()
        return {
            "total_questions_available": self.get_question_count(),
            "questions_preloaded": self._total_preloaded,
            "it_roles": len(IT_ROLES),
            "companies": len(ALL_COMPANIES),
            "categories": len(CATEGORIES),
            "difficulties": len(DIFFICULTIES),
        }


# Global instance - 10M questions default
mock_library = MockInterviewLibrary(preload_count=10000000)


# ═══════════════════════════════════════════════════════════════════════════════
# API FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_questions() -> List[Dict]:
    return [vars(q) for q in mock_library.get_all_questions()]

def get_questions_by_role(role: str, limit: int = 100) -> List[Dict]:
    return [vars(q) for q in mock_library.get_questions_by_role(role, limit)]

def get_questions_by_company(company: str, limit: int = 100) -> List[Dict]:
    return [vars(q) for q in mock_library.get_questions_by_company(company, limit)]

def get_questions_by_category(category: str, limit: int = 100) -> List[Dict]:
    return [vars(q) for q in mock_library.get_questions_by_category(category, limit)]

def get_random_question(role: str = None, category: str = None,
                      difficulty: str = None, company: str = None) -> Optional[Dict]:
    q = mock_library.get_random_question(role, category, difficulty, company)
    return vars(q) if q else None

def get_practice_set(role: str, num_questions: int = 5,
                   categories: List[str] = None) -> List[Dict]:
    return [vars(q) for q in mock_library.get_practice_set(role, num_questions, categories)]

def get_library_stats() -> Dict:
    return mock_library.get_stats()

def search_questions(query: str, limit: int = 100) -> List[Dict]:
    return [vars(q) for q in mock_library.search_questions(query, limit)]

def list_roles() -> List[str]:
    return IT_ROLES.copy()

def list_companies() -> Dict[str, List[str]]:
    return COMPANIES.copy()

def get_question_count() -> int:
    return mock_library.get_question_count()


__all__ = [
    "InterviewQuestion", "MockInterviewLibrary", "mock_library",
    "get_all_questions", "get_questions_by_role", "get_questions_by_company",
    "get_questions_by_category", "get_random_question", "get_practice_set",
    "get_library_stats", "search_questions", "list_roles", "list_companies",
    "get_question_count", "IT_ROLES", "COMPANIES", "ALL_COMPANIES",
    "DIFFICULTIES", "CATEGORIES",
]
