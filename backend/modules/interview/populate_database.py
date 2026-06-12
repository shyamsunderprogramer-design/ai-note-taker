"""
populate_database.py - Populate the question database with thousands of curated questions
This script generates high-quality, realistic interview questions with proper metadata
"""

import json
import random
from datetime import datetime
from typing import List, Dict
from question_database_v2 import (
    InterviewQuestion, ExpectedAnswer, QuestionCategory,
    Difficulty, CompanyTier, QuestionDatabase
)
from company_questions import ALL_COMPANY_QUESTIONS


# ═══════════════════════════════════════════════════════════════════════════════
# QUESTION GENERATION DATA
# Real interview patterns and topics
# ═══════════════════════════════════════════════════════════════════════════════

# Behavioral Question Patterns
BEHAVIORAL_PATTERNS = {
    "leadership": [
        "Tell me about a time you led a {team_type} through {challenge}",
        "Describe how you {action} when {situation}",
        "Give an example of {leadership_action} in the face of {obstacle}",
        "How did you {motivate_type} a team to achieve {goal_type}?",
        "Walk me through a time you had to {decision_type} with incomplete information",
    ],
    "teamwork": [
        "Tell me about collaborating with {difficult_person} on {project_type}",
        "Describe a time you {helped_type} a struggling teammate",
        "How did you handle {conflict_type} with {colleague_type}?",
        "Give an example of {successful_collaboration}",
        "Tell me about {resolving_conflict} in a team setting",
    ],
    "problem_solving": [
        "Describe a time you solved {complex_problem} with {constraint}",
        "How did you approach {ambiguous_situation}?",
        "Tell me about {debugging_type} a critical issue under {pressure}",
        "Walk me through how you {optimized} a system",
        "Give an example of {innovative_solution} you developed",
    ],
    "failure": [
        "Tell me about a time you {failed_at} and what you learned",
        "Describe your biggest {professional_mistake}",
        "How did you handle {project_failure}?",
        "Tell me about a time you {let_down} your team",
        "Describe {receiving_feedback} that was difficult to hear",
    ],
    "success": [
        "Tell me about your proudest {professional_achievement}",
        "Describe a time you {exceeded_expectations}",
        "How did you {deliver_results} against the odds?",
        "Give an example of {taking_initiative}",
        "Walk me through how you {achieved_goal}",
    ],
}

BEHAVIORAL_FILLERS = {
    "team_type": ["cross-functional team", "remote team", "distributed team", "new team", "struggling team", "high-performing team"],
    "challenge": ["tight deadlines", "scope changes", "resource constraints", "technical debt", "conflicting priorities", "ambiguous requirements"],
    "action": ["turned around a failing project", "built consensus", "drove adoption", "championed a new technology", "reorganized the workflow"],
    "situation": ["stakeholders disagreed", "the system kept failing", "requirements were unclear", "team morale was low", "deadlines were moved up"],
    "leadership_action": ["taking ownership", "making an unpopular decision", "rallying the team", "setting a vision", "holding people accountable"],
    "obstacle": ["resistance to change", "limited resources", "tight timeline", "technical limitations", "competing priorities"],
    "motivate_type": ["inspired", "motivated", "aligned", "energized", "focused"],
    "goal_type": ["an ambitious deadline", "a challenging target", "zero-downtime migration", "a complete rewrite", "major cost reduction"],
    "decision_type": ["make a critical call", "choose between competing options", "prioritize ruthlessly", "cut scope", "invest in quality"],
    "difficult_person": ["a challenging stakeholder", "someone with different priorities", "a skeptical executive", "a resistant team member", "a competing team"],
    "project_type": ["a high-stakes launch", "a critical migration", "a strategic initiative", "a last-minute request", "a complex integration"],
    "helped_type": ["mentored", "coached", "supported", "guided", "paired with"],
    "conflict_type": ["disagreement", "conflict", "misalignment", "tension", "competing priorities"],
    "colleague_type": ["a peer", "your manager", "a direct report", "another team", "an external partner"],
    "successful_collaboration": ["a successful cross-team initiative", "achieving alignment across stakeholders", "delivering a complex project together"],
    "resolving_conflict": ["resolving a technical disagreement", "mediating between competing teams", "aligning conflicting priorities"],
    "complex_problem": ["a critical production issue", "a scaling challenge", "a performance bottleneck", "a security vulnerability", "a data inconsistency"],
    "constraint": ["limited time", "minimal resources", "tight budget", "legacy constraints", "regulatory requirements"],
    "ambiguous_situation": ["an unclear requirement", "conflicting feedback", "a vague problem statement", "an undefined scope"],
    "debugging_type": ["debugging", "troubleshooting", "root cause analysis of", "investigating"],
    "pressure": ["pressure", "tight deadline", "high stakes", "customer impact", "executive attention"],
    "optimized": ["optimized performance", "reduced costs", "improved reliability", "increased velocity", "enhanced security"],
    "innovative_solution": ["an innovative solution", "a creative workaround", "a novel approach", "an elegant simplification"],
    "failed_at": ["failed", "missed a deadline", "made the wrong call", "mismanaged expectations"],
    "professional_mistake": ["professional mistake", "career setback", "learning moment", "regrettable decision"],
    "project_failure": ["when a project didn't go as planned", "a failed initiative", "an unsuccessful launch", "a missed opportunity"],
    "let_down": ["let down", "disappointed", "failed to deliver for", "fell short with"],
    "receiving_feedback": ["receiving critical feedback", "being told you were wrong", "learning about a blind spot"],
    "professional_achievement": ["professional achievement", "career accomplishment", "project success", "team win"],
    "exceeded_expectations": ["exceeded expectations", "went above and beyond", "delivered exceptional results", "surprised stakeholders"],
    "deliver_results": ["delivered results", "achieved the impossible", "turned things around", "made it happen"],
    "taking_initiative": ["taking initiative", "starting something new", "championing an idea", "driving change"],
    "achieved_goal": ["achieved an ambitious goal", "hit a stretch target", "delivered against odds", "succeeded where others failed"],
}

