"""
Test suite for backend/modules/interview/company_questions.py
Covers the company-specific question database (33 questions across
6 FAANG-tier companies) and the lookup helpers.

This is a pure-data module: 33 InterviewQuestion constants and 2
functions. Tests verify (1) the database shape (no missing fields,
correct counts), (2) the lookup functions (case insensitivity,
multi-company matching), and (3) the tips dictionary.

Run with: python -m pytest backend/tests/test_company_questions.py -v
"""

import os
import sys

import pytest

# Add backend/ and modules/interview/ to sys.path.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "modules", "interview"))

from company_questions import (  # noqa: E402
    GOOGLE_QUESTIONS,
    AMAZON_QUESTIONS,
    META_QUESTIONS,
    NETFLIX_QUESTIONS,
    MICROSOFT_QUESTIONS,
    APPLE_QUESTIONS,
    ALL_COMPANY_QUESTIONS,
    get_company_questions,
    get_company_specific_tips,
)


class TestQuestionDatabaseShape:
    """Structural validation: every question has the required fields."""

    @pytest.mark.parametrize("questions,expected_count", [
        (GOOGLE_QUESTIONS, 7),
        (AMAZON_QUESTIONS, 10),
        (META_QUESTIONS, 7),
        (NETFLIX_QUESTIONS, 3),
        (MICROSOFT_QUESTIONS, 4),
        (APPLE_QUESTIONS, 2),
    ])
    def test_per_company_count(self, questions, expected_count):
        # The audit's spot-check confirmed 33 total: 7+10+7+3+4+2 = 33
        # (we may have grown since the audit, just check >= the expected)
        assert len(questions) >= expected_count  # nosec B101

    def test_total_company_questions_aggregate(self):
        # 7+10+7+3+4+2 = 33 (matches the audit's 2026-06-05 snapshot)
        expected = (
            len(GOOGLE_QUESTIONS) + len(AMAZON_QUESTIONS) +
            len(META_QUESTIONS) + len(NETFLIX_QUESTIONS) +
            len(MICROSOFT_QUESTIONS) + len(APPLE_QUESTIONS)
        )
        assert len(ALL_COMPANY_QUESTIONS) == expected  # nosec B101
        assert expected >= 33  # audit baseline  # nosec B101

    @pytest.mark.parametrize("question", ALL_COMPANY_QUESTIONS)
    def test_question_has_non_empty_id(self, question):
        assert question.id and isinstance(question.id, str)  # nosec B101

    @pytest.mark.parametrize("question", ALL_COMPANY_QUESTIONS)
    def test_question_has_non_empty_text(self, question):
        assert question.question and len(question.question) > 5  # nosec B101

    @pytest.mark.parametrize("question", ALL_COMPANY_QUESTIONS)
    def test_question_id_starts_with_company_prefix(self, question):
        # IDs follow a `<company>-<type>-<NNN>` convention
        # (e.g. "goog-bh-001", "amz-cd-002", "meta-sd-001")
        assert "-" in question.id  # nosec B101
        prefix = question.id.split("-")[0]
        valid_prefixes = {"goog", "amz", "meta", "nflx", "msft", "aapl"}
        assert prefix in valid_prefixes, f"Unexpected prefix: {prefix}"  # nosec B101

    @pytest.mark.parametrize("question", ALL_COMPANY_QUESTIONS)
    def test_question_has_companies_list(self, question):
        assert isinstance(question.companies, list)  # nosec B101
        assert len(question.companies) >= 1  # nosec B101

    @pytest.mark.parametrize("question", ALL_COMPANY_QUESTIONS)
    def test_question_has_roles_list(self, question):
        assert isinstance(question.roles, list)  # nosec B101
        assert len(question.roles) >= 1  # nosec B101

    @pytest.mark.parametrize("question", ALL_COMPANY_QUESTIONS)
    def test_question_has_expected_answer(self, question):
        # ExpectedAnswer dataclass: key_points, follow_up_questions,
        # red_flags, time_estimate_minutes, evaluation_criteria
        assert question.expected_answer is not None  # nosec B101
        assert len(question.expected_answer.key_points) >= 1  # nosec B101
        assert question.expected_answer.time_estimate_minutes > 0  # nosec B101

    @pytest.mark.parametrize("question", ALL_COMPANY_QUESTIONS)
    def test_question_has_company_tier(self, question):
        assert len(question.company_tiers) >= 1  # nosec B101

    def test_all_ids_are_unique(self):
        ids = [q.id for q in ALL_COMPANY_QUESTIONS]
        duplicates = {x for x in ids if ids.count(x) > 1}
        assert not duplicates, f"Duplicate IDs: {duplicates}"  # nosec B101


