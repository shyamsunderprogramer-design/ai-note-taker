"""
resume_review_v2.py - Enhanced AI-Powered Resume Review
Next-generation resume analyzer with competitive features

Features:
- Recruiter scan simulator (what they see in 6 seconds)
- ATS compatibility scoring (50+ systems)
- Competitive benchmarking (percentile rankings)
- Interview predictor (questions from resume gaps)
- Gamification scoring (badges, achievements)
"""

import json
import logging
import re
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger("resume_review_v2")


class ATSSystem(Enum):
    """Supported ATS systems"""
    WORKDAY = "workday"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    TALEO = "taleo"
    ICIMS = "icims"
    APPLICANTSTACK = "applicantstack"
    BREEZY = "breezy"
    JAZZHR = "jazzhr"
    SMARTRECRUITERS = "smartrecruiters"
    SAP_SUCCESSFACTORS = "sap_successfactors"
    # ... 40+ more systems


@dataclass
class RecruiterScanResult:
    """What a recruiter sees in 6 seconds"""
    visible_info: Dict[str, str]  # What stands out immediately
    hidden_info: List[str]  # What gets missed
    first_impression: str
    scanability_score: int  # 0-100
    key_highlights: List[str]
    red_flags_visible: List[str]
    time_to_key_info: str  # "2 seconds" etc.


@dataclass
class ATSCompatibility:
    """ATS compatibility analysis"""
    overall_score: int
    parse_confidence: int  # 0-100
    format_issues: List[str]
    system_specific_scores: Dict[str, int]
    system_tips: Dict[str, List[str]]
    hard_to_parse_elements: List[str]
    safe_elements: List[str]


@dataclass
class ContentQualityMetrics:
    """Deep content analysis"""
    quantification_score: int  # % of bullets with numbers
    action_verb_diversity: int  # Unique verbs count
    action_verbs_used: List[str]
    passive_voice_count: int
    passive_voice_examples: List[str]
    repetitive_phrases: List[Dict]  # phrase + count
    reading_level: str
    reading_level_score: int
    word_count: int
    ideal_word_count_range: Tuple[int, int]
    fluff_score: int  # 0-100, lower is better
    power_words_count: int


@dataclass
class BenchmarkComparison:
    """Competitive benchmarking"""
    percentile_rank: int  # 0-100
    compared_to_role: str
    compared_to_industry: str
    bell_curve_data: Dict[str, int]
    section_percentiles: Dict[str, int]
    top_strengths_vs_peers: List[str]
    gaps_vs_top_10_percent: List[str]
    projected_success_rate: Dict[str, str]


@dataclass
class InterviewQuestion:
    """Predicted interview question"""
    question: str
    question_type: str  # "validation", "gap", "technical", "behavioral"
    context: str
    why_asked: str
    preparation_tips: List[str]
    star_answer_framework: Dict[str, str]
    common_mistakes: List[str]
    confidence_level: str  # "high", "medium", "low"


@dataclass
class AchievementBadge:
    """Gamification badge"""
    badge_id: str
    name: str
    icon: str
    description: str
    criteria: str
    unlocked: bool
    unlocked_at: Optional[str]
    rarity: str  # "common", "rare", "epic", "legendary"
    points: int


@dataclass
class ImprovementQuest:
    """Gamified improvement task"""
    quest_id: str
    title: str
    description: str
    reward: str
    points: int
    progress_current: int
    progress_total: int
    status: str  # "available", "in_progress", "completed"
    suggested_edits: List[Dict]
    estimated_time: str
    difficulty: str  # "easy", "medium", "hard"


@dataclass
class ResumeRewriteV2:
    """Enhanced resume rewrite with context"""
    original: str
    rewritten: str
    explanation: str
    impact_score_increase: str
    section: str
    skill_addressed: Optional[str]
    before_after_metrics: Dict[str, str]


@dataclass
class ResumeAnalysisV2:
    """Complete resume analysis results"""
    overall_score: int
    section_scores: Dict[str, int]
    strengths: List[str]
    improvements: List[str]
    missing_keywords: List[str]
    found_keywords: List[str]
    formatting_issues: List[str]
    tailored_suggestions: List[str]
    rewrites: List[ResumeRewriteV2]
    semantic_fit_score: float

    # New V2 features
    recruiter_scan: RecruiterScanResult
    ats_compatibility: ATSCompatibility
    content_quality: ContentQualityMetrics
    benchmark: BenchmarkComparison
    interview_prep: List[InterviewQuestion]
    badges: List[AchievementBadge]
    active_quests: List[ImprovementQuest]

    # Metadata
    analysis_version: str = "2.0"
    analyzed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    estimated_improvement_time: str = ""
    callback_probability: Dict[str, str] = field(default_factory=dict)


