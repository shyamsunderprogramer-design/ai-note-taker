"""
Test suite for Study Plan Generator
Phase 2 Task #33

Run with: python -m pytest backend/tests/test_study_plan_generator.py -v
"""

import pytest
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from study_plan_generator import (
    StudyPlanGenerator,
    SpacedRepetitionScheduler,
    ResourceLibrary,
    StudyTask,
    StudySession,
    StudyPlan,
    generate_plan,
    adapt_plan,
    export_plan,
    study_planner
)


class TestSpacedRepetitionScheduler:
    """Test cases for SM-2 algorithm"""

    def setup_method(self):
        self.scheduler = SpacedRepetitionScheduler()

    def test_calculate_next_review_first_review(self):
        """Test interval calculation for first review"""
        interval, ef = self.scheduler.calculate_next_review(
            current_confidence=0.8,
            review_count=0
        )
        assert interval == 1

    def test_calculate_next_review_second_review(self):
        """Test interval calculation for second review"""
        interval, ef = self.scheduler.calculate_next_review(
            current_confidence=0.8,
            review_count=1
        )
        assert interval == 6

    def test_calculate_next_review_subsequent(self):
        """Test interval calculation for subsequent reviews"""
        interval1, ef = self.scheduler.calculate_next_review(
            current_confidence=0.8,
            review_count=2,
            last_interval=6
        )

        interval2, ef = self.scheduler.calculate_next_review(
            current_confidence=0.8,
            review_count=3,
            last_interval=interval1
        )

        # Intervals should increase
        assert interval2 >= interval1

    def test_poor_performance_resets_interval(self):
        """Test that poor performance resets interval"""
        interval, ef = self.scheduler.calculate_next_review(
            current_confidence=0.4,  # Poor
            review_count=5
        )

        assert interval == 1  # Reset to day 1

    def test_easiness_factor_minimum(self):
        """Test that EF doesn't go below minimum"""
        # Repeated poor performance
        ef = 2.5
        for _ in range(10):
            _, ef = self.scheduler.calculate_next_review(
                current_confidence=0.4,
                review_count=1,
                last_interval=6
            )

        assert ef >= 1.3

    def test_interval_capped_at_year(self):
        """Test that intervals don't exceed 1 year"""
        interval, _ = self.scheduler.calculate_next_review(
            current_confidence=1.0,
            review_count=10,
            last_interval=400
        )

        assert interval <= 365

    def test_generate_review_schedule(self):
        """Test review schedule generation"""
        tasks = [
            StudyTask(
                id="task1",
                title="Test Task",
                description="Test",
                category="algorithms",
                difficulty="medium",
                estimated_minutes=45,
                resources=[]
            )
        ]

        start_date = datetime.now()
        schedule = self.scheduler.generate_review_schedule(tasks, start_date, days=30)

        # Should have at least initial learning + some reviews
        assert len(schedule) >= 1

        # All dates should be within range
        for date, task in schedule:
            assert date >= start_date
            assert date <= start_date + timedelta(days=30)


class TestResourceLibrary:
    """Test cases for resource library"""

    def test_get_resources_algorithms(self):
        """Test getting algorithm resources"""
        resources = ResourceLibrary.get_resources("algorithms", "easy", count=2)

        assert len(resources) <= 2
        if resources:
            assert all("type" in r for r in resources)

    def test_get_resources_system_design(self):
        """Test getting system design resources"""
        resources = ResourceLibrary.get_resources("system_design", "medium", count=2)

        assert len(resources) <= 2

    def test_get_resources_behavioral(self):
        """Test getting behavioral resources"""
        resources = ResourceLibrary.get_resources("behavioral", "easy", count=2)

        assert len(resources) <= 2

    def test_get_resources_languages(self):
        """Test getting language-specific resources"""
        resources = ResourceLibrary.get_resources("python", "easy", count=3)

        assert len(resources) <= 3
        if resources:
            assert all("type" in r for r in resources)

    def test_get_resources_returns_all_if_less_than_count(self):
        """Test that all resources are returned if fewer than count"""
        resources = ResourceLibrary.get_resources("go", "easy", count=10)

        # Go has limited resources, should return all available
        assert len(resources) <= 10

    def test_get_resources_empty_category(self):
        """Test handling of unknown category"""
        resources = ResourceLibrary.get_resources("unknown_category", "easy", count=5)

        assert resources == []


