"""
interview_simulator.py - AI-Powered Interview Simulator

Conducts mock interviews with real-time feedback:
- Selects questions based on company/role
- Records user responses via STT
- AI evaluates answers for completeness, structure, technical accuracy
- Provides immediate feedback
- Saves session to cognitive graph

This is Phase 3: Interview Simulator feature.
"""

import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger("interview_simulator")


class InterviewState(Enum):
    IDLE = "idle"
    QUESTION_ASKING = "question_asking"
    LISTENING = "listening"
    EVALUATING = "evaluating"
    FEEDBACK = "feedback"
    COMPLETED = "completed"


@dataclass
class InterviewSession:
    """Represents an active interview simulation session"""
    id: str
    company: str
    role: str
    started_at: datetime
    questions: List[Dict]
    current_question_idx: int = 0
    answers: List[Dict] = None
    state: str = "idle"
    user_id: str = "default"

    def __post_init__(self):
        if self.answers is None:
            self.answers = []

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "company": self.company,
            "role": self.role,
            "started_at": self.started_at.isoformat(),
            "questions": self.questions,
            "current_question_idx": self.current_question_idx,
            "answers": self.answers,
            "state": self.state,
            "user_id": self.user_id
        }


@dataclass
class AnswerEvaluation:
    """Evaluation of a user's answer"""
    completeness_score: float  # 0-100
    structure_score: float  # 0-100 (STAR method, clarity)
    technical_accuracy: float  # 0-100 (for technical questions)
    overall_score: float  # 0-100
    strengths: List[str]
    improvements: List[str]
    missing_points: List[str]
    suggested_follow_up: Optional[str]

    def to_dict(self) -> Dict:
        return asdict(self)


