"""Route module for career features: cover letter generation, resume tailoring,
interview prep, salary insights, and skill gap analysis."""
import logging
import re
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from security import ErrorCode, error_response
from security.auth import User, get_current_user

# ---------------------------------------------------------------------------
# Auth helpers (consistent with other route modules)
# ---------------------------------------------------------------------------
security_bearer = HTTPBearer(auto_error=False)


async def get_token_from_request(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
) -> str:
    if credentials:
        return credentials.credentials
    return None


async def require_authentication(token: str = Depends(get_token_from_request)) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


logger = logging.getLogger("routes.career")

# ---------------------------------------------------------------------------
# AI router availability
# ---------------------------------------------------------------------------
try:
    from ai_router import route_ai_stream  # noqa: F401
    HAS_AI = True
except ImportError:
    HAS_AI = False

# ---------------------------------------------------------------------------
# Question database availability (for interview prep)
# ---------------------------------------------------------------------------
try:
    import sys
    from pathlib import Path
    _interview_dir = str(Path(__file__).parent.parent / "modules" / "interview")
    if _interview_dir not in sys.path:
        sys.path.insert(0, _interview_dir)
    from question_database_v2 import InterviewQuestion, QuestionCategory, Difficulty
    from company_questions import GOOGLE_QUESTIONS, AMAZON_QUESTIONS, META_QUESTIONS
    COMPANY_QUESTIONS_AVAILABLE = True
except ImportError:
    COMPANY_QUESTIONS_AVAILABLE = False

# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------


class CoverLetterRequest(BaseModel):
    job_title: str = Field(..., min_length=1, description="Target job title")
    company: str = Field(..., min_length=1, description="Target company name")
    job_description: str = Field("", description="Job description text")
    user_skills: List[str] = Field(default_factory=list, description="List of user skills")
    experience_years: int = Field(0, ge=0, description="Years of experience")
    tone: str = Field("professional", description="Tone: professional, conversational, enthusiastic")


class ResumeTailorRequest(BaseModel):
    job_description: str = Field(..., min_length=1, description="Job description text")
    resume_text: str = Field(..., min_length=1, description="Current resume text")
    target_role: str = Field("", description="Target role title")


class SalaryInsightsRequest(BaseModel):
    role: str = Field(..., min_length=1, description="Job role")
    location: str = Field("US", description="Location / region")
    experience_years: int = Field(0, ge=0, description="Years of experience")


class SkillGapsRequest(BaseModel):
    target_role: str = Field(..., min_length=1, description="Target role title")
    current_skills: List[str] = Field(..., min_length=1, description="Current skill list")


# ---------------------------------------------------------------------------
# Fallback data: salary ranges by role (USD, annual)
# ---------------------------------------------------------------------------
_SALARY_DATA: Dict[str, Dict] = {
    "software_engineer": {
        "entry": (75000, 120000),
        "mid": (120000, 180000),
        "senior": (180000, 280000),
        "staff": (250000, 400000),
    },
    "data_scientist": {
        "entry": (80000, 125000),
        "mid": (125000, 185000),
        "senior": (185000, 290000),
        "staff": (260000, 380000),
    },
    "product_manager": {
        "entry": (80000, 130000),
        "mid": (130000, 190000),
        "senior": (190000, 300000),
        "staff": (270000, 400000),
    },
    "frontend_engineer": {
        "entry": (70000, 115000),
        "mid": (115000, 170000),
        "senior": (170000, 260000),
        "staff": (240000, 370000),
    },
    "backend_engineer": {
        "entry": (75000, 120000),
        "mid": (120000, 175000),
        "senior": (175000, 270000),
        "staff": (250000, 390000),
    },
    "devops_engineer": {
        "entry": (72000, 118000),
        "mid": (118000, 172000),
        "senior": (172000, 265000),
        "staff": (245000, 375000),
    },
    "fullstack_engineer": {
        "entry": (73000, 118000),
        "mid": (118000, 175000),
        "senior": (175000, 270000),
        "staff": (250000, 385000),
    },
    "engineering_manager": {
        "entry": (130000, 180000),
        "mid": (180000, 250000),
        "senior": (250000, 380000),
        "staff": (350000, 500000),
    },
    "default": {
        "entry": (60000, 100000),
        "mid": (100000, 160000),
        "senior": (160000, 250000),
        "staff": (230000, 350000),
    },
}