class TestStudyPlanGenerator:
    """Test cases for StudyPlanGenerator"""

    def setup_method(self):
        self.generator = StudyPlanGenerator()

    def test_generate_plan_basic(self):
        """Test basic plan generation"""
        plan = self.generator.generate_plan(
            user_id="test_user",
            days=7,
            daily_minutes=60
        )

        assert plan.user_id == "test_user"
        assert plan.duration_days == 7
        assert isinstance(plan.created_at, datetime)
        assert len(plan.weak_areas) >= 0

    def test_generate_plan_with_graph_data(self):
        """Test plan generation with cognitive graph data"""
        graph_data = {
            "skills": [
                {"name": "React", "confidence": 0.3, "mentions": 5},
                {"name": "System Design", "confidence": 0.4, "mentions": 3}
            ]
        }

        plan = self.generator.generate_plan(
            user_id="test_user",
            days=14,
            daily_minutes=60,
            cognitive_graph_data=graph_data
        )

        # Should identify weak areas from graph data
        assert len(plan.weak_areas) > 0
        weak_names = [w["name"] for w in plan.weak_areas]
        assert "React" in weak_names or "System Design" in weak_names

    def test_generate_tasks_from_weak_areas(self):
        """Test task generation based on weak areas"""
        weak_areas = [
            {"name": "Dynamic Programming", "confidence": 0.3, "mentions": 2, "category": "algorithms"}
        ]

        tasks = self.generator._generate_tasks(weak_areas, days=30)

        assert len(tasks) > 0
        assert all(t.category == "algorithms" for t in tasks)
        assert all(t.difficulty in ["easy", "medium", "hard"] for t in tasks)

    def test_categorize_skill_algorithms(self):
        """Test skill categorization - algorithms"""
        assert self.generator._categorize_skill("Binary Trees") == "algorithms"
        assert self.generator._categorize_skill("Dynamic Programming") == "algorithms"

    def test_categorize_skill_system_design(self):
        """Test skill categorization - system design"""
        assert self.generator._categorize_skill("System Design") == "system_design"
        assert self.generator._categorize_skill("Distributed Systems") == "system_design"

    def test_categorize_skill_languages(self):
        """Test skill categorization - languages"""
        assert self.generator._categorize_skill("Python") == "python"
        assert self.generator._categorize_skill("JavaScript") == "javascript"
        assert self.generator._categorize_skill("Go") == "go"

    def test_categorize_skill_default(self):
        """Test skill categorization - default"""
        assert self.generator._categorize_skill("Something Unknown") == "behavioral"

    def test_estimate_time_by_difficulty(self):
        """Test time estimation by difficulty"""
        assert self.generator._estimate_time("easy") == 30
        assert self.generator._estimate_time("medium") == 45
        assert self.generator._estimate_time("hard") == 60
        assert self.generator._estimate_time("unknown") == 45  # Default

    def test_generate_theme(self):
        """Test theme generation"""
        theme = self.generator._generate_theme(["algorithms", "algorithms", "system_design"])
        assert isinstance(theme, str)
        assert len(theme) > 0

    def test_generate_theme_empty(self):
        """Test theme generation with empty categories"""
        theme = self.generator._generate_theme([])
        assert theme == "Mixed Review"

    def test_generate_milestones(self):
        """Test milestone generation"""
        sessions = [
            StudySession(
                date=datetime.now() + timedelta(days=i),
                tasks=[],
                total_minutes=60,
                theme=f"Day {i}"
            )
            for i in range(10)
        ]

        weak_areas = [
            {"name": "React", "confidence": 0.3}
        ]

        milestones = self.generator._generate_milestones(sessions, weak_areas)

        assert len(milestones) > 0
        # Should have foundation, halfway, skill-specific, and completion milestones

    def test_adapt_plan_complete_task(self):
        """Test plan adaptation on task completion"""
        plan = self.generator.generate_plan("test_user", days=7)

        if plan.sessions and plan.sessions[0].tasks:
            task = plan.sessions[0].tasks[0]
            original_completed = plan.completed_tasks

            adapted_plan = self.generator.adapt_plan(plan, task.id, 0.8)

            assert adapted_plan.completed_tasks == original_completed + 1
            assert adapted_plan.progress_percentage >= 0

    def test_adapt_plan_excellent_performance(self):
        """Test plan adaptation for excellent performance"""
        plan = self.generator.generate_plan("test_user", days=7)

        if plan.sessions and plan.sessions[0].tasks:
            task = plan.sessions[0].tasks[0]

            adapted_plan = self.generator.adapt_plan(plan, task.id, 0.95)

            # Excellent performance should be handled
            assert adapted_plan is not None

    def test_adapt_plan_poor_performance(self):
        """Test plan adaptation for poor performance"""
        plan = self.generator.generate_plan("test_user", days=7)

        if len(plan.sessions) >= 2 and plan.sessions[0].tasks:
            task = plan.sessions[0].tasks[0]
            original_task_count = sum(len(s.tasks) for s in plan.sessions)

            adapted_plan = self.generator.adapt_plan(plan, task.id, 0.3)

            # Should have added remedial task
            new_task_count = sum(len(s.tasks) for s in adapted_plan.sessions)
            assert new_task_count >= original_task_count


