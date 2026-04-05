# Phase 2: Real-Time Intelligence & Analytics

## Overview

Phase 2 builds on the Cognitive Graph foundation to deliver real-time interview assistance and deeper insights through analytics.

**Goal**: Transform AI Note Taker from a passive notepad into an active interview coach.

---

## Task Breakdown

### Task #28: Real-Time Suggestion Engine
**Objective**: Provide contextual hints during live interviews without being distracting.

**Features**:
- Listen to interviewer questions in real-time
- Query cognitive graph for similar past questions
- Show subtle suggestion cards in the sidebar
- Support voice-activated queries ("What did I say about React?")

**Implementation**:
```python
# New file: backend/realtime_suggestions.py
class RealtimeSuggestionEngine:
    def __init__(self):
        self.cognitive_graph = cognitive_graph
        
    def on_transcript_segment(self, text: str, speaker: str) -> Optional[Dict]:
        """Called every 3-5 seconds during interview"""
        if self.is_question(text):
            matches = self.cognitive_graph.semantic_search(text, limit=3)
            if matches:
                return {
                    "type": "similar_question",
                    "matches": matches,
                    "confidence": self.calculate_relevance(text, matches)
                }
        return None
```

**UI Components**:
- Collapsible suggestion panel
- Keyboard shortcut: `Ctrl+Shift+S` to toggle
- Confidence threshold slider in settings

**Estimate**: 3-4 days

---

### Task #29: Enhanced Entity Extraction (ML-Based)
**Objective**: Improve extraction accuracy from current ~70% to >90%.

**Current**: Rule-based with regex patterns
**Phase 2**: Hybrid approach with lightweight ML

**Implementation**:
```python
# Enhance entity_extraction.py
class HybridEntityExtractor:
    def __init__(self):
        self.rule_based = EntityExtractor()  # Existing
        self.ml_model = self._load_spacy_ner()  # New
        
    def extract_all(self, text: str) -> Dict:
        # Combine both approaches
        rule_results = self.rule_based.extract_all(text)
        ml_results = self.ml_model(text)
        
        # Merge with confidence weighting
        return self.merge_results(rule_results, ml_results)
```

**Models to Evaluate**:
- spaCy NER (en_core_web_sm) - 40MB
- DistilBERT-NER - 250MB
- Custom fine-tuned model on interview transcripts

**Training Data**:
- Use existing ingested conversations as training set
- Label companies, skills, topics manually (500 samples)

**Estimate**: 4-5 days

---

### Task #30: Conversation Auto-Categorization
**Objective**: Automatically tag conversations by type and quality.

**Auto-Tagging Categories**:
| Tag | Detection Method |
|-----|------------------|
| `practice_session` | Self-identified via keywords |
| `mock_interview` | Multiple speakers detected |
| `real_interview` | Company name + "interview" in title |
| `system_design_focus` | >50% questions are system design |
| `algorithm_heavy` | >70% technical questions |
| `behavioral_only` | Only behavioral questions |

**Quality Metrics**:
```python
class ConversationAnalyzer:
    def analyze_quality(self, conversation: Dict) -> Dict:
        return {
            "completeness": self._check_answer_completeness(),
            "technical_depth": self._analyze_code_complexity(),
            "clarity_score": self._analyze_speech_patterns(),
            "areas_for_improvement": self._identify_gaps()
        }
```

**Estimate**: 2-3 days

---

### Task #31: Graph Analytics Dashboard
**Objective**: Visual insights from the knowledge graph.

**Visualizations**:

1. **Skill Progression Timeline**
   - Line chart showing confidence per skill over time
   - Identify trending skills (improving vs declining)

2. **Company Comparison Matrix**
   - Heatmap of question categories by company
   - Compare difficulty distributions

3. **Topic Network Graph**
   - D3.js force-directed graph
   - Nodes = topics, Edges = co-occurrence in interviews
   - Discover hidden connections (e.g., "React" ↔ "Hooks" ↔ "Performance")

4. **Interview Frequency Calendar**
   - GitHub-style contribution graph
   - Show practice streaks and consistency