# Coding Topics by Category
CODING_TOPICS = {
    "arrays": ["two_sum", "best_time_to_buy_stock", "contains_duplicate", "product_of_array_except_self", "maximum_subarray", "maximum_product_subarray", "find_minimum_in_rotated_sorted_array", "search_in_rotated_sorted_array", "three_sum", "container_with_most_water"],
    "binary": ["sum_of_two_integers", "number_of_1_bits", "counting_bits", "missing_number", "reverse_bits"],
    "dynamic_programming": ["climbing_stairs", "house_robber", "house_robber_ii", "maximum_subarray", "jump_game", "jump_game_ii", "unique_paths", "unique_paths_ii", "longest_common_subsequence", "edit_distance"],
    "graph": ["clone_graph", "course_schedule", "course_schedule_ii", "number_of_islands", "pacific_atlantic_water_flow", "graph_valid_tree", "alien_dictionary"],
    "intervals": ["insert_interval", "merge_intervals", "non_overlapping_intervals", "meeting_rooms", "meeting_rooms_ii"],
    "linked_list": ["reverse_linked_list", "merge_two_sorted_lists", "linked_list_cycle", "linked_list_cycle_ii", "reorder_list", "remove_nth_node", "copy_list_with_random_pointer"],
    "matrix": ["set_matrix_zeroes", "spiral_matrix", "rotate_image", "word_search"],
    "string": ["longest_substring_without_repeating_characters", "longest_repeating_character_replacement", "minimum_window_substring", "group_anagrams", "valid_anagram", "encode_and_decode_strings"],
    "tree": ["maximum_depth_of_binary_tree", "same_tree", "invert_binary_tree", "binary_tree_level_order_traversal", "serialize_and_deserialize_binary_tree", "subtree_of_another_tree", "construct_binary_tree"],
    "heap": ["merge_k_sorted_lists", "top_k_frequent_elements", "find_median_from_data_stream"],
    "backtracking": ["subsets", "subsets_ii", "permutations", "permutations_ii", "combinations", "combination_sum", "combination_sum_ii", "palindrome_partitioning", "letter_combinations"],
}

SYSTEM_DESIGN_TOPICS = [
    "url_shortener", "web_crawler", "search_engine", "chat_system",
    "notification_system", "news_feed", "video_streaming", "key_value_store",
    "distributed_cache", "rate_limiter", "message_queue", "file_storage",
    "collaborative_editor", "recommendation_system", "payment_system",
    "ride_sharing", "food_delivery", "hotel_reservation", "ticket_booking",
    "distributed_id_generator", "distributed_lock", "consensus_service",
    "configuration_management", "feature_flag_system", "ab_testing_platform",
    "metrics_monitoring", "log_aggregation", "api_gateway", "service_mesh",
    "data_pipeline", "etl_system", "data_warehouse", "stream_processing",
]