_LOCATION_MULTIPLIER: Dict[str, float] = {
    "san_francisco": 1.35,
    "new_york": 1.25,
    "seattle": 1.20,
    "boston": 1.15,
    "austin": 1.05,
    "chicago": 1.00,
    "los_angeles": 1.20,
    "london": 0.85,
    "berlin": 0.70,
    "remote_us": 0.95,
    "us": 1.00,
}

# ---------------------------------------------------------------------------
# Fallback data: expected skills by role
# ---------------------------------------------------------------------------
_ROLE_SKILLS: Dict[str, List[str]] = {
    "software_engineer": [
        "python", "java", "javascript", "data_structures", "algorithms",
        "system_design", "git", "sql", "rest_apis", "testing",
        "agile", "linux", "cloud_aws", "docker", "ci_cd",
    ],
    "frontend_engineer": [
        "javascript", "typescript", "react", "html", "css",
        "responsive_design", "webpack", "testing", "git", "rest_apis",
        "accessibility", "performance_optimization", "state_management",
    ],
    "backend_engineer": [
        "python", "java", "sql", "rest_apis", "databases",
        "microservices", "docker", "cloud_aws", "caching", "message_queues",
        "authentication", "ci_cd", "linux", "system_design",
    ],
    "data_scientist": [
        "python", "machine_learning", "statistics", "sql", "pandas",
        "numpy", "tensorflow", "data_visualization", "a_b_testing",
        "feature_engineering", "nlp", "deep_learning", "jupyter",
    ],
    "product_manager": [
        "product_strategy", "user_research", "data_analysis", "roadmapping",
        "agile", "stakeholder_management", "prioritization", "metrics",
        "competitive_analysis", "prds", "wireframing", "go_to_market",
    ],
    "devops_engineer": [
        "linux", "docker", "kubernetes", "ci_cd", "cloud_aws",
        "terraform", "ansible", "monitoring", "scripting", "networking",
        "security", "jenkins", "cloud_gcp",
    ],
    "fullstack_engineer": [
        "javascript", "python", "react", "node_js", "sql",
        "rest_apis", "html", "css", "git", "docker",
        "cloud_aws", "testing", "system_design", "typescript",
    ],
    "engineering_manager": [
        "team_leadership", "technical_strategy", "hiring", "code_reviews",
        "agile", "architecture", "stakeholder_management", "mentorship",
        "project_management", "performance_reviews", "roadmapping",
    ],
}

