"""
company_questions.py - Company-Specific Interview Questions
Verified questions asked by major tech companies
"""

from typing import List, Dict
from question_database_v2 import InterviewQuestion, QuestionCategory, Difficulty, ExpectedAnswer, CompanyTier

# ═══════════════════════════════════════════════════════════════════════════════
# GOOGLE INTERVIEW QUESTIONS
# ═══════════════════════════════════════════════════════════════════════════════

GOOGLE_QUESTIONS = [
    # Behavioral
    InterviewQuestion(
        id="goog-bh-001",
        question="Tell me about a time you had to deal with ambiguity at work.",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer", "product_manager", "engineering_manager"],
        companies=["google"],
        company_tiers=[CompanyTier.FAANG],
        topics=["ambiguity", "problem_solving", "leadership"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Google values dealing with ambiguity as a core trait",
                "Show comfort with unclear requirements",
                "Demonstrate ability to make progress without full information",
                "Highlight asking clarifying questions",
                "Show how you defined scope yourself"
            ],
            follow_up_questions=["How do you prioritize when everything seems important?"],
            red_flags=["Needing perfect clarity before starting", "Not making decisions"],
            time_estimate_minutes=10,
            evaluation_criteria={"comfort_with_ambiguity": "Core Google value", "proactivity": "Makes progress without perfect info"}
        ),
        hints=["Google specifically values 'Dealing with Ambiguity'", "Show comfort with unclear requirements"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="goog-bh-002",
        question="Describe a situation where you had to learn something quickly.",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.EASY,
        roles=["software_engineer", "data_scientist", "product_manager"],
        companies=["google"],
        company_tiers=[CompanyTier.FAANG],
        topics=["learning", "adaptability", "growth_mindset"],
        expected_answer=ExpectedAnswer(
            key_points=["Show intellectual humility", "Learning process/strategy", "Application of learning"],
            follow_up_questions=["How do you approach learning new technologies?"],
            red_flags=["Claiming to know everything already"],
            time_estimate_minutes=8,
            evaluation_criteria={"learning_ability": "Google values continuous learning"}
        ),
        hints=["Show learning strategy", "Intellectual humility"],
        frequency="common",
        source="verified"
    ),

    # Coding - Google loves these specific patterns
    InterviewQuestion(
        id="goog-cd-001",
        question="Given a string, find the length of the longest substring without repeating characters.",
        category=QuestionCategory.CODING,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer"],
        companies=["google"],
        company_tiers=[CompanyTier.FAANG],
        topics=["sliding_window", "hash_set", "strings"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Sliding window with hash set",
                "Expand window until duplicate found",
                "Contract from left until duplicate removed",
                "O(n) time, O(min(m,n)) space where m is charset size"
            ],
            follow_up_questions=["What if the input contains Unicode?", "Optimize for space"],
            red_flags=["Brute force O(n³)", "Not handling all repeating chars"],
            time_estimate_minutes=25,
            evaluation_criteria={"optimal_solution": "Sliding window O(n)"}
        ),
        hints=["Sliding window technique", "Hash set for O(1) lookup"],
        variations=["Longest Substring with At Most K Distinct Characters"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="goog-cd-002",
        question="Design a data structure that supports insert, delete, and getRandom in O(1) time.",
        category=QuestionCategory.CODING,
        difficulty=Difficulty.MEDIUM,
        roles=["senior_software_engineer", "staff_engineer"],
        companies=["google"],
        company_tiers=[CompanyTier.FAANG],
        topics=["hash_map", "array", "design", "random"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Hash map: value -> index in array",
                "Array: stores actual values",
                "Delete: swap with last element, update hash map",
                "getRandom: random index in array"
            ],
            follow_up_questions=["How to make it thread-safe?", "What about duplicates?"],
            red_flags=["Not using hash map", "O(n) deletion"],
            time_estimate_minutes=30,
            evaluation_criteria={"design": "Combines hash map + array"}
        ),
        hints=["Combine hash map with array", "Swap during delete"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="goog-cd-003",
        question="Implement a Prefix Trie (Autocomplete system).",
        category=QuestionCategory.CODING,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer"],
        companies=["google"],
        company_tiers=[CompanyTier.FAANG],
        topics=["trie", "prefix_matching", "trees"],
        expected_answer=ExpectedAnswer(
            key_points=["Trie node with children dict and is_end flag", "Insert: O(m) where m is word length", "Search: O(m)", "StartsWith: O(m)"],
            follow_up_questions=["Wildcard matching?", "How to implement autocomplete?"],
            red_flags=["Using array for children (waste space)"],
            time_estimate_minutes=25,
            evaluation_criteria={"trie_implementation": "Correct trie structure"}
        ),
        hints=["Use hash map for children", "is_end flag"],
        variations=["Word Search II", "Design Search Autocomplete System"],
        frequency="common",
        source="verified"
    ),

    # System Design
    InterviewQuestion(
        id="goog-sd-001",
        question="Design Google Search",
        category=QuestionCategory.SYSTEM_DESIGN,
        difficulty=Difficulty.EXPERT,
        roles=["senior_software_engineer", "staff_engineer", "principal_engineer"],
        companies=["google"],
        company_tiers=[CompanyTier.FAANG],
        topics=["search", "inverted_index", "distributed_systems", "crawler", "ranking"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Web crawler: distributed, polite",
                "Indexer: inverted index, tokenization",
                "Ranking: PageRank, machine learning",
                "Query processing: spelling correction, autocomplete",
                "Serving: low latency, high availability"
            ],
            follow_up_questions=["How to detect duplicate content?", "How to rank results?", "Real-time indexing?"],
            red_flags=["Not mentioning inverted index", "Single machine design"],
            time_estimate_minutes=60,
            evaluation_criteria={"search_fundamentals": "Inverted index understanding"}
        ),
        hints=["Start with inverted index", "Think about scale"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="goog-sd-002",
        question="Design Google Docs (Collaborative Editing)",
        category=QuestionCategory.SYSTEM_DESIGN,
        difficulty=Difficulty.HARD,
        roles=["senior_software_engineer", "staff_engineer"],
        companies=["google"],
        company_tiers=[CompanyTier.FAANG],
        topics=["collaborative_editing", "operational_transform", "conflict_resolution", "real_time"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Operational Transform (OT) or CRDT",
                "WebSocket for real-time sync",
                "Versioning and conflict resolution",
                "Cursor synchronization",
                "Storage: document snapshots + operations"
            ],
            follow_up_questions=["OT vs CRDT tradeoffs?", "Offline editing support?"],
            red_flags=["Not mentioning OT or CRDT", "Lock-based concurrency"],
            time_estimate_minutes=60,
            evaluation_criteria={"collaboration": "OT or CRDT understanding"}
        ),
        hints=["Research Operational Transform", "Real-time sync challenges"],
        frequency="common",
        source="verified"
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# AMAZON INTERVIEW QUESTIONS
# Focus on Leadership Principles
# ═══════════════════════════════════════════════════════════════════════════════

AMAZON_QUESTIONS = [
    # Leadership Principles - Customer Obsession
    InterviewQuestion(
        id="amz-bh-001",
        question="Tell me about a time you went above and beyond for a customer.",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer", "product_manager", "engineering_manager"],
        companies=["amazon", "aws"],
        company_tiers=[CompanyTier.FAANG],
        topics=["customer_obsession", "ownership", "leadership_principles"],
        expected_answer=ExpectedAnswer(
            key_points=[
                "Amazon Leadership Principle: Customer Obsession",
                "Started with customer need",
                "Went beyond job description",
                "Measurable customer impact",
                "Worked backwards from customer"
            ],
            follow_up_questions=["What was the customer feedback?", "How did you measure success?"],
            red_flags=["Not customer-focused", "Doing minimum required"],
            time_estimate_minutes=10,
            evaluation_criteria={"customer_obsession": "Core Amazon LP"}
        ),
        hints=["Amazon LP: Customer Obsession", "Work backwards"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="amz-bh-002",
        question="Give an example of when you took ownership of something outside your scope.",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer", "engineering_manager"],
        companies=["amazon", "aws"],
        company_tiers=[CompanyTier.FAANG],
        topics=["ownership", "leadership_principles", "bias_for_action"],
        expected_answer=ExpectedAnswer(
            key_points=["Amazon LP: Ownership", "Didn't wait to be asked", "Long-term thinking", "Never say 'not my job'"],
            follow_up_questions=["How did you balance with your regular work?"],
            red_flags=["Waiting for permission", "Short-term thinking"],
            time_estimate_minutes=10,
            evaluation_criteria={"ownership": "Core Amazon LP"}
        ),
        hints=["Amazon LP: Ownership", "Long-term thinking"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="amz-bh-003",
        question="Tell me about a time you failed and what you learned (Dive Deep question).",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer", "engineering_manager"],
        companies=["amazon", "aws"],
        company_tiers=[CompanyTier.FAANG],
        topics=["dive_deep", "failure", "learning", "ownership"],
        expected_answer=ExpectedAnswer(
            key_points=["Amazon LP: Dive Deep + Learn and Be Curious", "Root cause analysis", "Systemic fixes", "Ownership of failure"],
            follow_up_questions=["How did you prevent recurrence?", "What metrics did you track?"],
            red_flags=["Blaming others", "Superficial analysis"],
            time_estimate_minutes=12,
            evaluation_criteria={"dive_deep": "Thorough root cause analysis"}
        ),
        hints=["Amazon LP: Dive Deep", "Show thorough analysis"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="amz-bh-004",
        question="Describe a time you had to disagree with your manager or senior leader.",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.HARD,
        roles=["senior_software_engineer", "staff_engineer", "engineering_manager"],
        companies=["amazon", "aws"],
        company_tiers=[CompanyTier.FAANG],
        topics=["disagree_and_commit", "leadership_principles", "courage"],
        expected_answer=ExpectedAnswer(
            key_points=["Amazon LP: Disagree and Commit", "Data-driven disagreement", "Escalated appropriately", "Committed after decision made"],
            follow_up_questions=["How did you escalate?", "What happened if they didn't agree?"],
            red_flags=["Not committing after decision", "Emotional disagreement"],
            time_estimate_minutes=12,
            evaluation_criteria={"disagree_and_commit": "Core Amazon LP"}
        ),
        hints=["Amazon LP: Disagree and Commit", "Data over opinion"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="amz-bh-005",
        question="Tell me about a time you had to deliver results with tight deadlines and limited resources.",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer", "product_manager"],
        companies=["amazon", "aws"],
        company_tiers=[CompanyTier.FAANG],
        topics=[["deliver_results", "frugality", "bias_for_action"]],
        expected_answer=ExpectedAnswer(
            key_points=["Amazon LP: Deliver Results + Frugality", "Prioritization under constraints", "Still delivered quality", "Resourceful"],
            follow_up_questions=["What tradeoffs did you make?"],
            red_flags=["Sacrificing quality", "Not delivering"],
            time_estimate_minutes=10,
            evaluation_criteria={"deliver_results": "Focus on outcomes"}
        ),
        hints=["Amazon LP: Deliver Results", "Show resourcefulness"],
        frequency="common",
        source="verified"
    ),

    # Coding - Amazon style
    InterviewQuestion(
        id="amz-cd-001",
        question="Merge K Sorted Lists",
        category=QuestionCategory.CODING,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer"],
        companies=["amazon", "aws"],
        company_tiers=[CompanyTier.FAANG],
        topics=["linked_list", "heap", "divide_and_conquer", "sorting"],
        expected_answer=ExpectedAnswer(
            key_points=["Min-heap: O(N log k) time", "Divide and conquer: O(N log k)", "Compare one by one: O(kN) - suboptimal"],
            follow_up_questions=["What if lists are huge?", "Stream processing?"],
            red_flags=["Not knowing heap approach"],
            time_estimate_minutes=25,
            evaluation_criteria={"heap_usage": "Efficient heap approach"}
        ),
        hints=["Min-heap", "Compare heads"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="amz-cd-002",
        question="LRU Cache - Design and implement",
        category=QuestionCategory.CODING,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer"],
        companies=["amazon", "aws"],
        company_tiers=[CompanyTier.FAANG],
        topics=["design", "hash_map", "doubly_linked_list", "cache"],
        expected_answer=ExpectedAnswer(
            key_points=["Hash map + Doubly linked list", "O(1) get and put", "Head = most recent, Tail = least recent", "Handle capacity limits"],
            follow_up_questions=["Thread safety?", "Eviction policies?", "Distributed LRU?"],
            red_flags=["Using array (O(n) eviction)", "Not handling edge cases"],
            time_estimate_minutes=30,
            evaluation_criteria={"design": "Hash map + DLL combination"}
        ),
        hints=["Hash map for O(1) lookup", "DLL for O(1) reordering"],
        variations=["LFU Cache", "Design In-Memory File System"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="amz-cd-003",
        question="Trapping Rain Water",
        category=QuestionCategory.CODING,
        difficulty=Difficulty.HARD,
        roles=["senior_software_engineer", "software_engineer"],
        companies=["amazon", "aws"],
        company_tiers=[CompanyTier.FAANG],
        topics=["two_pointers", "dynamic_programming", "stack", "arrays"],
        expected_answer=ExpectedAnswer(
            key_points=["Two pointers: O(n) time, O(1) space", "Water trapped = min(max_left, max_right) - height[i]", "DP: O(n) time, O(n) space"],
            follow_up_questions=["3D version?", "What about multiple buildings?"],
            red_flags=["Brute force O(n²) without optimization"],
            time_estimate_minutes=30,
            evaluation_criteria={"optimal_solution": "Two pointers O(n)"}
        ),
        hints=["Calculate water at each position", "Two pointers from ends"],
        frequency="common",
        source="verified"
    ),

    # System Design
    InterviewQuestion(
        id="amz-sd-001",
        question="Design Amazon's Product Recommendation System",
        category=QuestionCategory.SYSTEM_DESIGN,
        difficulty=Difficulty.HARD,
        roles=["senior_software_engineer", "machine_learning_engineer", "data_engineer"],
        companies=["amazon", "aws"],
        company_tiers=[CompanyTier.FAANG],
        topics=["recommendation_system", "machine_learning", "big_data", "real_time"],
        expected_answer=ExpectedAnswer(
            key_points=["Collaborative filtering", "Content-based filtering", "Real-time vs batch", "A/B testing", "Cold start problem"],
            follow_up_questions=["How to handle new users?", "Real-time recommendations?"],
            red_flags=["Not mentioning cold start", "No ML discussion"],
            time_estimate_minutes=60,
            evaluation_criteria={"ml_knowledge": "Understanding of recommendation algorithms"}
        ),
        hints=["Collaborative + Content-based", "Cold start handling"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="amz-sd-002",
        question="Design Amazon Shopping Cart",
        category=QuestionCategory.SYSTEM_DESIGN,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer"],
        companies=["amazon", "aws"],
        company_tiers=[CompanyTier.FAANG],
        topics=["ecommerce", "cart", "session_management", "pricing", "inventory"],
        expected_answer=ExpectedAnswer(
            key_points=["Session vs Persistent cart", "Pricing changes", "Inventory reservation", "Multi-device sync", "Abandoned cart"],
            follow_up_questions=["How to handle price changes?", "Inventory reservation strategy?"],
            red_flags=["Not handling concurrent modifications"],
            time_estimate_minutes=45,
            evaluation_criteria={"ecommerce_domain": "Understanding of cart semantics"}
        ),
        hints=["Think about abandoned carts", "Price changes"],
        frequency="common",
        source="verified"
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# META/FACEBOOK INTERVIEW QUESTIONS
# Focus on Move Fast and Impact
# ═══════════════════════════════════════════════════════════════════════════════

META_QUESTIONS = [
    InterviewQuestion(
        id="meta-bh-001",
        question="Tell me about a time you moved fast and broke things. What happened?",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "product_manager", "engineering_manager"],
        companies=["meta", "facebook", "instagram", "whatsapp"],
        company_tiers=[CompanyTier.FAANG],
        topics=["move_fast", "risk_taking", "learning"],
        expected_answer=ExpectedAnswer(
            key_points=["Meta value: Move Fast", "Calculated risk", "Learned from failure", "Fixed quickly", "Didn't repeat"],
            follow_up_questions=["How did you mitigate the breakage?"],
            red_flags=["Being reckless", "Not learning"],
            time_estimate_minutes=10,
            evaluation_criteria={"move_fast": "Meta core value"}
        ),
        hints=["Meta value: Move Fast", "Calculated risks"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="meta-bh-002",
        question="Describe a time you had to sacrifice quality for speed. Was it worth it?",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer"],
        companies=["meta", "facebook"],
        company_tiers=[CompanyTier.FAANG],
        topics=["tradeoffs", "speed_vs_quality", "pragmatism"],
        expected_answer=ExpectedAnswer(
            key_points=["Meta: Move fast", "Intentional tech debt", "Plan to pay it back", "Business impact"],
            follow_up_questions=["When is it NOT worth it?"],
            red_flags=["Always sacrificing quality", "Not understanding tradeoffs"],
            time_estimate_minutes=10,
            evaluation_criteria={"pragmatism": "Understands business context"}
        ),
        hints=["Show pragmatic thinking", "Know when to pay debt back"],
        frequency="common",
        source="verified"
    ),

    # Coding
    InterviewQuestion(
        id="meta-cd-001",
        question="Valid Parentheses - Given a string containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.",
        category=QuestionCategory.CODING,
        difficulty=Difficulty.EASY,
        roles=["software_engineer", "frontend_engineer"],
        companies=["meta", "facebook", "instagram"],
        company_tiers=[CompanyTier.FAANG],
        topics=["stack", "string", "parentheses_matching"],
        expected_answer=ExpectedAnswer(
            key_points=["Stack: Push opening, pop and match closing", "O(n) time, O(n) space", "Edge cases: Empty, odd length"],
            follow_up_questions=["What about other characters?", "Multiple types of brackets?"],
            red_flags=["Not using stack", "Complex regex approach"],
            time_estimate_minutes=15,
            evaluation_criteria={"stack_usage": "Correct stack approach"}
        ),
        hints=["Use stack", "Match pairs"],
        variations=["Minimum Add to Make Parentheses Valid", "Longest Valid Parentheses"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="meta-cd-002",
        question="Clone Graph - Given a reference of a node in a connected undirected graph, return a deep copy of the graph.",
        category=QuestionCategory.CODING,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "senior_software_engineer"],
        companies=["meta", "facebook"],
        company_tiers=[CompanyTier.FAANG],
        topics=["graph", "dfs", "bfs", "hash_map", "deep_copy"],
        expected_answer=ExpectedAnswer(
            key_points=["Hash map: original node -> cloned node", "DFS or BFS traversal", "Handle cycles with visited set", "O(V+E) time, O(V) space"],
            follow_up_questions=["Directed graph?", "Weighted graph?", "How to test?"],
            red_flags=["Not handling cycles", "Not using hash map"],
            time_estimate_minutes=25,
            evaluation_criteria={"graph_traversal": "Correct DFS/BFS with hash map"}
        ),
        hints=["Hash map for mapping", "Handle cycles"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="meta-cd-003",
        question="Regular Expression Matching - Implement regular expression matching with support for '.' and '*'.",
        category=QuestionCategory.CODING,
        difficulty=Difficulty.HARD,
        roles=["senior_software_engineer", "staff_engineer"],
        companies=["meta", "facebook"],
        company_tiers=[CompanyTier.FAANG],
        topics=["dynamic_programming", "recursion", "memoization", "strings"],
        expected_answer=ExpectedAnswer(
            key_points=["DP: dp[i][j] = match s[0:i] with p[0:j]", "Handle '*' by zero or more", "Handle '.' as wildcard", "O(mn) time, O(mn) space"],
            follow_up_questions=["Optimize space?", "Support more regex features?"],
            red_flags=["Not recognizing DP problem", "Incorrect '*' handling"],
            time_estimate_minutes=35,
            evaluation_criteria={"dp_solution": "Correct DP approach"}
        ),
        hints=["DP table", "'*' can match zero or more"],
        frequency="common",
        source="verified"
    ),

    # System Design
    InterviewQuestion(
        id="meta-sd-001",
        question="Design Facebook News Feed",
        category=QuestionCategory.SYSTEM_DESIGN,
        difficulty=Difficulty.HARD,
        roles=["senior_software_engineer", "staff_engineer"],
        companies=["meta", "facebook", "instagram"],
        company_tiers=[CompanyTier.FAANG],
        topics=["news_feed", "fanout", "ranking", "caching", "social_graph"],
        expected_answer=ExpectedAnswer(
            key_points=["Fanout on write (push) vs Fanout on read (pull)", "Feed generation", "Ranking algorithm", "Caching hot feeds", "Real-time updates"],
            follow_up_questions=["How to rank posts?", "Celebrity problem?", "Consistency vs availability?"],
            red_flags=["Not considering fanout strategy", "No ranking discussion"],
            time_estimate_minutes=60,
            evaluation_criteria={"social_system": "Understanding of feed architecture"}
        ),
        hints=["Fanout on write vs read", "Celebrity problem"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="meta-sd-002",
        question="Design Facebook Messenger",
        category=QuestionCategory.SYSTEM_DESIGN,
        difficulty=Difficulty.HARD,
        roles=["senior_software_engineer", "staff_engineer"],
        companies=["meta", "facebook", "whatsapp"],
        company_tiers=[CompanyTier.FAANG],
        topics=["messaging", "real_time", "websocket", "presence", "notifications"],
        expected_answer=ExpectedAnswer(
            key_points=["WebSocket for real-time", "Message storage", "Delivery receipts", "Presence system", "Group chats", "Media storage"],
            follow_up_questions=["Message ordering?", "Offline message queue?", "End-to-end encryption?"],
            red_flags=["Polling approach", "No offline support"],
            time_estimate_minutes=60,
            evaluation_criteria={"real_time_system": "WebSocket/long-polling understanding"}
        ),
        hints=["WebSocket for real-time", "Handle offline messages"],
        frequency="common",
        source="verified"
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# NETFLIX INTERVIEW QUESTIONS
# Focus on Freedom & Responsibility
# ═══════════════════════════════════════════════════════════════════════════════

NETFLIX_QUESTIONS = [
    InterviewQuestion(
        id="nflx-bh-001",
        question="Tell me about a time you made a significant decision without asking permission.",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.MEDIUM,
        roles=["senior_software_engineer", "staff_engineer", "principal_engineer"],
        companies=["netflix"],
        company_tiers=[CompanyTier.FAANG],
        topics=["freedom_responsibility", "ownership", "decision_making"],
        expected_answer=ExpectedAnswer(
            key_points=["Netflix culture: Freedom & Responsibility", "Informed captain", "Took calculated risk", "Owned outcome", "Right level of communication"],
            follow_up_questions=["When would you escalate?"],
            red_flags=["Asking permission for everything", "Not communicating after decision"],
            time_estimate_minutes=10,
            evaluation_criteria={"freedom": "Netflix culture fit"}
        ),
        hints=["Netflix culture deck", "Informed captain"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="nflx-bh-002",
        question="Describe a time you had to let go of a talented but underperforming team member.",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.HARD,
        roles=["engineering_manager", "senior_engineering_manager", "director"],
        companies=["netflix"],
        company_tiers=[CompanyTier.FAANG],
        topics=["performance_management", "culture", "tough_decisions"],
        expected_answer=ExpectedAnswer(
            key_points=["Netflix: Adequate performance gets generous severance", "Tried to coach first", "Clear feedback", "Respectful exit", "Team performance improved"],
            follow_up_questions=["How did the team react?"],
            red_flags=["Keeping underperformers", "Sudden firing without feedback"],
            time_estimate_minutes=12,
            evaluation_criteria={"culture_fit": "Understands Netflix performance culture"}
        ),
        hints=["Netflix culture: Adequate performance gets severance", "Respectful process"],
        frequency="common",
        source="verified"
    ),

    # System Design
    InterviewQuestion(
        id="nflx-sd-001",
        question="Design Netflix Video Streaming Service",
        category=QuestionCategory.SYSTEM_DESIGN,
        difficulty=Difficulty.EXPERT,
        roles=["senior_software_engineer", "staff_engineer", "principal_engineer"],
        companies=["netflix"],
        company_tiers=[CompanyTier.FAANG],
        topics=["video_streaming", "cdn", "adaptive_bitrate", "encoding", "recommendation"],
        expected_answer=ExpectedAnswer(
            key_points=["Content ingestion and encoding", "Multiple bitrates", "CDN for distribution", "Client-side adaptation", "Digital rights management", "Recommendation engine"],
            follow_up_questions=["How to handle network fluctuations?", "Live streaming?", "Download for offline?"],
            red_flags=["Single bitrate", "No CDN discussion"],
            time_estimate_minutes=60,
            evaluation_criteria={"streaming_domain": "Understanding of video delivery"}
        ),
        hints=["Adaptive bitrate", "CDN distribution"],
        frequency="common",
        source="verified"
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# MICROSOFT INTERVIEW QUESTIONS
# Focus on Growth Mindset and Collaboration
# ═══════════════════════════════════════════════════════════════════════════════

MICROSOFT_QUESTIONS = [
    InterviewQuestion(
        id="msft-bh-001",
        question="Tell me about a time you received difficult feedback. How did you respond?",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.EASY,
        roles=["software_engineer", "product_manager", "program_manager"],
        companies=["microsoft"],
        company_tiers=[CompanyTier.FAANG],
        topics=["growth_mindset", "feedback", "learning"],
        expected_answer=ExpectedAnswer(
            key_points=["Microsoft value: Growth mindset", "Listened without defensiveness", "Sought to understand", "Made concrete changes", "Followed up with feedback giver"],
            follow_up_questions=["How do you actively seek feedback?"],
            red_flags=["Being defensive", "Dismissing feedback"],
            time_estimate_minutes=8,
            evaluation_criteria={"growth_mindset": "Core Microsoft value"}
        ),
        hints=["Microsoft: Growth mindset", "Show learning"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="msft-bh-002",
        question="Describe a time you collaborated with someone very different from you.",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.EASY,
        roles=["software_engineer", "product_manager", "designer"],
        companies=["microsoft"],
        company_tiers=[CompanyTier.FAANG],
        topics=["diversity", "collaboration", "inclusion"],
        expected_answer=ExpectedAnswer(
            key_points=["Microsoft value: Diversity and inclusion", "Found common ground", "Learned from differences", "Successful collaboration", "Appreciated different perspectives"],
            follow_up_questions=["What did you learn from them?"],
            red_flags=["Not valuing differences", "Avoiding collaboration"],
            time_estimate_minutes=8,
            evaluation_criteria={"collaboration": "Works well with diverse teams"}
        ),
        hints=["Microsoft values diversity", "Show inclusion"],
        frequency="common",
        source="verified"
    ),

    # Coding
    InterviewQuestion(
        id="msft-cd-001",
        question="Design Tic-Tac-Toe game",
        category=QuestionCategory.CODING,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "frontend_engineer"],
        companies=["microsoft"],
        company_tiers=[CompanyTier.FAANG],
        topics=["design", "oop", "game", "board"],
        expected_answer=ExpectedAnswer(
            key_points=["Board representation", "Move validation", "Win detection (rows, cols, diagonals)", "Player switching", "Draw detection"],
            follow_up_questions=["How to scale to N x N?", "How to scale to K players?", "AI opponent?"],
            red_flags=["Not OOP design", "Not handling edge cases"],
            time_estimate_minutes=25,
            evaluation_criteria={"oop_design": "Good object-oriented design"}
        ),
        hints=["Think about win conditions", "OOP classes"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="msft-cd-002",
        question="Design an Excel Spreadsheet with formula calculation",
        category=QuestionCategory.CODING,
        difficulty=Difficulty.HARD,
        roles=["senior_software_engineer", "staff_engineer"],
        companies=["microsoft"],
        company_tiers=[CompanyTier.FAANG],
        topics=["design", "dependency_graph", "topological_sort", "cycle_detection", "spreadsheet"],
        expected_answer=ExpectedAnswer(
            key_points=["Cell representation", "Formula parsing", "Dependency graph", "Topological sort for calculation order", "Cycle detection", "Incremental updates"],
            follow_up_questions=["How to optimize recalculation?", "Circular reference handling?", "Multi-sheet support?"],
            red_flags=["Not handling dependencies", "No cycle detection"],
            time_estimate_minutes=45,
            evaluation_criteria={"dependency_management": "Correct dependency graph handling"}
        ),
        hints=["Dependency graph", "Topological sort"],
        frequency="common",
        source="verified"
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# APPLE INTERVIEW QUESTIONS
# Focus on Secrecy and Craftsmanship
# ═══════════════════════════════════════════════════════════════════════════════

APPLE_QUESTIONS = [
    InterviewQuestion(
        id="aapl-bh-001",
        question="Tell me about a time you worked on something confidential.",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.MEDIUM,
        roles=["software_engineer", "hardware_engineer", "product_manager"],
        companies=["apple"],
        company_tiers=[CompanyTier.FAANG],
        topics=["confidentiality", "trust", "professionalism"],
        expected_answer=ExpectedAnswer(
            key_points=["Apple values secrecy", "Respected confidentiality", "No leaks", "Professional handling", "Trusted with sensitive info"],
            follow_up_questions=["How do you handle pressure to share?"],
            red_flags=["Discussing confidential details", "Not respecting boundaries"],
            time_estimate_minutes=8,
            evaluation_criteria={"trustworthiness": "Can be trusted with secrets"}
        ),
        hints=["Apple values secrecy", "Show professionalism"],
        frequency="common",
        source="verified"
    ),

    InterviewQuestion(
        id="aapl-bh-002",
        question="Describe your attention to detail on a project.",
        category=QuestionCategory.BEHAVIORAL,
        difficulty=Difficulty.EASY,
        roles=["software_engineer", "designer", "qa_engineer"],
        companies=["apple"],
        company_tiers=[CompanyTier.FAANG],
        topics=["craftsmanship", "attention_to_detail", "quality"],
        expected_answer=ExpectedAnswer(
            key_points=["Apple values craftsmanship", "Pixel-perfect implementation", "Edge cases handled", "Polished user experience", "Pride in work"],
            follow_up_questions=["How do you balance perfection with deadlines?"],
            red_flags=["Not caring about details", "Rushed work"],
            time_estimate_minutes=8,
            evaluation_criteria={"craftsmanship": "Attention to detail"}
        ),
        hints=["Apple values craftsmanship", "Show perfectionism"],
        frequency="common",
        source="verified"
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# AGGREGATE ALL COMPANY QUESTIONS
# ═══════════════════════════════════════════════════════════════════════════════

ALL_COMPANY_QUESTIONS = (
    GOOGLE_QUESTIONS +
    AMAZON_QUESTIONS +
    META_QUESTIONS +
    NETFLIX_QUESTIONS +
    MICROSOFT_QUESTIONS +
    APPLE_QUESTIONS
)


def get_company_questions(company: str) -> List[InterviewQuestion]:
    """Get all questions for a specific company"""
    return [q for q in ALL_COMPANY_QUESTIONS if company.lower() in [c.lower() for c in q.companies]]


def get_company_specific_tips(company: str) -> Dict[str, str]:
    """Get interview tips for specific companies"""
    tips = {
        "google": {
            "focus": "Problem-solving ability, dealing with ambiguity",
            "format": "4-5 interviews, 45 min each, coding + system design + behavioral",
            "key_values": "Intellectual humility, collaboration, user focus",
            "tips": "Expect follow-up questions, think out loud, show work"
        },
        "amazon": {
            "focus": "Leadership Principles (16 LPs)",
            "format": "4-5 interviews, STAR format required",
            "key_values": "Customer obsession, ownership, dive deep",
            "tips": "Have 2-3 examples per LP, use STAR, focus on 'I' not 'we'"
        },
        "meta": {
            "focus": "Move fast, boldness, impact",
            "format": "Coding (2), System Design (1), Behavioral (1)",
            "key_values": "Move fast, bold, be bold, focus on impact",
            "tips": "Be prepared to discuss tradeoffs, show pragmatism"
        },
        "netflix": {
            "focus": "Freedom \u0026 responsibility, high performance",
            "format": "Conversational, culture fit heavy",
            "key_values": "Freedom \u0026 responsibility, high performance",
            "tips": "Read culture deck, show independent decision making"
        },
        "microsoft": {
            "focus": "Growth mindset, diversity, collaboration",
            "format": "4-5 interviews, mix of coding and behavioral",
            "key_values": "Growth mindset, diversity, customer obsessed",
            "tips": "Show learning from failures, collaboration across teams"
        },
        "apple": {
            "focus": "Craftsmanship, secrecy, user experience",
            "format": "Varies by team, often very secretive",
            "key_values": "Secrecy, craftsmanship, user experience",
            "tips": "Don't ask about unannounced products, show attention to detail"
        }
    }
    return tips.get(company.lower(), {"focus": "General technical skills"})


__all__ = [
    "GOOGLE_QUESTIONS", "AMAZON_QUESTIONS", "META_QUESTIONS",
    "NETFLIX_QUESTIONS", "MICROSOFT_QUESTIONS", "APPLE_QUESTIONS",
    "ALL_COMPANY_QUESTIONS",
    "get_company_questions", "get_company_specific_tips"
]