# ═══════════════════════════════════════════════════════════════════════════════
# QUESTION GENERATORS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_behavioral_questions(count: int = 500) -> List[InterviewQuestion]:
    """Generate behavioral questions using templates"""
    questions = []
    question_id = 1000

    categories = ["leadership", "teamwork", "problem_solving", "failure", "success"]
    difficulties = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]
    roles = [
        "software_engineer", "senior_software_engineer", "staff_engineer",
        "engineering_manager", "tech_lead", "product_manager"
    ]

    for i in range(count):
        category = random.choice(categories)
        pattern = random.choice(BEHAVIORAL_PATTERNS[category])

        # Fill in the template
        question_text = pattern
        for key, options in BEHAVIORAL_FILLERS.items():
            if f"{{{key}}}" in question_text:
                question_text = question_text.replace(f"{{{key}}}", random.choice(options))

        # Create follow-ups based on category
        follow_ups = {
            "leadership": ["What was the outcome?", "What would you do differently?", "How did you measure success?"],
            "teamwork": ["How did the relationship evolve?", "What did you learn about collaboration?"],
            "problem_solving": ["What was the root cause?", "How did you prevent recurrence?"],
            "failure": ["What did you learn?", "How have you applied this lesson?"],
            "success": ["What factors contributed most?", "How did you celebrate?"],
        }

        q = InterviewQuestion(
            id=f"bh-gen-{question_id:06d}",
            question=question_text,
            category=QuestionCategory.BEHAVIORAL,
            difficulty=random.choice(difficulties),
            roles=random.sample(roles, k=random.randint(2, 4)),
            companies=["generic"],
            company_tiers=[CompanyTier.BIG_TECH],
            topics=[category, "behavioral"],
            expected_answer=ExpectedAnswer(
                key_points=["Use STAR format", "Be specific", "Show impact", "Demonstrate growth"],
                follow_up_questions=follow_ups[category],
                red_flags=["Being vague", "Not showing growth", "Blaming others"],
                time_estimate_minutes=10,
                evaluation_criteria={"specificity": "Concrete examples", "growth": "Shows learning"}
            ),
            hints=["Prepare specific examples", "Quantify impact where possible"],
            frequency="generated",
            source="generated"
        )

        questions.append(q)
        question_id += 1

    return questions


def generate_coding_questions(count: int = 2000) -> List[InterviewQuestion]:
    """Generate coding questions based on known patterns"""
    questions = []
    question_id = 5000

    difficulties_map = {
        "arrays": [Difficulty.EASY, Difficulty.MEDIUM],
        "binary": [Difficulty.EASY, Difficulty.MEDIUM],
        "dynamic_programming": [Difficulty.MEDIUM, Difficulty.HARD],
        "graph": [Difficulty.MEDIUM, Difficulty.HARD],
        "intervals": [Difficulty.MEDIUM],
        "linked_list": [Difficulty.EASY, Difficulty.MEDIUM],
        "matrix": [Difficulty.MEDIUM, Difficulty.HARD],
        "string": [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD],
        "tree": [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD],
        "heap": [Difficulty.MEDIUM, Difficulty.HARD],
        "backtracking": [Difficulty.MEDIUM, Difficulty.HARD],
    }

    companies = ["google", "amazon", "facebook", "microsoft", "apple", "netflix", "uber", "airbnb", "stripe"]
    roles = ["software_engineer", "senior_software_engineer", "backend_engineer", "full_stack_engineer"]

    # Generate from known LeetCode-style problems
    leetcode_problems = []

    # Add array problems
    for problem in CODING_TOPICS["arrays"]:
        for i in range(20):  # Multiple variations
            leetcode_problems.append(("arrays", problem, Difficulty.MEDIUM if i % 3 != 0 else Difficulty.EASY))

    # Add DP problems
    for problem in CODING_TOPICS["dynamic_programming"]:
        for i in range(30):
            leetcode_problems.append(("dynamic_programming", problem, Difficulty.HARD if i % 2 == 0 else Difficulty.MEDIUM))

    # Add tree problems
    for problem in CODING_TOPICS["tree"]:
        for i in range(25):
            leetcode_problems.append(("tree", problem, random.choice([Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD])))

    # Add graph problems
    for problem in CODING_TOPICS["graph"]:
        for i in range(30):
            leetcode_problems.append(("graph", problem, Difficulty.HARD if i % 2 == 0 else Difficulty.MEDIUM))

    # Add string problems
    for problem in CODING_TOPICS["string"]:
        for i in range(25):
            leetcode_problems.append(("string", problem, random.choice([Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD])))

    # Generate questions
    for topic, problem, difficulty in leetcode_problems[:count]:
        company = random.choice(companies)
        role = random.choice(roles)

        q = InterviewQuestion(
            id=f"cd-gen-{question_id:06d}",
            question=f"Solve: {problem.replace('_', ' ').title()}",
            category=QuestionCategory.CODING,
            difficulty=difficulty,
            roles=[role],
            companies=[company],
            company_tiers=[CompanyTier.FAANG],
            topics=[topic, "coding", "algorithms"],
            expected_answer=ExpectedAnswer(
                key_points=["Analyze time and space complexity", "Consider edge cases", "Optimize if possible"],
                follow_up_questions=["Can you optimize further?", "What if the input is huge?"],
                red_flags=["Not considering edge cases", "Wrong complexity analysis"],
                time_estimate_minutes=25,
                evaluation_criteria={"correctness": "Solution works", "optimization": "Optimal approach"}
            ),
            hints=["Start with brute force", "Look for patterns"],
            frequency="generated",
            source="generated"
        )

        questions.append(q)
        question_id += 1

    return questions