# ---------------------------------------------------------------------------
# Fallback data: company interview tips
# ---------------------------------------------------------------------------
_COMPANY_TIPS: Dict[str, Dict] = {
    "google": {
        "focus": ["system_design", "algorithms", "behavioral_star"],
        "culture_values": ["ambiguity", "user_focus", "innovation", "data_driven"],
        "tips": [
            "Practice system design with focus on scalability",
            "Expect behavioral questions using STAR method",
            "Google values 'Googliness' - intellectual humility and collaboration",
            "Coding interviews focus on optimal solutions and clean code",
            "Prepare for 4-5 interviews in the onsite loop",
        ],
        "common_questions": [
            "Tell me about a time you dealt with ambiguity",
            "Design Google Docs",
            "Find the longest substring without repeating characters",
        ],
    },
    "amazon": {
        "focus": ["leadership_principles", "system_design", "behavioral_star"],
        "culture_values": ["customer_obsession", "ownership", "bias_for_action", "frugality"],
        "tips": [
            "Every answer must map to a Leadership Principle",
            "Use STAR method with quantifiable results",
            "Expect 'Tell me about a time...' for every principle",
            "System design focuses on scale and reliability",
            "Have 2-3 stories per Leadership Principle",
        ],
        "common_questions": [
            "Tell me about a time you disagreed with a colleague",
            "Design a URL shortener",
            "Tell me about a time you went above and beyond for a customer",
        ],
    },
    "meta": {
        "focus": ["behavioral_star", "coding", "system_design"],
        "culture_values": ["move_fast", "be_bold", "focus_on_impact", "be_open"],
        "tips": [
            "Meta emphasizes speed and impact in answers",
            "Coding interviews expect optimal solutions quickly",
            "System design focuses on scale and data",
            "Behavioral questions probe for ownership and initiative",
            "Practice coding on a whiteboard / shared doc without IDE help",
        ],
        "common_questions": [
            "Tell me about a time you had to make a decision with incomplete data",
            "Design Facebook's news feed",
            "Implement LRU cache",
        ],
    },
    "microsoft": {
        "focus": ["behavioral_star", "system_design", "coding"],
        "culture_values": ["growth_mindset", "customer_focus", "diversity_inclusion", "one_microsoft"],
        "tips": [
            "Emphasize growth mindset and learning from failures",
            "Microsoft values collaboration across teams",
            "System design focuses on enterprise-scale solutions",
            "Show how you handle ambiguity and prioritize",
            "Be ready to discuss impact on customers",
        ],
        "common_questions": [
            "Tell me about a time you helped a colleague",
            "Design a distributed cache",
            "Reverse a linked list",
        ],
    },
    "apple": {
        "focus": ["domain_expertise", "behavioral_star", "coding"],
        "culture_values": ["innovation", "attention_to_detail", "secrecy", "excellence"],
        "tips": [
            "Apple values craftsmanship and attention to detail",
            "Expect domain-specific deep dives",
            "Show passion for the product and user experience",
            "Be prepared for cross-functional questions",
            "Demonstrate how you maintain quality under pressure",
        ],
        "common_questions": [
            "Why Apple?",
            "Design an efficient notification system",
            "Tell me about a time you pushed for quality",
        ],
    },
    "netflix": {
        "focus": ["culture_fit", "system_design", "coding"],
        "culture_values": ["freedom_responsibility", "context_not_control", "high_performance"],
        "tips": [
            "Read the Netflix culture deck before interviewing",
            "Emphasize independent decision-making",
            "Expect questions about handling ambiguous situations",
            "System design focuses on high availability at global scale",
            "Show you can operate with minimal supervision",
        ],
        "common_questions": [
            "Tell me about a time you took significant ownership",
            "Design Netflix's content delivery network",
            "How do you handle technical debt?",
        ],
    },
}

# ---------------------------------------------------------------------------
# Fallback: cover letter templates
# ---------------------------------------------------------------------------

_COVER_TEMPLATES = {
    "professional": (
        "Dear Hiring Manager,\n\n"
        "I am writing to express my interest in the {job_title} position at {company}. "
        "With {experience} years of experience in the field, I am confident that my background "
        "aligns well with the requirements of this role.\n\n"
        "{skills_paragraph}\n\n"
        "{jd_paragraph}\n\n"
        "I am excited about the opportunity to contribute to {company}'s mission and would welcome "
        "the chance to discuss how my experience can benefit your team.\n\n"
        "Thank you for considering my application.\n\n"
        "Sincerely,\n[Your Name]"
    ),
    "conversational": (
        "Hi there,\n\n"
        "I came across the {job_title} role at {company} and it really resonated with me. "
        "I have {experience} years of hands-on experience that I believe makes me a strong fit.\n\n"
        "{skills_paragraph}\n\n"
        "{jd_paragraph}\n\n"
        "I would love to chat about how I can help {company} achieve its goals. "
        "Looking forward to connecting!\n\n"
        "Best,\n[Your Name]"
    ),
    "enthusiastic": (
        "Dear Hiring Manager,\n\n"
        "I am thrilled to apply for the {job_title} position at {company}! "
        "With {experience} years of experience and a genuine passion for this work, "
        "I am eager to bring my skills to your team.\n\n"
        "{skills_paragraph}\n\n"
        "{jd_paragraph}\n\n"
        "I have long admired {company}'s work and would be honored to contribute to "
        "such an innovative organization. I look forward to the opportunity to discuss "
        "my application further.\n\n"
        "Warm regards,\n[Your Name]"
    ),
}


# ---------------------------------------------------------------------------
# Helper: normalise role name for lookups
# ---------------------------------------------------------------------------
def _normalize_role(role: str) -> str:
    normalized = role.lower().replace(" ", "_").replace("-", "_")
    for known in _SALARY_DATA:
        if known in normalized:
            return known
    return "default"


def _experience_tier(years: int) -> str:
    if years <= 2:
        return "entry"
    if years <= 5:
        return "mid"
    if years <= 8:
        return "senior"
    return "staff"


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter()


# ======================= 1. Cover Letter ================================