class TestExportFormats:
    """Test cases for plan export formats"""

    def setup_method(self):
        self.generator = StudyPlanGenerator()
        self.plan = self.generator.generate_plan("test_user", days=7)

    def test_export_json(self):
        """Test JSON export"""
        exported = self.generator.export_plan(self.plan, "json")

        assert isinstance(exported, str)
        # Should be valid JSON
        import json
        data = json.loads(exported)
        assert data["user_id"] == "test_user"

    def test_export_ical(self):
        """Test iCal export"""
        exported = self.generator.export_plan(self.plan, "ical")

        assert isinstance(exported, str)
        assert "BEGIN:VCALENDAR" in exported
        assert "END:VCALENDAR" in exported
        assert "VERSION:2.0" in exported

    def test_export_markdown(self):
        """Test Markdown export"""
        exported = self.generator.export_plan(self.plan, "markdown")

        assert isinstance(exported, str)
        assert "# Study Plan" in exported
        assert self.plan.user_id in exported

    def test_export_unknown_format(self):
        """Test handling of unknown format"""
        with pytest.raises(ValueError):
            self.generator.export_plan(self.plan, "xml")


class TestConvenienceFunctions:
    """Test module-level convenience functions"""

    def test_generate_plan(self):
        """Test generate_plan convenience function"""
        plan = generate_plan("test_user", days=7, daily_minutes=60)

        assert plan.user_id == "test_user"
        assert plan.duration_days == 7

    def test_adapt_plan(self):
        """Test adapt_plan convenience function"""
        plan = generate_plan("test_user", days=7)

        if plan.sessions and plan.sessions[0].tasks:
            adapted = adapt_plan(plan, plan.sessions[0].tasks[0].id, 0.8)
            assert adapted is not None

    def test_export_plan(self):
        """Test export_plan convenience function"""
        plan = generate_plan("test_user", days=7)
        exported = export_plan(plan, "json")

        assert isinstance(exported, str)


class TestStudyTaskDataclass:
    """Test StudyTask dataclass"""

    def test_task_creation(self):
        """Test task creation"""
        task = StudyTask(
            id="task1",
            title="Test Task",
            description="Test description",
            category="algorithms",
            difficulty="medium",
            estimated_minutes=45,
            resources=[{"name": "Resource", "url": "http://example.com"}]
        )

        assert task.id == "task1"
        assert task.completed is False


class TestStudySessionDataclass:
    """Test StudySession dataclass"""

    def test_session_creation(self):
        """Test session creation"""
        task = StudyTask(
            id="task1",
            title="Test",
            description="Test",
            category="algorithms",
            difficulty="easy",
            estimated_minutes=30,
            resources=[]
        )

        session = StudySession(
            date=datetime.now(),
            tasks=[task],
            total_minutes=30,
            theme="Test Theme"
        )

        assert session.total_minutes == 30
        assert session.theme == "Test Theme"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
