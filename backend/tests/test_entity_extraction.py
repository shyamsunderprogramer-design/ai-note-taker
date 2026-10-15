"""
Test suite for backend/modules/ai/entity_extraction.py
Covers EntityExtractor.extract_companies/topics/skills/roles,
categorize_question, estimate_difficulty, extract_all, and
process_transcript.

The module has two optional dependencies that may not be installed:
  - modules.ai.smart_classifier (for ML-backed classification)
  - hybrid_entity_extraction (for hybrid ML+rules)
Both are loaded lazily and gracefully degrade to the rule-based
fallback. The tests below exercise the fallback path.

Run with: python -m pytest backend/tests/test_entity_extraction.py -v
"""

import os
import sys

import pytest

# Add backend/ AND modules/ai/ to sys.path so the relative-ish imports
# inside entity_extraction.py resolve (it lives in modules/ai/).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "modules", "ai"))

from entity_extraction import (  # noqa: E402
    EntityExtractor,
    ExtractedEntity,
    extract_entities,
    process_transcript,
)


@pytest.fixture
def extractor():
    return EntityExtractor()


class TestExtractCompanies:
    """extract_companies: matches against the COMPANY_NAMES set."""

    def test_known_company_found(self, extractor):
        result = extractor.extract_companies("I worked at Google.")
        texts = [e.text for e in result]
        assert "google" in texts  # nosec B101

    def test_multiple_companies(self, extractor):
        result = extractor.extract_companies("I have used Google, Amazon, and Stripe products.")
        texts = {e.text for e in result}
        assert {"google", "amazon", "stripe"} <= texts  # nosec B101

    def test_unknown_company_not_found(self, extractor):
        result = extractor.extract_companies("I worked at FakeCompany Inc.")
        assert result == []  # nosec B101

    def test_empty_text(self, extractor):
        result = extractor.extract_companies("")
        assert result == []  # nosec B101

    def test_case_insensitive(self, extractor):
        result = extractor.extract_companies("GOOGLE is great. google is too. Google again.")
        texts = [e.text for e in result]
        # All matches are normalized to lowercase
        assert all(t == t.lower() for t in texts)  # nosec B101
        assert len(texts) >= 1  # nosec B101

    def test_partial_match_does_not_count(self, extractor):
        # "google" should match but "googleplex" should NOT (word boundary)
        result = extractor.extract_companies("googleplex is a thing")
        texts = [e.text for e in result]
        assert "google" not in texts  # nosec B101
        assert "googleplex" not in texts  # nosec B101

    def test_entity_metadata(self, extractor):
        result = extractor.extract_companies("I love Google")
        assert len(result) >= 1  # nosec B101
        e = result[0]
        assert e.label == "COMPANY"  # nosec B101
        assert e.confidence == 0.9  # nosec B101
        assert isinstance(e.start, int)  # nosec B101
        assert isinstance(e.end, int)  # nosec B101
        assert e.end > e.start  # nosec B101


class TestExtractTopics:
    """extract_topics: matches against TECHNICAL_TOPICS."""

    def test_known_topic_found(self, extractor):
        result = extractor.extract_topics("We discussed system design and caching.")
        texts = {e.text for e in result}
        assert "system design" in texts or "system" in texts or "caching" in texts  # nosec B101

    def test_kubernetes_matches(self, extractor):
        result = extractor.extract_topics("I know kubernetes and docker.")
        texts = {e.text for e in result}
        assert "kubernetes" in texts  # nosec B101
        assert "docker" in texts  # nosec B101

    def test_label_is_topic(self, extractor):
        result = extractor.extract_topics("system design")
        for e in result:
            assert e.label == "TOPIC"  # nosec B101

    def test_unknown_topic_empty(self, extractor):
        result = extractor.extract_topics("blah blah blarg nonexistent")
        assert result == []  # nosec B101


