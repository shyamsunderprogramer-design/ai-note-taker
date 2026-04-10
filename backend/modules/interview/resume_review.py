"""
resume_review.py - AI-Powered Resume Review

Analyzes resume against job descriptions and provides feedback.
"""

import json
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("resume_review")


@dataclass
class ResumeReview:
    """Resume analysis results"""
    overall_score: int
    strengths: List[str]
    improvements: List[str]
    missing_keywords: List[str]
    formatting_issues: List[str]
    section_scores: Dict[str, int]
    tailored_suggestions: List[str]


class ResumeReviewer:
    """AI-Powered Resume Reviewer"""

    def __init__(self):
        self.ai_router = None
        self._load_dependencies()

    def _load_dependencies(self):
        try:
            from ai_router import ai_router
            self.ai_router = ai_router
        except ImportError:
            pass

    def analyze_resume(
        self,
        resume_text: str,
        job_description: Optional[str] = None,
        role_type: str = "software_engineer"
    ) -> Dict:
        """
        Analyze resume and provide feedback.

        Args:
            resume_text: Full resume text content
            job_description: Optional job description to tailor against
            role_type: Type of role (software_engineer, data_scientist, etc.)

        Returns:
            Analysis results with scores and recommendations
        """
        # Extract sections
        sections = self._extract_sections(resume_text)

        # Analyze each section
        section_scores = self._score_sections(sections)

        # Check keywords against job description
        keywords = self._check_keywords(resume_text, role_type, job_description)

        # Check formatting
        formatting = self._check_formatting(resume_text)

        # Calculate overall score
        overall = sum(section_scores.values()) // len(section_scores) if section_scores else 50

        # Generate AI-enhanced feedback if available
        ai_feedback = None
        if self.ai_router and job_description:
            ai_feedback = self._get_ai_analysis(resume_text, job_description)

        # Compile results
        review = ResumeReview(
            overall_score=overall,
            strengths=self._identify_strengths(sections, keywords),
            improvements=self._identify_improvements(sections, keywords),
            missing_keywords=keywords.get('missing', []),
            formatting_issues=formatting,
            section_scores=section_scores,
            tailored_suggestions=ai_feedback.get('suggestions', []) if ai_feedback else []
        )

        return {
            "success": True,
            "analysis": {
                "overall_score": review.overall_score,
                "section_scores": review.section_scores,
                "strengths": review.strengths[:5],
                "improvements": review.improvements[:5],
                "missing_keywords": review.missing_keywords[:10],
                "formatting_issues": review.formatting_issues,
                "tailored_suggestions": review.tailored_suggestions
            },
            "ats_compatibility": self._check_ats_compatibility(resume_text),
            "word_count": len(resume_text.split()),
            "estimated_reading_time": len(resume_text.split()) // 200  # ~200 WPM
        }

    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract resume sections"""
        sections = {}
        lines = text.split('\n')
        current_section = None
        current_content = []

        section_headers = [
            'summary', 'objective', 'experience', 'work', 'employment',
            'education', 'skills', 'projects', 'certifications', 'awards',
            'publications', 'languages', 'interests'
        ]

        for line in lines:
            line_lower = line.lower().strip()

            # Check if line is a section header
            is_header = False
            for header in section_headers:
                if header in line_lower and len(line_lower) < 50:
                    if current_section:
                        sections[current_section] = '\n'.join(current_content)
                    current_section = header
                    current_content = []
                    is_header = True
                    break

            if not is_header and current_section:
                current_content.append(line)
            elif not current_section:
                # Content before first header (usually contact info)
                if 'summary' not in sections:
                    current_section = 'header'
                    current_content = [line]

        if current_section:
            sections[current_section] = '\n'.join(current_content)

        return sections

    def _score_sections(self, sections: Dict[str, str]) -> Dict[str, int]:
        """Score each resume section"""
        scores = {}

        # Experience section
        if 'experience' in sections or 'work' in sections:
            exp_text = sections.get('experience', sections.get('work', ''))
            scores['experience'] = self._score_experience(exp_text)
        else:
            scores['experience'] = 20  # Missing experience section

        # Skills section
        if 'skills' in sections:
            scores['skills'] = self._score_skills(sections['skills'])
        else:
            scores['skills'] = 30

        # Education section
        if 'education' in sections:
            scores['education'] = 85  # Present
        else:
            scores['education'] = 40

        # Summary/Objective
        if 'summary' in sections or 'objective' in sections:
            scores['summary'] = 75
        else:
            scores['summary'] = 50

        return scores

    def _score_experience(self, text: str) -> int:
        """Score experience section"""
        score = 50
        text_lower = text.lower()

        # Check for quantifiable achievements
        if any(x in text for x in ['%', 'percent', 'increased', 'decreased', 'improved']):
            score += 15

        # Check for action verbs
        action_verbs = ['led', 'managed', 'developed', 'implemented', 'created',
                       'designed', 'built', 'launched', 'optimized', 'reduced']
        verb_count = sum(1 for verb in action_verbs if verb in text_lower)
        score += min(verb_count * 5, 20)

        # Check for technical depth
        if any(x in text_lower for x in ['architecture', 'scalability', 'performance']):
            score += 10

        return min(score, 100)

    def _score_skills(self, text: str) -> int:
        """Score skills section"""
        score = 60

        # Count skills (comma or bullet separated)
        skills = [s.strip() for s in text.replace('•', ',').split(',')]
        num_skills = len([s for s in skills if len(s) > 2])

        if num_skills >= 10:
            score += 20
        elif num_skills >= 5:
            score += 10

        # Check for categorization
        if any(x in text.lower() for x in ['programming', 'languages', 'tools', 'frameworks']):
            score += 10

        return min(score, 100)

    def _extract_keywords_from_jd(self, job_description: str) -> List[str]:
        """Extract important keywords from job description"""
        if not job_description:
            return []

        import re

        # Clean and normalize
        text = job_description.lower()

        # Remove common stop words
        stop_words = {'the', 'and', 'or', 'a', 'an', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were',
                     'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
                     'did', 'will', 'would', 'could', 'should', 'may', 'might',
                     'can', 'must', 'shall', 'you', 'we', 'they', 'it', 'this',
                     'that', 'these', 'those', 'your', 'our', 'their', 'its'}

        # Extract words and phrases
        keywords = []

        # Look for technical skills (programming languages, tools, frameworks)
        tech_patterns = [
            r'\b(?:python|javascript|java|c\+\+|c#|go|rust|ruby|php|swift|kotlin)\b',
            r'\b(?:react|angular|vue|svelte|node\.?js|express|django|flask|rails)\b',
            r'\b(?:aws|azure|gcp|docker|kubernetes|jenkins|gitlab|github)\b',
            r'\b(?:sql|mysql|postgresql|mongodb|redis|elasticsearch|dynamodb)\b',
            r'\b(?:tensorflow|pytorch|keras|scikit|pandas|numpy|spark|hadoop)\b',
            r'\b(?:agile|scrum|kanban|jira|confluence|ci/cd|devops|sre)\b',
        ]

        for pattern in tech_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.extend(matches)

        # Extract requirements section
        req_section = re.search(r'(?:requirements|qualifications|what you need|skills required)[\s\S]*?(?:\n\n|responsibilities|$)',
                                text, re.IGNORECASE)

        if req_section:
            req_text = req_section.group(0)
            # Extract bullet points and key phrases
            lines = re.findall(r'[•\-\*]\s*([^\n]+)', req_text)
            for line in lines:
                # Clean and extract key terms
                words = re.findall(r'\b[a-z][a-z0-9+.#]*(?:\s+[a-z][a-z0-9+.]*){0,2}\b', line.lower())
                for phrase in words:
                    if len(phrase) > 2 and phrase not in stop_words:
                        keywords.append(phrase.strip())

        # Remove duplicates and limit
        unique_keywords = list(set(kw.lower() for kw in keywords))
        return unique_keywords[:20]

    def _check_keywords(self, text: str, role_type: str, job_description: Optional[str] = None) -> Dict:
        """Check for important keywords - from JD if provided, otherwise fallback"""
        text_lower = text.lower()

        # Extract keywords from job description if provided
        if job_description:
            keywords = self._extract_keywords_from_jd(job_description)
        else:
            # Fallback to generic keywords by role
            keywords_by_role = {
                'software_engineer': [
                    'python', 'javascript', 'java', 'c++', 'react', 'node',
                    'sql', 'aws', 'docker', 'kubernetes', 'git', 'ci/cd',
                    'agile', 'scrum', 'rest', 'api', 'microservices'
                ],
                'data_scientist': [
                    'python', 'r', 'sql', 'machine learning', 'deep learning',
                    'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn',
                    'statistics', 'visualization', 'tableau', 'power bi'
                ],
                'product_manager': [
                    'roadmap', 'strategy', 'stakeholders', 'metrics', 'kpi',
                    'user research', 'a/b testing', 'agile', 'scrum',
                    'prioritization', 'cross-functional', 'data-driven'
                ]
            }
            keywords = keywords_by_role.get(role_type, keywords_by_role['software_engineer'])

        # Normalize keywords for comparison
        normalized_keywords = [kw.lower().strip() for kw in keywords if len(kw.strip()) > 0]

        found = []
        missing = []

        for kw in normalized_keywords:
            # Check if keyword or close variant exists in resume
            if kw in text_lower:
                found.append(kw)
            else:
                # Check for partial matches (e.g., "javascript" in "javascript frameworks")
                partial_match = any(kw in word for word in text_lower.split())
                if partial_match:
                    found.append(kw)
                else:
                    missing.append(kw)

        return {
            'found': found,
            'missing': missing,
            'coverage': round((len(found) / len(normalized_keywords)) * 100, 1) if normalized_keywords else 0,
            'total_keywords': len(normalized_keywords)
        }

    def _check_formatting(self, text: str) -> List[str]:
        """Check for formatting issues"""
        issues = []

        if len(text) > 10000:
            issues.append("Resume is quite long. Consider condensing to 1-2 pages.")

        if text.count('\n\n\n') > 10:
            issues.append("Inconsistent spacing detected")

        # Check for very long lines
        long_lines = [line for line in text.split('\n') if len(line) > 120]
        if len(long_lines) > 5:
            issues.append("Some lines are very long. Consider breaking into bullet points.")

        return issues

    def _identify_strengths(self, sections: Dict, keywords: Dict) -> List[str]:
        """Identify resume strengths"""
        strengths = []

        if 'experience' in sections:
            strengths.append("Strong work experience section")

        if len(keywords['found']) >= 10:
            strengths.append(f"Good keyword coverage ({len(keywords['found'])} relevant skills)")

        if 'projects' in sections:
            strengths.append("Projects section demonstrates practical application")

        if 'education' in sections:
            strengths.append("Clear education background")

        return strengths

    def _identify_improvements(self, sections: Dict, keywords: Dict) -> List[str]:
        """Identify areas for improvement"""
        improvements = []

        if 'summary' not in sections:
            improvements.append("Add a brief professional summary at the top")

        if len(keywords['missing']) > 0:
            top_missing = keywords['missing'][:5]
            improvements.append(f"Consider adding relevant keywords: {', '.join(top_missing)}")

        if 'skills' not in sections:
            improvements.append("Add a dedicated skills section")

        return improvements

    def _check_ats_compatibility(self, text: str) -> Dict:
        """Check ATS (Applicant Tracking System) compatibility"""
        issues = []

        # Check for special characters that might confuse ATS
        if '•' in text:
            issues.append("Contains bullet characters. Use standard hyphens or asterisks for better ATS compatibility.")

        # Check for tables (simplified check)
        if '|' in text or '\t' in text:
            issues.append("May contain tabular data. ATS systems may not parse tables correctly.")

        # Check for headers/footers (simplified)
        if text.count('\f') > 0:
            issues.append("Contains page breaks. Remove page breaks for better ATS parsing.")

        return {
            "compatible": len(issues) == 0,
            "score": 100 - (len(issues) * 10),
            "warnings": issues
        }

    def _get_ai_analysis(self, resume: str, job_desc: str) -> Optional[Dict]:
        """Get AI-powered analysis"""
        if not self.ai_router:
            return None

        prompt = f"""Analyze this resume against the job description. Provide 3 tailored suggestions for improvement.

Job Description:
{job_desc[:1000]}

Resume:
{resume[:1500]}

Format response as JSON:
{{
    "suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"],
    "match_score": 75
}}"""

        try:
            response = self.ai_router.generate(prompt, mode="fast")
            # Parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"AI analysis error: {e}")

        return None


# Global instance
resume_reviewer = ResumeReviewer()


def analyze_resume(resume_text: str, job_description: str = None, role_type: str = "software_engineer") -> Dict:
    """Analyze a resume"""
    return resume_reviewer.analyze_resume(resume_text, job_description, role_type)
