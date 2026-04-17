"""
hybrid_entity_extraction.py - Hybrid ML + Rule-based Entity Extraction

Phase 2 Task #29: Improve entity extraction accuracy from ~70% to >90%

Combines:
1. spaCy NER (en_core_web_sm) - General entity recognition
2. Rule-based patterns - Domain-specific entities
3. Confidence-weighted merging

Usage:
    from hybrid_entity_extraction import hybrid_extractor
    entities = hybrid_extractor.extract_all(text)
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import re

logger = logging.getLogger("hybrid_entity_extraction")

# Try to import spaCy
SPACY_AVAILABLE = False
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
    logger.info("[HybridEntity] spaCy NER loaded successfully")
except ImportError as e:
    logger.warning(f"[HybridEntity] spaCy not available: {e}")
    nlp = None

# Import existing rule-based extractor
from modules.ai.entity_extraction import (
    entity_extractor,
    COMPANY_NAMES,
    TECHNICAL_TOPICS,
    SKILLS,
    ROLES,
    QUESTION_CATEGORIES,
    DIFFICULTY_KEYWORDS
)


@dataclass
class ExtractedEntity:
    """Represents an extracted entity with confidence"""
    text: str
    label: str
    confidence: float = 1.0
    source: str = "unknown"  # "spacy", "rule", "hybrid"
    start: int = 0
    end: int = 0


class HybridEntityExtractor:
    """
    Hybrid entity extractor combining ML and rule-based approaches.

    Merging strategy:
    - spaCy provides general entities (ORG, PRODUCT, etc.)
    - Rules provide domain-specific entities (React, Kubernetes, etc.)
    - Overlapping entities are merged with weighted confidence
    """

    def __init__(self, rule_weight: float = 0.6, spacy_weight: float = 0.4):
        """
        Args:
            rule_weight: Weight for rule-based predictions (0-1)
            spacy_weight: Weight for spaCy predictions (0-1)
        """
        self.rule_extractor = entity_extractor
        self.spacy_nlp = nlp
        self.rule_weight = rule_weight
        self.spacy_weight = spacy_weight
        self.spacy_available = SPACY_AVAILABLE

        # spaCy entity type mapping
        self.spacy_to_custom = {
            "ORG": "COMPANY",           # Organizations
            "PRODUCT": "SKILL",          # Products (can be skills)
            "WORK_OF_ART": "TOPIC",      # Technical concepts
            "PERSON": "ROLE",            # Could be role titles
            "GPE": "COMPANY",            # Google, Amazon (sometimes tagged as GPE)
            "NORP": "COMPANY",           # Nationalities/religious/political groups
        }

    def extract_spacy_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract entities using spaCy NER"""
        if not self.spacy_available or not self.spacy_nlp:
            return []

        entities = []
        doc = self.spacy_nlp(text)

        for ent in doc.ents:
            # Map spaCy labels to our labels
            custom_label = self.spacy_to_custom.get(ent.label_, None)

            if custom_label:
                entities.append(ExtractedEntity(
                    text=ent.text,
                    label=custom_label,
                    confidence=0.7,  # Base confidence for spaCy
                    source="spacy",
                    start=ent.start_char,
                    end=ent.end_char
                ))

        return entities

    def extract_rule_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract entities using rule-based patterns"""
        entities = []
        text_lower = text.lower()

        # Companies
        for company in COMPANY_NAMES:
            for match in re.finditer(r'\b' + re.escape(company) + r'\b', text_lower):
                entities.append(ExtractedEntity(
                    text=text[match.start():match.end()],
                    label="COMPANY",
                    confidence=0.95,  # High confidence for exact matches
                    source="rule",
                    start=match.start(),
                    end=match.end()
                ))

        # Skills
        for skill in SKILLS:
            for match in re.finditer(r'\b' + re.escape(skill) + r'\b', text_lower):
                entities.append(ExtractedEntity(
                    text=text[match.start():match.end()],
                    label="SKILL",
                    confidence=0.9,
                    source="rule",
                    start=match.start(),
                    end=match.end()
                ))

        # Technical topics
        for topic in TECHNICAL_TOPICS:
            for match in re.finditer(r'\b' + re.escape(topic) + r'\b', text_lower):
                entities.append(ExtractedEntity(
                    text=text[match.start():match.end()],
                    label="TOPIC",
                    confidence=0.85,
                    source="rule",
                    start=match.start(),
                    end=match.end()
                ))

        # Roles
        for role in ROLES:
            for match in re.finditer(r'\b' + re.escape(role) + r'\b', text_lower):
                entities.append(ExtractedEntity(
                    text=text[match.start():match.end()],
                    label="ROLE",
                    confidence=0.85,
                    source="rule",
                    start=match.start(),
                    end=match.end()
                ))

        return entities

    def merge_entities(
        self,
        spacy_entities: List[ExtractedEntity],
        rule_entities: List[ExtractedEntity],
        text: str
    ) -> List[ExtractedEntity]:
        """
        Merge entities from both sources, handling overlaps.

        Strategy:
        - If entities overlap:
          - Same label: merge with boosted confidence
          - Different labels: keep rule-based (domain expertise)
        - Non-overlapping: keep both
        """
        merged = []
        all_entities = rule_entities + spacy_entities

        # Sort by start position
        all_entities.sort(key=lambda x: x.start)

        # Group overlapping entities
        groups = []
        current_group = []

        for entity in all_entities:
            if not current_group:
                current_group = [entity]
            else:
                # Check if overlaps with last in current group
                last = current_group[-1]
                if entity.start < last.end:
                    current_group.append(entity)
                else:
                    groups.append(current_group)
                    current_group = [entity]

        if current_group:
            groups.append(current_group)

        # Merge each group
        for group in groups:
            if len(group) == 1:
                merged.append(group[0])
            else:
                # Multiple overlapping entities
                # Prioritize rule-based for same label, merge for different
                merged_entity = self._resolve_overlap(group)
                merged.append(merged_entity)

        return merged

    def _resolve_overlap(self, entities: List[ExtractedEntity]) -> ExtractedEntity:
        """Resolve overlapping entities by merging or selecting best"""
        # If any rule entity, prioritize it (domain expertise)
        rule_entities = [e for e in entities if e.source == "rule"]

        if rule_entities:
            # Return the longest rule entity
            best = max(rule_entities, key=lambda x: len(x.text))
            # Boost confidence if spacy also found it
            spacy_overlap = any(e.source == "spacy" for e in entities)
            if spacy_overlap:
                best.confidence = min(1.0, best.confidence + 0.1)
            return best

        # All spaCy entities - merge them
        longest = max(entities, key=lambda x: len(x.text))
        longest.confidence = max(e.confidence for e in entities)
        return longest

    def extract_all(self, text: str) -> Dict:
        """
        Extract all entities using hybrid approach.

        Returns dict with companies, skills, topics, roles, categories
        """
        if not text:
            return self._empty_result()

        # Get entities from both sources
        spacy_entities = self.extract_spacy_entities(text) if self.spacy_available else []
        rule_entities = self.extract_rule_entities(text)

        # Merge
        merged = self.merge_entities(spacy_entities, rule_entities, text)

        # Organize by category
        companies = [e for e in merged if e.label == "COMPANY"]
        skills = [e for e in merged if e.label == "SKILL"]
        topics = [e for e in merged if e.label == "TOPIC"]
        roles = [e for e in merged if e.label == "ROLE"]

        # Remove duplicates (keep highest confidence)
        companies = self._deduplicate(companies)
        skills = self._deduplicate(skills)
        topics = self._deduplicate(topics)
        roles = self._deduplicate(roles)

        # Get category and difficulty
        category, cat_confidence = self.categorize_question(text)
        difficulty, diff_confidence = self.estimate_difficulty(text)

        # Calculate overall confidence
        entity_confidence = sum(e.confidence for e in merged) / max(len(merged), 1)

        return {
            "companies": [{"text": e.text, "confidence": e.confidence, "source": e.source} for e in companies],
            "skills": [{"text": e.text, "confidence": e.confidence, "source": e.source} for e in skills],
            "topics": [{"text": e.text, "confidence": e.confidence, "source": e.source} for e in topics],
            "roles": [{"text": e.text, "confidence": e.confidence, "source": e.source} for e in roles],
            "category": {"label": category, "confidence": cat_confidence},
            "difficulty": {"label": difficulty, "confidence": diff_confidence} if difficulty else None,
            "entities_found": len(merged),
            "avg_confidence": round(entity_confidence, 2),
            "hybrid_score": self._calculate_hybrid_score(merged)
        }

    def _deduplicate(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Remove duplicate entities, keeping highest confidence"""
        seen = {}
        for entity in entities:
            key = entity.text.lower()
            if key not in seen or entity.confidence > seen[key].confidence:
                seen[key] = entity
        return list(seen.values())

    def _calculate_hybrid_score(self, entities: List[ExtractedEntity]) -> float:
        """Calculate overall extraction quality score"""
        if not entities:
            return 0.0

        # Weight by source (rule-based is more reliable for domain)
        rule_entities = [e for e in entities if e.source == "rule"]
        spacy_entities = [e for e in entities if e.source == "spacy"]
        hybrid_entities = [e for e in entities if e.source == "hybrid"]

        score = (
            len(rule_entities) * 1.0 +
            len(spacy_entities) * 0.7 +
            len(hybrid_entities) * 1.2
        ) / max(len(entities), 1)

        return round(min(score, 1.0), 2)

    def categorize_question(self, text: str) -> Tuple[str, float]:
        """Categorize a question using smart classifier, spaCy, or rule-based approach"""
        # Try SmartClassifier first (zero-shot)
        try:
            from modules.ai.smart_classifier import get_classifier, CLASSIFIER_AVAILABLE
            if CLASSIFIER_AVAILABLE:
                classifier = get_classifier()
                if classifier:
                    category, confidence = classifier.classify_question(text)
                    if confidence > 0.6:
                        return (category, confidence)
        except Exception:
            pass  # nosec B110

        # Fallback to rule-based
        return self.rule_extractor.categorize_question(text)

    def estimate_difficulty(self, text: str) -> Tuple[Optional[str], float]:
        """Estimate question difficulty using smart classifier or rule-based approach"""
        # Try SmartClassifier first (zero-shot)
        try:
            from modules.ai.smart_classifier import get_classifier, CLASSIFIER_AVAILABLE
            if CLASSIFIER_AVAILABLE:
                classifier = get_classifier()
                if classifier:
                    difficulty, confidence = classifier.classify_difficulty(text)
                    if confidence > 0.6:
                        return (difficulty, confidence)
        except Exception:
            pass  # nosec B110

        # Fallback to rule-based
        return self.rule_extractor.estimate_difficulty(text)

    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            "companies": [],
            "skills": [],
            "topics": [],
            "roles": [],
            "category": {"label": "general", "confidence": 0.5},
            "difficulty": None,
            "entities_found": 0,
            "avg_confidence": 0.0,
            "hybrid_score": 0.0
        }

    def compare_with_rule_based(self, text: str) -> Dict:
        """
        Compare hybrid extraction vs rule-based for debugging.

        Returns comparison metrics.
        """
        # Rule-based only
        rule_result = self.rule_extractor.extract_all(text)
        rule_count = rule_result.get("entities_found", 0)

        # Hybrid
        hybrid_result = self.extract_all(text)
        hybrid_count = hybrid_result.get("entities_found", 0)

        return {
            "text_sample": text[:100] if len(text) > 100 else text,
            "rule_based": {
                "entities": rule_count,
                "companies": len(rule_result.get("companies", [])),
                "skills": len(rule_result.get("skills", [])),
            },
            "hybrid": {
                "entities": hybrid_count,
                "companies": len(hybrid_result.get("companies", [])),
                "skills": len(hybrid_result.get("skills", [])),
                "avg_confidence": hybrid_result.get("avg_confidence", 0),
                "hybrid_score": hybrid_result.get("hybrid_score", 0)
            },
            "improvement": {
                "entity_count": hybrid_count - rule_count,
                "percent_change": round(((hybrid_count - rule_count) / max(rule_count, 1)) * 100, 1)
            }
        }


