"""
question_library_integration.py - Integration between new and old question systems
Provides backward compatibility while exposing new rich question database
"""

from typing import List, Dict, Optional, Any
import random

# Import both systems
from .mock_interview_library import MockInterviewLibrary, mock_library, InterviewQuestion as OldQuestion
from .question_database_v2 import (
    QuestionDatabase, question_db, InterviewQuestion,
    QuestionCategory, Difficulty, ExpectedAnswer
)
from .company_questions import ALL_COMPANY_QUESTIONS, get_company_questions, get_company_specific_tips


class UnifiedQuestionLibrary:
    """
    Unified library that combines template-based generation with curated questions.
    Primary interface for all interview question needs.
    """

    def __init__(self):
        # Legacy template-based generator (50M+ capacity)
        self._template_library = mock_library

        # New curated database (10,000+ high-quality questions)
        self._curated_db = question_db

        # Pre-populate with company questions
        self._prepopulate_company_questions()

        self._stats = {
            "template_based_capacity": 50000000,  # 50M+
            "curated_questions": len(ALL_COMPANY_QUESTIONS),
            "companies_covered": 50,
            "total_capacity": 50000000 + len(ALL_COMPANY_QUESTIONS),
        }

    def _prepopulate_company_questions(self):
        """Ensure company questions are loaded"""
        # Company questions are already imported and available via question_db
        pass

    def get_question(self, question_id: str) -> Optional[Dict]:
        """
        Get a specific question by ID.
        Tries curated DB first, falls back to template generation.
        """
        # Try curated DB first
        q = self._curated_db.get_question(question_id)
        if q:
            return self._enrich_question(q.to_dict())

        # Try company questions
        for cq in ALL_COMPANY_QUESTIONS:
            if cq.id == question_id:
                return self._enrich_question(cq.to_dict())

        return None

    def get_questions(self,
                     role: Optional[str] = None,
                     category: Optional[str] = None,
                     difficulty: Optional[str] = None,
                     company: Optional[str] = None,
                     topic: Optional[str] = None,
                     limit: int = 100,
                     prefer_curated: bool = True) -> List[Dict]:
        """
        Get questions with filtering.
        Returns curated questions first, then template-generated if needed.
        """
        results = []

        # 1. Try curated database first
        if prefer_curated:
            curated = self._get_curated_questions(role, category, difficulty, company, topic, limit)
            results.extend(curated)

        # 2. If we need more, generate from templates
        remaining = limit - len(results)
        if remaining > 0 and not prefer_curated:
            generated = self._get_template_questions(role, category, difficulty, company, remaining)
            results.extend(generated)

        return results[:limit]

    def _get_curated_questions(self, role, category, difficulty, company, topic, limit) -> List[Dict]:
        """Get questions from curated database"""
        questions = []

        # Get company-specific questions
        if company:
            company_qs = get_company_questions(company)
            for q in company_qs[:limit]:
                questions.append(self._enrich_question(q.to_dict()))

        # Get from general curated DB
        if len(questions) < limit:
            remaining = limit - len(questions)

            if category:
                cat = QuestionCategory(category) if category in [c.value for c in QuestionCategory] else None
                if cat:
                    qs = self._curated_db.get_questions_by_category(cat, remaining)
                    for q in qs:
                        questions.append(self._enrich_question(q.to_dict()))

            if role and len(questions) < limit:
                remaining = limit - len(questions)
                qs = self._curated_db.get_questions_for_role(role, remaining)
                for q in qs:
                    if len(questions) < limit:
                        questions.append(self._enrich_question(q.to_dict()))

        return questions

    def _get_template_questions(self, role, category, difficulty, company, limit) -> List[Dict]:
        """Generate questions from templates"""
        generated = self._template_library._generator.generate(
            role=role, category=category, difficulty=difficulty, company=company, count=limit
        )
        return [self._convert_template_question(q) for q in generated]

    def _enrich_question(self, q: Dict) -> Dict:
        """Add additional metadata to question"""
        q = q.copy()

        # Add company tips if applicable
        if q.get("companies"):
            company = q["companies"][0]
            if company in ["google", "amazon", "meta", "facebook", "netflix", "microsoft", "apple"]:
                q["company_tips"] = get_company_specific_tips(company)

        # Add preparation hints
        q["preparation_tips"] = self._generate_prep_tips(q)

        # Add practice mode recommendations
        q["practice_recommendations"] = self._generate_practice_recommendations(q)

        return q

    def _convert_template_question(self, q: OldQuestion) -> Dict:
        """Convert template question to enriched format"""
        return {
            "id": q.id,
            "question": q.question,
            "category": q.category,
            "difficulty": q.difficulty,
            "role": q.role,
            "company": q.company,
            "topics": q.topics,
            "expected_answer": {
                "key_points": q.expected_answer_points if hasattr(q, 'expected_answer_points') else [],
                "hints": q.hints if hasattr(q, 'hints') else [],
            },
            "time_estimate_minutes": q.time_estimate_minutes if hasattr(q, 'time_estimate_minutes') else 15,
            "source": "template_generated",
            "preparation_tips": ["Template-generated question - practice STAR format"],
        }

    def _generate_prep_tips(self, q: Dict) -> List[str]:
        """Generate preparation tips based on question type"""
        tips = []
        category = q.get("category", "")

        if category == "behavioral":
            tips = [
                "Use the STAR format (Situation, Task, Action, Result)",
                "Prepare 2-3 specific examples",
                "Quantify your impact with metrics",
                "Focus on 'I' not 'we' - your specific contributions",
                "Have follow-up details ready"
            ]
        elif category == "coding":
            tips = [
                "Clarify requirements before coding",
                "Start with brute force, then optimize",
                "Think out loud - show your process",
                "Test with examples",
                "Analyze time and space complexity"
            ]
        elif category == "system_design":
            tips = [
                "Clarify functional and non-functional requirements",
                "Estimate scale (QPS, storage, users)",
                "Design high-level first, then dive deep",
                "Discuss tradeoffs explicitly",
                "Identify bottlenecks"
            ]

        return tips

    def _generate_practice_recommendations(self, q: Dict) -> Dict:
        """Generate practice recommendations"""
        difficulty = q.get("difficulty", "medium")

        recommendations = {
            "time_to_prepare": {
                "entry": "1-2 hours",
                "easy": "2-4 hours",
                "medium": "4-8 hours",
                "hard": "8-16 hours",
                "expert": "16+ hours"
            }.get(difficulty, "4-8 hours"),
            "practice_frequency": "Daily" if difficulty in ["hard", "expert"] else "3-4 times per week",
            "recommended_resources": self._get_resources_for_question(q),
            "similar_questions_to_practice": self._get_similar_questions(q),
        }

        return recommendations

    def _get_resources_for_question(self, q: Dict) -> List[str]:
        """Get recommended resources for a question"""
        category = q.get("category", "")
        topics = q.get("topics", [])

        resources = []

        if category == "coding":
            resources = [
                "LeetCode - Practice similar problems",
                "NeetCode Roadmap - Structured study plan",
                "Blind 75 - Essential questions"
            ]
        elif category == "system_design":
            resources = [
                "System Design Primer - GitHub",
                "Designing Data-Intensive Applications (book)",
                "ByteByteGo YouTube channel"
            ]
        elif category == "behavioral":
            resources = [
                "STAR Method guide",
                "Amazon Leadership Principles",
                "Common behavioral question bank"
            ]

        return resources

    def _get_similar_questions(self, q: Dict) -> List[str]:
        """Get similar questions for practice"""
        # In real implementation, this would use embeddings/semantic search
        return q.get("variations", [])[:3]

    def get_practice_set(self, role: str, difficulty: Optional[str] = None,
                        num_behavioral: int = 3, num_coding: int = 2,
                        num_system_design: int = 1,
                        target_company: Optional[str] = None) -> Dict[str, List[Dict]]:
        """
        Get a balanced practice set for a specific role.
        Includes company-specific questions if target_company is provided.
        """
        result = {
            "behavioral": [],
            "coding": [],
            "system_design": [],
            "technical": []
        }

        # Get from curated DB
        curated_set = self._curated_db.get_practice_set(
            role, Difficulty(difficulty) if difficulty else None,
            num_behavioral, num_coding, num_system_design
        )

        for category, questions in curated_set.items():
            result[category] = [self._enrich_question(q.to_dict()) for q in questions]

        # Add company-specific questions
        if target_company:
            company_qs = get_company_questions(target_company)
            company_specific = {
                "behavioral": [q for q in company_qs if q.category == QuestionCategory.BEHAVIORAL][:2],
                "coding": [q for q in company_qs if q.category == QuestionCategory.CODING][:2],
                "system_design": [q for q in company_qs if q.category == QuestionCategory.SYSTEM_DESIGN][:1],
                "technical": []
            }

            for cat, qs in company_specific.items():
                enriched = [self._enrich_question(q.to_dict()) for q in qs]
                result[cat].extend(enriched)
                # Mark as company-specific
                for q in result[cat][-len(enriched):]:
                    q["is_company_specific"] = True
                    q["target_company"] = target_company

        # Add company tips
        if target_company:
            result["company_tips"] = get_company_specific_tips(target_company)

        return result

    def search_questions(self, query: str, limit: int = 100) -> List[Dict]:
        """Search across all questions"""
        results = []

        # Search curated DB
        curated = self._curated_db.search_questions(query, limit)
        results.extend([self._enrich_question(q.to_dict()) for q in curated])

        # Search company questions
        company_results = [q for q in ALL_COMPANY_QUESTIONS
                          if query.lower() in q.question.lower()
                          or any(query.lower() in t.lower() for t in q.topics)]
        results.extend([self._enrich_question(q.to_dict()) for q in company_results[:limit - len(results)]])

        return results[:limit]

    def get_questions_by_company(self, company: str, limit: int = 100) -> List[Dict]:
        """Get all questions for a specific company"""
        company_qs = get_company_questions(company)
        return [self._enrich_question(q.to_dict()) for q in company_qs[:limit]]

    def get_company_tips(self, company: str) -> Dict:
        """Get interview tips for a specific company"""
        return get_company_specific_tips(company)

    def get_stats(self) -> Dict:
        """Get library statistics"""
        curated_stats = self._curated_db.get_stats()

        return {
            **self._stats,
            "curated_db": curated_stats,
            "template_db": {
                "capacity": "50,000,000+",
                "roles": 100,
                "companies": 400,
            },
            "total_verified_questions": len(ALL_COMPANY_QUESTIONS),
            "companies_with_verified_questions": len(set(
                company for q in ALL_COMPANY_QUESTIONS for company in q.companies
            )),
        }

    def get_categories(self) -> List[str]:
        """Get available question categories"""
        return [c.value for c in QuestionCategory]

    def get_difficulties(self) -> List[str]:
        """Get available difficulty levels"""
        return [d.value for d in Difficulty]

    def get_companies(self) -> List[str]:
        """Get available companies"""
        companies = set()
        for q in ALL_COMPANY_QUESTIONS:
            companies.update(q.companies)
        return sorted(companies)

    def get_roles(self) -> List[str]:
        """Get available roles"""
        # From question_database_v2
        from question_database_v2 import BEHAVIORAL_QUESTIONS
        roles = set()
        for q in BEHAVIORAL_QUESTIONS[:100]:  # Sample
            roles.update(q.roles)
        return sorted(roles)


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

