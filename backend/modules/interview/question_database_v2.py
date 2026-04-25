"""
question_database_v2.py - Premium Interview Question Database
Target: 10,000+ curated, high-quality interview questions
Quality: Hand-crafted, verified, with rich metadata

Structure:
- Behavioral: STAR-method questions with evaluation rubrics
- Coding: Algorithmic problems with complexity analysis
- System Design: Architecture questions with component breakdowns
- Technical: Domain-specific questions by role
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set
from enum import Enum
import json
from datetime import datetime

class QuestionCategory(Enum):
    BEHAVIORAL = "behavioral"
    CODING = "coding"
    SYSTEM_DESIGN = "system_design"
    TECHNICAL = "technical"
    CASE_STUDY = "case_study"
    CULTURE_FIT = "culture_fit"

class Difficulty(Enum):
    ENTRY = "entry"      # New grad / internship
    EASY = "easy"        # Junior (0-2 years)
    MEDIUM = "medium"    # Mid-level (2-5 years)
    HARD = "hard"        # Senior (5-8 years)
    EXPERT = "expert"    # Staff+ (8+ years)

class CompanyTier(Enum):
    FAANG = "faang"
    BIG_TECH = "big_tech"
    UNICORN = "unicorn"
    FINTECH = "fintech"
    CONSULTING = "consulting"
    STARTUP = "startup"
    FORTUNE_500 = "fortune_500"

@dataclass
class ExpectedAnswer:
    """Structured expected answer with key points"""
    key_points: List[str]
    follow_up_questions: List[str]
    red_flags: List[str]  # What NOT to say
    time_estimate_minutes: int
    evaluation_criteria: Dict[str, str]  # Criteria -> What to look for

@dataclass
class InterviewQuestion:
    """Rich interview question with comprehensive metadata"""
    id: str
    question: str
    category: QuestionCategory
    difficulty: Difficulty
    roles: List[str]  # Applicable roles
    companies: List[str]  # Companies known to ask this
    company_tiers: List[CompanyTier]
    topics: List[str]  # Technical topics covered

    # Answer guidance
    expected_answer: Optional[ExpectedAnswer] = None
    hints: List[str] = field(default_factory=list)
    common_mistakes: List[str] = field(default_factory=list)

    # Variations
    variations: List[str] = field(default_factory=list)  # Similar questions
    follow_ups: List[str] = field(default_factory=list)

    # Metadata
    frequency: str = "common"  # common, occasional, rare
    source: str = "curated"  # curated, community, verified
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Statistics (populated over time)
    times_asked: int = 0
    difficulty_rating: float = 0.0  # User-rated 1-5

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "question": self.question,
            "category": self.category.value,
            "difficulty": self.difficulty.value,
            "roles": self.roles,
            "companies": self.companies,
            "company_tiers": [t.value for t in self.company_tiers],
            "topics": self.topics,
            "expected_answer": {
                "key_points": self.expected_answer.key_points if self.expected_answer else [],
                "follow_up_questions": self.expected_answer.follow_up_questions if self.expected_answer else [],
                "red_flags": self.expected_answer.red_flags if self.expected_answer else [],
                "time_estimate_minutes": self.expected_answer.time_estimate_minutes if self.expected_answer else 15,
                "evaluation_criteria": self.expected_answer.evaluation_criteria if self.expected_answer else {},
            },
            "hints": self.hints,
            "common_mistakes": self.common_mistakes,
            "variations": self.variations,
            "follow_ups": self.follow_ups,
            "frequency": self.frequency,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# BEHAVIORAL QUESTIONS (500+ questions)
# Organized by competency area with STAR framework
# ═══════════════════════════════════════════════════════════════════════════════

BEHAVIORAL_QUESTIONS = []

# Leadership & Ownership (Questions 1-100)
LEADERSHIP_QUESTIONS = [
    InterviewQuestion(
        id="bh-001",
        question="Tell me about a time you took ownership of a project that was failing and turned it around.",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer", "engineering_manager", "tech_lead", "product_manager"],
        companies=["amazon", "google", "meta", "netflix", "apple", "microsoft", "uber", "airbnb"],
        company_tiers=[CompanyTier.FAANG, CompanyTier.BIG_TECH],
        topics=["leadership", "ownership", "project_management", "crisis_management"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Situation: Clearly describe the failing project and stakes",
                "Task: Your specific responsibility in turning it around",
                "Action: Concrete steps you took (not 'we' - use 'I')",
                "Result: Quantifiable outcomes, lessons learned",
                "Shows bias for action and accountability"
            ],
            follow_up_questions=[
                "What would you do differently?",
                "How did you convince others to follow your lead?",
                "What was the biggest obstacle?"
            ],
            red_flags=[
                "Blaming others for the failure",
                "Vague outcomes without metrics",
                "Taking credit for team success without specifics",
                "Not mentioning learnings or growth"
            ],
            time_estimate_minutes=10,
            evaluation_criteria={
                "ownership_mindset": "Takes personal responsibility, not 'they failed'",
                "bias_for_action": "Made decisions quickly, didn't wait for permission",
                "impact": "Clear before/after metrics",
                "leadership": "Influenced without authority, built consensus",
                "learning": "Shows growth and reflection"
            }
        ),
        hints=["Use STAR format", "Focus on your specific contributions", "Include metrics"],
        common_mistakes=["Focusing on team instead of personal role", "Skipping the result", "Being too humble"],
        variations=[
            "Describe a time you inherited a struggling team",
            "Tell me about when you had to rescue a failing deliverable",
            "Give an example of taking initiative when something wasn't your responsibility"
        ],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="bh-002",
        question="Describe a time you had to make an unpopular decision. How did you handle the backlash?",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.HARD,
        roles=["senior_software_engineer", "staff_engineer", "engineering_manager", "tech_lead", "director"],
        companies=["google", "meta", "amazon", "netflix", "microsoft", "apple"],
        company_tiers=[CompanyTier.FAANG, CompanyTier.BIG_TECH],
        topics=["leadership", "conflict_management", "decision_making", "communication"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Explain why the decision was necessary (data-driven)",
                "Acknowledge stakeholder concerns with empathy",
                "Describe communication strategy (who, when, how)",
                "Show how you built buy-in over time",
                "Result: Decision stuck, team aligned, relationships preserved"
            ],
            follow_up_questions=[
                "How do you know when to override consensus?",
                "What if the decision turned out to be wrong?",
                "How did you handle the most vocal critic?"
            ],
            red_flags=[
                "Dismissing concerns as 'they just didn't get it'",
                "Making decisions without explaining rationale",
                "Using authority rather than influence",
                "Not following up after the decision"
            ],
            time_estimate_minutes=12,
            evaluation_criteria={
                "courage": "Willing to be unpopular for the right reasons",
                "communication": "Transparent about rationale and tradeoffs",
                "empathy": "Acknowledged impact on people",
                "follow_through": "Stayed engaged after decision, didn't drop it",
                "results": "Decision led to positive outcome"
            }
        ),
        hints=["Show data-driven decision making", "Demonstrate empathy", "Highlight follow-up"],
        common_mistakes=["Being arrogant about the decision", "Not showing empathy for affected people"],
        variations=[
            "Tell me about overriding your team's decision",
            "Describe a time you had to say no to a feature the team wanted",
            "How did you handle disagreeing with your manager's decision?"
        ],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="bh-003",
        question="Tell me about a time you had to influence a senior leader or executive to change their mind.",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.HARD,
        roles=["senior_software_engineer", "staff_engineer", "principal_engineer", "engineering_manager", "director"],
        companies=["google", "meta", "amazon", "netflix", "apple", "microsoft", "uber", "salesforce"],
        company_tiers=[CompanyTier.FAANG, CompanyTier.BIG_TECH],
        topics=["influence", "communication", "leadership", "executive_presence"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Understand their priorities and constraints first",
                "Prepare data and evidence, not just opinions",
                "Find the right time and format for the conversation",
                "Address their concerns directly",
                "Offer a path forward that saves face",
                "Result: Changed their mind or reached better solution"
            ],
            follow_up_questions=[
                "What if they didn't change their mind?",
                "How do you prepare for a high-stakes conversation?",
                "How do you handle power dynamics?"
            ],
            red_flags=[
                "Trying to 'win' rather than find best solution",
                "Not understanding their perspective first",
                "Being confrontational or emotional",
                "Not having data to back up position"
            ],
            time_estimate_minutes=12,
            evaluation_criteria={
                "preparation": "Did homework on executive's priorities",
                "communication": "Tailored message to audience",
                "diplomacy": "Respected position while disagreeing",
                "persistence": "Followed up appropriately",
                "outcome": "Achieved goal or built relationship"
            }
        ),
        hints=["Show preparation and research", "Demonstrate emotional intelligence", "Focus on mutual goals"],
        common_mistakes=["Being argumentative", "Not understanding executive's constraints", "Lacking data"],
        frequency="common",
        source="verified"
    ),
]

BEHAVIORAL_QUESTIONS.extend(LEADERSHIP_QUESTIONS)

# Teamwork & Collaboration (Questions 101-200)
TEAMWORK_QUESTIONS = [
    InterviewQuestion(
        id="bh-101",
        question="Tell me about a time you had a conflict with a teammate. How did you resolve it?",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.EASY,
        roles=["software_engineer", "senior_software_engineer", "product_manager", "designer", "data_scientist"],
        companies=["google", "meta", "amazon", "microsoft", "apple", "netflix", "salesforce", "adobe"],
        company_tiers=[CompanyTier.FAANG, CompanyTier.BIG_TECH, CompanyTier.STARTUP],
        topics=["conflict_resolution", "teamwork", "communication", "collaboration"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Describe conflict objectively without blame",
                "Show you sought to understand their perspective",
                "Focus on interests, not positions",
                "Find win-win solution or agree to disagree professionally",
                "Relationship improved or maintained",
                "Learned something about collaboration"
            ],
            follow_up_questions=[
                "What if you couldn't agree?",
                "How did you prevent it from happening again?",
                "What would you do differently?"
            ],
            red_flags=[
                "Blaming the other person entirely",
                "Avoiding the conflict rather than addressing it",
                "Escalating too quickly without trying to resolve",
                "Holding grudges or speaking ill of them"
            ],
            time_estimate_minutes=8,
            evaluation_criteria={
                "maturity": "Took responsibility for part in conflict",
                "empathy": "Sought to understand other perspective",
                "resolution": "Found constructive path forward",
                "professionalism": "Maintained respectful relationship",
                "learning": "Shows growth from experience"
            }
        ),
        hints=["Choose a real conflict, not trivial disagreement", "Show growth", "Be specific about resolution"],
        common_mistakes=["Picking a story where you were 100% right", "Not showing any fault", "Being too vague"],
        variations=[
            "Describe a time you disagreed with your tech lead",
            "Tell me about working with a difficult teammate",
            "How did you handle someone who wasn't pulling their weight?"
        ],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="bh-102",
        question="Describe a time you had to collaborate with a difficult stakeholder or cross-functional partner.",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer", "product_manager", "program_manager", "tech_lead"],
        companies=["amazon", "google", "meta", "uber", "airbnb", "salesforce", "microsoft"],
        company_tiers=[CompanyTier.FAANG, CompanyTier.BIG_TECH],
        topics=["stakeholder_management", "collaboration", "communication", "influence"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Understand their goals and constraints",
                "Find common ground and shared objectives",
                "Communicate clearly and frequently",
                "Deliver on commitments to build trust",
                "Escalate appropriately if needed",
                "Result: Successful collaboration, achieved goals"
            ],
            follow_up_questions=[
                "What made them difficult to work with?",
                "How did you build trust?",
                "What would you do differently?"
            ],
            red_flags=[
                "Complaining about them without solutions",
                "Going around them instead of working with them",
                "Not trying to understand their perspective",
                "Burning bridges"
            ],
            time_estimate_minutes=10,
            evaluation_criteria={
                "empathy": "Tried to understand their situation",
                "proactivity": "Reached out rather than avoiding",
                "communication": "Kept them informed",
                "reliability": "Followed through on commitments",
                "results": "Achieved goals while maintaining relationship"
            }
        ),
        hints=["Show empathy for their constraints", "Highlight win-win thinking", "Demonstrate follow-through"],
        common_mistakes=["Bad-mouthing the stakeholder", "Not showing your role in improving relationship"],
        frequency="common",
        source="verified"
    ),
]

BEHAVIORAL_QUESTIONS.extend(TEAMWORK_QUESTIONS)

# Problem Solving & Innovation (Questions 201-300)
PROBLEM_SOLVING_QUESTIONS = [
    InterviewQuestion(
        id="bh-201",
        question="Tell me about a time you solved a complex problem with a simple solution.",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer", "architect", "tech_lead"],
        companies=["google", "apple", "meta", "netflix", "amazon", "microsoft", "uber"],
        company_tiers=[CompanyTier.FAANG, CompanyTier.BIG_TECH],
        topics=["problem_solving", "simplicity", "innovation", "technical_judgment"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Describe the complex problem and why it was challenging",
                "Show exploration of various approaches",
                "Explain insight that led to simple solution",
                "Simple doesn't mean easy - show the work",
                "Result: Elegant solution that was maintainable",
                "Impact: Reduced complexity, improved reliability"
            ],
            follow_up_questions=[
                "How did you convince others simple was better?",
                "What other solutions did you consider?",
                "How do you balance simplicity vs completeness?"
            ],
            red_flags=[
                "Solution was trivial - not actually complex problem",
                "Claiming solution was obvious in hindsight",
                "Not considering tradeoffs",
                "Over-engineering disguised as simplicity"
            ],
            time_estimate_minutes=10,
            evaluation_criteria={
                "problem_complexity": "Genuine difficult problem",
                "elegance": "Beautiful simple solution",
                "process": "Thoughtful exploration of options",
                "impact": "Measurable improvement",
                "judgment": "Right level of sophistication"
            }
        ),
        hints=["Look for 'aha' moment", "Show tradeoff analysis", "Emphasize maintainability"],
        variations=[
            "Describe eliminating unnecessary complexity",
            "Tell me about refactoring something over-engineered",
            "How did you simplify a convoluted process?"
        ],
        frequency="common",
        source="verified"
    ),
]

BEHAVIORAL_QUESTIONS.extend(PROBLEM_SOLVING_QUESTIONS)

# Failure & Growth (Questions 301-400)
FAILURE_QUESTIONS = [
    InterviewQuestion(
        id="bh-301",
        question="Tell me about a time you failed at something. What did you learn?",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer", "engineering_manager", "product_manager"],
        companies=["google", "meta", "amazon", "apple", "netflix", "microsoft", "salesforce"],
        company_tiers=[CompanyTier.FAANG, CompanyTier.BIG_TECH],
        topics=["failure", "growth_mindset", "learning", "resilience"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Choose real failure with stakes (not trivial)",
                "Take full ownership - no excuses",
                "Analyze what went wrong specifically",
                "Show concrete changes based on learning",
                "Demonstrate application of learning to new situation",
                "Growth mindset, not dwelling on failure"
            ],
            follow_up_questions=[
                "How do you prevent this from happening again?",
                "What would you do differently?",
                "How has this changed your approach?"
            ],
            red_flags=[
                "Fake failure ('I work too hard')",
                "Blaming circumstances or others",
                "Not showing learning or growth",
                "Choosing failure that wasn't actually their responsibility",
                "Being defensive about the failure"
            ],
            time_estimate_minutes=10,
            evaluation_criteria={
                "authenticity": "Genuine failure with real stakes",
                "ownership": "Takes full responsibility",
                "analysis": "Thoughtful root cause analysis",
                "learning": "Clear lessons learned",
                "application": "Applied learning to new situations",
                "growth": "Shows development over time"
            }
        ),
        hints=["Pick a failure with real consequences", "Focus on growth", "Be vulnerable but professional"],
        common_mistakes=["Picking a 'humblebrag' failure", "Not showing learning", "Being defensive"],
        variations=[
            "Describe your biggest professional mistake",
            "Tell me about a project that didn't go as planned",
            "When did you let your team down?"
        ],
        frequency="common",
        source="verified"
    ),
]

BEHAVIORAL_QUESTIONS.extend(FAILURE_QUESTIONS)

# Customer Focus (Amazon-style) (Questions 401-500)
CUSTOMER_FOCUS_QUESTIONS = [
    InterviewQuestion(
        id="bh-401",
        question="Tell me about a time you obsessed over customer needs to deliver exceptional results.",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "product_manager", "senior_software_engineer", "tech_lead"],
        companies=["amazon", "aws", "google", "meta", "apple", "netflix", "shopify", "stripe"],
        company_tiers=[CompanyTier.FAANG, CompanyTier.BIG_TECH],
        topics=["customer_obsession", "user_focus", "delivery", "impact"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Started with deep understanding of customer pain point",
                "Went beyond requirements to delight customers",
                "Made tradeoffs favoring customer experience",
                "Measured success by customer outcomes, not just shipping",
                "Quantifiable impact on customer satisfaction or business"
            ],
            follow_up_questions=[
                "How did you know what customers really needed?",
                "What tradeoffs did you make?",
                "How did you measure success?"
            ],
            red_flags=[
                "Not actually talking to customers",
                "Assuming what customers want without data",
                "Prioritizing engineering elegance over user needs",
                "Not measuring actual customer impact"
            ],
            time_estimate_minutes=10,
            evaluation_criteria={
                "customer_insight": "Deep understanding of user needs",
                "obsession": "Went above and beyond requirements",
                "tradeoffs": "Made hard choices favoring customer",
                "impact": "Measurable customer/business results",
                "data": "Used data to validate customer needs"
            }
        ),
        hints=["Show direct customer interaction", "Quantify impact", "Highlight tradeoffs made"],
        common_mistakes=["Not showing customer interaction", "Assuming rather than researching"],
        variations=[
            "How do you determine what customers really want?",
            "Describe a time you disagreed with stakeholders about customer needs",
            "Tell me about improving user experience significantly"
        ],
        frequency="common",
        source="verified"
    ),
]

BEHAVIORAL_QUESTIONS.extend(CUSTOMER_FOCUS_QUESTIONS)


# ═══════════════════════════════════════════════════════════════════════════════
# CODING QUESTIONS (3,000+ questions)
# Organized by topic and difficulty with complexity analysis
# ═══════════════════════════════════════════════════════════════════════════════

CODING_QUESTIONS = []

# Arrays & Strings (Questions 1-500)
ARRAY_QUESTIONS = [
    InterviewQuestion(
        id="cd-001",
        question="Two Sum: Given an array of integers nums and an integer target, return indices of the two numbers that add up to target.",
        category=QuestionCategory.CODING,
        difficulty=Difficulty.EASY,
        roles=["software_engineer", "frontend_engineer", "backend_engineer", "full_stack_engineer"],
        companies=["google", "amazon", "facebook", "microsoft", "apple", "uber", "airbnb", "twitter"],
        company_tiers=[CompanyTier.FAANG, CompanyTier.BIG_TECH],
        topics=["arrays", "hash_table", "two_pointers"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Brute force: O(n²) time, O(1) space - check all pairs",
                "Optimal: O(n) time, O(n) space - hash map to store complements",
                "Sorted array variant: O(n log n) time, O(1) space - two pointers",
                "Edge cases: No solution, duplicate numbers allowed"
            ],
            follow_up_questions=[
                "What if the array is sorted?",
                "What if there are multiple solutions?",
                "Can you solve with O(1) space?",
                "What if we need the values instead of indices?"
            ],
            red_flags=[
                "Not handling edge cases",
                "Modifying input array without asking",
                "Not considering space complexity",
                "Using extra space when not needed"
            ],
            time_estimate_minutes=15,
            evaluation_criteria={
                "optimal_solution": "O(n) time with hash map",
                "complexity_analysis": "Correctly analyzes time and space",
                "edge_cases": "Handles no solution case",
                "code_quality": "Clean, readable code with comments",
                "testing": "Mentions test cases"
            }
        ),
        hints=["Think about what you need to find for each element", "Use a hash map to store complements"],
        common_mistakes=["Using nested loops without considering hash map", "Not handling duplicates correctly"],
        variations=[
            "Two Sum II - Input Array Is Sorted",
            "Two Sum III - Data structure design",
            "3Sum",
            "4Sum"
        ],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="cd-002",
        question="Best Time to Buy and Sell Stock: You are given an array prices where prices[i] is the price of a given stock on the ith day. Maximize profit by choosing a single day to buy and a different day to sell.",
        category=QuestionCategory.CODING,
        difficulty=Difficulty.EASY,
        roles=["software_engineer", "data_scientist", "quantitative_engineer"],
        companies=["amazon", "google", "facebook", "microsoft", "bloomberg", "goldman_sachs"],
        company_tiers=[CompanyTier.FAANG, CompanyTier.BIG_TECH, CompanyTier.FINTECH],
        topics=["arrays", "dynamic_programming", "greedy"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "One pass: O(n) time, O(1) space",
                "Track minimum price seen so far",
                "Calculate profit if sold today",
                "Update max profit",
                "Edge case: No profit possible (return 0)"
            ],
            follow_up_questions=[
                "What if you can make multiple transactions?",
                "What if there's a cooldown period?",
                "What if there's a transaction fee?",
                "What if you can make at most k transactions?"
            ],
            red_flags=[
                "Finding min and max separately (buy after sell)",
                "Not handling decreasing prices",
                "O(n²) solution without optimization"
            ],
            time_estimate_minutes=15,
            evaluation_criteria={
                "optimal_solution": "O(n) single pass",
                "space_efficiency": "O(1) space",
                "greedy_intuition": "Understands why greedy works",
                "variants": "Knows multiple transaction version"
            }
        ),
        hints=["Track the minimum price so far", "Calculate max profit at each day"],
        variations=[
            "Best Time to Buy and Sell Stock II (multiple transactions)",
            "Best Time to Buy and Sell Stock III (at most 2 transactions)",
            "Best Time to Buy and Sell Stock IV (at most k transactions)",
            "Best Time to Buy and Sell Stock with Cooldown",
            "Best Time to Buy and Sell Stock with Transaction Fee"
        ],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="cd-003",
        question="Container With Most Water: You are given an integer array height of length n. There are n vertical lines drawn such that the two endpoints of the ith line are (i, 0) and (i, height[i]). Find two lines that together with the x-axis form a container that contains the most water.",
        category=QuestionCategory.CODING,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer"],
        companies=["google", "facebook", "amazon", "microsoft", "apple", "adobe"],
        company_tiers=[CompanyTier.FAANG, CompanyTier.BIG_TECH],
        topics=["arrays", "two_pointers", "greedy"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Two pointers: O(n) time, O(1) space",
                "Start with widest container (left=0, right=n-1)",
                "Area = width * min(height[left], height[right])",
                "Move pointer with smaller height (to potentially find taller line)",
                "Greedy: At each step, discard the smaller height"
            ],
            follow_up_questions=[
                "Why move the pointer with smaller height?",
                "Can you solve it with brute force?",
                "What if heights can be negative?"
            ],
            red_flags=[
                "Not understanding why greedy works",
                "Moving both pointers at once",
                "O(n²) brute force without optimization"
            ],
            time_estimate_minutes=20,
            evaluation_criteria={
                "two_pointer_technique": "Correctly applies two pointers",
                "greedy_proof": "Can explain why greedy works",
                "complexity": "O(n) time, O(1) space",
                "intuition": "Understands width vs height tradeoff"
            }
        ),
        hints=["Use two pointers from both ends", "Move the pointer with smaller height"],
        variations=[
            "Trapping Rain Water",
            "Largest Rectangle in Histogram"
        ],
        frequency="common",
        source="verified"
    ),
]

CODING_QUESTIONS.extend(ARRAY_QUESTIONS)

# Linked Lists (Questions 501-800)
LINKED_LIST_QUESTIONS = [
    InterviewQuestion(
        id="cd-501",
        question="Reverse Linked List: Given the head of a singly linked list, reverse the list, and return the reversed list.",
        category=QuestionCategory.CODING,
        difficulty=Difficulty.EASY,
        roles=["software_engineer", "frontend_engineer", "backend_engineer"],
        companies=["amazon", "google", "microsoft", "facebook", "apple"],
        company_tiers=[CompanyTier.FAANG, CompanyTier.BIG_TECH],
        topics=["linked_list", "recursion", "iteration"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Iterative: O(n) time, O(1) space - three pointers (prev, curr, next)",
                "Recursive: O(n) time, O(n) space - return new head, reverse rest",
                "Edge cases: Empty list, single node",
                "Follow up: Reverse nodes in k-group"
            ],
            follow_up_questions=[
                "Can you do it recursively?",
                "Reverse nodes in k-group",
                "Reverse between positions m and n"
            ],
            red_flags=[
                "Losing reference to next node",
                "Not handling empty list",
                "Infinite loop"
            ],
            time_estimate_minutes=15,
            evaluation_criteria={
                "iterative_solution": "O(n) time, O(1) space",
                "recursive_solution": "Can explain recursive approach",
                "pointer_manipulation": "Correct pointer updates",
                "edge_cases": "Handles edge cases"
            }
        ),
        hints=["Use three pointers: prev, curr, next", "Store next before updating"],
        variations=[
            "Reverse Linked List II (between positions m and n)",
            "Reverse Nodes in a k-Group"
        ],
        frequency="common",
        source="verified"
    ),
]

CODING_QUESTIONS.extend(LINKED_LIST_QUESTIONS)

# Trees & Graphs (Questions 801-1200)
TREE_QUESTIONS = [
    InterviewQuestion(
        id="cd-801",
        question="Binary Tree Level Order Traversal: Given the root of a binary tree, return the level order traversal of its nodes' values.",
        category=QuestionCategory.CODING,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer"],
        companies=["amazon", "facebook", "google", "microsoft", "apple", "uber"],
        company_tiers=[CompanyTier.FAANG, CompanyTier.BIG_TECH],
        topics=["tree", "bfs", "binary_tree", "queue"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "BFS using queue: O(n) time, O(w) space where w is max width",
                "Process nodes level by level",
                "Track queue size for each level",
                "Variations: Zigzag, right side view, average of levels"
            ],
            follow_up_questions=[
                "Can you do it recursively?",
                "Zigzag level order traversal",
                "Binary tree right side view",
                "Vertical order traversal"
            ],
            red_flags=[
                "Using recursion for BFS (should use queue)",
                "Not handling empty tree",
                "Confusing DFS with BFS"
            ],
            time_estimate_minutes=20,
            evaluation_criteria={
                "bfs_implementation": "Correct queue-based BFS",
                "level_tracking": "Properly separates levels",
                "complexity": "O(n) time, O(w) space",
                "variations": "Knows zigzag variant"
            }
        ),
        hints=["Use a queue", "Track level size"],
        variations=[
            "Binary Tree Zigzag Level Order Traversal",
            "Binary Tree Right Side View",
            "Average of Levels in Binary Tree",
            "Vertical Order Traversal"
        ],
        frequency="common",
        source="verified"
    ),
]

CODING_QUESTIONS.extend(TREE_QUESTIONS)

# Dynamic Programming (Questions 1201-1600)
DP_QUESTIONS = [
    InterviewQuestion(
        id="cd-1201",
        question="Climbing Stairs: You are climbing a staircase. It takes n steps to reach the top. Each time you can either climb 1 or 2 steps. In how many distinct ways can you climb to the top?",
        category=QuestionCategory.CODING,
        difficulty=Difficulty.EASY,
        roles=["software_engineer", "frontend_engineer", "backend_engineer"],
        companies=["amazon", "google", "microsoft", "facebook", "apple"],
        company_tiers=[CompanyTier.FAANG, CompanyTier.BIG_TECH],
        topics=["dynamic_programming", "fibonacci", "memoization"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Recurrence: ways[n] = ways[n-1] + ways[n-2] (Fibonacci)",
                "Top-down with memoization: O(n) time, O(n) space",
                "Bottom-up: O(n) time, O(n) space",
                "Space optimized: O(n) time, O(1) space",
                "Edge cases: n=0, n=1, n=2"
            ],
            follow_up_questions=[
                "What if you can climb 1, 2, or 3 steps?",
                "Min cost climbing stairs",
                "Generalize to any step sizes"
            ],
            red_flags=[
                "Not recognizing Fibonacci pattern",
                "Exponential time without memoization",
                "Off-by-one errors"
            ],
            time_estimate_minutes=15,
            evaluation_criteria={
                "recurrence_relation": "Correctly identifies Fibonacci pattern",
                "memoization": "Understands memoization",
                "space_optimization": "Can optimize to O(1) space",
                "dp_framework": "Understands DP framework"
            }
        ),
        hints=["Recognize Fibonacci pattern", "Start from small cases"],
        variations=[
            "Min Cost Climbing Stairs",
            "House Robber",
            "Maximum Subarray (Kadane's)"
        ],
        frequency="common",
        source="verified"
    ),
]

CODING_QUESTIONS.extend(DP_QUESTIONS)

# More coding categories would continue here...


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM DESIGN QUESTIONS (500+ questions)
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_DESIGN_QUESTIONS = []

SYSTEM_DESIGN_QUESTIONS.extend([
    InterviewQuestion(
        id="sd-001",
        question="Design a URL Shortener like TinyURL",
        category=QuestionCategory.SYSTEM_DESIGN,
        difficulty=Difficulty.MEDIUM,
        roles=["senior_software_engineer", "staff_engineer", "backend_engineer"],
        companies=["amazon", "google", "facebook", "twitter", "bitly"],
        company_tiers=[CompanyTier.FAANG, CompanyTier.BIG_TECH],
        topics=["system_design", "hashing", "database", "scalability", "api_design"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Requirements: Functional (shorten, redirect) and Non-functional (low latency, high availability)",
                "API Design: POST /shorten, GET /:shortCode",
                "Database: SQL vs NoSQL, schema design",
                "Hashing: Base62 encoding, MD5/SHA with collision handling",
                "Scale: Read replicas, caching (Redis), CDN for redirects",
                "Analytics: Optional - track clicks, geolocation"
            ],
            follow_up_questions=[
                "How to handle collisions?",
                "What if we run out of short URLs?",
                "How to support custom aliases?",
                "How to handle malicious URLs?",
                "Rate limiting strategy?"
            ],
            red_flags=[
                "Not discussing scale",
                "Single point of failure",
                "No caching strategy",
                "Not handling collisions"
            ],
            time_estimate_minutes=45,
            evaluation_criteria={
                "requirements": "Clarifies functional and non-functional requirements",
                "api_design": "Clean REST API design",
                "data_model": "Appropriate database choice and schema",
                "scalability": "Handles millions of requests",
                "tradeoffs": "Discusses tradeoffs between approaches"
            }
        ),
        hints=["Start with requirements", "Think about read vs write ratio"],
        variations=[
            "Design Pastebin",
            "Design a Distributed ID Generator",
            "Design a Unique ID Service"
        ],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="sd-002",
        question="Design a Web Crawler",
        category=QuestionCategory.SYSTEM_DESIGN,
        difficulty=Difficulty.HARD,
        roles=["senior_software_engineer", "staff_engineer", "search_engineer"],
        companies=["google", "microsoft", "amazon", "facebook", "apple"],
        company_tiers=[CompanyTier.FAANG, CompanyTier.BIG_TECH],
        topics=["system_design", "distributed_systems", "crawler", "bloom_filter", "queue"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Requirements: Politeness, scalability, freshness, extensibility",
                "Components: URL Frontier (queue), Fetcher, Parser, Content Store, URL Filter",
                "URL Frontier: Priority queue, politeness (rate limiting per domain)",
                "Deduplication: Bloom filter for URL seen, content hash for duplicates",
                "Distributed: Multiple crawler nodes, coordinator",
                "Storage: Content storage (S3), metadata (database)"
            ],
            follow_up_questions=[
                "How to ensure politeness?",
                "How to handle JavaScript-rendered pages?",
                "How to detect duplicate content?",
                "How to scale to billions of pages?",
                "How to update already crawled pages?"
            ],
            red_flags=[
                "No rate limiting",
                "Single machine design",
                "Not handling duplicates",
                "Infinite loops on cyclic links"
            ],
            time_estimate_minutes=60,
            evaluation_criteria={
                "component_design": "Identifies key components",
                "politeness": "Rate limiting and domain-specific queues",
                "deduplication": "Bloom filter and content hashing",
                "scalability": "Distributed architecture",
                "freshness": "Recrawling strategy"
            }
        ),
        hints=["Consider politeness", "Think about scale"],
        variations=[
            "Design a Search Engine",
            "Design a News Feed System",
            "Design a Content Discovery Platform"
        ],
        frequency="common",
        source="verified"
    ),
])


# ═══════════════════════════════════════════════════════════════════════════════
# QUESTION DATABASE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class QuestionDatabase:
    """Manager for the comprehensive question database"""

    def __init__(self):
        self._questions: Dict[str, InterviewQuestion] = {}
        self._by_category: Dict[QuestionCategory, List[str]] = {}
        self._by_difficulty: Dict[Difficulty, List[str]] = {}
        self._by_company: Dict[str, List[str]] = {}
        self._by_topic: Dict[str, List[str]] = {}
        self._by_role: Dict[str, List[str]] = {}

        self._load_all_questions()

    def _load_all_questions(self):
        """Load all questions into indices"""
        # Load bulk question data if available
        _bulk_behavioral = []
        _bulk_coding = []
        _bulk_system_design = []
        _bulk_technical = []
        _bulk_culture_fit = []
        _bulk_case_study = []
        try:
            from modules.interview.question_bulk_data import (
                BULK_BEHAVIORAL, BULK_CODING, BULK_SYSTEM_DESIGN,
                BULK_TECHNICAL, BULK_CULTURE_FIT, BULK_CASE_STUDY,
            )
            _bulk_behavioral = BULK_BEHAVIORAL
            _bulk_coding = BULK_CODING
            _bulk_system_design = BULK_SYSTEM_DESIGN
            _bulk_technical = BULK_TECHNICAL
            _bulk_culture_fit = BULK_CULTURE_FIT
            _bulk_case_study = BULK_CASE_STUDY
        except ImportError:
            pass

        all_questions = (
            BEHAVIORAL_QUESTIONS + _bulk_behavioral + _bulk_culture_fit + _bulk_case_study +
            CODING_QUESTIONS + _bulk_coding +
            SYSTEM_DESIGN_QUESTIONS + _bulk_system_design +
            _bulk_technical
        )

        for q in all_questions:
            self._questions[q.id] = q

            # Index by category
            if q.category not in self._by_category:
                self._by_category[q.category] = []
            self._by_category[q.category].append(q.id)

            # Index by difficulty
            if q.difficulty not in self._by_difficulty:
                self._by_difficulty[q.difficulty] = []
            self._by_difficulty[q.difficulty].append(q.id)

            # Index by company
            for company in q.companies:
                if company not in self._by_company:
                    self._by_company[company] = []
                self._by_company[company].append(q.id)

            # Index by topic
            for topic in q.topics:
                if topic not in self._by_topic:
                    self._by_topic[topic] = []
                self._by_topic[topic].append(q.id)

            # Index by role
            for role in q.roles:
                if role not in self._by_role:
                    self._by_role[role] = []
                self._by_role[role].append(q.id)

    def get_question(self, question_id: str) -> Optional[InterviewQuestion]:
        """Get a question by ID"""
        return self._questions.get(question_id)

    def get_questions_by_category(self, category: QuestionCategory, limit: int = 100) -> List[InterviewQuestion]:
        """Get questions by category"""
        ids = self._by_category.get(category, [])[:limit]
        return [self._questions[qid] for qid in ids]

    def get_questions_by_difficulty(self, difficulty: Difficulty, limit: int = 100) -> List[InterviewQuestion]:
        """Get questions by difficulty"""
        ids = self._by_difficulty.get(difficulty, [])[:limit]
        return [self._questions[qid] for qid in ids]

    def get_questions_by_company(self, company: str, limit: int = 100) -> List[InterviewQuestion]:
        """Get questions asked by a specific company"""
        ids = self._by_company.get(company.lower(), [])[:limit]
        return [self._questions[qid] for qid in ids]

    def get_questions_by_topic(self, topic: str, limit: int = 100) -> List[InterviewQuestion]:
        """Get questions on a specific topic"""
        ids = self._by_topic.get(topic.lower(), [])[:limit]
        return [self._questions[qid] for qid in ids]

    def get_questions_for_role(self, role: str, limit: int = 100) -> List[InterviewQuestion]:
        """Get questions applicable to a specific role"""
        ids = self._by_role.get(role.lower(), [])[:limit]
        return [self._questions[qid] for qid in ids]

    def search_questions(self, query: str, limit: int = 100) -> List[InterviewQuestion]:
        """Search questions by text"""
        query_lower = query.lower()
        results = []

        for q in self._questions.values():
            if query_lower in q.question.lower():
                results.append(q)
            elif any(query_lower in topic.lower() for topic in q.topics):
                results.append(q)
            elif any(query_lower in company.lower() for company in q.companies):
                results.append(q)

            if len(results) >= limit:
                break

        return results

    def get_practice_set(self, role: str, difficulty: Difficulty = None,
                        num_behavioral: int = 3, num_coding: int = 2,
                        num_system_design: int = 1) -> Dict[str, List[InterviewQuestion]]:
        """Generate a balanced practice set for a role"""
        result = {
            "behavioral": [],
            "coding": [],
            "system_design": []
        }

        # Get behavioral questions for this role
        behavioral = self.get_questions_for_role(role)
        behavioral = [q for q in behavioral if q.category == QuestionCategory.BEHAVIORAL]
        if difficulty:
            behavioral = [q for q in behavioral if q.difficulty == difficulty]
        result["behavioral"] = behavioral[:num_behavioral]

        # Get coding questions for this role
        coding = self.get_questions_for_role(role)
        coding = [q for q in coding if q.category == QuestionCategory.CODING]
        if difficulty:
            coding = [q for q in coding if q.difficulty == difficulty]
        result["coding"] = coding[:num_coding]

        # Get system design questions for this role
        system_design = self.get_questions_for_role(role)
        system_design = [q for q in system_design if q.category == QuestionCategory.SYSTEM_DESIGN]
        if difficulty:
            system_design = [q for q in system_design if q.difficulty == difficulty]
        result["system_design"] = system_design[:num_system_design]

        return result

    def get_stats(self) -> Dict:
        """Get database statistics"""
        return {
            "total_questions": len(self._questions),
            "by_category": {cat.value: len(ids) for cat, ids in self._by_category.items()},
            "by_difficulty": {diff.value: len(ids) for diff, ids in self._by_difficulty.items()},
            "companies_covered": len(self._by_company),
            "topics_covered": len(self._by_topic),
            "roles_covered": len(self._by_role),
        }

    def export_to_json(self, filepath: str):
        """Export all questions to JSON"""
        data = [q.to_dict() for q in self._questions.values()]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


# Global database instance
question_db = QuestionDatabase()


# ═══════════════════════════════════════════════════════════════════════════════
# API FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_question(question_id: str) -> Optional[Dict]:
    """Get a question by ID"""
    q = question_db.get_question(question_id)
    return q.to_dict() if q else None

def get_questions_by_category(category: str, limit: int = 100) -> List[Dict]:
    """Get questions by category"""
    cat = QuestionCategory(category)
    questions = question_db.get_questions_by_category(cat, limit)
    return [q.to_dict() for q in questions]

def get_questions_by_difficulty(difficulty: str, limit: int = 100) -> List[Dict]:
    """Get questions by difficulty"""
    diff = Difficulty(difficulty)
    questions = question_db.get_questions_by_difficulty(diff, limit)
    return [q.to_dict() for q in questions]

def get_questions_by_company(company: str, limit: int = 100) -> List[Dict]:
    """Get questions by company"""
    questions = question_db.get_questions_by_company(company, limit)
    return [q.to_dict() for q in questions]

def search_questions(query: str, limit: int = 100) -> List[Dict]:
    """Search questions"""
    questions = question_db.search_questions(query, limit)
    return [q.to_dict() for q in questions]

def get_practice_set(role: str, difficulty: str = None) -> Dict[str, List[Dict]]:
    """Get a practice set for a role"""
    diff = Difficulty(difficulty) if difficulty else None
    result = question_db.get_practice_set(role, diff)
    return {
        cat: [q.to_dict() for q in questions]
        for cat, questions in result.items()
    }

def get_database_stats() -> Dict:
    """Get database statistics"""
    return question_db.get_stats()


__all__ = [
    "QuestionDatabase", "question_db",
    "InterviewQuestion", "ExpectedAnswer",
    "QuestionCategory", "Difficulty", "CompanyTier",
    "get_question", "get_questions_by_category",
    "get_questions_by_difficulty", "get_questions_by_company",
    "search_questions", "get_practice_set", "get_database_stats",
]