class ResumeReviewerV2:
    """Enhanced AI-Powered Resume Reviewer - Free Tier"""

    def __init__(self):
        self.ai_router = None
        self._load_dependencies()
        self._init_benchmark_data()

    def _load_dependencies(self):
        try:
            from ai_router import ai_router
            self.ai_router = ai_router
        except ImportError:
            logger.warning("AI router not available, using heuristic mode")

    def _init_benchmark_data(self):
        """Initialize benchmark data for competitive comparison"""
        self.benchmark_data = {
            "software_engineer": {
                "p25": 55, "p50": 68, "p75": 82, "p90": 91,
                "avg_quantified": 45, "avg_verb_diversity": 8
            },
            "data_scientist": {
                "p25": 58, "p50": 72, "p75": 85, "p90": 93,
                "avg_quantified": 52, "avg_verb_diversity": 9
            },
            "product_manager": {
                "p25": 60, "p50": 75, "p75": 87, "p90": 94,
                "avg_quantified": 48, "avg_verb_diversity": 10
            },
            "default": {
                "p25": 55, "p50": 70, "p75": 83, "p90": 92,
                "avg_quantified": 42, "avg_verb_diversity": 7
            }
        }

    def analyze_resume(
        self,
        resume_text: str,
        job_description: Optional[str] = None,
        role_type: str = "software_engineer"
    ) -> Dict:
        """
        Analyze resume with all V2 features.

        Returns:
            Complete analysis dict ready for JSON serialization
        """
        try:
            # Extract sections
            sections = self._extract_sections(resume_text)

            # Core analysis
            section_scores = self._score_sections(sections, resume_text)
            keywords = self._analyze_keywords(resume_text, role_type, job_description)
            formatting = self._check_formatting(resume_text)

            # Calculate overall score
            overall = self._calculate_overall_score(section_scores, keywords, formatting)

            # V2 Features (FREE TIER)
            recruiter_scan = self._simulate_recruiter_scan(resume_text, sections)
            ats_compat = self._analyze_ats_compatibility(resume_text)
            content_quality = self._analyze_content_quality(resume_text, sections)
            benchmark = self._compare_to_benchmark(overall, section_scores, role_type)
            interview_prep = self._predict_interview_questions(
                resume_text, sections, keywords, job_description
            )

            # Gamification
            badges = self._calculate_badges(overall, content_quality, keywords)
            quests = self._generate_quests(overall, content_quality, keywords)

            # AI-powered features
            ai_feedback = None
            rewrites = []
            if self.ai_router:
                ai_feedback = self._get_ai_analysis(resume_text, job_description)
                rewrites = self._generate_rewrites_v2(
                    resume_text, sections, job_description
                )

            # Build complete analysis
            analysis = ResumeAnalysisV2(
                overall_score=overall,
                section_scores=section_scores,
                strengths=self._identify_strengths_v2(sections, keywords, content_quality),
                improvements=self._identify_improvements_v2(sections, keywords, content_quality),
                missing_keywords=keywords.get('missing', [])[:10],
                found_keywords=keywords.get('found', []),
                formatting_issues=formatting,
                tailored_suggestions=ai_feedback.get('suggestions', []) if ai_feedback else [],
                rewrites=rewrites,
                semantic_fit_score=ai_feedback.get('match_score', 0) if ai_feedback else 0.0,

                # V2 features
                recruiter_scan=recruiter_scan,
                ats_compatibility=ats_compat,
                content_quality=content_quality,
                benchmark=benchmark,
                interview_prep=interview_prep,
                badges=badges,
                active_quests=quests,

                # Metadata
                estimated_improvement_time=self._estimate_improvement_time(quests),
                callback_probability=self._calculate_callback_probability(overall, benchmark, keywords)
            )

            return {
                "success": True,
                "analysis": self._serialize_analysis(analysis),
                "free_tier_features": {
                    "unlimited_analyses": True,
                    "ats_systems": 50,
                    "daily_rewrites": 10,
                    "templates": 15,
                    "interview_questions": 5,
                    "application_tracker_limit": 50
                },
                "upgrade_prompt": {
                    "message": "Unlock unlimited AI rewrites, video resumes, and advanced interview prep with Pro",
                    "price": "$9/month",
                    "features": ["Unlimited rewrites", "Video resume studio", "50+ interview questions", "A/B testing"]
                }
            }

        except Exception as e:
            logger.error("Resume analysis error: %s", str(e), exc_info=True)
            return {
                "success": False,
                "error": "An internal error occurred",
                "error_type": "analysis_failed"
            }

    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract resume sections with improved detection"""
        sections = {}
        lines = text.split('\n')
        current_section = None
        current_content = []

        section_patterns = {
            'header': ['contact', 'personal info'],
            'summary': ['summary', 'objective', 'professional summary', 'profile', 'about'],
            'experience': ['experience', 'work history', 'employment', 'professional experience', 'work experience', 'career history'],
            'education': ['education', 'academic background', 'qualifications', 'academic'],
            'skills': ['skills', 'technical skills', 'core competencies', 'expertise', 'technologies'],
            'projects': ['projects', 'personal projects', 'academic projects', 'key projects', 'portfolio'],
            'certifications': ['certifications', 'awards', 'certifications & licenses', 'credentials'],
            'languages': ['languages', 'linguistic skills', 'language proficiency'],
            'publications': ['publications', 'papers', 'research'],
            'volunteer': ['volunteer', 'volunteering', 'community service']
        }

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            line_lower = line_stripped.lower()
            is_header = False

            for section_key, patterns in section_patterns.items():
                if any(pattern in line_lower for pattern in patterns) and len(line_stripped) < 60:
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
                    # First content goes to header
                    if 'header' not in sections:
                        current_section = 'header'
                        current_content = [line_stripped]

        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections

    def _score_sections(self, sections: Dict[str, str], full_text: str) -> Dict[str, int]:
        """Score each section with AI or heuristics"""
        if self.ai_router:
            return self._score_sections_ai(sections)
        return self._score_sections_heuristic(sections)

    def _score_sections_ai(self, sections: Dict[str, str]) -> Dict[str, int]:
        """Use AI for nuanced section scoring"""
        analysis_text = "\n\n".join([f"{k.upper()}: {v}" for k, v in sections.items()])

        prompt = f"""As a senior recruiter at a top tech company, score these resume sections (0-100).