**Implementation**:
```javascript
// New file: renderer/analytics-dashboard.js
// Using Chart.js or D3.js for visualizations

// API endpoints to add:
GET /analytics/skill-progression?user_id={id}&skill={name}
GET /analytics/company-heatmap
GET /analytics/topic-network
GET /analytics/interview-calendar
```

**Estimate**: 4-5 days

---

### Task #32: Interview Performance Insights
**Objective**: Compare your answers against best practices.

**Features**:
- Pattern matching for STAR method (Situation, Task, Action, Result)
- Code quality scoring (if technical interview)
- Speaking pace analysis (too fast/slow)
- Filler word tracking

**Implementation**:
```python
class PerformanceAnalyzer:
    def analyze_answer_structure(self, answer: str) -> Dict:
        """Check if answer follows STAR method"""
        return {
            "has_situation": self._detect_section(answer, "situation"),
            "has_task": self._detect_section(answer, "task"),
            "has_action": self._detect_section(answer, "action"),
            "has_result": self._detect_section(answer, "result"),
            "completeness_score": calculate_completeness()
        }
```

**Estimate**: 3-4 days

---

### Task #33: Personalized Study Plan Generator
**Objective**: AI-generated preparation roadmap based on gaps.

**Input**:
- Target company/role
- Current skill levels (from cognitive graph)
- Time until interview

**Output**:
- Daily/weekly practice schedule
- Prioritized topic list
- Resource recommendations (LeetCode problems, system design videos)
- Progress tracking

**Implementation**:
```python
class StudyPlanGenerator:
    def generate_plan(
        self,
        target_company: str,
        target_role: str,
        weeks_available: int,
        user_id: str
    ) -> Dict:
        # Analyze current state
        current_skills = self.cognitive_graph.get_skill_progression(user_id)
        
        # Get requirements for target
        required_skills = self.get_company_requirements(target_company, target_role)
        
        # Calculate gaps
        gaps = self.calculate_gaps(current_skills, required_skills)
        
        # Generate schedule
        return self.create_schedule(gaps, weeks_available)
```

**Estimate**: 3-4 days

---

## Phase 2 Timeline

| Week | Tasks | Deliverable |
|------|-------|-------------|
| 1 | #28 Real-Time Suggestions | Working suggestion engine with toggle |
| 2 | #29 ML Entity Extraction | Hybrid extractor with >90% accuracy |
| 3 | #30 Auto-Categorization + #32 Performance | Auto-tagged conversations + STAR analysis |
| 4 | #31 Analytics Dashboard | 4 visualization screens |
| 5 | #33 Study Plan + Polish | Full study plan feature, bug fixes |

**Total Duration**: 5 weeks (flexible)

---

## Success Metrics

| Metric | Phase 1 (Current) | Phase 2 Target |
|--------|-------------------|----------------|
| Entity Extraction Accuracy | ~70% | >90% |
| Query Response Time | ~200ms | <100ms |
| Suggestion Relevance | N/A | >80% user finds helpful |
| Active Users (weekly) | Baseline | +30% |

---

## Technical Considerations

### Performance
- Real-time suggestions must not impact transcription latency
- Consider WebWorkers for client-side ML inference
- Cache common queries in memory

### Privacy
- ML models must run locally (no cloud inference)
- User data stays in Neo4j on their machine
- Optional: Allow users to disable real-time analysis

### Dependencies
```
# New requirements
spacy>=3.7.0
en-core-web-sm>=3.7.0  # NER model
chart.js>=4.4.0       # Analytics visualizations
d3>=7.8.0             # Network graphs
```

---

## Open Questions

1. Should real-time suggestions be voice-activated or always-on?
2. Do we need user feedback mechanism for suggestion quality?
3. Should study plans sync with calendar (Google/Outlook)?
4. How to handle multiple interview prep simultaneously?

---

## Next Steps

1. Review plan with stakeholders
2. Prioritize tasks based on user feedback from Phase 1
3. Set up spaCy and download NER models
4. Create feature branches for each task
5. Start with Task #28 (Real-Time Suggestions) as MVP

---

*Document Version: 1.0*
*Last Updated: 2026-04-05*
*Author: Claude + User*
