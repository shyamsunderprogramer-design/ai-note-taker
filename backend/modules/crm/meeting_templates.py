"""
Meeting Templates Module
Predefined templates for different meeting types
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


def _default_meeting_templates_dir() -> str:
    """Canonical meeting-template storage: backend/data/meeting_templates/.

    Resolved relative to *this* file so the path is stable regardless of
    server CWD. Overridable via the ANT_MEETING_TEMPLATES_DIR env var.
    """
    env_override = os.environ.get("ANT_MEETING_TEMPLATES_DIR")
    if env_override:
        return env_override
    backend_root = Path(__file__).resolve().parent.parent.parent
    return str(backend_root / "data" / "meeting_templates")


@dataclass
class MeetingTemplate:
    id: str
    name: str
    description: str
    category: str
    icon: str
    agenda_items: List[str]
    suggested_questions: List[str]
    duration_minutes: int
    participants: List[str]
    notes_template: str
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


# Predefined meeting templates
DEFAULT_TEMPLATES = [
    # Daily Standup
    MeetingTemplate(
        id="daily-standup",
        name="Daily Standup",
        description="Quick daily sync for team progress updates",
        category="agile",
        icon="🌅",
        agenda_items=[
            "What did you accomplish yesterday?",
            "What are you working on today?",
            "Any blockers or impediments?"
        ],
        suggested_questions=[
            "How can we unblock you?",
            "Do you need any resources?",
            "Any dependencies on other teams?"
        ],
        duration_minutes=15,
        participants=["Scrum Master", "Product Owner", "Development Team"],
        notes_template="""# Daily Standup - {date}

## Attendees
{participants}

## Updates
{agenda_items}

## Blockers
-

## Action Items
- [ ]

## Notes
"""
    ),

    # Sprint Planning
    MeetingTemplate(
        id="sprint-planning",
        name="Sprint Planning",
        description="Plan work for the upcoming sprint",
        category="agile",
        icon="🎯",
        agenda_items=[
            "Review sprint goal and capacity",
            "Discuss and estimate backlog items",
            "Select items for sprint backlog",
            "Define Definition of Done",
            "Team commitment"
        ],
        suggested_questions=[
            "What is our sprint velocity?",
            "Are there any dependencies to consider?",
            "Do we have enough information to start each story?",
            "What risks should we plan for?"
        ],
        duration_minutes=120,
        participants=["Scrum Master", "Product Owner", "Development Team"],
        notes_template="""# Sprint Planning - {date}

## Sprint Goal
{sprint_goal}

## Capacity
- Sprint duration: {sprint_duration}
- Team velocity: {velocity}

## Backlog Items Selected
| Item | Points | Owner |
|------|--------|-------|
| | | |

## Definition of Done
- [ ] Code reviewed
- [ ] Tests written
- [ ] Documentation updated
- [ ] Deployed to staging

## Risks & Dependencies
-

## Action Items
- [ ]
"""
    ),

    # Sprint Retrospective
    MeetingTemplate(
        id="sprint-retrospective",
        name="Sprint Retrospective",
        description="Reflect on the sprint and identify improvements",
        category="agile",
        icon="🔄",
        agenda_items=[
            "Set the stage - Safety check",
            "Gather data - What went well",
            "Gather data - What could be improved",
            "Generate insights - Root cause analysis",
            "Decide actions - Top priorities",
            "Close - Summary and commitment"
        ],
        suggested_questions=[
            "What should we start doing?",
            "What should we stop doing?",
            "What should we continue doing?",
            "What experiments can we try?"
        ],
        duration_minutes=60,
        participants=["Scrum Master", "Development Team"],
        notes_template="""# Sprint Retrospective - {date}

## Safety Check (1-5)
Average: {safety_score}

## What Went Well 🟢
-

## What Could Be Improved 🔴
-

## Action Items
| Action | Owner | Due Date |
|--------|-------|----------|
| | | |