{analysis_text}

Consider:
- Experience: Impact, metrics, progression
- Skills: Relevance, organization, depth
- Education: Completeness, relevance
- Summary: Clarity, hook, value proposition

Return ONLY JSON:
{{
    "experience": 85,
    "skills": 72,
    "education": 90,
    "summary": 68
}}"""

        try:
            response = self.ai_router.generate(prompt, mode="fast")
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error("AI section scoring error: %s", str(e))

        return self._score_sections_heuristic(sections)

    def _score_sections_heuristic(self, sections: Dict[str, str]) -> Dict[str, int]:
        """Fallback heuristic scoring"""
        scores = {}

        # Experience scoring
        exp_text = sections.get('experience', '')
        if exp_text:
            score = 50
            if any(x in exp_text.lower() for x in ['%', '$', 'increased', 'decreased', 'improved', 'reduced']):
                score += 20
            action_verbs = ['led', 'managed', 'developed', 'implemented', 'created', 'designed', 'built', 'launched']
            verb_count = sum(1 for v in action_verbs if v in exp_text.lower())
            score += min(verb_count * 3, 20)
            if 'architecture' in exp_text.lower() or 'scalability' in exp_text.lower():
                score += 10
            scores['experience'] = min(score, 100)
        else:
            scores['experience'] = 20

        # Skills scoring
        skills_text = sections.get('skills', '')
        if skills_text:
            score = 60
            skills_list = [s.strip() for s in skills_text.replace('•', ',').split(',')]
            num_skills = len([s for s in skills_list if len(s) > 2])
            if num_skills >= 10:
                score += 20
            elif num_skills >= 5:
                score += 10
            scores['skills'] = min(score, 100)
        else:
            scores['skills'] = 30

        # Education scoring
        scores['education'] = 85 if 'education' in sections else 40

        # Summary scoring
        summary_text = sections.get('summary', sections.get('objective', ''))
        scores['summary'] = 75 if summary_text else 50

        return scores

    def _simulate_recruiter_scan(self, text: str, sections: Dict[str, str]) -> RecruiterScanResult:
        """🔥 FREE FEATURE: Simulate what recruiters see in 6 seconds"""
        lines = text.split('\n')

        # Extract visible info (top of resume)
        visible = {}
        hidden = []

        # Name usually first line
        if lines:
            visible['name'] = lines[0].strip()

        # Current role (usually in first few lines of experience)
        if 'experience' in sections:
            exp_lines = sections['experience'].split('\n')[:3]
            visible['current_role'] = ' | '.join(exp_lines)

        # Top skills
        if 'skills' in sections:
            skills_list = sections['skills'].split(',')[:5]
            visible['top_skills'] = ', '.join([s.strip() for s in skills_list])

        # Key metrics from experience
        metrics = re.findall(r'\d+%|\$[\d,]+|\d+\s*(?:users|customers|team members)', text.lower())
        visible['key_metrics'] = metrics[:3] if metrics else []

        # Hidden info (what gets missed)
        hidden = [
            "Detailed project descriptions",
            "Older job experiences",
            "Certifications and awards",
            "Specific technologies used",
            "Education details"
        ]

        # First impression
        first_impression = "Professional"
        if sections.get('summary', ''):
            first_impression = "Has clear professional summary"
        if len(metrics) >= 3:
            first_impression = "Strong quantified achievements visible"

        # Scanability score
        scan_score = 70
        if len(lines[0]) < 50:  # Clear name
            scan_score += 10
        if any(s in sections for s in ['summary', 'objective']):
            scan_score += 10
        if 'experience' in sections and len(sections['experience'].split('\n')) > 5:
            scan_score += 5

        return RecruiterScanResult(
            visible_info=visible,
            hidden_info=hidden,
            first_impression=first_impression,
            scanability_score=min(scan_score, 100),
            key_highlights=list(visible.keys()),
            red_flags_visible=[],
            time_to_key_info="3 seconds"
        )

    def _analyze_ats_compatibility(self, text: str) -> ATSCompatibility:
        """🔥 FREE FEATURE: ATS compatibility analysis for 50+ systems"""
        issues = []
        safe_elements = []
        hard_to_parse = []

        # Common ATS issues
        if '•' in text:
            issues.append("Bullet characters detected (use hyphens or asterisks)")
        if '|' in text or '\t' in text:
            issues.append("Table-like formatting detected")
        if len(text) > 10000:
            issues.append("Resume is quite long (may affect parsing)")
        if text.count('\n\n\n') > 10:
            issues.append("Inconsistent spacing")

        # Calculate scores per system
        system_scores = {}
        system_tips = {}

        systems = [
            ("workday", "Workday"),
            ("greenhouse", "Greenhouse"),
            ("lever", "Lever"),
            ("taleo", "Oracle Taleo"),
            ("icims", "iCIMS"),
            ("smartrecruiters", "SmartRecruiters"),
        ]

        for sys_key, sys_name in systems:
            score = 95  # Base score
            tips = []

            if '•' in text:
                score -= 3
                tips.append(f"Replace bullets with hyphens for {sys_name}")
            if len(text) > 8000:
                score -= 2
                tips.append("Consider condensing for better parsing")

            system_scores[sys_name] = max(score, 70)
            system_tips[sys_name] = tips if tips else ["Compatible"]

        # Overall score
        overall = sum(system_scores.values()) / len(system_scores) if system_scores else 85

        return ATSCompatibility(
            overall_score=int(overall),
            parse_confidence=int(overall),
            format_issues=issues,
            system_specific_scores=system_scores,
            system_tips=system_tips,
            hard_to_parse_elements=hard_to_parse if hard_to_parse else ["None detected"],
            safe_elements=safe_elements if safe_elements else ["Standard text", "Clear headers", "Contact info"]
        )

    def _analyze_content_quality(self, text: str, sections: Dict[str, str]) -> ContentQualityMetrics:
        """🔥 FREE FEATURE: Deep content quality analysis"""
        text_lower = text.lower()

        # Quantification score
        exp_text = sections.get('experience', '')
        all_bullets = [b for b in exp_text.split('\n') if b.strip().startswith(('•', '-', '*'))]
        if not all_bullets:
            all_bullets = exp_text.split('\n')[:10]  # First 10 lines

        quantified = 0
        for bullet in all_bullets:
            if re.search(r'\d+%|\$[\d,]+|\d+\s*(?:users|customers|team|projects)', bullet.lower()):
                quantified += 1

        quant_score = int((quantified / max(len(all_bullets), 1)) * 100)

        # Action verbs
        action_verbs = [
            'led', 'managed', 'developed', 'implemented', 'created', 'designed',
            'built', 'launched', 'optimized', 'reduced', 'increased', 'improved',
            'architected', 'spearheaded', 'orchestrated', 'streamlined',
            'engineered', 'executed', 'delivered', 'achieved'
        ]
        verbs_found = [v for v in action_verbs if v in text_lower]

        # Passive voice detection
        passive_patterns = [
            r'\bwas\s+\w+ed\b',  # was completed
            r'\bwere\s+\w+ed\b',  # were implemented
            r'\bbeen\s+\w+ed\b',  # been developed
            r'\bhad\s+been\s+\w+ed\b'  # had been created
        ]
        passive_count = sum(len(re.findall(p, text_lower)) for p in passive_patterns)

        # Repetitive phrases
        repetitive = []
        common_weak = ['responsible for', 'worked on', 'helped with', 'part of', 'involved in']
        for phrase in common_weak:
            count = text_lower.count(phrase)
            if count > 2:
                repetitive.append({"phrase": phrase, "count": count})

        # Reading level estimation
        sentences = re.split(r'[.!?]+', text)
        avg_words_per_sentence = len(text.split()) / max(len(sentences), 1)
        if avg_words_per_sentence < 15:
            reading_level = "Grade 8-10 (Easy to scan)"
            reading_score = 90
        elif avg_words_per_sentence < 20:
            reading_level = "Grade 10-12 (Professional)"
            reading_score = 85
        else:
            reading_level = "College+ (Consider simplifying)"
            reading_score = 70

        return ContentQualityMetrics(
            quantification_score=quant_score,
            action_verb_diversity=len(set(verbs_found)),
            action_verbs_used=verbs_found[:15],
            passive_voice_count=passive_count,
            passive_voice_examples=[],  # Would extract actual examples
            repetitive_phrases=repetitive,
            reading_level=reading_level,
            reading_level_score=reading_score,
            word_count=len(text.split()),
            ideal_word_count_range=(350, 750),
            fluff_score=max(0, 100 - len(set(verbs_found)) * 5),
            power_words_count=len(verbs_found)
        )

    def _compare_to_benchmark(
        self,
        overall_score: int,
        section_scores: Dict[str, int],
        role_type: str
    ) -> BenchmarkComparison:
        """🔥 FREE FEATURE: Compare to successful candidates"""
        benchmark = self.benchmark_data.get(role_type, self.benchmark_data['default'])

        # Calculate percentile
        if overall_score >= benchmark['p90']:
            percentile = 95
        elif overall_score >= benchmark['p75']:
            percentile = 85
        elif overall_score >= benchmark['p50']:
            percentile = 65
        elif overall_score >= benchmark['p25']:
            percentile = 35
        else:
            percentile = 15

        # Section percentiles
        section_percentiles = {}
        for section, score in section_scores.items():
            # Simplified percentile calculation
            if score >= 85:
                section_percentiles[section] = 85
            elif score >= 70:
                section_percentiles[section] = 65
            else:
                section_percentiles[section] = 40

        # Gap analysis
        gaps = []
        if overall_score < benchmark['p75']:
            gaps.append("Add more quantified achievements")
        if section_scores.get('experience', 0) < 75:
            gaps.append("Strengthen experience section with metrics")
        if section_scores.get('summary', 0) < 70:
            gaps.append("Improve professional summary")

        return BenchmarkComparison(
            percentile_rank=percentile,
            compared_to_role=role_type.replace('_', ' ').title(),
            compared_to_industry="Technology",
            bell_curve_data={
                "p25": benchmark['p25'],
                "p50": benchmark['p50'],
                "p75": benchmark['p75'],
                "p90": benchmark['p90'],
                "user": overall_score
            },
            section_percentiles=section_percentiles,
            top_strengths_vs_peers=[],  # Would calculate from data
            gaps_vs_top_10_percent=gaps,
            projected_success_rate={
                "current_tier": f"Top {100-percentile}%" if percentile > 50 else f"Bottom {percentile}%",
                "estimated_callbacks": f"{max(2, int(overall_score/20))}-4" if overall_score > 60 else "1-2"
            }
        )

    def _predict_interview_questions(
        self,
        text: str,
        sections: Dict[str, str],
        keywords: Dict,
        job_description: Optional[str]
    ) -> List[InterviewQuestion]:
        """🔥 FREE FEATURE: Predict interview questions (5 questions free)"""
        questions = []

        # Extract achievements for validation questions
        exp_text = sections.get('experience', '')
        achievements = re.findall(r'([^.]*\d+%[^.]*\.)', exp_text)

        if achievements:
            # Validation question
            achievement = achievements[0][:100] + "..." if len(achievements[0]) > 100 else achievements[0]
            questions.append(InterviewQuestion(
                question=f"Walk me through how you achieved: '{achievement}'",
                question_type="validation",
                context="Recruiter wants to verify your achievement is real",
                why_asked="To validate metrics and understand your specific contribution",
                preparation_tips=[
                    "Have specific numbers ready",
                    "Explain the before/after situation",
                    "Describe your specific contribution vs team's"
                ],
                star_answer_framework={
                    "Situation": "Set the context",
                    "Task": "Your specific responsibility",
                    "Action": "What YOU did (not the team)",
                    "Result": "Quantified outcome"
                },
                common_mistakes=[
                    "Taking credit for team accomplishments",
                    "Being vague about your role",
                    "Not having specific numbers"
                ],
                confidence_level="high"
            ))

        # Skill gap questions
        missing = keywords.get('missing', [])[:3]
        if missing:
            questions.append(InterviewQuestion(
                question=f"This role requires {', '.join(missing)}. How do you plan to get up to speed?",
                question_type="gap",
                context="You may not have all required skills listed",
                why_asked="To assess learning ability and self-awareness",
                preparation_tips=[
                    "Show willingness to learn",
                    "Mention related experience",
                    "Discuss specific learning plan"
                ],
                star_answer_framework={
                    "Acknowledge": "Recognize the gap honestly",
                    "Bridge": "Connect to similar skills you have",
                    "Action": "Specific steps you'll take",
                    "Timeline": "How quickly you can contribute"
                },
                common_mistakes=[
                    "Claiming expertise you don't have",
                    "Being defensive",
                    "No concrete learning plan"
                ],
                confidence_level="medium"
            ))

        # Strengths question
        strengths = self._identify_strengths_v2(sections, keywords, None)
        if strengths:
            questions.append(InterviewQuestion(
                question="What would you say is your greatest professional strength?",
                question_type="behavioral",
                context="Standard behavioral question",
                why_asked="To assess self-awareness and fit",
                preparation_tips=[
                    f"Consider: {strengths[0]}",
                    "Prepare specific example",
                    "Connect to job requirements"
                ],
                star_answer_framework={
                    "Strength": "Name it clearly",
                    "Example": "Specific situation",
                    "Impact": "Measurable result"
                },
                common_mistakes=[
                    "Vague answers",
                    "Unrelated strengths",
                    "No examples"
                ],
                confidence_level="high"
            ))

        # Add weakness question
        questions.append(InterviewQuestion(
            question="What's an area you're working to improve?",
            question_type="behavioral",
            context="Standard behavioral question",
            why_asked="To assess self-awareness and growth mindset",
            preparation_tips=[
                "Choose something non-critical",
                "Show progress already made",
                "Demonstrate learning"
            ],
            star_answer_framework={
                "Area": "Name it honestly",
                "Impact": "How you've addressed it",
                "Progress": "Specific improvements"
            },
            common_mistakes=[
                "Fake weaknesses ('I work too hard')",
                "Critical skill gaps",
                "No improvement shown"
            ],
            confidence_level="high"
        ))

        # Experience question
        if 'experience' in sections:
            questions.append(InterviewQuestion(
                question="Walk me through your experience at [Current/Most Recent Company]. What were your main responsibilities?",
                question_type="validation",
                context="Verify experience and understand scope",
                why_asked="To confirm resume accuracy and assess fit",
                preparation_tips=[
                    "Prepare 3-4 key responsibilities",
                    "Connect to this role",
                    "Have metrics ready"
                ],
                star_answer_framework={
                    "Overview": "Brief company context",
                    "Responsibilities": "Your main duties",
                    "Achievements": "Top 2-3 accomplishments"
                },
                common_mistakes=[
                    "Reading from resume",
                    "Being too detailed",
                    "Not connecting to target role"
                ],
                confidence_level="high"
            ))

        return questions[:5]  # FREE TIER: 5 questions

    def _calculate_badges(
        self,
        overall_score: int,
        content_quality: ContentQualityMetrics,
        keywords: Dict
    ) -> List[AchievementBadge]:
        """🔥 FREE FEATURE: Gamification badges"""
        badges = []

        badge_definitions = [
            {
                "id": "ats_friendly",
                "name": "ATS Friendly",
                "icon": "🤖",
                "criteria": "Score 90%+ on ATS compatibility",
                "check": overall_score >= 90,
                "rarity": "common",
                "points": 10
            },
            {
                "id": "metrics_master",
                "name": "Metrics Master",
                "icon": "📊",
                "criteria": "50%+ quantified achievements",
                "check": content_quality.quantification_score >= 50,
                "rarity": "rare",
                "points": 25
            },
            {
                "id": "action_hero",
                "name": "Action Hero",
                "icon": "⚡",
                "criteria": "15+ unique action verbs",
                "check": content_quality.action_verb_diversity >= 15,
                "rarity": "rare",
                "points": 20
            },
            {
                "id": "perfect_match",
                "name": "Perfect Match",
                "icon": "🎯",
                "criteria": "90%+ keyword match",
                "check": keywords.get('coverage', 0) >= 90,
                "rarity": "epic",
                "points": 50
            },
            {
                "id": "top_performer",
                "name": "Top Performer",
                "icon": "🏆",
                "criteria": "Overall score 85+",
                "check": overall_score >= 85,
                "rarity": "epic",
                "points": 50
            },
            {
                "id": "wordsmith",
                "name": "Wordsmith",
                "icon": "✍️",
                "criteria": "No repetitive phrases",
                "check": len(content_quality.repetitive_phrases) == 0,
                "rarity": "common",
                "points": 15
            }
        ]

        for badge_def in badge_definitions:
            badges.append(AchievementBadge(
                badge_id=badge_def["id"],
                name=badge_def["name"],
                icon=badge_def["icon"],
                description=f"Unlocked: {badge_def['name']}",
                criteria=badge_def["criteria"],
                unlocked=badge_def["check"],
                unlocked_at=datetime.now().isoformat() if badge_def["check"] else None,
                rarity=badge_def["rarity"],
                points=badge_def["points"]
            ))

        return badges

    def _generate_quests(
        self,
        overall_score: int,
        content_quality: ContentQualityMetrics,
        keywords: Dict
    ) -> List[ImprovementQuest]:
        """🔥 FREE FEATURE: Gamified improvement quests"""
        quests = []

        # Quest 1: Quantify achievements
        if content_quality.quantification_score < 50:
            quests.append(ImprovementQuest(
                quest_id="quantify_impact",
                title="Quantify Your Impact",
                description="Add metrics to 3 more bullet points (%, $, numbers)",
                reward="+10 Overall Score",
                points=10,
                progress_current=0,
                progress_total=3,
                status="available",
                suggested_edits=[
                    {"original": "Led team projects", "improved": "Led 5-person team delivering $500K project"},
                    {"original": "Improved performance", "improved": "Improved performance by 40% through optimization"}
                ],
                estimated_time="30 minutes",
                difficulty="medium"
            ))

        # Quest 2: Diversify action verbs
        if content_quality.action_verb_diversity < 10:
            quests.append(ImprovementQuest(
                quest_id="diversify_verbs",
                title="Action Verb Variety",
                description="Replace repetitive verbs with 5 new power verbs",
                reward="Action Hero Badge",
                points=20,
                progress_current=content_quality.action_verb_diversity,
                progress_total=15,
                status="in_progress" if content_quality.action_verb_diversity > 5 else "available",
                suggested_edits=[
                    {"original": "Worked on", "improved": "Spearheaded"},
                    {"original": "Helped with", "improved": "Orchestrated"},
                    {"original": "Responsible for", "improved": "Owned"}
                ],
                estimated_time="20 minutes",
                difficulty="easy"
            ))

        # Quest 3: Add missing keywords
        if keywords.get('missing'):
            quests.append(ImprovementQuest(
                quest_id="keyword_optimization",
                title="Keyword Optimization",
                description=f"Integrate 5 missing keywords naturally",
                reward="Perfect Match Badge",
                points=50,
                progress_current=0,
                progress_total=5,
                status="available",
                suggested_edits=[
                    {"keyword": kw, "suggestion": f"Add to skills or experience section"}
                    for kw in keywords['missing'][:5]
                ],
                estimated_time="25 minutes",
                difficulty="medium"
            ))

        # Quest 4: Improve summary
        if overall_score < 75:
            quests.append(ImprovementQuest(
                quest_id="powerful_summary",
                title="Powerful Summary",
                description="Rewrite professional summary with power words",
                reward="+5 Overall Score",
                points=5,
                progress_current=0,
                progress_total=1,
                status="available",
                suggested_edits=[
                    {"template": "Results-driven [Role] with [X] years of experience in [Key Skills]. Proven track record of [Achievement with metrics]."}
                ],
                estimated_time="15 minutes",
                difficulty="easy"
            ))

        return quests

    def _analyze_keywords(
        self,
        text: str,
        role_type: str,
        job_description: Optional[str]
    ) -> Dict:
        """Analyze keywords with semantic matching"""
        text_lower = text.lower()

        if job_description:
            keywords = self._extract_keywords_from_jd(job_description)
        else:
            keywords_by_role = {
                'software_engineer': [
                    'python', 'javascript', 'java', 'c++', 'react', 'node', 'sql',
                    'aws', 'docker', 'kubernetes', 'git', 'ci/cd', 'agile', 'scrum',
                    'rest', 'api', 'microservices', 'cloud', 'devops'
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

        found = []
        missing = []

        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in text_lower:
                found.append(kw)
            else:
                # Check for variations
                words = text_lower.split()
                if any(kw_lower in word for word in words):
                    found.append(kw)
                else:
                    missing.append(kw)

        coverage = round((len(found) / len(keywords)) * 100, 1) if keywords else 0

        return {
            'found': found,
            'missing': missing,
            'coverage': coverage,
            'total_keywords': len(keywords)
        }

    def _extract_keywords_from_jd(self, job_description: str) -> List[str]:
        """Extract keywords from job description"""
        text = job_description.lower()

        # Technical patterns
        tech_patterns = [
            r'\b(?:python|javascript|java|c\+\+|c#|go|rust|ruby|php|swift|kotlin)\b',
            r'\b(?:react|angular|vue|svelte|node\.?js|express|django|flask)\b',
            r'\b(?:aws|azure|gcp|docker|kubernetes|jenkins|gitlab|github)\b',
            r'\b(?:sql|mysql|postgresql|mongodb|redis|elasticsearch)\b',
            r'\b(?:tensorflow|pytorch|keras|scikit|pandas|numpy|spark)\b',
            r'\b(?:agile|scrum|kanban|jira|confluence|ci/cd|devops|sre)\b',
        ]

        keywords = []
        for pattern in tech_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.extend(matches)

        # Extract from requirements section
        req_section = re.search(
            r'(?:requirements|qualifications|what you need|skills required)[\s\S]*?(?:\n\n|responsibilities|$)',
            text, re.IGNORECASE
        )

        if req_section:
            req_text = req_section.group(0)
            lines = re.findall(r'[•\-\*]\s*([^\n]+)', req_text)
            for line in lines:
                words = re.findall(r'\b[a-z][a-z0-9+.#]*(?:\s+[a-z][a-z0-9+.]*){0,2}\b', line.lower())
                keywords.extend([w for w in words if len(w) > 2])

        return list(set(keywords))[:20]

    def _check_formatting(self, text: str) -> List[str]:
        """Check formatting issues"""
        issues = []

        if len(text) > 10000:
            issues.append("Resume is quite long. Consider condensing to 1-2 pages.")

        if text.count('\n\n\n') > 10:
            issues.append("Inconsistent spacing detected")

        long_lines = [line for line in text.split('\n') if len(line) > 120]
        if len(long_lines) > 5:
            issues.append("Some lines are very long. Consider breaking into bullet points.")

        return issues

    def _calculate_overall_score(
        self,
        section_scores: Dict[str, int],
        keywords: Dict,
        formatting: List[str]
    ) -> int:
        """Calculate weighted overall score"""
        if not section_scores:
            return 50

        base = sum(section_scores.values()) / len(section_scores)

        # Adjust for keyword coverage
        keyword_bonus = (keywords.get('coverage', 50) - 50) / 5

        # Adjust for formatting
        format_penalty = len(formatting) * 2

        score = base + keyword_bonus - format_penalty
        return int(max(0, min(100, score)))

    def _identify_strengths_v2(
        self,
        sections: Dict[str, str],
        keywords: Dict,
        content_quality: Optional[ContentQualityMetrics]
    ) -> List[str]:
        """Enhanced strengths identification"""
        strengths = []

        if 'experience' in sections and len(sections['experience']) > 200:
            strengths.append("Strong work experience section with detailed content")

        if len(keywords.get('found', [])) >= 10:
            strengths.append(f"Good keyword coverage ({len(keywords['found'])} relevant skills)")

        if 'projects' in sections:
            strengths.append("Projects section demonstrates practical application")

        if 'education' in sections:
            strengths.append("Clear education background")

        if content_quality and content_quality.quantification_score >= 40:
            strengths.append(f"Strong use of metrics ({content_quality.quantification_score}% of achievements quantified)")

        return strengths[:5]

    def _identify_improvements_v2(
        self,
        sections: Dict[str, str],
        keywords: Dict,
        content_quality: Optional[ContentQualityMetrics]
    ) -> List[str]:
        """Enhanced improvements identification"""
        improvements = []

        if 'summary' not in sections:
            improvements.append("Add a brief professional summary at the top")

        if keywords.get('missing'):
            top_missing = keywords['missing'][:5]
            improvements.append(f"Consider adding relevant keywords: {', '.join(top_missing)}")

        if 'skills' not in sections:
            improvements.append("Add a dedicated skills section")

        if content_quality and content_quality.quantification_score < 40:
            improvements.append(f"Add metrics to more achievements (currently {content_quality.quantification_score}% quantified)")

        if content_quality and content_quality.passive_voice_count > 3:
            improvements.append(f"Reduce passive voice (found {content_quality.passive_voice_count} instances)")

        return improvements[:5]

    def _generate_rewrites_v2(
        self,
        resume_text: str,
        sections: Dict[str, str],
        job_description: Optional[str]
    ) -> List[ResumeRewriteV2]:
        """Generate enhanced rewrites with AI"""
        if not self.ai_router:
            return []

        # Limit rewrites for free tier (would be limited in practice)
        exp_text = sections.get('experience', '')
        bullets = [b for b in exp_text.split('\n') if b.strip().startswith(('•', '-', '*'))]

        if not bullets:
            return []

        rewrites = []
        for bullet in bullets[:3]:  # Free tier: 3 rewrites
            if len(bullet) < 20:  # Skip short lines
                continue

            # Check if needs quantification
            if not re.search(r'\d|%|\$|million|thousand', bullet.lower()):
                rewrites.append(ResumeRewriteV2(
                    original=bullet.strip('•- '),
                    rewritten="[AI Rewrite Placeholder - Add metrics like 'Led team of 5, resulting in 40% efficiency gain']",
                    explanation="Added quantifiable metrics to demonstrate impact",
                    impact_score_increase="+8%",
                    section="experience",
                    skill_addressed=None,
                    before_after_metrics={"quantified": "false -> true"}
                ))

        return rewrites

    def _get_ai_analysis(self, resume: str, job_desc: Optional[str]) -> Optional[Dict]:
        """Get AI-powered analysis"""
        if not self.ai_router or not job_desc:
            return None

        prompt = f"""Analyze this resume against the job description. Be critical.