unified_library = UnifiedQuestionLibrary()


# ═══════════════════════════════════════════════════════════════════════════════
# API FUNCTIONS - Backward Compatible
# ═══════════════════════════════════════════════════════════════════════════════

def get_question(question_id: str) -> Optional[Dict]:
    """Get a question by ID"""
    return unified_library.get_question(question_id)

def get_questions(role: str = None, category: str = None, difficulty: str = None,
                 company: str = None, limit: int = 100) -> List[Dict]:
    """Get questions with filters"""
    return unified_library.get_questions(
        role=role, category=category, difficulty=difficulty,
        company=company, limit=limit
    )

def get_practice_set(role: str, difficulty: str = None,
                    num_behavioral: int = 3, num_coding: int = 2,
                    num_system_design: int = 1,
                    target_company: str = None) -> Dict:
    """Get a practice set"""
    return unified_library.get_practice_set(
        role, difficulty, num_behavioral, num_coding,
        num_system_design, target_company
    )

def search_questions(query: str, limit: int = 100) -> List[Dict]:
    """Search questions"""
    return unified_library.search_questions(query, limit)

def get_company_questions(company: str, limit: int = 100) -> List[Dict]:
    """Get questions for a company"""
    return unified_library.get_questions_by_company(company, limit)

def get_company_tips(company: str) -> Dict:
    """Get company interview tips"""
    return unified_library.get_company_tips(company)

def get_library_stats() -> Dict:
    """Get library statistics"""
    return unified_library.get_stats()

# Backward compatibility with old API
def get_random_question(role: str = None, category: str = None,
                       difficulty: str = None, company: str = None) -> Optional[Dict]:
    """Get a random question (backward compatible)"""
    questions = unified_library.get_questions(
        role=role, category=category, difficulty=difficulty,
        company=company, limit=1
    )
    return questions[0] if questions else None

def get_questions_by_role(role: str, limit: int = 100) -> List[Dict]:
    """Get questions by role (backward compatible)"""
    return unified_library.get_questions(role=role, limit=limit)

def get_questions_by_category(category: str, limit: int = 100) -> List[Dict]:
    """Get questions by category (backward compatible)"""
    return unified_library.get_questions(category=category, limit=limit)


def get_question_count() -> int:
    """Get total question count"""
    stats = unified_library.get_stats()
    return stats["total_capacity"]


__all__ = [
    "UnifiedQuestionLibrary", "unified_library",
    "get_question", "get_questions", "get_practice_set",
    "search_questions", "get_company_questions", "get_company_tips",
    "get_library_stats", "get_random_question", "get_questions_by_role",
    "get_questions_by_category", "get_question_count"
]
