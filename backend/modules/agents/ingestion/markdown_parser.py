"""
Markdown Q&A Parser — Extracts structured Q&A pairs from DevOps-Interview-Questions1
repository Markdown files.

Expected format:
    ### **1. What is DevOps?**

    **Answer:** DevOps is a set of practices that combines...

Each category README has 60 questions (20 beginner + 20 intermediate + 20 advanced).
"""

import re
import os
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("agents.ingestion.markdown_parser")

# Category mapping: directory name -> display category
CATEGORY_MAP = {
    "core-concepts": "Core Concepts",
    "cloud": "Cloud",
    "containers": "Containers",
    "ci-cd": "CI/CD",
    "infrastructure-as-code": "Infrastructure as Code",
    "monitoring-logging": "Monitoring & Logging",
    "networking-security": "Networking & Security",
    "automation-scripting": "Automation & Scripting",
    "linux-system-admin": "Linux & System Admin",
    "version-control": "Version Control",
    "best-practices": "Best Practices",
    "mock-interviews": "Mock Interviews",
}

# Questions per difficulty tier
QUESTIONS_PER_TIER = 20


@dataclass
class ParsedQA:
    """A parsed Q&A pair from a Markdown file."""
    question: str
    answer: str
    number: int
    category: str            # e.g. "containers", "ci-cd"
    difficulty: str           # "beginner", "intermediate", "advanced"
    source_file: str
    code_blocks: List[str] = field(default_factory=list)
    has_code: bool = False

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer[:200] + "..." if len(self.answer) > 200 else self.answer,
            "number": self.number,
            "category": self.category,
            "difficulty": self.difficulty,
            "source_file": self.source_file,
            "has_code": self.has_code,
        }

    def full_text(self) -> str:
        """Format as a single text block for RAG ingestion."""
        parts = [f"Q: {self.question}", f"A: {self.answer}"]
        if self.code_blocks:
            for i, block in enumerate(self.code_blocks, 1):
                parts.append(f"\nCode Example {i}:\n{block}")
        return "\n".join(parts)