@router.post("/career/cover-letter")
async def generate_cover_letter(
    body: CoverLetterRequest,
    user: User = Depends(require_authentication),
):
    """Generate a cover letter. Uses AI router when available, falls back to
    template-based generation."""
    if HAS_AI:
        try:
            prompt = (
                f"Generate a {body.tone} cover letter for a {body.job_title} position "
                f"at {body.company}.\n"
                f"Job description: {body.job_description}\n"
                f"Applicant skills: {', '.join(body.user_skills)}\n"
                f"Years of experience: {body.experience_years}\n"
                "Return only the cover letter text."
            )
            result_parts = []
            async for chunk in route_ai_stream(prompt):
                result_parts.append(chunk)
            cover_letter = "".join(result_parts).strip()
            if cover_letter:
                return {
                    "success": True,
                    "cover_letter": cover_letter,
                    "source": "ai",
                }
        except Exception as exc:
            logger.warning("[CoverLetter] AI generation failed, using template: %s", exc)

    # Template-based fallback
    tone = body.tone if body.tone in _COVER_TEMPLATES else "professional"
    template = _COVER_TEMPLATES[tone]

    skills_paragraph = ""
    if body.user_skills:
        top_skills = body.user_skills[:6]
        skills_paragraph = (
            f"My key skills include {', '.join(top_skills[:-1])} and {top_skills[-1]}, "
            f"which I have applied across multiple projects and teams."
        )

    jd_paragraph = ""
    if body.job_description:
        jd_paragraph = (
            f"Reviewing the job description, I see a strong alignment between my experience "
            f"and the needs of the {body.job_title} role at {body.company}. "
            f"I am particularly drawn to the challenges described and am confident in my "
            f"ability to deliver results."
        )

    cover_letter = template.format(
        job_title=body.job_title,
        company=body.company,
        experience=str(body.experience_years),
        skills_paragraph=skills_paragraph,
        jd_paragraph=jd_paragraph,
    )

    return {
        "success": True,
        "cover_letter": cover_letter,
        "source": "template",
    }


# ======================= 2. Resume Tailor ===============================


@router.post("/career/resume-tailor")
async def tailor_resume(
    body: ResumeTailorRequest,
    user: User = Depends(require_authentication),
):
    """Tailor resume for a specific job. Returns tailored bullet points and
    keyword match analysis. Uses AI router when available, falls back to
    keyword matching."""
    if HAS_AI:
        try:
            prompt = (
                f"Tailor the following resume for this job description.\n\n"
                f"Target role: {body.target_role}\n"
                f"Job description:\n{body.job_description}\n\n"
                f"Current resume:\n{body.resume_text}\n\n"
                "Return a JSON object with keys: "
                "'tailored_bullets' (list of rewritten bullet points), "
                "'missing_keywords' (list of keywords from the JD missing in the resume), "
                "'strengths' (list of resume strengths relative to this JD), "
                "'summary_suggestion' (a tailored professional summary)."
            )
            result_parts = []
            async for chunk in route_ai_stream(prompt):
                result_parts.append(chunk)
            ai_result = "".join(result_parts).strip()
            if ai_result:
                return {
                    "success": True,
                    "result": ai_result,
                    "source": "ai",
                }
        except Exception as exc:
            logger.warning("[ResumeTailor] AI generation failed, using keyword match: %s", exc)

    # Keyword-based fallback
    jd_words = set(
        re.sub(r"[^a-z0-9_#+.]", " ", body.job_description.lower()).split()
    )
    resume_words = set(
        re.sub(r"[^a-z0-9_#+.]", " ", body.resume_text.lower()).split()
    )

    # Common tech / skill keywords to look for
    _skill_keywords = {
        "python", "java", "javascript", "typescript", "react", "angular",
        "vue", "node", "aws", "azure", "gcp", "docker", "kubernetes",
        "sql", "nosql", "postgresql", "mongodb", "redis", "graphql",
        "rest", "api", "ci/cd", "git", "agile", "scrum", "kanban",
        "microservices", "terraform", "ansible", "machine", "learning",
        "deep", "tensorflow", "pytorch", "spark", "kafka", "rabbitmq",
        "testing", "jest", "mocha", "selenium", "cypress",
    }

    jd_skills = jd_words & _skill_keywords
    resume_skills = resume_words & _skill_keywords
    missing_skills = sorted(jd_skills - resume_skills)
    matched_skills = sorted(jd_skills & resume_words)

    # Build tailored bullets by finding resume sentences that match JD keywords
    resume_lines = [
        line.strip()
        for line in body.resume_text.split("\n")
        if line.strip() and len(line.strip()) > 20
    ]

    tailored_bullets = []
    for line in resume_lines[:10]:
        line_lower = line.lower()
        overlap = sum(1 for w in jd_words if w in line_lower)
        if overlap >= 2:
            tailored_bullets.append(line)

    # If not enough matched, provide generic suggestions
    if not tailored_bullets:
        tailored_bullets = [
            "Highlight measurable impact with metrics (e.g., 'reduced latency by 40%')",
            "Emphasize experience relevant to the target role",
            "Include keywords from the job description in context",
        ]

    strengths = [
        f"Your resume mentions {skill}" for skill in matched_skills[:5]
    ] or ["Review your resume for relevant keywords to highlight strengths"]

    missing_narrative = (
        f"Consider adding experience with: {', '.join(missing_skills)}"
        if missing_skills
        else "Your resume covers most key skills in the job description."
    )

    summary_suggestion = (
        f"Experienced {body.target_role or 'professional'} with expertise in "
        f"{', '.join(matched_skills[:4])}. "
        f"{'Looking to leverage ' + ', '.join(missing_skills[:3]) + ' skills.' if missing_skills else 'Well-positioned for this role.'}"
    )

    return {
        "success": True,
        "tailored_bullets": tailored_bullets,
        "missing_keywords": missing_skills,
        "strengths": strengths,
        "summary_suggestion": summary_suggestion,
        "keyword_match_count": len(matched_skills),
        "keyword_missing_count": len(missing_skills),
        "source": "keyword_match",
    }


