"""
predictive_interview.py - Predictive Interview Intelligence

Predicts likely interview questions based on:
- Company historical patterns (from cognitive graph)
- Role/title matching
- Question difficulty progression
- Common question categories by company

This is Phase 1 of the Predictive Interview Intelligence feature.
"""

import json
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from collections import Counter

logger = logging.getLogger("predictive_interview")

# Common interview questions database (curated from public sources)
# In production, this would be populated by scraping Glassdoor/Blind
COMMON_QUESTIONS_DB = {
    "Google": {
        "technical": [
            {"question": "Implement a LRU cache", "difficulty": "medium", "frequency": 0.9},
            {"question": "Design a URL shortener", "difficulty": "medium", "frequency": 0.85},
            {"question": "Find the k largest elements in an array", "difficulty": "medium", "frequency": 0.8},
            {"question": "Merge k sorted arrays", "difficulty": "hard", "frequency": 0.75},
            {"question": "Design a distributed key-value store", "difficulty": "hard", "frequency": 0.7},
            {"question": "Implement a garbage collector", "difficulty": "hard", "frequency": 0.6},
            {"question": "Find median in a stream", "difficulty": "hard", "frequency": 0.65},
        ],
        "system_design": [
            {"question": "Design YouTube", "difficulty": "hard", "frequency": 0.9},
            {"question": "Design a search autocomplete system", "difficulty": "medium", "frequency": 0.85},
            {"question": "Design Google Maps", "difficulty": "hard", "frequency": 0.8},
            {"question": "Design a rate limiter", "difficulty": "medium", "frequency": 0.75},
            {"question": "Design a web crawler", "difficulty": "medium", "frequency": 0.7},
        ],
        "behavioral": [
            {"question": "Tell me about a time you had to learn something quickly", "difficulty": "medium", "frequency": 0.9},
            {"question": "Describe a conflict with a teammate and how you resolved it", "difficulty": "medium", "frequency": 0.85},
            {"question": "Why do you want to work at Google?", "difficulty": "easy", "frequency": 0.95},
            {"question": "Tell me about a project you're proud of", "difficulty": "medium", "frequency": 0.8},
            {"question": "Describe a time you made a mistake", "difficulty": "medium", "frequency": 0.75},
        ]
    },
    "Meta": {
        "technical": [
            {"question": "Clone a graph", "difficulty": "medium", "frequency": 0.8},
            {"question": "Subtree of another tree", "difficulty": "medium", "frequency": 0.75},
            {"question": "Binary tree vertical order traversal", "difficulty": "medium", "frequency": 0.7},
            {"question": "Sum of distances in tree", "difficulty": "hard", "frequency": 0.6},
        ],
        "system_design": [
            {"question": "Design Facebook News Feed", "difficulty": "hard", "frequency": 0.95},
            {"question": "Design Facebook Messenger", "difficulty": "hard", "frequency": 0.9},
            {"question": "Design a photo sharing system", "difficulty": "medium", "frequency": 0.8},
            {"question": "Design Instagram", "difficulty": "hard", "frequency": 0.85},
        ],
        "behavioral": [
            {"question": "Tell me about a time you took a risk", "difficulty": "medium", "frequency": 0.9},
            {"question": "Describe a time you failed and what you learned", "difficulty": "medium", "frequency": 0.85},
            {"question": "How do you handle stress?", "difficulty": "medium", "frequency": 0.8},
        ]
    },
    "Amazon": {
        "behavioral": [
            {"question": "Tell me about a time you took ownership", "difficulty": "medium", "frequency": 0.95},
            {"question": "Describe a time you made a decision without data", "difficulty": "medium", "frequency": 0.85},
            {"question": "Tell me about a time you had to disagree with a manager", "difficulty": "hard", "frequency": 0.8},
            {"question": "Describe a situation where you had to work under tight deadlines", "difficulty": "medium", "frequency": 0.85},
            {"question": "Tell me about a time you innovated", "difficulty": "medium", "frequency": 0.8},
        ],
        "technical": [
            {"question": "Two sum", "difficulty": "easy", "frequency": 0.7},
            {"question": "LRU cache", "difficulty": "medium", "frequency": 0.8},
            {"question": "Merge intervals", "difficulty": "medium", "frequency": 0.75},
            {"question": "Number of islands", "difficulty": "medium", "frequency": 0.7},
        ],
        "system_design": [
            {"question": "Design an inventory management system", "difficulty": "medium", "frequency": 0.8},
            {"question": "Design Amazon's recommendation system", "difficulty": "hard", "frequency": 0.75},
            {"question": "Design a distributed cache", "difficulty": "hard", "frequency": 0.7},
        ]
    },
    "Netflix": {
        "system_design": [
            {"question": "Design a video streaming service", "difficulty": "hard", "frequency": 0.95},
            {"question": "Design the Netflix recommendation engine", "difficulty": "hard", "frequency": 0.9},
            {"question": "How would you handle regional content restrictions?", "difficulty": "medium", "frequency": 0.75},
        ],
        "technical": [
            {"question": "Top k frequent elements", "difficulty": "medium", "frequency": 0.7},
            {"question": "Design a hit counter", "difficulty": "medium", "frequency": 0.65},
        ]
    },
    "Microsoft": {
        "technical": [
            {"question": "Implement a trie", "difficulty": "medium", "frequency": 0.8},
            {"question": "Word break problem", "difficulty": "medium", "frequency": 0.75},
            {"question": "Serialize and deserialize binary tree", "difficulty": "medium", "frequency": 0.7},
        ],
        "system_design": [
            {"question": "Design OneDrive", "difficulty": "hard", "frequency": 0.85},
            {"question": "Design a collaborative editor like Word Online", "difficulty": "hard", "frequency": 0.8},
        ]
    },
    "Apple": {
        "technical": [
            {"question": "Rotate array", "difficulty": "medium", "frequency": 0.7},
            {"question": "Implement a thread-safe queue", "difficulty": "medium", "frequency": 0.75},
            {"question": "Memory management questions", "difficulty": "hard", "frequency": 0.7},
        ],
        "system_design": [
            {"question": "Design Apple Pay", "difficulty": "hard", "frequency": 0.8},
            {"question": "Design iCloud Photo Library", "difficulty": "hard", "frequency": 0.75},
        ]
    },
    "Uber": {
        "technical": [
            {"question": "Find median from data stream", "difficulty": "hard", "frequency": 0.75},
            {"question": "Design a ride matching algorithm", "difficulty": "medium", "frequency": 0.8},
            {"question": "Sliding window maximum", "difficulty": "hard", "frequency": 0.7},
        ],
        "system_design": [
            {"question": "Design Uber's ride matching system", "difficulty": "hard", "frequency": 0.95},
            {"question": "Design Uber Eats", "difficulty": "hard", "frequency": 0.85},
            {"question": "Design a surge pricing system", "difficulty": "hard", "frequency": 0.8},
        ],
        "behavioral": [
            {"question": "Tell me about a time you had to make a quick decision", "difficulty": "medium", "frequency": 0.85},
            {"question": "Describe a time you dealt with an angry customer", "difficulty": "medium", "frequency": 0.8},
        ]
    },
    "Airbnb": {
        "technical": [
            {"question": "House robber problem", "difficulty": "medium", "frequency": 0.75},
            {"question": "Word search II", "difficulty": "hard", "frequency": 0.7},
            {"question": "Design a booking system", "difficulty": "medium", "frequency": 0.8},
        ],
        "system_design": [
            {"question": "Design Airbnb's booking system", "difficulty": "hard", "frequency": 0.9},
            {"question": "Design a recommendation system for listings", "difficulty": "hard", "frequency": 0.85},
            {"question": "Design a pricing algorithm", "difficulty": "hard", "frequency": 0.8},
        ],
        "behavioral": [
            {"question": "Tell me about a time you created belonging", "difficulty": "medium", "frequency": 0.9},
            {"question": "Describe a time you went above and beyond", "difficulty": "medium", "frequency": 0.85},
        ]
    },
    "LinkedIn": {
        "technical": [
            {"question": "Design a social graph", "difficulty": "medium", "frequency": 0.8},
            {"question": "Mutual friends algorithm", "difficulty": "medium", "frequency": 0.75},
            {"question": "Level order traversal of binary tree", "difficulty": "easy", "frequency": 0.7},
        ],
        "system_design": [
            {"question": "Design LinkedIn's connection system", "difficulty": "hard", "frequency": 0.9},
            {"question": "Design the news feed", "difficulty": "hard", "frequency": 0.85},
            {"question": "Design job recommendation engine", "difficulty": "hard", "frequency": 0.8},
        ],
        "behavioral": [
            {"question": "Tell me about a time you transformed a process", "difficulty": "medium", "frequency": 0.85},
            {"question": "Describe a time you helped someone grow", "difficulty": "medium", "frequency": 0.8},
        ]
    },
    "Twitter": {
        "technical": [
            {"question": "Design a tweet ranking algorithm", "difficulty": "medium", "frequency": 0.8},
            {"question": "Top k trending topics", "difficulty": "medium", "frequency": 0.75},
            {"question": "Design a timeline algorithm", "difficulty": "hard", "frequency": 0.7},
        ],
        "system_design": [
            {"question": "Design Twitter's timeline", "difficulty": "hard", "frequency": 0.95},
            {"question": "Design the tweet service", "difficulty": "hard", "frequency": 0.9},
            {"question": "Design trending topics", "difficulty": "hard", "frequency": 0.85},
        ],
        "behavioral": [
            {"question": "Tell me about a time you received critical feedback", "difficulty": "medium", "frequency": 0.85},
            {"question": "Describe a time you had to simplify something complex", "difficulty": "medium", "frequency": 0.8},
        ]
    },
    "Stripe": {
        "technical": [
            {"question": "Design a payment processor", "difficulty": "hard", "frequency": 0.85},
            {"question": "Implement idempotency keys", "difficulty": "medium", "frequency": 0.8},
            {"question": "Design a fraud detection system", "difficulty": "hard", "frequency": 0.75},
        ],
        "system_design": [
            {"question": "Design Stripe's payment processing", "difficulty": "hard", "frequency": 0.95},
            {"question": "Design a subscription billing system", "difficulty": "hard", "frequency": 0.85},
            {"question": "Design webhooks infrastructure", "difficulty": "medium", "frequency": 0.8},
        ],
        "behavioral": [
            {"question": "Tell me about a time you optimized for user experience", "difficulty": "medium", "frequency": 0.9},
            {"question": "Describe a time you handled a security incident", "difficulty": "hard", "frequency": 0.75},
        ]
    },
    "Lyft": {
        "technical": [
            {"question": "Design a pathfinding algorithm", "difficulty": "medium", "frequency": 0.8},
            {"question": "Implement dynamic pricing", "difficulty": "hard", "frequency": 0.75},
        ],
        "system_design": [
            {"question": "Design Lyft's ride matching", "difficulty": "hard", "frequency": 0.9},
            {"question": "Design a driver incentive system", "difficulty": "medium", "frequency": 0.8},
        ],
        "behavioral": [
            {"question": "Tell me about a time you improved efficiency", "difficulty": "medium", "frequency": 0.85},
        ]
    },
    "DoorDash": {
        "technical": [
            {"question": "Traveling salesman problem variant", "difficulty": "hard", "frequency": 0.75},
            {"question": "Design a delivery route optimizer", "difficulty": "hard", "frequency": 0.8},
        ],
        "system_design": [
            {"question": "Design DoorDash's dispatch system", "difficulty": "hard", "frequency": 0.9},
            {"question": "Design real-time order tracking", "difficulty": "medium", "frequency": 0.85},
        ],
        "behavioral": [
            {"question": "Tell me about a time you hustled", "difficulty": "medium", "frequency": 0.9},
        ]
    },
    "Instacart": {
        "technical": [
            {"question": "Design a shopping cart system", "difficulty": "medium", "frequency": 0.8},
            {"question": "Optimize delivery batching", "difficulty": "hard", "frequency": 0.75},
        ],
        "system_design": [
            {"question": "Design Instacart's shopper app", "difficulty": "hard", "frequency": 0.9},
            {"question": "Design inventory management", "difficulty": "medium", "frequency": 0.8},
        ],
        "behavioral": [
            {"question": "Tell me about a time you improved operations", "difficulty": "medium", "frequency": 0.85},
        ]
    },
    "Coinbase": {
        "technical": [
            {"question": "Design a crypto wallet", "difficulty": "hard", "frequency": 0.85},
            {"question": "Implement blockchain transaction validation", "difficulty": "hard", "frequency": 0.8},
        ],
        "system_design": [
            {"question": "Design a crypto exchange", "difficulty": "hard", "frequency": 0.95},
            {"question": "Design fraud detection for crypto", "difficulty": "hard", "frequency": 0.9},
        ],
        "behavioral": [
            {"question": "Tell me about a time you dealt with ambiguity", "difficulty": "medium", "frequency": 0.85},
        ]
    },
    "Robinhood": {
        "technical": [
            {"question": "Design a stock trading system", "difficulty": "hard", "frequency": 0.9},
            {"question": "Implement real-time price updates", "difficulty": "hard", "frequency": 0.85},
        ],
        "system_design": [
            {"question": "Design a brokerage platform", "difficulty": "hard", "frequency": 0.95},
            {"question": "Design fractional share trading", "difficulty": "hard", "frequency": 0.85},
        ],
        "behavioral": [
            {"question": "Tell me about democratizing finance", "difficulty": "medium", "frequency": 0.9},
        ]
    },
    "OpenAI": {
        "technical": [
            {"question": "Design an LLM serving infrastructure", "difficulty": "hard", "frequency": 0.95},
            {"question": "Implement token streaming", "difficulty": "hard", "frequency": 0.9},
            {"question": "Design prompt caching", "difficulty": "hard", "frequency": 0.85},
        ],
        "system_design": [
            {"question": "Design ChatGPT's backend", "difficulty": "hard", "frequency": 0.95},
            {"question": "Design RLHF training pipeline", "difficulty": "hard", "frequency": 0.9},
        ],
        "behavioral": [
            {"question": "Tell me about your interest in AI safety", "difficulty": "medium", "frequency": 0.9},
            {"question": "Describe how you'd improve ChatGPT", "difficulty": "medium", "frequency": 0.85},
        ]
    },
    "Anthropic": {
        "technical": [
            {"question": "Design constitutional AI architecture", "difficulty": "hard", "frequency": 0.9},
            {"question": "Implement safety guardrails", "difficulty": "hard", "frequency": 0.85},
        ],
        "system_design": [
            {"question": "Design Claude's inference system", "difficulty": "hard", "frequency": 0.95},
        ],
        "behavioral": [
            {"question": "Tell me about responsible AI development", "difficulty": "medium", "frequency": 0.95},
        ]
    },
    "Snowflake": {
        "technical": [
            {"question": "Design a columnar storage system", "difficulty": "hard", "frequency": 0.85},
            {"question": "Optimize SQL query execution", "difficulty": "hard", "frequency": 0.8},
        ],
        "system_design": [
            {"question": "Design a data warehouse", "difficulty": "hard", "frequency": 0.9},
            {"question": "Design multi-tenant database isolation", "difficulty": "hard", "frequency": 0.85},
        ],
        "behavioral": [
            {"question": "Tell me about handling data at scale", "difficulty": "medium", "frequency": 0.85},
        ]
    },
    "Databricks": {
        "technical": [
            {"question": "Design Spark job optimization", "difficulty": "hard", "frequency": 0.85},
            {"question": "Implement Delta Lake features", "difficulty": "hard", "frequency": 0.8},
        ],
        "system_design": [
            {"question": "Design a data lakehouse", "difficulty": "hard", "frequency": 0.9},
            {"question": "Design ML model serving", "difficulty": "hard", "frequency": 0.85},
        ],
        "behavioral": [
            {"question": "Tell me about democratizing data and AI", "difficulty": "medium", "frequency": 0.9},
        ]
    },
    "Salesforce": {
        "technical": [
            {"question": "Design a CRM data model", "difficulty": "medium", "frequency": 0.8},
            {"question": "Implement custom object relationships", "difficulty": "medium", "frequency": 0.75},
        ],
        "system_design": [
            {"question": "Design Salesforce's multi-tenant architecture", "difficulty": "hard", "frequency": 0.85},
        ],
        "behavioral": [
            {"question": "Tell me about Ohana culture", "difficulty": "medium", "frequency": 0.9},
        ]
    },
    "Oracle": {
        "technical": [
            {"question": "Design database indexing strategies", "difficulty": "hard", "frequency": 0.85},
            {"question": "Optimize SQL joins", "difficulty": "medium", "frequency": 0.8},
        ],
        "system_design": [
            {"question": "Design Oracle's database architecture", "difficulty": "hard", "frequency": 0.9},
        ],
        "behavioral": [
            {"question": "Tell me about enterprise software experience", "difficulty": "medium", "frequency": 0.85},
        ]
    },
    "Adobe": {
        "technical": [
            {"question": "Design an image processing pipeline", "difficulty": "hard", "frequency": 0.85},
            {"question": "Implement undo/redo system", "difficulty": "medium", "frequency": 0.8},
        ],
        "system_design": [
            {"question": "Design Creative Cloud sync", "difficulty": "hard", "frequency": 0.85},
        ],
        "behavioral": [
            {"question": "Tell me about creativity enablement", "difficulty": "medium", "frequency": 0.85},
        ]
    },
    "Shopify": {
        "technical": [
            {"question": "Design an e-commerce cart", "difficulty": "medium", "frequency": 0.85},
            {"question": "Implement inventory management", "difficulty": "medium", "frequency": 0.8},
        ],
        "system_design": [
            {"question": "Design Shopify's platform", "difficulty": "hard", "frequency": 0.9},
            {"question": "Design multi-tenant storefronts", "difficulty": "hard", "frequency": 0.85},
        ],
        "behavioral": [
            {"question": "Tell me about empowering entrepreneurs", "difficulty": "medium", "frequency": 0.9},
        ]
    },
    "Spotify": {
        "technical": [
            {"question": "Design a music recommendation algorithm", "difficulty": "hard", "frequency": 0.9},
            {"question": "Implement audio fingerprinting", "difficulty": "hard", "frequency": 0.8},
        ],
        "system_design": [
            {"question": "Design Spotify's music streaming", "difficulty": "hard", "frequency": 0.95},
            {"question": "Design Discover Weekly", "difficulty": "hard", "frequency": 0.9},
        ],
        "behavioral": [
            {"question": "Tell me about music and culture", "difficulty": "medium", "frequency": 0.9},
        ]
    },
    "Netflix": {
        "technical": [
            {"question": "Design a video recommendation system", "difficulty": "hard", "frequency": 0.95},
            {"question": "Implement A/B testing framework", "difficulty": "hard", "frequency": 0.85},
        ],
        "system_design": [
            {"question": "Design video streaming at scale", "difficulty": "hard", "frequency": 0.95},
            {"question": "Design content delivery network", "difficulty": "hard", "frequency": 0.9},
            {"question": "Design personalized home page", "difficulty": "hard", "frequency": 0.85},
        ],
        "behavioral": [
            {"question": "Tell me about a time you used data to make decisions", "difficulty": "medium", "frequency": 0.9},
        ]
    },
    "Dropbox": {
        "technical": [
            {"question": "Design a file sync algorithm", "difficulty": "hard", "frequency": 0.9},
            {"question": "Implement conflict resolution", "difficulty": "hard", "frequency": 0.85},
        ],
        "system_design": [
            {"question": "Design Dropbox's sync system", "difficulty": "hard", "frequency": 0.95},
            {"question": "Design file versioning", "difficulty": "medium", "frequency": 0.8},
        ],
        "behavioral": [
            {"question": "Tell me about simplifying complex workflows", "difficulty": "medium", "frequency": 0.85},
        ]
    },
    "Slack": {
        "technical": [
            {"question": "Design real-time messaging", "difficulty": "hard", "frequency": 0.9},
            {"question": "Implement message threading", "difficulty": "medium", "frequency": 0.8},
        ],
        "system_design": [
            {"question": "Design Slack's architecture", "difficulty": "hard", "frequency": 0.95},
            {"question": "Design notification system", "difficulty": "medium", "frequency": 0.85},
        ],
        "behavioral": [
            {"question": "Tell me about improving team collaboration", "difficulty": "medium", "frequency": 0.9},
        ]
    },
    "Zoom": {
        "technical": [
            {"question": "Design video compression", "difficulty": "hard", "frequency": 0.9},
            {"question": "Implement echo cancellation", "difficulty": "hard", "frequency": 0.85},
        ],
        "system_design": [
            {"question": "Design Zoom's video infrastructure", "difficulty": "hard", "frequency": 0.95},
            {"question": "Design breakout rooms", "difficulty": "medium", "frequency": 0.8},
        ],
        "behavioral": [
            {"question": "Tell me about enabling remote work", "difficulty": "medium", "frequency": 0.9},
        ]
    },
    "TikTok": {
        "technical": [
            {"question": "Design a video recommendation feed", "difficulty": "hard", "frequency": 0.95},
            {"question": "Implement video upload processing", "difficulty": "medium", "frequency": 0.8},
        ],
        "system_design": [
            {"question": "Design TikTok's For You Page", "difficulty": "hard", "frequency": 0.95},
            {"question": "Design short video infrastructure", "difficulty": "hard", "frequency": 0.9},
        ],
        "behavioral": [
            {"question": "Tell me about content moderation", "difficulty": "hard", "frequency": 0.85},
        ]
    },
    "Snapchat": {
        "technical": [
            {"question": "Design ephemeral messaging", "difficulty": "medium", "frequency": 0.85},
            {"question": "Implement AR filters", "difficulty": "hard", "frequency": 0.8},
        ],
        "system_design": [
            {"question": "Design Snapchat's stories", "difficulty": "hard", "frequency": 0.9},
            {"question": "Design AR lens platform", "difficulty": "hard", "frequency": 0.85},
        ],
        "behavioral": [
            {"question": "Tell me about privacy by design", "difficulty": "medium", "frequency": 0.85},
        ]
    },
    "Pinterest": {
        "technical": [
            {"question": "Design visual search", "difficulty": "hard", "frequency": 0.85},
            {"question": "Implement image classification", "difficulty": "hard", "frequency": 0.8},
        ],
        "system_design": [
            {"question": "Design Pinterest's boards", "difficulty": "medium", "frequency": 0.85},
            {"question": "Design visual discovery", "difficulty": "hard", "frequency": 0.9},
        ],
        "behavioral": [
            {"question": "Tell me about inspiring creativity", "difficulty": "medium", "frequency": 0.9},
        ]
    },
    "Reddit": {
        "technical": [
            {"question": "Design a voting system", "difficulty": "medium", "frequency": 0.85},
            {"question": "Implement ranking algorithms", "difficulty": "hard", "frequency": 0.8},
        ],
        "system_design": [
            {"question": "Design Reddit's feed", "difficulty": "hard", "frequency": 0.9},
            {"question": "Design subreddit moderation tools", "difficulty": "medium", "frequency": 0.8},
        ],
        "behavioral": [
            {"question": "Tell me about community building", "difficulty": "medium", "frequency": 0.9},
        ]
    }
}