## Experiments to Try
-"""
    ),

    # Sprint Review
    MeetingTemplate(
        id="sprint-review",
        name="Sprint Review",
        description="Demo completed work to stakeholders",
        category="agile",
        icon="👀",
        agenda_items=[
            "Welcome stakeholders",
            "Review sprint goal and completion",
            "Demo completed features",
            "Collect feedback",
            "Update product backlog",
            "Discuss release planning"
        ],
        suggested_questions=[
            "Does this meet your expectations?",
            "What would you like to see next?",
            "Any concerns about the current direction?",
            "Should we prioritize differently?"
        ],
        duration_minutes=60,
        participants=["Product Owner", "Development Team", "Stakeholders"],
        notes_template="""# Sprint Review - {date}

## Sprint Goal
{goal}

## Completed Features
| Feature | Status | Notes |
|---------|--------|-------|
| | | |

## Stakeholder Feedback
-

## Backlog Updates Needed
-

## Release Considerations
-"""
    ),

    # 1:1 Meeting
    MeetingTemplate(
        id="one-on-one",
        name="1:1 Meeting",
        description="Regular one-on-one between manager and direct report",
        category="management",
        icon="👥",
        agenda_items=[
            "Check-in and personal updates",
            "Progress on goals and projects",
            "Challenges and blockers",
            "Career development discussion",
            "Feedback exchange",
            "Action items and next steps"
        ],
        suggested_questions=[
            "How are you feeling about your work?",
            "What would make your job easier?",
            "What are your career goals?",
            "How can I support you better?"
        ],
        duration_minutes=30,
        participants=["Manager", "Direct Report"],
        notes_template="""# 1:1 Meeting - {date}

## Attendees
{attendees}

## Check-in
{personal_updates}

## Goals & Projects
{project_updates}

## Challenges
-

## Career Development
-

## Feedback
- Manager to employee:
- Employee to manager:

## Action Items
- [ ]

## Next Meeting
{next_meeting_date}
"""
    ),

    # Technical Discussion
    MeetingTemplate(
        id="technical-discussion",
        name="Technical Discussion",
        description="Deep dive into technical architecture or design",
        category="technical",
        icon="⚙️",
        agenda_items=[
            "Context and problem statement",
            "Current approach limitations",
            "Proposed solution overview",
            "Technical deep dive",
            "Trade-off analysis",
            "Decision and next steps"
        ],
        suggested_questions=[
            "What are the scalability implications?",
            "How does this affect existing systems?",
            "What are the security considerations?",
            "What is the migration strategy?"
        ],
        duration_minutes=60,
        participants=["Tech Lead", "Senior Engineers", "Architect"],
        notes_template="""# Technical Discussion - {date}

## Problem Statement
{problem}

## Current Approach
{current_approach}

## Proposed Solution
{proposed_solution}

## Trade-offs
| Option | Pros | Cons |
|--------|------|------|
| | | |

## Decision
{decision}

## Action Items
- [ ]

## Follow-up Required
-"""
    ),

    # Code Review
    MeetingTemplate(
        id="code-review",
        name="Code Review Session",
        description="Collaborative code review for complex changes",
        category="technical",
        icon="👁️",
        agenda_items=[
            "Context of the change",
            "Walk through key files",
            "Design pattern review",
            "Edge cases and error handling",
            "Test coverage",
            "Documentation review"
        ],
        suggested_questions=[
            "Is this following our coding standards?",
            "Are there any performance concerns?",
            "How is this handling errors?",
            "Are the tests comprehensive?"
        ],
        duration_minutes=45,
        participants=["Author", "Reviewers"],
        notes_template="""# Code Review - {date}

## PR/Change
{change_reference}

## Context
{context}

## Key Files Reviewed
-

## Findings
### Issues Found 🔴
-

### Suggestions 🟡
-

### Good Practices 🟢
-

## Required Changes
- [ ]