# ======================= 3. Interview Prep ==============================


@router.get("/career/interview-prep/{company}")
async def get_interview_prep(
    company: str,
    user: User = Depends(require_authentication),
):
    """Get interview preparation materials for a specific company.
    Returns common questions, tips, and company-specific advice."""
    company_lower = company.lower().strip()

    # Try AI-powered generation first
    if HAS_AI:
        try:
            prompt = (
                f"Provide interview preparation materials for {company}. Include: "
                "1) Common interview questions (5-10), "
                "2) Company culture and values to highlight, "
                "3) Interview tips specific to this company, "
                "4) Key focus areas for preparation. "
                "Return as structured text."
            )
            result_parts = []
            async for chunk in route_ai_stream(prompt):
                result_parts.append(chunk)
            ai_result = "".join(result_parts).strip()
            if ai_result:
                return {
                    "success": True,
                    "company": company,
                    "prep_materials": ai_result,
                    "source": "ai",
                }
        except Exception as exc:
            logger.warning("[InterviewPrep] AI generation failed, using curated data: %s", exc)

    # Curated data fallback
    tips_data = _COMPANY_TIPS.get(company_lower)
    if tips_data:
        # Build questions from company_questions module if available
        questions = []
        if COMPANY_QUESTIONS_AVAILABLE:
            module_map = {
                "google": "GOOGLE_QUESTIONS",
                "amazon": "AMAZON_QUESTIONS",
                "meta": "META_QUESTIONS",
            }
            q_list_name = module_map.get(company_lower)
            if q_list_name:
                q_list = globals().get(q_list_name, [])
                questions = [
                    {
                        "id": q.id,
                        "question": q.question,
                        "category": q.category.value,
                        "difficulty": q.difficulty.value,
                        "topics": q.topics,
                    }
                    for q in q_list[:15]
                ]

        return {
            "success": True,
            "company": company,
            "focus_areas": tips_data["focus"],
            "culture_values": tips_data["culture_values"],
            "tips": tips_data["tips"],
            "common_questions": tips_data["common_questions"],
            "database_questions": questions,
            "source": "curated",
        }

    # Generic fallback for unknown companies
    generic_prep = {
        "focus": ["behavioral_star", "technical", "role_specific"],
        "culture_values": ["teamwork", "innovation", "impact"],
        "tips": [
            "Research the company's mission and recent news before the interview",
            "Prepare STAR stories for behavioral questions",
            "Practice coding problems relevant to the role",
            "Prepare thoughtful questions about the team and role",
            "Review system design fundamentals if applicable",
        ],
        "common_questions": [
            "Tell me about yourself",
            "Why do you want to work here?",
            "Tell me about a time you faced a challenge at work",
            "Where do you see yourself in 5 years?",
            "What are your strengths and weaknesses?",
        ],
    }

    return {
        "success": True,
        "company": company,
        "focus_areas": generic_prep["focus"],
        "culture_values": generic_prep["culture_values"],
        "tips": generic_prep["tips"],
        "common_questions": generic_prep["common_questions"],
        "note": "Company-specific curated data not available. Showing generic interview prep tips.",
        "source": "generic",
    }