class MarkdownQAParser:
    """Parse Q&A pairs from DevOps-Interview-Questions1 Markdown files."""

    # Regex patterns for the specific format
    QUESTION_PATTERN = re.compile(
        r'###\s*\*\*(\d+)\.\s*(.+?)\*\*\s*\n',
        re.MULTILINE
    )
    ANSWER_START_PATTERN = re.compile(
        r'\*\*Answer:\*\*\s*',
        re.MULTILINE
    )
    CODE_FENCE_PATTERN = re.compile(
        r'```[\w]*\n(.*?)```',
        re.DOTALL
    )

    def parse_readme(self, file_path: str, category: str = "") -> List[ParsedQA]:
        """Parse a single README.md file and extract all Q&A pairs.

        Args:
            file_path: Path to the README.md file
            category: Category name (e.g. "containers", "ci-cd")

        Returns:
            List of ParsedQA objects
        """
        if not os.path.exists(file_path):
            logger.warning(f"[MarkdownParser] File not found: {file_path}")
            return []

        # Infer category from directory name if not provided
        if not category:
            dir_name = os.path.basename(os.path.dirname(file_path))
            category = CATEGORY_MAP.get(dir_name, dir_name)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"[MarkdownParser] Failed to read {file_path}: {e}")
            return []

        qa_pairs = self._parse_content(content, category, os.path.basename(file_path))
        logger.info(f"[MarkdownParser] Parsed {len(qa_pairs)} Q&A pairs from {os.path.basename(file_path)}")
        return qa_pairs

    def _parse_content(self, content: str, category: str, source_file: str) -> List[ParsedQA]:
        """Parse Markdown content and extract Q&A pairs."""
        qa_pairs = []

        # Find all question headings
        question_matches = list(self.QUESTION_PATTERN.finditer(content))

        if not question_matches:
            # Try alternative format: ### Question text (without number)
            alt_pattern = re.compile(r'###\s*(.+?)\s*\n', re.MULTILINE)
            alt_matches = list(alt_pattern.finditer(content))
            if alt_matches:
                qa_pairs = self._parse_alternative_format(content, alt_matches, category, source_file)
            return qa_pairs

        for i, match in enumerate(question_matches):
            number = int(match.group(1))
            question_text = match.group(2).strip()

            # Extract answer: everything from "**Answer:**" to the next question heading (or EOF)
            start_pos = match.end()
            end_pos = question_matches[i + 1].start() if i + 1 < len(question_matches) else len(content)

            section_text = content[start_pos:end_pos]

            # Find the answer start
            answer_match = self.ANSWER_START_PATTERN.search(section_text)
            if answer_match:
                answer_text = section_text[answer_match.end():].strip()
            else:
                # No explicit Answer: marker — use everything after the heading
                answer_text = section_text.strip()

            # Clean up the answer text
            answer_text = self._clean_answer(answer_text)

            # Extract code blocks
            clean_answer, code_blocks = self._extract_code_blocks(answer_text)

            # Detect difficulty from question number
            difficulty = self._detect_difficulty(number)

            qa = ParsedQA(
                question=question_text,
                answer=clean_answer,
                number=number,
                category=category,
                difficulty=difficulty,
                source_file=source_file,
                code_blocks=code_blocks,
                has_code=len(code_blocks) > 0,
            )
            qa_pairs.append(qa)

        return qa_pairs

    def _parse_alternative_format(
        self,
        content: str,
        matches: list,
        category: str,
        source_file: str,
    ) -> List[ParsedQA]:
        """Parse alternative format where questions don't have numbered prefixes."""
        qa_pairs = []
        for i, match in enumerate(matches):
            question_text = match.group(1).strip()
            # Skip if it looks like a section header, not a question
            if question_text.isupper() or question_text in ("Answer", "Explanation"):
                continue

            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section_text = content[start_pos:end_pos].strip()

            answer_match = self.ANSWER_START_PATTERN.search(section_text)
            if answer_match:
                answer_text = section_text[answer_match.end():].strip()
            else:
                answer_text = section_text

            answer_text = self._clean_answer(answer_text)
            clean_answer, code_blocks = self._extract_code_blocks(answer_text)

            qa = ParsedQA(
                question=question_text,
                answer=clean_answer,
                number=i + 1,
                category=category,
                difficulty=self._detect_difficulty(i + 1),
                source_file=source_file,
                code_blocks=code_blocks,
                has_code=len(code_blocks) > 0,
            )
            qa_pairs.append(qa)

        return qa_pairs

    def parse_repo(self, repo_path: str) -> List[ParsedQA]:
        """Parse all README.md files in a DevOps-Interview-Questions1 repo.

        Scans subdirectories for README.md files and parses each one.

        Args:
            repo_path: Path to the cloned repository root

        Returns:
            List of all ParsedQA objects across all categories
        """
        all_qa = []

        if not os.path.isdir(repo_path):
            logger.error(f"[MarkdownParser] Not a directory: {repo_path}")
            return []

        # Look for category subdirectories with README.md
        for entry in sorted(os.listdir(repo_path)):
            subdir = os.path.join(repo_path, entry)
            if not os.path.isdir(subdir):
                continue
            if entry.startswith("."):
                continue

            readme_path = os.path.join(subdir, "README.md")
            if os.path.exists(readme_path):
                category = CATEGORY_MAP.get(entry, entry)
                qa_pairs = self.parse_readme(readme_path, category)
                all_qa.extend(qa_pairs)

        # Also check for root-level README.md with Q&A content
        root_readme = os.path.join(repo_path, "README.md")
        if os.path.exists(root_readme):
            # Only parse if it contains Q&A patterns (skip intro READMEs)
            try:
                with open(root_readme, "r", encoding="utf-8") as f:
                    content = f.read()
                if "**Answer:**" in content or "**Answer :**" in content:
                    qa_pairs = self.parse_readme(root_readme, "General")
                    all_qa.extend(qa_pairs)
            except Exception:
                pass  # nosec B110

        logger.info(f"[MarkdownParser] Parsed {len(all_qa)} total Q&A pairs from {repo_path}")
        return all_qa

    def _detect_difficulty(self, number: int) -> str:
        """Map question number to difficulty tier.

        1-20 = beginner, 21-40 = intermediate, 41-60 = advanced.
        Handles arbitrary numbering by computing the tier from modular position.
        """
        tier = ((number - 1) // QUESTIONS_PER_TIER) + 1
        if tier <= 1:
            return "beginner"
        elif tier <= 2:
            return "intermediate"
        else:
            return "advanced"

    @staticmethod
    def _clean_answer(text: str) -> str:
        """Clean up answer text by removing excessive whitespace and normalizing."""
        # Remove leading/trailing whitespace
        text = text.strip()

        # Normalize multiple blank lines to a single one
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove trailing whitespace from each line
        text = '\n'.join(line.rstrip() for line in text.split('\n'))

        return text

    @staticmethod
    def _extract_code_blocks(text: str) -> Tuple[str, List[str]]:
        """Extract code blocks from answer text.

        Returns:
            Tuple of (cleaned_text_without_code, list_of_code_blocks)
        """
        code_blocks = []
        matches = list(MarkdownQAParser.CODE_FENCE_PATTERN.finditer(text))

        for match in matches:
            code_blocks.append(match.group(1).strip())

        # Replace code fences with a placeholder
        clean_text = MarkdownQAParser.CODE_FENCE_PATTERN.sub('[code example]', text)

        return clean_text, code_blocks

    @staticmethod
    def detect_repo_type(repo_path: str) -> str:
        """Detect whether a repo contains Q&A markdown or PDF books.

        Returns: "qa_markdown", "pdf_books", or "unknown"
        """
        if not os.path.isdir(repo_path):
            return "unknown"

        # Check for category subdirectories with README.md
        has_readme_dirs = False
        has_pdfs = False

        for entry in os.listdir(repo_path):
            full_path = os.path.join(repo_path, entry)
            if entry.startswith("."):
                continue

            if os.path.isdir(full_path):
                if os.path.exists(os.path.join(full_path, "README.md")):
                    has_readme_dirs = True
            elif entry.lower().endswith(".pdf"):
                has_pdfs = True

        if has_readme_dirs:
            return "qa_markdown"
        elif has_pdfs:
            return "pdf_books"
        else:
            return "unknown"