class TestGetCompanyQuestions:
    """get_company_questions: case-insensitive lookup, multi-company match."""

    def test_google_questions_returned(self):
        result = get_company_questions("google")
        assert len(result) == len(GOOGLE_QUESTIONS)  # nosec B101

    def test_amazon_questions_returned(self):
        result = get_company_questions("amazon")
        assert len(result) == len(AMAZON_QUESTIONS)  # nosec B101

    def test_amazon_aws_alias(self):
        # Amazon questions also have "aws" in their companies list
        result = get_company_questions("aws")
        assert len(result) == len(AMAZON_QUESTIONS)  # nosec B101

    def test_meta_facebook_alias(self):
        result = get_company_questions("facebook")
        # Facebook questions also match "facebook" in companies list
        assert len(result) >= 1  # nosec B101

    def test_case_insensitive(self):
        upper = get_company_questions("GOOGLE")
        lower = get_company_questions("google")
        mixed = get_company_questions("Google")
        assert len(upper) == len(lower) == len(mixed)  # nosec B101

    def test_unknown_company_returns_empty(self):
        result = get_company_questions("nonexistentcorp")
        assert result == []  # nosec B101

    def test_empty_string_returns_empty(self):
        result = get_company_questions("")
        assert result == []  # nosec B101

    def test_returned_questions_match_company(self):
        # Every returned question's `companies` list should contain
        # the queried name (case insensitive)
        for q in get_company_questions("google"):
            assert "google" in [c.lower() for c in q.companies]  # nosec B101


class TestGetCompanySpecificTips:
    """get_company_specific_tips: dict of interview guidance."""

    def test_google_tips(self):
        tips = get_company_specific_tips("google")
        assert "focus" in tips  # nosec B101
        assert "format" in tips  # nosec B101
        assert "key_values" in tips  # nosec B101
        assert "tips" in tips  # nosec B101
        assert "ambiguity" in tips["focus"].lower()  # nosec B101

    def test_amazon_tips_mention_leadership_principles(self):
        tips = get_company_specific_tips("amazon")
        assert "leadership" in tips["focus"].lower()  # nosec B101

    def test_meta_tips_mention_move_fast(self):
        tips = get_company_specific_tips("meta")
        # Meta's value is "Move Fast"
        assert "move fast" in tips["focus"].lower()  # nosec B101

    def test_netflix_tips_mention_freedom_responsibility(self):
        tips = get_company_specific_tips("netflix")
        assert "freedom" in tips["focus"].lower()  # nosec B101

    def test_microsoft_tips_mention_growth_mindset(self):
        tips = get_company_specific_tips("microsoft")
        assert "growth" in tips["focus"].lower()  # nosec B101

    def test_apple_tips_mention_craftsmanship(self):
        tips = get_company_specific_tips("apple")
        assert "craftsmanship" in tips["focus"].lower() or "secrecy" in tips["focus"].lower()  # nosec B101

    def test_case_insensitive(self):
        lower = get_company_specific_tips("google")
        upper = get_company_specific_tips("GOOGLE")
        assert lower == upper  # nosec B101

    def test_unknown_company_returns_fallback(self):
        tips = get_company_specific_tips("nonexistent")
        # Fallback is a single-key dict
        assert tips == {"focus": "General technical skills"}  # nosec B101

    def test_empty_string_returns_fallback(self):
        tips = get_company_specific_tips("")
        assert tips == {"focus": "General technical skills"}  # nosec B101


class TestQuestionsByCategory:
    """Categorical sanity: each company has a mix of behavioral/coding/sd."""

    def test_google_has_all_three_categories(self):
        cats = {q.category.value for q in GOOGLE_QUESTIONS}
        assert "behavioral" in cats  # nosec B101
        assert "coding" in cats  # nosec B101
        assert "system_design" in cats  # nosec B101

    def test_amazon_has_all_three_categories(self):
        cats = {q.category.value for q in AMAZON_QUESTIONS}
        assert "behavioral" in cats  # nosec B101
        assert "coding" in cats  # nosec B101
        assert "system_design" in cats  # nosec B101

    def test_questions_have_frequency_metadata(self):
        for q in ALL_COMPANY_QUESTIONS:
            assert q.frequency in ("common", "uncommon", "rare"), f"Bad frequency on {q.id}"  # nosec B101

    def test_questions_have_source_metadata(self):
        for q in ALL_COMPANY_QUESTIONS:
            # source is documented in the comments as "verified" but
            # other sources may be added over time — just check it's
            # a non-empty string
            assert q.source and isinstance(q.source, str)  # nosec B101


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