# ======================= 4. Salary Insights =============================


@router.post("/career/salary-insights")
async def get_salary_insights(
    body: SalaryInsightsRequest,
    user: User = Depends(require_authentication),
):
    """Get salary insights based on role, location, and experience.
    Returns estimated compensation range."""
    if HAS_AI:
        try:
            prompt = (
                f"Provide salary insights for a {body.role} in {body.location} "
                f"with {body.experience_years} years of experience. "
                "Include base salary range, total compensation estimate, and key factors. "
                "Return as structured text."
            )
            result_parts = []
            async for chunk in route_ai_stream(prompt):
                result_parts.append(chunk)
            ai_result = "".join(result_parts).strip()
            if ai_result:
                return {
                    "success": True,
                    "role": body.role,
                    "location": body.location,
                    "experience_years": body.experience_years,
                    "insights": ai_result,
                    "source": "ai",
                }
        except Exception as exc:
            logger.warning("[SalaryInsights] AI generation failed, using lookup: %s", exc)

    # Lookup-table fallback
    role_key = _normalize_role(body.role)
    tier = _experience_tier(body.experience_years)
    base_range = _SALARY_DATA.get(role_key, _SALARY_DATA["default"]).get(
        tier, _SALARY_DATA["default"]["mid"]
    )

    location_key = body.location.lower().replace(" ", "_").replace(",", "")
    multiplier = _LOCATION_MULTIPLIER.get(location_key, 1.0)
    # Try partial match
    if multiplier == 1.0:
        for loc_key, loc_mult in _LOCATION_MULTIPLIER.items():
            if loc_key in location_key:
                multiplier = loc_mult
                break

    low = int(base_range[0] * multiplier)
    high = int(base_range[1] * multiplier)

    # Total compensation estimate (base + equity/bonus)
    total_low = int(low * 1.15)
    total_high = int(high * 1.40)

    level_label = tier.replace("_", " ").title()

    return {
        "success": True,
        "role": body.role,
        "location": body.location,
        "experience_years": body.experience_years,
        "level": level_label,
        "base_salary_range": {"low": low, "high": high, "currency": "USD"},
        "total_compensation_range": {"low": total_low, "high": total_high, "currency": "USD"},
        "location_multiplier": multiplier,
        "factors": [
            "Cost of living adjustment",
            "Company size and funding stage",
            "Equity / RSU component",
            "Negotiation leverage from competing offers",
        ],
        "source": "lookup_table",
    }


# ======================= 5. Skill Gaps ==================================


