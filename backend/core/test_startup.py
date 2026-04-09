"""
Startup verification script for AI Note Taker backend
Tests all imports and key functionality
"""

import sys
import os

def test_imports():
    """Test all critical imports"""
    print("Testing imports...")
    errors = []

    try:
        from main import app
        print("✓ main.py imports OK")
    except Exception as e:
        errors.append(f"✗ main.py: {e}")

    try:
        from realtime_suggestions import RealtimeSuggestionEngine
        print("✓ realtime_suggestions.py imports OK")
    except Exception as e:
        errors.append(f"✗ realtime_suggestions.py: {e}")

    try:
        from performance_analyzer import PerformanceAnalyzer
        print("✓ performance_analyzer.py imports OK")
    except Exception as e:
        errors.append(f"✗ performance_analyzer.py: {e}")

    try:
        from study_plan_generator import StudyPlanGenerator
        print("✓ study_plan_generator.py imports OK")
    except Exception as e:
        errors.append(f"✗ study_plan_generator.py: {e}")

    try:
        from analytics_engine import AnalyticsEngine
        print("✓ analytics_engine.py imports OK")
    except Exception as e:
        errors.append(f"✗ analytics_engine.py: {e}")

    try:
        from conversation_analyzer import ConversationAnalyzer
        print("✓ conversation_analyzer.py imports OK")
    except Exception as e:
        errors.append(f"✗ conversation_analyzer.py: {e}")

    return errors

def test_functionality():
    """Test basic functionality"""
    print("\nTesting functionality...")
    errors = []

    # Test performance analyzer
    try:
        from performance_analyzer import PerformanceAnalyzer
        analyzer = PerformanceAnalyzer()
        result = analyzer.analyze_answer("I worked on React for 3 years.", "behavioral")
        assert "overall_score" in result
        print("✓ PerformanceAnalyzer works")
    except Exception as e:
        errors.append(f"✗ PerformanceAnalyzer: {e}")

    # Test study plan generator
    try:
        from study_plan_generator import StudyPlanGenerator
        planner = StudyPlanGenerator()
        plan = planner.generate_plan("test_user", days=7)
        assert plan.user_id == "test_user"
        print("✓ StudyPlanGenerator works")
    except Exception as e:
        errors.append(f"✗ StudyPlanGenerator: {e}")

    # Test realtime suggestions
    try:
        from realtime_suggestions import RealtimeSuggestionEngine
        engine = RealtimeSuggestionEngine()
        result = engine.process_segment("What is your experience?", "interviewer")
        print("✓ RealtimeSuggestionEngine works")
    except Exception as e:
        errors.append(f"✗ RealtimeSuggestionEngine: {e}")

    return errors

def main():
    print("="*60)
    print("AI Note Taker Backend Verification")
    print("="*60)

    import_errors = test_imports()
    func_errors = test_functionality()

    all_errors = import_errors + func_errors

    print("\n" + "="*60)
    if all_errors:
        print(f"ERRORS FOUND ({len(all_errors)}):")
        for err in all_errors:
            print(f"  {err}")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED!")
        print("Backend is ready to run.")
        sys.exit(0)

if __name__ == "__main__":
    main()