## Approval Status
{status}
"""
    ),

    # Interview Debrief
    MeetingTemplate(
        id="interview-debrief",
        name="Interview Debrief",
        description="Post-interview discussion with hiring team",
        category="hiring",
        icon="🎤",
        agenda_items=[
            "Candidate background review",
            "Technical assessment feedback",
            "Culture fit evaluation",
            "Strengths and concerns",
            "Reference check items",
            "Hiring decision"
        ],
        suggested_questions=[
            "Did they meet the bar?",
            "How did they handle difficult questions?",
            "Would they work well with the team?",
            "Any red flags or concerns?"
        ],
        duration_minutes=30,
        participants=["Hiring Manager", "Interviewers", "Recruiter"],
        notes_template="""# Interview Debrief - {date}

## Candidate
{candidate_name} - {role}

## Interviewers
{interviewers}

## Technical Assessment
{technical_feedback}

## Culture Fit
{culture_fit}

## Strengths
-

## Concerns
-

## Decision
{decision} - {reasoning}

## Next Steps
-
"""
    ),

    # Product Roadmap Review
    MeetingTemplate(
        id="roadmap-review",
        name="Product Roadmap Review",
        description="Quarterly roadmap planning and prioritization",
        category="product",
        icon="🗺️",
        agenda_items=[
            "Market and competitive landscape",
            "Customer feedback summary",
            "Current roadmap status",
            "New opportunities and requests",
            "Prioritization framework",
            "Resource allocation",
            "Commitments and milestones"
        ],
        suggested_questions=[
            "Does this align with our company strategy?",
            "What are the must-haves vs nice-to-haves?",
            "Do we have capacity for these commitments?",
            "What risks should we plan for?"
        ],
        duration_minutes=90,
        participants=["Product Manager", "Engineering Lead", "Design", "Stakeholders"],
        notes_template="""# Roadmap Review - {date}

## Market Context
{market_updates}

## Customer Insights
{feedback_summary}

## Current Status
{roadmap_status}

## Priorities
| Priority | Feature | Timeline | Owner |
|----------|---------|----------|-------|
| P0 | | | |
| P1 | | | |
| P2 | | | |

## Resource Requirements
-

## Key Decisions
-

## Action Items
- [ ]
"""
    ),

    # Incident Post-Mortem
    MeetingTemplate(
        id="incident-postmortem",
        name="Incident Post-Mortem",
        description="Review and learn from production incidents",
        category="operations",
        icon="🔥",
        agenda_items=[
            "Incident timeline",
            "Impact assessment",
            "Root cause analysis",
            "What went well in response",
            "What could be improved",
            "Action items for prevention",
            "Runbook updates"
        ],
        suggested_questions=[
            "When was the issue first detected?",
            "Were alerts timely and clear?",
            "What could have prevented this?",
            "How do we detect this faster next time?"
        ],
        duration_minutes=60,
        participants=["Incident Commander", "On-call Engineers", "Stakeholders"],
        notes_template="""# Post-Mortem - {incident_id}

## Incident Summary
- ID: {incident_id}
- Severity: {severity}
- Duration: {duration}
- Impact: {impact}

## Timeline
| Time | Event |
|------|-------|
| | |

## Root Cause
{root_cause}

## Resolution
{resolution}

## What Went Well
-

## What Could Be Improved
-

## Action Items
| Item | Owner | Due | Priority |
|------|-------|-----|----------|
| | | | |

## Runbook Updates
-"""
    ),

    # Design Review
    MeetingTemplate(
        id="design-review",
        name="Design Review",
        description="Review UX/UI designs before development",
        category="design",
        icon="🎨",
        agenda_items=[
            "User problem and goals",
            "Design solution walkthrough",
            "Interaction patterns",
            "Accessibility considerations",
            "Responsive behavior",
            "Edge cases and error states",
            "Implementation notes"
        ],
        suggested_questions=[
            "Does this solve the user problem?",
            "Is this consistent with our design system?",
            "How does this work on mobile?",
            "Are there accessibility concerns?"
        ],
        duration_minutes=45,
        participants=["Designer", "Product Manager", "Engineering", "UX Research"],
        notes_template="""# Design Review - {date}

## User Problem
{problem}

