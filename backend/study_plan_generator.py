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
import random
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
    category: str  # "algorithms", "system_design", "behavioral", "language"
    difficulty: str  # "easy", "medium", "hard"
    estimated_minutes: int
    resources: List[Dict]
    prerequisites: List[str] = field(default_factory=list)
    completed: bool = False
    scheduled_date: Optional[datetime] = None
    confidence_target: float = 0.8


@dataclass
class StudySession:
    """A study session with multiple tasks"""
    date: datetime
    tasks: List[StudyTask]
    total_minutes: int
    theme: str  # e.g., "Graph Algorithms", "System Design Fundamentals"


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


class SpacedRepetitionScheduler:
    """
    SM-2 Algorithm implementation for spaced repetition scheduling.
    Optimizes review intervals based on performance.
    """

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
            ef = 2.5

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
    """Library of study resources organized by category"""

    RESOURCES = {
        "algorithms": {
            "easy": [
                {
                    "name": "Two Sum",
                    "type": "leetcode",
                    "url": "https://leetcode.com/problems/two-sum/",
                    "description": "Hash map approach - O(n) time complexity"
                },
                {
                    "name": "Valid Parentheses",
                    "type": "leetcode",
                    "url": "https://leetcode.com/problems/valid-parentheses/",
                    "description": "Stack-based solution"
                },
                {
                    "name": "Merge Two Sorted Lists",
                    "type": "leetcode",
                    "url": "https://leetcode.com/problems/merge-two-sorted-lists/",
                    "description": "Linked list manipulation"
                }
            ],
            "medium": [
                {
                    "name": "Binary Tree Level Order Traversal",
                    "type": "leetcode",
                    "url": "https://leetcode.com/problems/binary-tree-level-order-traversal/",
                    "description": "BFS with queue"
                },
                {
                    "name": "3Sum",
                    "type": "leetcode",
                    "url": "https://leetcode.com/problems/3sum/",
                    "description": "Two-pointer technique"
                },
                {
                    "name": "Word Break",
                    "type": "leetcode",
                    "url": "https://leetcode.com/problems/word-break/",
                    "description": "Dynamic programming"
                }
            ],
            "hard": [
                {
                    "name": "Merge k Sorted Lists",
                    "type": "leetcode",
                    "url": "https://leetcode.com/problems/merge-k-sorted-lists/",
                    "description": "Divide and conquer / Heap"
                },
                {
                    "name": "LRU Cache",
                    "type": "leetcode",
                    "url": "https://leetcode.com/problems/lru-cache/",
                    "description": "Hash map + Doubly linked list"
                }
            ]
        },
        "system_design": {
            "easy": [
                {
                    "name": "Design URL Shortener",
                    "type": "system_design",
                    "url": "https://github.com/donnemartin/system-design-primer",
                    "description": "Hash-based shortening, database sharding"
                },
                {
                    "name": "Design Key-Value Store",
                    "type": "system_design",
                    "url": "https://github.com/donnemartin/system-design-primer",
                    "description": "CAP theorem, consistency patterns"
                }
            ],
            "medium": [
                {
                    "name": "Design News Feed",
                    "type": "system_design",
                    "url": "https://github.com/donnemartin/system-design-primer",
                    "description": "Fan-out on write vs read, caching strategies"
                },
                {
                    "name": "Design Rate Limiter",
                    "type": "system_design",
                    "url": "https://github.com/donnemartin/system-design-primer",
                    "description": "Token bucket, sliding window"
                }
            ],
            "hard": [
                {
                    "name": "Design Distributed Message Queue",
                    "type": "system_design",
                    "url": "https://github.com/donnemartin/system-design-primer",
                    "description": "Kafka-like architecture, partitioning"
                },
                {
                    "name": "Design Web Crawler",
                    "type": "system_design",
                    "url": "https://github.com/donnemartin/system-design-primer",
                    "description": "Distributed crawling, politeness"
                }
            ]
        },
        "behavioral": {
            "easy": [
                {
                    "name": "Tell me about yourself",
                    "type": "behavioral",
                    "description": "2-minute pitch with key achievements"
                },
                {
                    "name": "Why this company?",
                    "type": "behavioral",
                    "description": "Research company values and mission"
                }
            ],
            "medium": [
                {
                    "name": "Describe a conflict",
                    "type": "behavioral",
                    "description": "Use STAR: Situation, Task, Action, Result"
                },
                {
                    "name": "Tell me about a failure",
                    "type": "behavioral",
                    "description": "Emphasize learning and growth"
                }
            ],
            "hard": [
                {
                    "name": "Describe leading without authority",
                    "type": "behavioral",
                    "description": "Influence through expertise and relationships"
                },
                {
                    "name": "Tell me about a system you built",
                    "type": "behavioral",
                    "description": "Technical depth + business impact"
                }
            ]
        },
        "languages": {
            "python": [
                {"name": "Python Context Managers", "type": "concept", "description": "with statements, __enter__, __exit__"},
                {"name": "Python Generators", "type": "concept", "description": "yield, memory efficiency"},
                {"name": "Python Decorators", "type": "concept", "description": "@syntax, higher-order functions"}
            ],
            "javascript": [
                {"name": "JS Promises & Async/Await", "type": "concept", "description": "Event loop, microtasks"},
                {"name": "JS Closures", "type": "concept", "description": "Lexical scoping"},
                {"name": "JS Prototypes", "type": "concept", "description": "Prototype chain, inheritance"}
            ],
            "go": [
                {"name": "Go Concurrency", "type": "concept", "description": "Goroutines, channels, select"},
                {"name": "Go Interfaces", "type": "concept", "description": "Implicit interfaces, composition"}
            ]
        }
    }

    @classmethod
    def get_resources(
        cls,
        category: str,
        difficulty: str,
        count: int = 3
    ) -> List[Dict]:
        """Get random resources for a category/difficulty"""
        if category in ["python", "javascript", "go", "java", "cpp", "rust"]:
            # Language-specific
            resources = cls.RESOURCES.get("languages", {}).get(category, [])
        else:
            resources = cls.RESOURCES.get(category, {}).get(difficulty, [])

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

    def generate_plan(
        self,
        user_id: str,
        days: int = 30,
        daily_minutes: int = 60,
        cognitive_graph_data: Optional[Dict] = None
    ) -> StudyPlan:
        """
        Generate a complete study plan for a user.

        Args:
            user_id: User identifier
            days: Plan duration in days
            daily_minutes: Target study time per day
            cognitive_graph_data: Optional pre-fetched graph data

        Returns:
            Complete StudyPlan object
        """
        start_date = datetime.now()

        # Analyze weak and strong areas
        weak_areas = self._identify_weak_areas(cognitive_graph_data)
        strong_areas = self._identify_strong_areas(cognitive_graph_data)

        # Generate tasks based on weak areas
        tasks = self._generate_tasks(weak_areas, days)

        # Schedule tasks using spaced repetition
        schedule = self.scheduler.generate_review_schedule(tasks, start_date, days)

        # Group into daily sessions
        sessions = self._create_sessions(schedule, daily_minutes)

        # Generate milestones
        milestones = self._generate_milestones(sessions, weak_areas)

        # Calculate totals
        total_tasks = len(tasks)

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
            progress_percentage=0.0
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
        else:
            # Default weak areas if no graph data
            weak_areas = [
                {
                    "name": "Dynamic Programming",
                    "confidence": 0.3,
                    "mentions": 2,
                    "category": "algorithms"
                },
                {
                    "name": "System Design",
                    "confidence": 0.4,
                    "mentions": 3,
                    "category": "system_design"
                },
                {
                    "name": "Behavioral Questions",
                    "confidence": 0.45,
                    "mentions": 5,
                    "category": "behavioral"
                }
            ]

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
        """Generate milestone checkpoints"""
        milestones = []

        if not sessions:
            return milestones

        total_sessions = len(sessions)
        quarter = total_sessions // 4

        # 25% milestone
        if quarter > 0:
            milestones.append({
                "name": f"Foundation Complete",
                "description": f"Complete first {quarter} study sessions",
                "target_date": sessions[quarter].date.isoformat(),
                "type": "progress",
                "reward": "Unlock intermediate challenges"
            })

        # 50% milestone
        if quarter * 2 > 0 and quarter * 2 < total_sessions:
            milestones.append({
                "name": f"Halfway Point",
                "description": "50% of study plan completed",
                "target_date": sessions[quarter * 2].date.isoformat(),
                "type": "progress",
                "reward": "Schedule mock interview"
            })

        # Area-specific milestones
        for i, area in enumerate(weak_areas[:3]):
            if i * 5 + 5 < total_sessions:
                milestones.append({
                    "name": f"{area['name']} Mastery",
                    "description": f"Achieve {area['confidence'] * 100 + 20:.0f}% confidence in {area['name']}",
                    "target_date": sessions[min(i * 5 + 5, total_sessions - 1)].date.isoformat(),
                    "type": "skill",
                    "target_skill": area["name"]
                })

        # Final milestone
        milestones.append({
            "name": "Study Plan Complete",
            "description": "All sessions completed!",
            "target_date": sessions[-1].date.isoformat(),
            "type": "completion",
            "reward": "Ready for interviews!"
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
        for session in plan.sessions:
            for task in session.tasks:
                if task.id == completed_task_id:
                    task.completed = True
                    plan.completed_tasks += 1
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

    def _to_ical(self, plan: StudyPlan) -> str:
        """Convert plan to iCal format for calendar import"""
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//AI Note Taker//Study Plan//EN"
        ]

        for session in plan.sessions:
            for task in session.tasks:
                date_str = session.date.strftime("%Y%m%d")
                lines.extend([
                    "BEGIN:VEVENT",
                    f"UID:{task.id}@ainotetaker.local",
                    f"DTSTART;VALUE=DATE:{date_str}",
                    f"SUMMARY:{task.title}",
                    f"DESCRIPTION:{task.description}",
                    f"CATEGORIES:{task.category}",
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
    graph_data: Optional[Dict] = None
) -> StudyPlan:
    """Generate study plan - convenience function"""
    return study_planner.generate_plan(user_id, days, daily_minutes, graph_data)


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