class TestExtractSkills:
    """extract_skills: matches against SKILLS."""

    def test_python_matches(self, extractor):
        result = extractor.extract_skills("I write Python every day")
        texts = [e.text for e in result]
        assert "python" in texts  # nosec B101

    def test_react_matches(self, extractor):
        result = extractor.extract_skills("Frontend with React and TypeScript")
        texts = {e.text for e in result}
        assert "react" in texts  # nosec B101
        assert "typescript" in texts  # nosec B101

    def test_label_is_skill(self, extractor):
        result = extractor.extract_skills("python")
        for e in result:
            assert e.label == "SKILL"  # nosec B101

    def test_framework_names_match(self, extractor):
        # Both "react" (under SKILLS) and "react" (under TOPICS) match,
        # so the same word can appear in both extract_skills and extract_topics.
        result_topics = extractor.extract_topics("react")
        result_skills = extractor.extract_skills("react")
        assert len(result_topics) >= 1  # nosec B101
        assert len(result_skills) >= 1  # nosec B101


class TestExtractRoles:
    """extract_roles: matches against ROLES."""

    def test_software_engineer(self, extractor):
        result = extractor.extract_roles("I am a software engineer.")
        texts = [e.text for e in result]
        assert "software engineer" in texts  # nosec B101

    def test_data_scientist(self, extractor):
        result = extractor.extract_roles("Hired as data scientist in 2020")
        texts = [e.text for e in result]
        assert "data scientist" in texts  # nosec B101

    def test_label_is_role(self, extractor):
        result = extractor.extract_roles("product manager")
        for e in result:
            assert e.label == "ROLE"  # nosec B101


class TestCategorizeQuestion:
    """categorize_question: rule-based fallback (keyword scoring)."""

    def test_technical_keyword(self, extractor):
        category, confidence = extractor.categorize_question("What is the time complexity of this algorithm?")
        assert category == "technical"  # nosec B101
        assert 0 < confidence <= 1.0  # nosec B101

    def test_behavioral_keyword(self, extractor):
        category, _ = extractor.categorize_question("Tell me about a time you led a team through a challenge.")
        assert category == "behavioral"  # nosec B101

    def test_system_design_keyword(self, extractor):
        category, _ = extractor.categorize_question("Design a distributed system for our messaging service.")
        assert category == "system_design"  # nosec B101

    def test_knowledge_keyword(self, extractor):
        category, _ = extractor.categorize_question("What is the difference between SQL and NoSQL?")
        assert category == "knowledge"  # nosec B101

    def test_no_keywords_returns_general(self, extractor):
        category, confidence = extractor.categorize_question("Hello there, how are you?")
        assert category == "general"  # nosec B101
        assert confidence == 0.5  # nosec B101

    def test_confidence_increases_with_more_keywords(self, extractor):
        # Multiple category keywords → higher confidence
        _, c1 = extractor.categorize_question("What is the time complexity?")
        _, c2 = extractor.categorize_question("What is the time complexity and space complexity of the algorithm?")
        assert c2 > c1  # nosec B101


class TestEstimateDifficulty:
    """estimate_difficulty: returns (label, confidence) or (None, 0.0)."""

    def test_easy_keyword(self, extractor):
        label, conf = extractor.estimate_difficulty("This is a simple basic question.")
        assert label == "easy"  # nosec B101
        assert conf > 0  # nosec B101

    def test_hard_keyword(self, extractor):
        label, conf = extractor.estimate_difficulty("This is a difficult complex problem.")
        assert label == "hard"  # nosec B101

    def test_indicator_words_for_hard(self, extractor):
        # "optimize" / "distributed" / "scale" map to hard with 0.6 confidence
        label, conf = extractor.estimate_difficulty("How would you optimize this?")
        assert label == "hard"  # nosec B101
        assert conf == 0.6  # nosec B101

    def test_no_keywords_returns_none(self, extractor):
        # Note: the implementation uses SUBSTRING matching, not word
        # boundaries, so e.g. "difficulty" triggers "difficult".
        # Use a text with zero substrings of any keyword or indicator.
        label, conf = extractor.estimate_difficulty("xyzzy plover")
        assert label is None  # nosec B101
        assert conf == 0.0  # nosec B101