## Solution Overview
{solution}

## Designs
{design_links}

## Feedback
### Engineering 🟡
-

### Product 🟡
-

### Accessibility 🟡
-

## Required Changes
- [ ]

## Implementation Notes
-

## Approval
{status}
"""
    ),

    # Quarterly Planning
    MeetingTemplate(
        id="quarterly-planning",
        name="Quarterly Planning",
        description="Team quarterly goal setting and planning",
        category="planning",
        icon="📊",
        agenda_items=[
            "Previous quarter review",
            "Company objectives alignment",
            "Key initiatives discussion",
            "Resource planning",
            "OKR drafting",
            "Dependencies identification",
            "Commitments and timeline"
        ],
        suggested_questions=[
            "What are our top 3 priorities?",
            "What could derail us?",
            "What do we need from other teams?",
            "How do we measure success?"
        ],
        duration_minutes=180,
        participants=["Team Lead", "Team Members", "Stakeholders"],
        notes_template="""# Q{quarter} Planning - {year}

## Previous Quarter Review
{previous_review}

## Company Objectives
{company_okrs}

## Team OKRs
| Objective | Key Results | Owner |
|-----------|-------------|-------|
| | | |

## Key Initiatives
| Initiative | Timeline | Dependencies |
|------------|----------|--------------|
| | | |

## Resource Allocation
-

## Risks
-

