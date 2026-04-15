"""
resume_review.py - AI-Powered Resume Review

Analyzes resume against job descriptions and provides feedback.
"""

import json
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("resume_review")


@dataclass
class ResumeRewrite:
    """Structured rewrite for a resume bullet point"""
    original: str
    rewritten: str
    explanation: str
    impact_score_increase: str

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
    rewrites: List[ResumeRewrite] = field(default_factory=list)
    semantic_fit_score: float = 0.0


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
            tailored_suggestions=ai_feedback.get('suggestions', []) if ai_feedback else [],
            rewrites=[
                ResumeRewrite(**r) for r in ai_feedback.get('rewrites', [])
            ] if ai_feedback and 'rewrites' in ai_feedback else [],
            semantic_fit_score=float(ai_feedback.get('match_score', 0)) if ai_feedback else 0.0
        )

        return {
            "success": True,
            "analysis": {
                "overall_score": review.overall_score,
                "section_scores": review.section_scores,
                "strengths": review.strengths[:5],
                "improvements": review.improvements[:5],
                "missing_keywords": review.missing_keywords[:10],
                "found_keywords": keywords.get('found', []),
                "formatting_issues": review.formatting_issues,
                "tailored_suggestions": review.tailored_suggestions,
                "rewrites": [
                    {"original": r.original, "rewritten": r.rewritten, "explanation": r.explanation, "impact": r.impact_score_increase}
                    for r in review.rewrites
                ],
                "semantic_fit": review.semantic_fit_score
            },
            "ats_compatibility": self._check_ats_compatibility(resume_text),
            "word_count": len(resume_text.split()),
            "estimated_reading_time": len(resume_text.split()) // 200  # ~200 WPM
        }

    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract resume sections with improved structural detection"""
        sections = {}
        lines = text.split('\n')
        current_section = None
        current_content = []

        # Expanded headers with common variations
        section_patterns = {
            'summary': ['summary', 'objective', 'professional summary', 'profile'],
            'experience': ['experience', 'work history', 'employment', 'professional experience', 'work experience'],
            'education': ['education', 'academic background', 'qualifications'],
            'skills': ['skills', 'technical skills', 'core competencies', 'expertise'],
            'projects': ['projects', 'personal projects', 'academic projects', 'key projects'],
            'certifications': ['certifications', 'awards', 'certifications & licenses'],
            'languages': ['languages', 'linguistic skills']
        }

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            line_lower = line_stripped.lower()

            # Check if line is a section header (usually short, capitalized or distinct)
            is_header = False
            for section_key, patterns in section_patterns.items():
                if any(pattern == line_lower or line_lower.startswith(pattern + ':') for pattern in patterns) and len(line_stripped) < 60:
                    if current_section:
                        sections[current_section] = '\n'.join(current_content).strip()
                    current_section = section_key
                    current_content = []
                    is_header = True
                    break

            if not is_header:
                if current_section:
                    current_content.append(line_stripped)
                else:
                    # Initial content (Contact info/Header)
                    if 'header' not in sections:
                        current_section = 'header'
                        current_content = [line_stripped]

        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections

    def _score_sections(self, sections: Dict[str, str]) -> Dict[str, int]:
        """Score each resume section using a Senior Recruiter's perspective"""
        if not self.ai_router:
            # Fallback to original heuristics if AI is unavailable
            return self._score_sections_heuristic(sections)

        # Combine relevant sections for context
        analysis_text = "\n".join([f"{k}: {v}" for k, v in sections.items()])

        prompt = f"""Persona: Senior Technical Recruiter at a FAANG company.
Task: Score the following resume sections on a scale of 0-100 based on professional impact, clarity, and technical depth.

Resume Sections:
{analysis_text}

Provide a JSON response with scores for these keys: 'experience', 'skills', 'education', 'summary'.
Return ONLY JSON:
{{
    "experience": 85,
    "skills": 70,
    "education": 90,
    "summary": 60
}}"""
        try:
            response = self.ai_router.generate(prompt, mode="fast")
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"AI section scoring error: {e}")

        return self._score_sections_heuristic(sections)

    def _score_sections_heuristic(self, sections: Dict[str, str]) -> Dict[str, int]:
        """Original heuristic scoring fallback"""
        scores = {}
        if 'experience' in sections or 'work' in sections:
            exp_text = sections.get('experience', sections.get('work', ''))
            scores['experience'] = self._score_experience(exp_text)
        else:
            scores['experience'] = 20
        if 'skills' in sections:
            scores['skills'] = self._score_skills(sections['skills'])
        else:
            scores['skills'] = 30
        if 'education' in sections:
            scores['education'] = 85
        else:
            scores['education'] = 40
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
        """Check for important keywords using semantic-aware matching"""
        text_lower = text.lower()

        if job_description:
            keywords = self._extract_keywords_from_jd(job_description)
        else:
            keywords_by_role = {
                'software_engineer': ['python', 'javascript', 'java', 'c++', 'react', 'node', 'sql', 'aws', 'docker', 'kubernetes', 'git', 'ci/cd', 'agile', 'scrum', 'rest', 'api', 'microservices'],
                'data_scientist': ['python', 'r', 'sql', 'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn', 'statistics', 'visualization', 'tableau', 'power bi'],
                'product_manager': ['roadmap', 'strategy', 'stakeholders', 'metrics', 'kpi', 'user research', 'a/b testing', 'agile', 'scrum', 'prioritization', 'cross-functional', 'data-driven']
            }
            keywords = keywords_by_role.get(role_type, keywords_by_role['software_engineer'])

        normalized_keywords = [kw.lower().strip() for kw in keywords if len(kw.strip()) > 0]
        found = []
        missing = []

        # Enhanced Semantic Matching
        for kw in normalized_keywords:
            # Exact or substring match
            if kw in text_lower:
                found.append(kw)
            else:
                # Semantic fallback: use AI to check if the skill is present even if wording differs
                if self.ai_router:
                    semantic_prompt = f"Does the following resume text demonstrate a professional skill in '{kw}'? Respond with only 'YES' or 'NO'.\n\nResume: {text[:2000]}"
                    try:
                        res = self.ai_router.generate(semantic_prompt, mode="fast").strip().upper()
                        if 'YES' in res:
                            found.append(kw)
                            continue
                    except:
                        pass

                # Final fallback: partial word match
                if any(kw in word for word in text_lower.split()):
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
        """Get professional AI-powered analysis and rewrites"""
        if not self.ai_router:
            return None

        prompt = f"""Persona: Brutally Honest Senior Technical Recruiter and Executive Resume Writer at a top FAANG company.
Task: Analyze the resume against the job description. Do not be lenient. Your goal is to make this candidate a 'Top 1%' applicant.

1. Professional Match Score (0-100): Be critical. A score of 80+ means the candidate is a perfect fit.
2. Tailored Suggestions: Provide 3 high-impact, strategic suggestions to move the resume from 'good' to 'elite'.
3. Mandatory Rewrites: Identify the 3 most generic or weak bullet points. Even if the resume is strong, find ways to make them more impactful. Rewrite them using the XYZ formula: "Accomplished [X] as measured by [Y], by doing [Z]".
   - If critical keywords from the JD are missing, use these rewrites to naturally integrate them.

Job Description:
{job_desc[:2000]}

Resume:
{resume[:3000]}

Return the response ONLY as a JSON object with this structure:
{{
    "match_score": 85,
    "suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"],
    "rewrites": [
        {{
            "original": "Original bullet text",
            "rewritten": "High impact XYZ version",
            "explanation": "Why this is better (e.g., 'Integrated missing keyword [X] and added metric [Y]')",
            "impact_score_increase": "+10%"
        }},
        ...
    ]
}}"""

        try:
            response = self.ai_router.generate(prompt, mode="fast")
            import re
            # Aggressive JSON extraction: find the first '{' and last '}'
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                json_str = response[start:end+1]
                # Remove potential trailing commas in arrays/objects before closing brace
                json_str = re.sub(r',\s*([\]}])', r'\1', json_str)
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            # Return a safe default so the app doesn't crash
            return {
                "match_score": 0,
                "suggestions": ["AI analysis temporarily unavailable. Please try again."],
                "rewrites": []
            }


# Global instance
resume_reviewer = ResumeReviewer()


def analyze_resume(resume_text: str, job_description: str = None, role_type: str = "software_engineer") -> Dict:
    """Analyze a resume"""
    return resume_reviewer.analyze_resume(resume_text, job_description, role_type)
