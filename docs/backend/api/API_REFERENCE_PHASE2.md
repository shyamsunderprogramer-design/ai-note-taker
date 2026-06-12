# Phase 2 API Reference

Complete API documentation for Phase 2 features.

**Base URL:** `http://127.0.0.1:8000`

---

## Real-Time Suggestions API

### POST /realtime/process
Process a transcript segment and return suggestion if relevant.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| text | string | Yes | Transcript text segment |
| speaker | string | Yes | `"user"` or `"interviewer"` |
| conversation_id | string | No | Optional conversation ID |

**Response:**
```json
{
  "has_suggestion": true,
  "suggestion": {
    "id": "sugg-0",
    "type": "similar_question",
    "content": "You've seen a similar question before...",
    "confidence": 0.75,
    "relevance_score": 0.8,
    "context": {...}
  }
}
```

### POST /realtime/command
Process voice commands during interview.

**Supported Commands:**
- `"what did i say about X"` - Search history
- `"remind me about X"` - Get past answers
- `"give me a hint"` - Request suggestion

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| text | string | Yes | Voice command text |
| conversation_id | string | No | Optional conversation ID |

**Response:**
```json
{
  "action": "search_results",
  "query": "React",
  "results": [...]
}
```

---

## Conversation Analysis API

### POST /analyze/conversation
Analyze a conversation for auto-tagging and quality metrics.

**Request Body:**
```json
{
  "id": "conv-123",
  "title": "Google Interview",
  "messages": [
    {"role": "user", "content": "Tell me about yourself"},
    {"role": "assistant", "content": "I am a software engineer..."}
  ]
}
```

**Response:**
```json
{
  "tags": {
    "conversation_type": "mock_interview",
    "focus_areas": ["behavioral", "technical"],
    "quality_tier": "good"
  },
  "quality_metrics": {
    "overall_score": 75,
    "completeness": 80,
    "technical_depth": 70,
    "clarity": 75
  },
  "recommendations": [
    "Add more specific examples",
    "Include quantifiable results"
  ]
}
```

### GET /analyze/types
Get supported conversation types.

**Response:**
```json
{
  "types": [
    {"id": "practice_session", "label": "Practice Session"},
    {"id": "mock_interview", "label": "Mock Interview"},
    {"id": "real_interview", "label": "Real Interview"}
  ]
}
```

---

## Performance Analysis API

### POST /performance/analyze
Analyze an interview answer for STAR method, code quality, and speaking patterns.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| answer_text | string | Yes | The answer to analyze |
| question_type | string | No | `"behavioral"`, `"technical"`, `"system_design"` |

**Response:**
```json
{
  "answer_length": 500,
  "word_count": 85,
  "question_type": "behavioral",
  "star_analysis": {
    "has_situation": true,
    "has_task": true,
    "has_action": true,
    "has_result": false,
    "completeness_score": 0.75,
    "components_found": 3
  },
  "code_quality": {
    "has_code": false,
    "code_blocks": 0,
    "language": null,
    "complexity_score": 0.0,
    "best_practices_score": 0.0
  },
  "speaking_patterns": {
    "word_count": 85,
    "sentence_count": 6,
    "avg_words_per_sentence": 14.2,
    "filler_word_count": 2,
    "filler_word_ratio": 2.4,
    "pace_assessment": "good"
  },
  "overall_score": 72.5,
  "quality_tier": "good",
  "recommendations": [
    "Include quantifiable results",
    "Reduce filler words"
  ],
  "strengths": ["Strong STAR structure"],
  "weaknesses": ["Missing result component"]
}
```

### POST /performance/analyze-batch
Analyze multiple answers in batch.

**Request Body:**
```json
{
  "answers": [
    {"text": "...", "type": "behavioral"},
    {"text": "...", "type": "technical"}
  ]
}
```

### GET /performance/tiers
Get quality tier thresholds.

**Response:**
```json
{
  "excellent": {"min_score": 80, "description": "Excellent answer quality"},
  "good": {"min_score": 65, "description": "Good with minor improvements"},
  "average": {"min_score": 50, "description": "Average, needs work"},
  "needs_improvement": {"min_score": 0, "description": "Needs substantial improvement"}
}
```

---

## Analytics Dashboard API

### GET /analytics/dashboard/{user_id}
Get dashboard summary with key metrics.

**Response:**
```json
{
  "user_id": "default",
  "summary": {
    "total_interviews": 15,
    "current_streak": 5,
    "total_skills": 12,
    "improving_count": 8
  },
  "top_skills": [...],
  "recommendations": ["Review these skills: System Design"]
}
```

### GET /analytics/skill-progression/{user_id}
Get skill progression over time.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| skill | string | Yes | Skill name |
| months | int | No | Number of months (default: 6) |

**Response:**
```json
{
  "skill": "React",
  "data_points": [
    {"month": "2025-10", "mentions": 3, "confidence": 0.65},
    {"month": "2025-11", "mentions": 5, "confidence": 0.75}
  ],
  "overall_trend": 0.1,
  "trend_direction": "up"
}
```

### GET /analytics/topic-network/{user_id}
Get topic co-occurrence network for visualization.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| min_connections | int | No | Minimum connections (default: 2) |

**Response:**
```json
{
  "nodes": [
    {"id": "React", "name": "React", "group": "frontend", "size": 15}
  ],
  "edges": [
    {"source": "React", "target": "Hooks", "weight": 5}
  ]
}
```

### GET /analytics/interview-calendar/{user_id}
Get interview frequency data for calendar heatmap.

**Response:**
```json
{
  "daily_activity": {
    "2025-11-01": 2,
    "2025-11-02": 1
  },
  "total_interviews": 15,
  "current_streak": 5,
  "longest_streak": 8
}
```

---

## Study Plan API

### POST /study-plan/generate
Generate personalized study plan.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| user_id | string | Yes | User identifier |
| days | int | No | Plan duration (default: 30) |
| daily_minutes | int | No | Daily study target (default: 60) |

**Response:**
```json
{
  "user_id": "default",
  "duration_days": 30,
  "progress": {
    "total_tasks": 45,
    "completed_tasks": 0,
    "percentage": 0
  },
  "weak_areas": [
    {"name": "Dynamic Programming", "confidence": 0.3}
  ],
  "milestones": [
    {"name": "Foundation Complete", "target_date": "2026-04-15"}
  ],
  "sessions": [
    {
      "date": "2026-04-05",
      "theme": "Algorithm Fundamentals",
      "tasks": [...]
    }
  ]
}
```

### GET /study-plan/{user_id}
Get current study plan.

### GET /study-plan/{user_id}/today
Get today's study session.

### POST /study-plan/{user_id}/complete-task
Mark task as complete.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| task_id | string | Yes | Task ID |
| performance_score | float | No | Rating 0.0-1.0 |

### POST /study-plan/{user_id}/export
Export study plan.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| format | string | Yes | `"json"`, `"ical"`, `"markdown"` |

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "error": "Description of what went wrong"
}
```

**Common HTTP Status Codes:**
| Code | Meaning |
|------|---------|
| 200 | Success |
| 422 | Validation error |
| 500 | Internal server error |

---

## Testing

Run the test suite:

```bash
# All Phase 2 tests
python -m pytest backend/tests/ -v

# Specific module
python -m pytest backend/tests/test_realtime_suggestions.py -v
python -m pytest backend/tests/test_performance_analyzer.py -v
python -m pytest backend/tests/test_study_plan_generator.py -v
```

---

*Last Updated: 2026-04-05*