## Action Items
- [ ]
"""
    ),
]


class MeetingTemplatesManager:
    """Manager for meeting templates"""

    def __init__(self, storage_dir: str = None):
        # Use absolute path derived from this file's location so meeting-
        # template data lives in the same place regardless of server CWD.
        self.storage_dir = storage_dir or _default_meeting_templates_dir()
        self.custom_templates_file = os.path.join(self.storage_dir, "custom_templates.json")
        self.custom_templates: Dict[str, MeetingTemplate] = {}

        os.makedirs(self.storage_dir, exist_ok=True)
        self._load_custom_templates()

    def _load_custom_templates(self):
        """Load custom templates from storage"""
        if os.path.exists(self.custom_templates_file):
            try:
                with open(self.custom_templates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for template_data in data.get('templates', []):
                        template = MeetingTemplate(**template_data)
                        self.custom_templates[template.id] = template
            except Exception as e:
                print(f"[MeetingTemplates] Error loading custom templates: {e}")

    def _save_custom_templates(self):
        """Save custom templates to storage"""
        try:
            data = {
                'templates': [
                    asdict(t) for t in self.custom_templates.values()
                ]
            }
            with open(self.custom_templates_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[MeetingTemplates] Error saving custom templates: {e}")

    def get_all_templates(self) -> List[Dict]:
        """Get all templates (default + custom)"""
        all_templates = []

        # Add default templates
        for template in DEFAULT_TEMPLATES:
            all_templates.append(asdict(template))

        # Add custom templates
        for template in self.custom_templates.values():
            all_templates.append(asdict(template))

        return all_templates

    def get_template_by_id(self, template_id: str) -> Optional[Dict]:
        """Get a specific template by ID"""
        # Check default templates
        for template in DEFAULT_TEMPLATES:
            if template.id == template_id:
                return asdict(template)

        # Check custom templates
        if template_id in self.custom_templates:
            return asdict(self.custom_templates[template_id])

        return None

    def get_templates_by_category(self, category: str) -> List[Dict]:
        """Get templates filtered by category"""
        templates = []

        for template in DEFAULT_TEMPLATES:
            if template.category == category:
                templates.append(asdict(template))

        for template in self.custom_templates.values():
            if template.category == category:
                templates.append(asdict(template))

        return templates

    def get_categories(self) -> List[Dict]:
        """Get all available categories"""
        categories = {}

        for template in DEFAULT_TEMPLATES:
            cat = template.category
            if cat not in categories:
                categories[cat] = {
                    'id': cat,
                    'name': cat.replace('_', ' ').title(),
                    'icon': self._get_category_icon(cat),
                    'count': 0
                }
            categories[cat]['count'] += 1

        for template in self.custom_templates.values():
            cat = template.category
            if cat not in categories:
                categories[cat] = {
                    'id': cat,
                    'name': cat.replace('_', ' ').title(),
                    'icon': self._get_category_icon(cat),
                    'count': 0
                }
            categories[cat]['count'] += 1

        return list(categories.values())

    def _get_category_icon(self, category: str) -> str:
        """Get icon for category"""
        icons = {
            'agile': '🔄',
            'management': '👔',
            'technical': '⚙️',
            'hiring': '👥',
            'product': '📦',
            'operations': '🔧',
            'design': '🎨',
            'planning': '📅',
            'custom': '✨'
        }
        return icons.get(category, '📋')

    def create_custom_template(self, template_data: Dict) -> Dict:
        """Create a new custom template"""
        template_id = template_data.get('id') or f"custom-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        template = MeetingTemplate(
            id=template_id,
            name=template_data.get('name', 'Untitled Template'),
            description=template_data.get('description', ''),
            category=template_data.get('category', 'custom'),
            icon=template_data.get('icon', '✨'),
            agenda_items=template_data.get('agenda_items', []),
            suggested_questions=template_data.get('suggested_questions', []),
            duration_minutes=template_data.get('duration_minutes', 30),
            participants=template_data.get('participants', []),
            notes_template=template_data.get('notes_template', '')
        )

        self.custom_templates[template_id] = template
        self._save_custom_templates()

        return asdict(template)

    def update_template(self, template_id: str, updates: Dict) -> Optional[Dict]:
        """Update a custom template"""
        if template_id not in self.custom_templates:
            return None

        template = self.custom_templates[template_id]

        # Update fields
        for field in ['name', 'description', 'category', 'icon', 'agenda_items',
                      'suggested_questions', 'duration_minutes', 'participants', 'notes_template']:
            if field in updates:
                setattr(template, field, updates[field])

        self._save_custom_templates()
        return asdict(template)

    def delete_template(self, template_id: str) -> bool:
        """Delete a custom template"""
        if template_id in self.custom_templates:
            del self.custom_templates[template_id]
            self._save_custom_templates()
            return True
        return False

    def generate_meeting_notes(self, template_id: str, context: Dict) -> str:
        """Generate meeting notes from template"""
        template = self.get_template_by_id(template_id)
        if not template:
            return "Template not found"

        notes_template = template.get('notes_template', '')

        # Replace placeholders
        notes = notes_template
        for key, value in context.items():
            placeholder = '{' + key + '}'
            notes = notes.replace(placeholder, str(value))

        # Add date if not provided
        if '{date}' in notes:
            from datetime import datetime
            notes = notes.replace('{date}', datetime.now().strftime('%Y-%m-%d'))

        return notes

    def search_templates(self, query: str) -> List[Dict]:
        """Search templates by name or description"""
        query = query.lower()
        results = []

        for template in self.get_all_templates():
            if (query in template.get('name', '').lower() or
                query in template.get('description', '').lower() or
                query in template.get('category', '').lower()):
                results.append(template)

        return results


# Global instance
templates_manager = MeetingTemplatesManager()


# Convenience functions for API
def get_all_templates() -> List[Dict]:
    return templates_manager.get_all_templates()


def get_template(template_id: str) -> Optional[Dict]:
    return templates_manager.get_template_by_id(template_id)


def get_categories() -> List[Dict]:
    return templates_manager.get_categories()


def create_template(template_data: Dict) -> Dict:
    return templates_manager.create_custom_template(template_data)


def update_template(template_id: str, updates: Dict) -> Optional[Dict]:
    return templates_manager.update_template(template_id, updates)


def delete_template(template_id: str) -> bool:
    return templates_manager.delete_template(template_id)


def search_templates(query: str) -> List[Dict]:
    return templates_manager.search_templates(query)


def generate_notes(template_id: str, context: Dict) -> str:
    return templates_manager.generate_meeting_notes(template_id, context)