@router.post("/career/skill-gaps")
async def identify_skill_gaps(
    body: SkillGapsRequest,
    user: User = Depends(require_authentication),
):
    """Identify skill gaps between current skills and a target role.
    Returns missing skills and suggested learning resources."""
    if HAS_AI:
        try:
            prompt = (
                f"Identify skill gaps for the role '{body.target_role}'. "
                f"The person's current skills are: {', '.join(body.current_skills)}. "
                "List missing skills with a brief explanation of why each is important, "
                "and suggest specific learning resources (courses, books, projects) for each. "
                "Return as structured text."
            )
            result_parts = []
            async for chunk in route_ai_stream(prompt):
                result_parts.append(chunk)
            ai_result = "".join(result_parts).strip()
            if ai_result:
                return {
                    "success": True,
                    "target_role": body.target_role,
                    "current_skills": body.current_skills,
                    "analysis": ai_result,
                    "source": "ai",
                }
        except Exception as exc:
            logger.warning("[SkillGaps] AI generation failed, using comparison: %s", exc)

    # Comparison-based fallback
    role_key = _normalize_role(body.target_role)
    expected_skills = _ROLE_SKILLS.get(role_key, [])

    current_normalized = {s.lower().replace(" ", "_").replace("-", "_") for s in body.current_skills}

    # Map common aliases
    _ALIASES: Dict[str, str] = {
        "js": "javascript",
        "ts": "typescript",
        "k8s": "kubernetes",
        "aws": "cloud_aws",
        "gcp": "cloud_gcp",
        "azure": "cloud_azure",
        "ml": "machine_learning",
        "dl": "deep_learning",
        "reactjs": "react",
        "vuejs": "vue",
        "nodejs": "node_js",
        "rdbms": "sql",
        "postgres": "postgresql",
    }
    current_normalized = {_ALIASES.get(s, s) for s in current_normalized}

    missing = [s for s in expected_skills if s not in current_normalized]
    matched = [s for s in expected_skills if s in current_normalized]
    extra = sorted(current_normalized - set(expected_skills))

    # Learning resource suggestions per skill
    _LEARNING_RESOURCES: Dict[str, Dict] = {
        "python": {"type": "course", "resource": "Python for Everybody (Coursera)", "effort": "4-6 weeks"},
        "javascript": {"type": "course", "resource": "JavaScript: The Good Parts (book)", "effort": "3-4 weeks"},
        "typescript": {"type": "course", "resource": "TypeScript Handbook (official)", "effort": "2-3 weeks"},
        "react": {"type": "course", "resource": "React Official Tutorial + Epic React (Kent Dodds)", "effort": "4-6 weeks"},
        "system_design": {"type": "book", "resource": "Designing Data-Intensive Applications (Kleppmann)", "effort": "6-8 weeks"},
        "algorithms": {"type": "course", "resource": "LeetCode + Grokking the Coding Interview", "effort": "6-8 weeks"},
        "data_structures": {"type": "course", "resource": "Coursera: Data Structures and Algorithms (UCSD)", "effort": "6-8 weeks"},
        "docker": {"type": "course", "resource": "Docker Official Tutorial + KodeKloud", "effort": "2-3 weeks"},
        "kubernetes": {"type": "course", "resource": "Kubernetes Official Docs + CKA Course", "effort": "4-6 weeks"},
        "cloud_aws": {"type": "cert", "resource": "AWS Solutions Architect Associate", "effort": "8-12 weeks"},
        "terraform": {"type": "course", "resource": "HashiCorp Terraform Associate Certification", "effort": "4-6 weeks"},
        "sql": {"type": "course", "resource": "Mode Analytics SQL Tutorial", "effort": "2-3 weeks"},
        "machine_learning": {"type": "course", "resource": "Andrew Ng's ML Specialization (Coursera)", "effort": "10-12 weeks"},
        "ci_cd": {"type": "project", "resource": "Set up GitHub Actions for a personal project", "effort": "1-2 weeks"},
        "rest_apis": {"type": "course", "resource": "REST API Design (Moz/OWASP guides)", "effort": "2-3 weeks"},
        "testing": {"type": "course", "resource": "Testing Python/JS (pytest / Jest docs)", "effort": "2-3 weeks"},
        "microservices": {"type": "book", "resource": "Building Microservices (Sam Newman)", "effort": "4-6 weeks"},
        "git": {"type": "course", "resource": "Git Official Book (progit)", "effort": "1-2 weeks"},
        "agile": {"type": "course", "resource": "Scrum Guide + Agile Manifesto", "effort": "1-2 weeks"},
        "linux": {"type": "course", "resource": "Linux Foundation: Intro to Linux (edX)", "effort": "3-4 weeks"},
    }

    learning_plan = []
    for skill in missing:
        resource = _LEARNING_RESOURCES.get(skill, {
            "type": "research",
            "resource": f"Search for '{skill.replace('_', ' ')}' tutorials and documentation",
            "effort": "2-4 weeks",
        })
        learning_plan.append({
            "skill": skill,
            **resource,
        })

    match_pct = (len(matched) / len(expected_skills) * 100) if expected_skills else 0

    return {
        "success": True,
        "target_role": body.target_role,
        "current_skills": sorted(body.current_skills),
        "matched_skills": matched,
        "missing_skills": missing,
        "extra_skills": extra[:10],
        "match_percentage": round(match_pct, 1),
        "learning_plan": learning_plan,
        "source": "skill_comparison",
    }