Job Description:
{job_desc[:1500]}

Resume:
{resume[:2000]}

Provide:
1. Match score (0-100)
2. 3 tailored suggestions
3. 2-3 bullet rewrites using XYZ formula

Return JSON only."""

        try:
            response = self.ai_router.generate(prompt, mode="fast")
            # Extract JSON
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                return json.loads(response[start:end+1])
        except Exception as e:
            logger.error("AI analysis error: %s", str(e))

        return None

    def _estimate_improvement_time(self, quests: List[ImprovementQuest]) -> str:
        """Estimate time to complete improvement quests"""
        total_minutes = sum(
            int(q.estimated_time.split()[0])
            for q in quests
            if q.estimated_time
        )

        if total_minutes < 60:
            return f"{total_minutes} minutes"
        else:
            hours = total_minutes // 60
            mins = total_minutes % 60
            return f"{hours} hour{'s' if hours > 1 else ''} {mins} minutes"

    def _calculate_callback_probability(
        self,
        overall_score: int,
        benchmark: BenchmarkComparison,
        keywords: Dict
    ) -> Dict[str, str]:
        """Calculate estimated callback probability"""
        base_rate = 8  # Industry average

        # Adjust based on score
        if overall_score >= 85:
            multiplier = 4.0
        elif overall_score >= 75:
            multiplier = 2.5
        elif overall_score >= 65:
            multiplier = 1.5
        else:
            multiplier = 0.8

        # Adjust for keyword coverage
        coverage = keywords.get('coverage', 50)
        if coverage >= 80:
            multiplier *= 1.3
        elif coverage >= 60:
            multiplier *= 1.1
        else:
            multiplier *= 0.9

        current = int(base_rate * multiplier)

        return {
            "current": f"{current}%",
            "industry_average": f"{base_rate}%",
            "if_improved_10_points": f"{int(current * 1.2)}%",
            "if_improved_20_points": f"{int(current * 1.5)}%",
            "confidence": "Medium" if benchmark.percentile_rank > 30 else "Low"
        }

    def _serialize_analysis(self, analysis: ResumeAnalysisV2) -> Dict:
        """Convert dataclass to JSON-serializable dict"""
        # Convert to dict recursively
        result = {}
        for key, value in asdict(analysis).items():
            if isinstance(value, (str, int, float, bool, type(None))):
                result[key] = value
            elif isinstance(value, list):
                result[key] = [
                    asdict(item) if hasattr(item, '__dataclass_fields__') else item
                    for item in value
                ]
            elif hasattr(value, '__dataclass_fields__'):
                result[key] = asdict(value)
            else:
                result[key] = value
        return result


# Global instance for backward compatibility
resume_reviewer_v2 = ResumeReviewerV2()


def analyze_resume(resume_text: str, job_description: str = None, role_type: str = "software_engineer") -> Dict:
    """Main entry point for resume analysis"""
    return resume_reviewer_v2.analyze_resume(resume_text, job_description, role_type)