class InterviewSimulator:
    """
    AI-Powered Interview Simulator
    """

    def __init__(self):
        self.sessions: Dict[str, InterviewSession] = {}
        self.predictive_interview = None
        self.ai_router = None
        self.cognitive_graph = None
        self._load_dependencies()

    def _load_dependencies(self):
        """Lazy load dependencies"""
        try:
            from predictive_interview import predictive_interview
            self.predictive_interview = predictive_interview
        except ImportError:
            logger.warning("[InterviewSimulator] predictive_interview not available")

        try:
            from ai_router import ai_router
            self.ai_router = ai_router
        except ImportError:
            logger.warning("[InterviewSimulator] ai_router not available")

        try:
            from cognitive_graph import cognitive_graph
            self.cognitive_graph = cognitive_graph
        except ImportError:
            logger.warning("[InterviewSimulator] cognitive_graph not available")

    def create_session(
        self,
        company: str,
        role: Optional[str] = None,
        num_questions: int = 5,
        user_id: str = "default",
        difficulty: Optional[str] = None
    ) -> Dict:
        """
        Create a new interview simulation session.

        Args:
            company: Target company (e.g., "Google", "Meta")
            role: Job role (e.g., "Senior Software Engineer")
            num_questions: Number of questions to ask
            user_id: User identifier
            difficulty: Filter by difficulty (easy/medium/hard)

        Returns:
            Session details with selected questions
        """
        session_id = str(uuid.uuid4())

        # Get predicted questions
        if self.predictive_interview:
            prediction = self.predictive_interview.get_company_predictions(
                company, role, num_questions * 2  # Get extra for filtering
            )
            questions = prediction.get("predictions", [])

            # Filter by difficulty if specified
            if difficulty:
                questions = [q for q in questions if q.get("difficulty") == difficulty]

            # Take only what we need
            questions = questions[:num_questions]
        else:
            # Fallback: generic questions
            questions = self._get_generic_questions(num_questions)

        if not questions:
            questions = self._get_generic_questions(num_questions)

        # Create session
        session = InterviewSession(
            id=session_id,
            company=company,
            role=role or "Software Engineer",
            started_at=datetime.now(),
            questions=questions,
            current_question_idx=0,
            state="idle",
            user_id=user_id
        )

        self.sessions[session_id] = session

        logger.info(f"[InterviewSimulator] Created session {session_id} for {company} {role}")

        return {
            "session_id": session_id,
            "company": company,
            "role": role,
            "total_questions": len(questions),
            "questions": questions,
            "status": "created"
        }

    def _get_generic_questions(self, num: int) -> List[Dict]:
        """Fallback generic interview questions"""
        generic = [
            {
                "question": "Tell me about yourself and your background.",
                "category": "behavioral",
                "difficulty": "easy",
                "frequency": 0.95
            },
            {
                "question": "Describe a challenging project you worked on.",
                "category": "behavioral",
                "difficulty": "medium",
                "frequency": 0.90
            },
            {
                "question": "Why do you want to work at this company?",
                "category": "behavioral",
                "difficulty": "medium",
                "frequency": 0.95
            },
            {
                "question": "Explain the difference between REST and GraphQL.",
                "category": "technical",
                "difficulty": "medium",
                "frequency": 0.70
            },
            {
                "question": "How would you design a URL shortener like bit.ly?",
                "category": "system_design",
                "difficulty": "medium",
                "frequency": 0.80
            },
            {
                "question": "What happens when you type a URL in your browser?",
                "category": "technical",
                "difficulty": "medium",
                "frequency": 0.75
            },
            {
                "question": "Describe a time you had to learn something quickly.",
                "category": "behavioral",
                "difficulty": "medium",
                "frequency": 0.85
            },
            {
                "question": "How do you handle tight deadlines and pressure?",
                "category": "behavioral",
                "difficulty": "medium",
                "frequency": 0.80
            }
        ]
        return generic[:num]

    def get_next_question(self, session_id: str) -> Optional[Dict]:
        """
        Get the next question in the session.

        Returns:
            Question data or None if interview complete
        """
        session = self.sessions.get(session_id)
        if not session:
            return None

        if session.current_question_idx >= len(session.questions):
            return None

        question = session.questions[session.current_question_idx]
        session.state = "question_asking"

        return {
            "session_id": session_id,
            "question_number": session.current_question_idx + 1,
            "total_questions": len(session.questions),
            "question": question.get("question"),
            "category": question.get("category", "general"),
            "difficulty": question.get("difficulty", "medium"),
            "progress_percent": int((session.current_question_idx / len(session.questions)) * 100)
        }

    def submit_answer(
        self,
        session_id: str,
        transcript: str,
        duration_ms: int = 0
    ) -> Dict:
        """
        Submit user's answer and get AI evaluation.

        Args:
            session_id: Active session ID
            transcript: User's spoken answer text
            duration_ms: Answer duration in milliseconds

        Returns:
            Evaluation results and next steps
        """
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        if session.current_question_idx >= len(session.questions):
            return {"error": "No more questions"}

        current_question = session.questions[session.current_question_idx]

        # Store answer
        answer_record = {
            "question_idx": session.current_question_idx,
            "question": current_question.get("question"),
            "transcript": transcript,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat()
        }
        session.answers.append(answer_record)

        # Evaluate answer
        evaluation = self._evaluate_answer(
            current_question.get("question"),
            transcript,
            current_question.get("category", "general"),
            current_question.get("difficulty", "medium")
        )

        # Add evaluation to answer record
        answer_record["evaluation"] = evaluation.to_dict()

        # Move to next question
        session.current_question_idx += 1

        # Check if complete
        is_complete = session.current_question_idx >= len(session.questions)

        if is_complete:
            session.state = "completed"
            summary = self._generate_session_summary(session)
            answer_record["summary"] = summary

        return {
            "session_id": session_id,
            "evaluation": evaluation.to_dict(),
            "is_complete": is_complete,
            "next_question": None if is_complete else self.get_next_question(session_id),
            "progress": {
                "answered": len(session.answers),
                "total": len(session.questions)
            }
        }

    def _evaluate_answer(
        self,
        question: str,
        answer: str,
        category: str,
        difficulty: str
    ) -> AnswerEvaluation:
        """
        Use AI to evaluate the user's answer.

        For now, uses rule-based evaluation with AI enhancement.
        """
        # Rule-based scoring
        completeness = self._score_completeness(answer, category)
        structure = self._score_structure(answer, category)

        # Technical accuracy (only for technical questions)
        if category in ["technical", "system_design"]:
            technical = self._score_technical(answer, question)
        else:
            technical = 70.0  # Default for behavioral

        # Calculate overall
        if category == "behavioral":
            overall = (completeness * 0.4 + structure * 0.4 + technical * 0.2)
        elif category == "system_design":
            overall = (completeness * 0.3 + structure * 0.3 + technical * 0.4)
        else:
            overall = (completeness * 0.35 + structure * 0.35 + technical * 0.3)

        # Generate feedback
        strengths = self._identify_strengths(answer, category)
        improvements = self._identify_improvements(answer, category, completeness, structure)
        missing = self._identify_missing_points(answer, question, category)

        # Get AI-enhanced feedback if available
        if self.ai_router:
            try:
                ai_feedback = self._get_ai_feedback(question, answer, category)
                if ai_feedback:
                    strengths.extend(ai_feedback.get("strengths", []))
                    improvements.extend(ai_feedback.get("improvements", []))
            except Exception as e:
                logger.error("[InterviewSimulator] AI feedback error: %s", str(e))

        return AnswerEvaluation(
            completeness_score=round(completeness, 1),
            structure_score=round(structure, 1),
            technical_accuracy=round(technical, 1),
            overall_score=round(overall, 1),
            strengths=list(set(strengths))[:3],  # Max 3, unique
            improvements=list(set(improvements))[:3],
            missing_points=missing[:3],
            suggested_follow_up=self._generate_follow_up(question, answer, category) if overall < 70 else None
        )

    def _score_completeness(self, answer: str, category: str) -> float:
        """Score answer completeness based on length and content"""
        word_count = len(answer.split())

        if category == "behavioral":
            # Behavioral: expect STAR format, 100-300 words
            if word_count < 30:
                return 40.0
            elif word_count < 80:
                return 60.0
            elif word_count < 150:
                return 80.0
            else:
                return 90.0
        elif category == "system_design":
            # System design: expect comprehensive answer
            if word_count < 50:
                return 30.0
            elif word_count < 150:
                return 60.0
            elif word_count < 300:
                return 80.0
            else:
                return 95.0
        else:
            # Technical: depends on question
            if word_count < 20:
                return 50.0
            elif word_count < 50:
                return 70.0
            else:
                return 85.0

    def _score_structure(self, answer: str, category: str) -> float:
        """Score answer structure"""
        score = 70.0  # Base

        # Check for structure indicators
        lower_answer = answer.lower()

        if category == "behavioral":
            # STAR method indicators
            star_indicators = [
                ("situation", 10), ("context", 5),
                ("task", 10), ("needed to", 5), ("responsible for", 5),
                ("action", 10), ("i did", 5), ("i implemented", 5),
                ("result", 10), ("outcome", 10), ("achieved", 5),
                ("learned", 5)
            ]
            for indicator, points in star_indicators:
                if indicator in lower_answer:
                    score += points

        elif category == "system_design":
            # System design structure
            structure_indicators = [
                ("requirements", 15), ("functional", 10), ("non-functional", 10),
                ("api", 10), ("database", 10), ("cache", 10),
                ("scale", 10), ("bottleneck", 10), ("trade", 10)
            ]
            for indicator, points in structure_indicators:
                if indicator in lower_answer:
                    score += points

        else:
            # Technical questions
            if "for example" in lower_answer or "instance" in lower_answer:
                score += 10
            if "because" in lower_answer or "since" in lower_answer:
                score += 10

        return min(score, 100.0)

    def _score_technical(self, answer: str, question: str) -> float:
        """Score technical accuracy (simplified)"""
        # This would ideally use AI or domain-specific evaluation
        # For now, check for technical keywords and explanation depth
        score = 60.0
        lower_answer = answer.lower()

        # Technical depth indicators
        technical_terms = [
            "algorithm", "complexity", "O(", "time", "space",
            "database", "cache", "API", "HTTP", "REST", "JSON",
            "scalability", "performance", "optimization",
            "distributed", "microservice", "container", "docker",
            "kubernetes", "cloud", "AWS", "azure", "gcp"
        ]

        for term in technical_terms:
            if term in lower_answer:
                score += 5

        # Check for code examples
        if "```" in answer or "def " in answer or "function" in lower_answer:
            score += 15

        return min(score, 100.0)

    def _identify_strengths(self, answer: str, category: str) -> List[str]:
        """Identify strengths in the answer"""
        strengths = []
        lower_answer = answer.lower()
        word_count = len(answer.split())

        if word_count > 100:
            strengths.append("Provided detailed response with good depth")

        if "specific" in lower_answer or "example" in lower_answer:
            strengths.append("Used specific examples to illustrate points")

        if category == "behavioral":
            if any(x in lower_answer for x in ["result", "outcome", "achieved"]):
                strengths.append("Clear outcome/results section")
            if any(x in lower_answer for x in ["learned", "takeaway", "lesson"]):
                strengths.append("Demonstrated learning and reflection")

        elif category == "system_design":
            if "trade" in lower_answer:
                strengths.append("Discussed trade-offs and alternatives")
            if "bottleneck" in lower_answer or "limitation" in lower_answer:
                strengths.append("Identified potential bottlenecks")

        if not strengths:
            strengths.append("Answered the question clearly")

        return strengths

    def _identify_improvements(
        self,
        answer: str,
        category: str,
        completeness: float,
        structure: float
    ) -> List[str]:
        """Identify areas for improvement"""
        improvements = []
        word_count = len(answer.split())

        if completeness < 60:
            improvements.append("Provide more detail and depth in your answer")

        if structure < 60:
            if category == "behavioral":
                improvements.append("Use the STAR method: Situation, Task, Action, Result")
            elif category == "system_design":
                improvements.append("Structure your answer: requirements, design, trade-offs")

        if word_count < 50 and category in ["behavioral", "system_design"]:
            improvements.append("Expand with specific examples and details")

        lower_answer = answer.lower()
        if category == "behavioral":
            if not any(x in lower_answer for x in ["i did", "i implemented", "i created"]):
                improvements.append("Emphasize YOUR specific actions (not just team)")

        if not improvements:
            improvements.append("Practice delivering more concisely")

        return improvements

    def _identify_missing_points(self, answer: str, question: str, category: str) -> List[str]:
        """Identify key points that were missing"""
        missing = []
        lower_answer = answer.lower()

        if category == "system_design":
            if "database" not in lower_answer:
                missing.append("Database design and schema")
            if "scale" not in lower_answer and "capacity" not in lower_answer:
                missing.append("Scalability considerations")
            if "api" not in lower_answer:
                missing.append("API design and endpoints")

        elif category == "technical":
            if "complexity" not in lower_answer and "O(" not in answer:
                missing.append("Time/space complexity analysis")
            if "trade" not in lower_answer:
                missing.append("Trade-offs between approaches")

        return missing

    def _generate_follow_up(self, question: str, answer: str, category: str) -> Optional[str]:
        """Generate a follow-up question if answer was weak"""
        if category == "behavioral":
            return "Can you provide more specific details about what YOU did?"
        elif category == "system_design":
            return "How would you handle data consistency across regions?"
        elif category == "technical":
            return "Can you walk through your solution with an example?"
        return None

    def _get_ai_feedback(self, question: str, answer: str, category: str) -> Optional[Dict]:
        """Get AI-powered feedback if router is available"""
        if not self.ai_router:
            return None

        prompt = f"""You are an expert interview coach. Evaluate this answer to a {category} interview question.

Question: {question}

Candidate's Answer: {answer}

Provide structured feedback:
1. Two specific strengths of this answer
2. Two specific improvements needed
3. One key point that was missing (if any)

Format as JSON:
{{
  "strengths": ["strength 1", "strength 2"],
  "improvements": ["improvement 1", "improvement 2"],
  "missing": ["missing point"]
}}"""

        try:
            response = self.ai_router.generate(prompt, mode="fast")
            # Try to parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error("[InterviewSimulator] AI feedback parsing error: %s", str(e))

        return None

    def _generate_session_summary(self, session: InterviewSession) -> Dict:
        """Generate final summary of the interview session"""
        if not session.answers:
            return {"error": "No answers recorded"}

        evaluations = [a.get("evaluation", {}) for a in session.answers]

        avg_overall = sum(e.get("overall_score", 0) for e in evaluations) / len(evaluations)
        avg_completeness = sum(e.get("completeness_score", 0) for e in evaluations) / len(evaluations)
        avg_structure = sum(e.get("structure_score", 0) for e in evaluations) / len(evaluations)

        # Category breakdown
        categories = {}
        for i, ans in enumerate(session.answers):
            cat = session.questions[i].get("category", "general")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(ans.get("evaluation", {}).get("overall_score", 0))

        category_scores = {
            cat: round(sum(scores) / len(scores), 1)
            for cat, scores in categories.items()
        }

        # Strengths and weaknesses
        all_strengths = []
        all_improvements = []
        for e in evaluations:
            all_strengths.extend(e.get("strengths", []))
            all_improvements.extend(e.get("improvements", []))

        from collections import Counter
        top_strengths = [s for s, _ in Counter(all_strengths).most_common(3)]
        top_improvements = [i for i, _ in Counter(all_improvements).most_common(3)]

        return {
            "total_questions": len(session.questions),
            "answered_questions": len(session.answers),
            "average_scores": {
                "overall": round(avg_overall, 1),
                "completeness": round(avg_completeness, 1),
                "structure": round(avg_structure, 1)
            },
            "category_breakdown": category_scores,
            "top_strengths": top_strengths,
            "top_areas_for_improvement": top_improvements,
            "estimated_readiness": self._estimate_readiness(avg_overall),
            "duration_minutes": self._calculate_duration(session)
        }

    def _estimate_readiness(self, avg_score: float) -> str:
        """Estimate interview readiness based on average score"""
        if avg_score >= 85:
            return "Excellent - You're well prepared!"
        elif avg_score >= 70:
            return "Good - Continue practicing to improve"
        elif avg_score >= 55:
            return "Fair - Focus on areas for improvement"
        else:
            return "Needs Work - Significant practice recommended"

    def _calculate_duration(self, session: InterviewSession) -> int:
        """Calculate interview duration in minutes"""
        duration = sum(a.get("duration_ms", 0) for a in session.answers)
        return int(duration / 60000)  # Convert ms to minutes

    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """Get current session status"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        return {
            "session_id": session_id,
            "state": session.state,
            "progress": {
                "answered": len(session.answers),
                "total": len(session.questions),
                "percent": int((len(session.answers) / len(session.questions)) * 100)
            },
            "current_question": session.current_question_idx + 1 if session.current_question_idx < len(session.questions) else None,
            "company": session.company,
            "role": session.role
        }

    def save_to_cognitive_graph(self, session_id: str) -> bool:
        """Save completed interview to cognitive graph"""
        session = self.sessions.get(session_id)
        if not session or session.state != "completed":
            return False

        if not self.cognitive_graph:
            logger.warning("[InterviewSimulator] Cognitive graph not available")
            return False

        try:
            from cognitive_graph import InterviewNode

            # Create interview node
            interview = InterviewNode(
                id=f"sim-{session_id}",
                title=f"Mock Interview - {session.company} {session.role}",
                timestamp=session.started_at,
                duration_ms=sum(a.get("duration_ms", 0) for a in session.answers),
                user_id=session.user_id
            )

            self.cognitive_graph.add_interview(interview)

            # Add questions and answers
            for i, (q_data, ans) in enumerate(zip(session.questions, session.answers)):
                from cognitive_graph import QuestionNode, AnswerNode

                question = QuestionNode(
                    id=f"sim-{session_id}-q{i}",
                    text=q_data.get("question"),
                    category=q_data.get("category", "general"),
                    difficulty=q_data.get("difficulty")
                )

                answer = AnswerNode(
                    id=f"sim-{session_id}-a{i}",
                    text=ans.get("transcript", "")[:500],  # Truncate for storage
                    transcript=ans.get("transcript", ""),
                    confidence=ans.get("evaluation", {}).get("overall_score", 50) / 100
                )

                self.cognitive_graph.add_question_answer(
                    f"sim-{session_id}",
                    question,
                    answer,
                    None
                )

            logger.info(f"[InterviewSimulator] Saved session {session_id} to cognitive graph")
            return True

        except Exception as e:
            logger.error("[InterviewSimulator] Failed to save to graph: %s", str(e))
            return False

    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up sessions older than specified hours"""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        to_remove = []

        for session_id, session in self.sessions.items():
            session_age = session.started_at.timestamp()
            if session_age < cutoff and session.state == "completed":
                to_remove.append(session_id)

        for session_id in to_remove:
            del self.sessions[session_id]

        return len(to_remove)


# Global instance
interview_simulator = InterviewSimulator()


# Convenience functions
def create_interview(
    company: str,
    role: Optional[str] = None,
    num_questions: int = 5,
    user_id: str = "default"
) -> Dict:
    """Create a new interview session"""
    return interview_simulator.create_session(company, role, num_questions, user_id)


def get_question(session_id: str) -> Optional[Dict]:
    """Get next question"""
    return interview_simulator.get_next_question(session_id)


def submit_response(session_id: str, transcript: str, duration_ms: int = 0) -> Dict:
    """Submit answer and get evaluation"""
    return interview_simulator.submit_answer(session_id, transcript, duration_ms)


def finish_interview(session_id: str) -> Dict:
    """Complete interview and save to graph"""
    # Save to cognitive graph
    saved = interview_simulator.save_to_cognitive_graph(session_id)

    # Get final summary
    session = interview_simulator.sessions.get(session_id)
    summary = {}
    if session and session.answers:
        last_answer = session.answers[-1]
        summary = last_answer.get("summary", {})

    return {
        "session_id": session_id,
        "saved_to_graph": saved,
        "summary": summary
    }