class TestExtractAll:
    """extract_all: dict-of-lists result with category + difficulty."""

    def test_returns_expected_keys(self, extractor):
        result = extractor.extract_all("I worked at Google as a software engineer using Python.")
        assert "companies" in result  # nosec B101
        assert "topics" in result  # nosec B101
        assert "skills" in result  # nosec B101
        assert "roles" in result  # nosec B101
        assert "category" in result  # nosec B101
        assert "difficulty" in result  # nosec B101
        assert "entities_found" in result  # nosec B101

    def test_companies_skill_role_listed(self, extractor):
        result = extractor.extract_all("I am a software engineer at Google using Python.")
        company_texts = [c["text"] for c in result["companies"]]
        skill_texts = [s["text"] for s in result["skills"]]
        role_texts = [r["text"] for r in result["roles"]]
        assert "google" in company_texts  # nosec B101
        assert "python" in skill_texts  # nosec B101
        assert "software engineer" in role_texts  # nosec B101

    def test_entities_found_count(self, extractor):
        result = extractor.extract_all("google python")
        # Should find at least 1 company and 1 skill
        assert result["entities_found"] >= 2  # nosec B101

    def test_category_block_format(self, extractor):
        result = extractor.extract_all("What is recursion?")
        assert "label" in result["category"]  # nosec B101
        assert "confidence" in result["category"]  # nosec B101
        assert result["category"]["label"] in (
            "technical", "behavioral", "system_design", "knowledge", "general"
        )  # nosec B101

    def test_difficulty_none_when_unknown(self, extractor):
        result = extractor.extract_all("blah")
        # When no difficulty signal, the field is None
        assert result["difficulty"] is None  # nosec B101


class TestProcessTranscript:
    """process_transcript: split on ? and question-introducing lines."""

    def test_simple_qa_pair(self, extractor):
        transcript = "What is Python?\nPython is a programming language."
        pairs = extractor.process_transcript(transcript)
        assert len(pairs) == 1  # nosec B101
        assert "What is Python?" in pairs[0]["question"]  # nosec B101
        assert "Python is a programming language" in pairs[0]["answer"]  # nosec B101

    def test_q_keyword_introduces_question(self, extractor):
        transcript = "Tell me about your background.\nI have 5 years of experience."
        pairs = extractor.process_transcript(transcript)
        assert len(pairs) == 1  # nosec B101
        assert pairs[0]["question"].startswith("Tell me about")  # nosec B101

    def test_qa_pair_includes_entities(self, extractor):
        transcript = "What is Python used for at Google?\nPython is used at Google for ML."
        pairs = extractor.process_transcript(transcript)
        assert len(pairs) == 1  # nosec B101
        assert "entities" in pairs[0]  # nosec B101
        assert "companies" in pairs[0]["entities"]  # nosec B101
        company_texts = [c["text"] for c in pairs[0]["entities"]["companies"]]
        assert "google" in company_texts  # nosec B101

    def test_empty_transcript(self, extractor):
        pairs = extractor.process_transcript("")
        assert pairs == []  # nosec B101

    def test_only_questions_no_answers(self, extractor):
        # A line that ends with ? but has no following answer is still
        # captured as a question (no Q&A pair formed because no answer).
        transcript = "What is your name?"
        pairs = extractor.process_transcript(transcript)
        # No answer following → no Q&A pair is saved
        assert pairs == []  # nosec B101

    def test_multiple_qa_pairs(self, extractor):
        transcript = (
            "What is Python?\n"
            "A programming language.\n"
            "Why use Python?\n"
            "Because it's readable."
        )
        pairs = extractor.process_transcript(transcript)
        assert len(pairs) == 2  # nosec B101


class TestConvenienceFunctions:
    """Module-level helpers: extract_entities, process_transcript."""

    def test_extract_entities_convenience(self):
        result = extract_entities("I work at Google with Python")
        assert "companies" in result  # nosec B101
        assert "skills" in result  # nosec B101

    def test_process_transcript_convenience(self):
        pairs = process_transcript("What is X?\nX is a thing.")
        assert len(pairs) == 1  # nosec B101


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