# Role-specific question patterns
ROLE_PATTERNS = {
    "software engineer": {
        "technical_ratio": 0.5,
        "system_design_ratio": 0.3,
        "behavioral_ratio": 0.2,
        "typical_difficulty": "medium"
    },
    "senior software engineer": {
        "technical_ratio": 0.3,
        "system_design_ratio": 0.5,
        "behavioral_ratio": 0.2,
        "typical_difficulty": "hard"
    },
    "staff engineer": {
        "technical_ratio": 0.2,
        "system_design_ratio": 0.6,
        "behavioral_ratio": 0.2,
        "typical_difficulty": "hard"
    },
    "engineering manager": {
        "technical_ratio": 0.2,
        "system_design_ratio": 0.3,
        "behavioral_ratio": 0.5,
        "typical_difficulty": "medium"
    },
    "frontend engineer": {
        "focus_topics": ["react", "javascript", "css", "dom", "performance"],
        "technical_ratio": 0.6,
        "system_design_ratio": 0.2,
        "behavioral_ratio": 0.2
    },
    "backend engineer": {
        "focus_topics": ["databases", "apis", "microservices", "caching"],
        "technical_ratio": 0.5,
        "system_design_ratio": 0.4,
        "behavioral_ratio": 0.1
    },
    "fullstack engineer": {
        "technical_ratio": 0.5,
        "system_design_ratio": 0.3,
        "behavioral_ratio": 0.2
    }
}