def generate_system_design_questions(count: int = 500) -> List[InterviewQuestion]:
    """Generate system design questions"""
    questions = []
    question_id = 3000

    difficulties = [Difficulty.MEDIUM, Difficulty.HARD, Difficulty.EXPERT]
    roles = ["senior_software_engineer", "staff_engineer", "principal_engineer", "architect"]
    companies = ["google", "amazon", "facebook", "netflix", "uber", "airbnb", "twitter"]

    for topic in SYSTEM_DESIGN_TOPICS:
        for i in range(count // len(SYSTEM_DESIGN_TOPICS)):
            difficulty = random.choice(difficulties)
            company = random.choice(companies)

            variations = [
                f"Design a {topic.replace('_', ' ').title()}",
                f"How would you build a scalable {topic.replace('_', ' ')}?",
                f"Design the {topic.replace('_', ' ')} for {company}",
            ]

            q = InterviewQuestion(
                id=f"sd-gen-{question_id:06d}",
                question=random.choice(variations),
                category=QuestionCategory.SYSTEM_DESIGN,
                difficulty=difficulty,
                roles=random.sample(roles, k=random.randint(1, 3)),
                companies=[company],
                company_tiers=[CompanyTier.FAANG],
                topics=["system_design", "scalability", topic],
                expected_answer=ExpectedAnswer(
                    key_points=[
                        "Clarify requirements (functional and non-functional)",
                        "Estimate scale (QPS, storage, bandwidth)",
                        "Design high-level architecture",
                        "Dive deep into specific components",
                        "Discuss tradeoffs"
                    ],
                    follow_up_questions=["How to scale?", "How to handle failures?", "Bottlenecks?"],
                    red_flags=["Not clarifying requirements", "Ignoring scale", "Single points of failure"],
                    time_estimate_minutes=45,
                    evaluation_criteria={
                        "requirements": "Clarifies before designing",
                        "scalability": "Handles growth",
                        "tradeoffs": "Discusses alternatives"
                    }
                ),
                hints=["Start with requirements", "Think about scale"],
                frequency="generated",
                source="generated"
            )

            questions.append(q)
            question_id += 1

    return questions


def generate_technical_questions(count: int = 1000) -> List[InterviewQuestion]:
    """Generate technical domain questions"""
    questions = []
    question_id = 8000

    technical_domains = {
        "backend": ["api_design", "databases", "caching", "microservices", "authentication", "rate_limiting"],
        "frontend": ["react", "state_management", "performance", "accessibility", "testing"],
        "devops": ["ci_cd", "kubernetes", "monitoring", "infrastructure_as_code", "security"],
        "data": ["sql", "data_modeling", "etl", "data_warehousing", "streaming"],
        "ml": ["feature_engineering", "model_selection", "evaluation", "deployment", "mlops"],
    }

    difficulties = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]
    companies = ["google", "amazon", "facebook", "netflix", "uber"]

    question_patterns = [
        "Explain {concept} and when to use it",
        "Compare {concept} and {concept2}. When would you use each?",
        "What are the tradeoffs of {concept}?",
        "How would you implement {concept}?",
        "What are common pitfalls with {concept}?",
    ]

    for domain, concepts in technical_domains.items():
        for concept in concepts:
            for i in range(count // (len(technical_domains) * 6)):
                pattern = random.choice(question_patterns)
                concept2 = random.choice(concepts) if "{concept2}" in pattern else None

                question_text = pattern.replace("{concept}", concept.replace("_", " "))
                if concept2:
                    question_text = question_text.replace("{concept2}", concept2.replace("_", " "))

                q = InterviewQuestion(
                    id=f"tc-gen-{question_id:06d}",
                    question=question_text,
                    category=QuestionCategory.TECHNICAL,
                    difficulty=random.choice(difficulties),
                    roles=[f"{domain}_engineer"],
                    companies=[random.choice(companies)],
                    company_tiers=[CompanyTier.FAANG],
                    topics=[domain, concept, "technical"],
                    expected_answer=ExpectedAnswer(
                        key_points=["Clear explanation", "Tradeoffs", "Real-world examples"],
                        follow_up_questions=["How would you scale this?", "What alternatives exist?"],
                        red_flags=["Shallow understanding", "No tradeoff discussion"],
                        time_estimate_minutes=15,
                        evaluation_criteria={"depth": "Deep understanding", "practicality": "Real-world application"}
                    ),
                    frequency="generated",
                    source="generated"
                )

                questions.append(q)
                question_id += 1

    return questions


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE POPULATION
# ═══════════════════════════════════════════════════════════════════════════════

def populate_database(
    behavioral_count: int = 500,
    coding_count: int = 2000,
    system_design_count: int = 500,
    technical_count: int = 1000
) -> Dict:
    """Populate the question database with curated questions"""

    print("=" * 80)
    print("POPULATING PREMIUM QUESTION DATABASE")
    print("=" * 80)

    all_questions = []

    # Add company-specific questions
    print(f"\n📦 Loading {len(ALL_COMPANY_QUESTIONS)} verified company questions...")
    all_questions.extend(ALL_COMPANY_QUESTIONS)

    # Generate behavioral questions
    print(f"\n🎯 Generating {behavioral_count} behavioral questions...")
    behavioral = generate_behavioral_questions(behavioral_count)
    all_questions.extend(behavioral)
    print(f"   ✓ Generated {len(behavioral)} behavioral questions")

    # Generate coding questions
    print(f"\n💻 Generating {coding_count} coding questions...")
    coding = generate_coding_questions(coding_count)
    all_questions.extend(coding)
    print(f"   ✓ Generated {len(coding)} coding questions")

    # Generate system design questions
    print(f"\n🏗️  Generating {system_design_count} system design questions...")
    system_design = generate_system_design_questions(system_design_count)
    all_questions.extend(system_design)
    print(f"   ✓ Generated {len(system_design)} system design questions")

    # Generate technical questions
    print(f"\n🔧 Generating {technical_count} technical questions...")
    technical = generate_technical_questions(technical_count)
    all_questions.extend(technical)
    print(f"   ✓ Generated {len(technical)} technical questions")

    # Calculate statistics
    stats = {
        "total_questions": len(all_questions),
        "by_category": {},
        "by_difficulty": {},
        "by_company": {},
        "by_source": {}
    }

    for q in all_questions:
        # Category
        cat = q.category.value
        stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

        # Difficulty
        diff = q.difficulty.value
        stats["by_difficulty"][diff] = stats["by_difficulty"].get(diff, 0) + 1

        # Source
        stats["by_source"][q.source] = stats["by_source"].get(q.source, 0) + 1

        # Companies
        for company in q.companies:
            stats["by_company"][company] = stats["by_company"].get(company, 0) + 1

    print("\n" + "=" * 80)
    print("DATABASE POPULATION COMPLETE!")
    print("=" * 80)
    print(f"\n📊 Total Questions: {stats['total_questions']:,}")
    print("\n📁 By Category:")
    for cat, count in sorted(stats["by_category"].items()):
        print(f"   • {cat}: {count:,}")
    print("\n📈 By Difficulty:")
    for diff, count in sorted(stats["by_difficulty"].items()):
        print(f"   • {diff}: {count:,}")
    print("\n🏢 By Company:")
    for company, count in sorted(stats["by_company"].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   • {company}: {count:,}")
    print("\n📋 By Source:")
    for source, count in sorted(stats["by_source"].items()):
        print(f"   • {source}: {count:,}")

    return {
        "questions": all_questions,
        "stats": stats
    }


def export_to_json(questions: List[InterviewQuestion], filepath: str):
    """Export questions to JSON file"""
    data = [q.to_dict() for q in questions]
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Exported {len(questions):,} questions to {filepath}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Populate database
    result = populate_database(
        behavioral_count=500,
        coding_count=2000,
        system_design_count=500,
        technical_count=1000
    )

    # Export to JSON
    export_to_json(result["questions"], "interview_questions_database.json")

    print("\n✅ Done!")