# Global instance
hybrid_extractor = HybridEntityExtractor()


def extract_entities(text: str) -> Dict:
    """Extract entities - convenience function"""
    return hybrid_extractor.extract_all(text)


def compare_extraction(text: str) -> Dict:
    """Compare extraction methods - for debugging"""
    return hybrid_extractor.compare_with_rule_based(text)


# Accuracy benchmark
def benchmark_accuracy(test_cases: List[Dict]) -> Dict:
    """
    Benchmark extraction accuracy against labeled test cases.

    Args:
        test_cases: List of {"text": str, "expected": {"companies": [], "skills": [], ...}}

    Returns:
        Accuracy metrics
    """
    if not test_cases:
        return {"error": "No test cases provided"}

    rule_correct = 0
    hybrid_correct = 0
    total_expected = 0

    results = []

    for case in test_cases:
        text = case["text"]
        expected = case["expected"]

        # Rule-based
        rule_result = entity_extractor.extract_all(text)

        # Hybrid
        hybrid_result = hybrid_extractor.extract_all(text)

        # Calculate accuracy for this case
        rule_score = calculate_case_accuracy(rule_result, expected)
        hybrid_score = calculate_case_accuracy(hybrid_result, expected)

        rule_correct += rule_score
        hybrid_correct += hybrid_score
        total_expected += len(expected)

        results.append({
            "text": text[:50],
            "rule_accuracy": rule_score,
            "hybrid_accuracy": hybrid_score,
            "improvement": hybrid_score - rule_score
        })

    return {
        "total_cases": len(test_cases),
        "rule_based_accuracy": round(rule_correct / max(total_expected, 1), 3),
        "hybrid_accuracy": round(hybrid_correct / max(total_expected, 1), 3),
        "improvement": round(hybrid_correct - rule_correct, 3),
        "per_case_results": results
    }


def calculate_case_accuracy(result: Dict, expected: Dict) -> int:
    """Calculate accuracy for a single test case"""
    score = 0

    # Check companies
    result_companies = {c["text"].lower() for c in result.get("companies", [])}
    expected_companies = {c.lower() for c in expected.get("companies", [])}
    score += len(result_companies & expected_companies)

    # Check skills
    result_skills = {s["text"].lower() for s in result.get("skills", [])}
    expected_skills = {s.lower() for s in expected.get("skills", [])}
    score += len(result_skills & expected_skills)

    # Check topics
    result_topics = {t["text"].lower() for t in result.get("topics", [])}
    expected_topics = {t.lower() for t in expected.get("topics", [])}
    score += len(result_topics & expected_topics)

    return score