class PredictiveInterview:
    """Predict interview questions based on company, role, and history"""

    def __init__(self):
        self.question_db = COMMON_QUESTIONS_DB

    def get_company_predictions(
        self,
        company_name: str,
        role: Optional[str] = None,
        num_questions: int = 10
    ) -> Dict:
        """
        Get predicted questions for a company/role combination.

        Args:
            company_name: Target company (e.g., "Google", "Meta")
            role: Job role (e.g., "Senior Software Engineer")
            num_questions: Number of predictions to return

        Returns:
            Dictionary with predictions and metadata
        """
        company = self._normalize_company_name(company_name)
        normalized_role = self._normalize_role(role) if role else None

        # Get company data from database
        company_data = self.question_db.get(company, {})

        if not company_data:
            return {
                "company": company_name,
                "role": role,
                "predictions": [],
                "confidence": 0.0,
                "message": "No data available for this company"
            }

        # Get role patterns
        role_pattern = ROLE_PATTERNS.get(normalized_role, ROLE_PATTERNS["software engineer"])

        # Generate predictions
        predictions = []

        # Weight categories by role
        categories = []
        if "technical_ratio" in role_pattern:
            tech_count = int(num_questions * role_pattern["technical_ratio"])
            categories.extend(["technical"] * tech_count)

        if "system_design_ratio" in role_pattern:
            sd_count = int(num_questions * role_pattern["system_design_ratio"])
            categories.extend(["system_design"] * sd_count)

        if "behavioral_ratio" in role_pattern:
            beh_count = int(num_questions * role_pattern["behavioral_ratio"])
            categories.extend(["behavioral"] * beh_count)

        # Fill remaining with technical
        while len(categories) < num_questions:
            categories.append("technical")

        # Select questions from each category, avoiding duplicates
        seen_questions = set()
        for category in categories[:num_questions]:
            if category in company_data:
                # Sort by frequency and pick top ones
                questions = sorted(
                    company_data[category],
                    key=lambda x: x.get("frequency", 0),
                    reverse=True
                )

                # Add top question from this category that hasn't been seen yet
                for q in questions:
                    question_key = q.get("question", "")
                    if question_key not in seen_questions:
                        seen_questions.add(question_key)
                        predictions.append({
                            **q,
                            "category": category,
                            "likelihood": self._calculate_likelihood(q, company)
                        })
                        break

        # Sort by likelihood
        predictions.sort(key=lambda x: x.get("likelihood", 0), reverse=True)

        # Calculate overall confidence
        confidence = self._calculate_confidence(company, normalized_role, len(predictions))

        return {
            "company": company_name,
            "role": role,
            "predictions": predictions[:num_questions],
            "confidence": confidence,
            "stats": {
                "total_questions_in_db": sum(len(v) for v in company_data.values()),
                "categories_covered": list(company_data.keys()),
                "role_pattern_applied": bool(normalized_role)
            }
        }

    def get_preparation_checklist(
        self,
        company_name: str,
        role: Optional[str] = None
    ) -> Dict:
        """
        Generate a preparation checklist for an interview.

        Returns structured preparation tasks organized by category.
        """
        company = self._normalize_company_name(company_name)
        normalized_role = self._normalize_role(role) if role else None

        predictions = self.get_company_predictions(company, role, num_questions=15)

        # Organize by category
        by_category = {}
        for pred in predictions["predictions"]:
            cat = pred.get("category", "other")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(pred)

        # Generate checklist items
        checklist = {
            "technical_prep": [
                "Review data structures: arrays, trees, graphs, hash maps",
                "Practice 5 medium/hard LeetCode problems",
                "Review time/space complexity analysis",
                "Prepare to explain your thought process out loud"
            ],
            "system_design_prep": [
                "Review system design fundamentals (load balancing, caching, databases)",
                "Practice designing a scalable web application",
                "Study trade-offs between different architectures",
                "Prepare diagrams to explain your design"
            ],
            "behavioral_prep": [
                "Prepare 5 STAR-format stories (Situation, Task, Action, Result)",
                "Review leadership principles (if applicable to company)",
                "Prepare questions to ask the interviewer",
                "Research company culture and recent news"
            ],
            "company_specific": [
                f"Research {company_name}'s products and tech stack",
                f"Review {company_name}'s engineering blog",
                "Check recent Glassdoor interview experiences"
            ]
        }

        # Add predicted questions to checklist
        if "technical" in by_category:
            checklist["likely_technical"] = [
                f"Practice: {q['question']}" for q in by_category["technical"][:3]
            ]

        if "system_design" in by_category:
            checklist["likely_system_design"] = [
                f"Outline: {q['question']}" for q in by_category["system_design"][:2]
            ]

        if "behavioral" in by_category:
            checklist["likely_behavioral"] = [
                f"Prepare story for: {q['question']}" for q in by_category["behavioral"][:3]
            ]

        return {
            "company": company_name,
            "role": role,
            "predictions_summary": predictions,
            "checklist": checklist,
            "estimated_prep_time": self._estimate_prep_time(by_category)
        }

    def analyze_user_history(
        self,
        user_id: str,
        company_name: Optional[str] = None
    ) -> Dict:
        """
        Analyze user's interview history to find gaps.

        This would integrate with cognitive graph to find:
        - Weak topics
        - Companies user has seen before
        - Skill progression areas
        """
        # This is a placeholder - would integrate with cognitive_graph.py
        # to query actual user history

        return {
            "user_id": user_id,
            "company": company_name,
            "gaps": [
                "System design questions show lower confidence",
                "Consider practicing more behavioral questions"
            ],
            "recommended_focus": ["distributed systems", "leadership principles"],
            "message": "Full history analysis requires cognitive graph data"
        }

    def _normalize_company_name(self, name: str) -> str:
        """Normalize company name to match database keys.

        Tries exact alias lookup first, then semantic similarity matching
        via EmbeddingService if available.
        """
        name = name.strip().lower()

        # Fast path: exact alias lookup
        aliases = {
            "google": "Google",
            "alphabet": "Google",
            "meta": "Meta",
            "facebook": "Meta",
            "amazon": "Amazon",
            "microsoft": "Microsoft",
            "apple": "Apple",
            "netflix": "Netflix",
            "uber": "Uber",
            "airbnb": "Airbnb",
            "linkedin": "LinkedIn",
            "twitter": "Twitter",
            "x": "Twitter",
            "stripe": "Stripe",
            "lyft": "Lyft",
            "doordash": "DoorDash",
            "instacart": "Instacart",
            "coinbase": "Coinbase",
            "robinhood": "Robinhood",
            "openai": "OpenAI",
            "anthropic": "Anthropic",
            "snowflake": "Snowflake",
            "databricks": "Databricks",
            "salesforce": "Salesforce",
            "oracle": "Oracle",
            "adobe": "Adobe",
            "shopify": "Shopify",
            "spotify": "Spotify",
            "dropbox": "Dropbox",
            "slack": "Slack",
            "zoom": "Zoom",
            "tiktok": "TikTok",
            "bytedance": "TikTok",
            "snapchat": "Snapchat",
            "snap": "Snapchat",
            "pinterest": "Pinterest",
            "reddit": "Reddit"
        }

        if name in aliases:
            return aliases[name]

        # Semantic fallback: find closest company name via embeddings
        try:
            from modules.ai.embedding_service import get_embedding_service, EMBEDDING_AVAILABLE
            if EMBEDDING_AVAILABLE:
                service = get_embedding_service()
                if service:
                    company_names = list(self.question_db.keys())
                    results = service.find_most_similar(name, company_names, top_k=1, threshold=0.5)
                    if results:
                        return company_names[results[0][0]]
        except Exception:
            pass

        return name.capitalize()

    def _normalize_role(self, role: str) -> str:
        """Normalize role to match pattern keys"""
        if not role:
            return "software engineer"

        role = role.lower().strip()

        # Extract base role
        if "staff" in role:
            return "staff engineer"
        elif "senior" in role or "sr." in role:
            return "senior software engineer"
        elif "manager" in role:
            return "engineering manager"
        elif "frontend" in role or "front-end" in role:
            return "frontend engineer"
        elif "backend" in role or "back-end" in role:
            return "backend engineer"
        elif "fullstack" in role or "full-stack" in role or "full stack" in role:
            return "fullstack engineer"

        return "software engineer"

    def _calculate_likelihood(self, question: Dict, company: str) -> float:
        """Calculate likelihood score for a question"""
        base_freq = question.get("frequency", 0.5)

        # Boost for high-frequency questions
        if base_freq > 0.8:
            base_freq *= 1.2

        return min(base_freq, 1.0)

    def _calculate_confidence(
        self,
        company: str,
        role: Optional[str],
        num_predictions: int
    ) -> float:
        """Calculate overall confidence in predictions"""
        if company not in self.question_db:
            return 0.1

        base_confidence = 0.6

        # Increase confidence for well-known companies
        if company in ["Google", "Meta", "Amazon"]:
            base_confidence += 0.2

        # Decrease if few predictions
        if num_predictions < 5:
            base_confidence -= 0.2

        # Increase if role is specified
        if role:
            base_confidence += 0.1

        return min(max(base_confidence, 0.0), 1.0)

    def _estimate_prep_time(self, by_category: Dict) -> str:
        """Estimate preparation time based on categories"""
        total_items = sum(len(v) for v in by_category.values())

        if total_items < 5:
            return "2-3 days"
        elif total_items < 10:
            return "4-7 days"
        else:
            return "1-2 weeks"


# Global instance
predictive_interview = PredictiveInterview()


# Convenience functions
def get_predictions(company: str, role: Optional[str] = None, num_questions: int = 10) -> Dict:
    """Get predictions for a company/role"""
    return predictive_interview.get_company_predictions(company, role, num_questions)


def get_checklist(company: str, role: Optional[str] = None) -> Dict:
    """Get preparation checklist"""
    return predictive_interview.get_preparation_checklist(company, role)


def analyze_history(user_id: str, company: Optional[str] = None) -> Dict:
    """Analyze user interview history"""
    return predictive_interview.analyze_user_history(user_id, company)
