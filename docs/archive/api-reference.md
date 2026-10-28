# Backend API reference — historical source records

These are dated source records preserved during documentation consolidation. Their prices, legal statements, feature completion claims, paths, and benchmark numbers have not been revalidated. They are not current setup instructions or release acceptance results.

Current guide: [Backend API reference](../backend/api/API_REFERENCE.md).

## Source index
- [API_REFERENCE.md](#source-api-reference)
- [API_REFERENCE_PHASE2.md](#source-api-reference-phase2)
- [COGNITIVE_GRAPH_API.md](#source-cognitive-graph-api)

<a id="source-api-reference"></a>

## Source: API_REFERENCE.md

<details>
<summary>Read the original source record</summary>

# AI Note Taker API Reference

**Base URL:** `http://localhost:8000`

**Backend:** FastAPI with Neo4j Cognitive Graph Database

---

## Table of Contents

- [Cognitive Graph Endpoints](#cognitive-graph-endpoints)
- [Interview Prediction Endpoints](#interview-prediction-endpoints)
- [Search Endpoints](#search-endpoints)
- [Entity Extraction Endpoints](#entity-extraction-endpoints)
- [Export/Import Endpoints](#exportimport-endpoints)
- [Health & Status Endpoints](#health--status-endpoints)

---

## Cognitive Graph Endpoints

### GET /cognitive-graph/status

Check if the Neo4j cognitive graph is available and connected.

**Parameters:** None

**Response:**
```json
{
  "available": true,
  "connected": true
}
```

**Error Response:**
```json
{
  "available": false,
  "error": "Cognitive graph module not installed"
}
```

**Error Codes:**
- `200 OK` - Status retrieved successfully
- `500 Internal Server Error` - Unexpected error

---

### POST /cognitive-graph/initialize

Initialize the cognitive graph schema (constraints and indexes).

**Request Body:** None

**Response:**
```json
{
  "initialized": true
}
```

**Error Response:**
```json
{
  "error": "Cognitive graph not available"
}
```

**Error Codes:**
- `200 OK` - Schema initialized successfully
- `400 Bad Request` - Cognitive graph not available
- `500 Internal Server Error` - Initialization failed

---

### POST /cognitive-graph/ingest/{conversation_id}

Ingest a conversation into the cognitive graph with full Q&A parsing and entity extraction.

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| conversation_id | string | Yes | Unique conversation identifier |

**Request Body:**
```json
{
  "title": "Senior Backend Engineer Interview",
  "user_id": "user-123",
  "updatedAt": 1712345678901,
  "duration_ms": 3600000,
  "messages": [
    {
      "role": "interviewer",
      "content": "Can you explain how you would design a rate limiter?",
      "timestamp": 1712345679000
    },
    {
      "role": "user",
      "content": "I would use a token bucket algorithm...",
      "timestamp": 1712345680000
    }
  ]
}
```

**Response:**
```json
{
  "ingested": true,
  "conversation_id": "conv-abc-123"
}
```

**Error Response:**
```json
{
  "ingested": false,
  "error": "Cognitive graph not available"
}
```

**Error Codes:**
- `200 OK` - Conversation ingested successfully
- `400 Bad Request` - Invalid request body or cognitive graph unavailable
- `500 Internal Server Error` - Ingestion failed

---

### POST /cognitive-graph/interview

Add a single interview session to the cognitive graph.

**Request Body:**
```json
{
  "id": "interview-001",
  "title": "Frontend Interview - Company X",
  "timestamp": "2024-01-15T14:30:00",
  "duration_ms": 3600000,
  "user_id": "user-123"
}
```

**Response:**
```json
{
  "added": true,
  "interview_id": "interview-001"
}
```

**Error Codes:**
- `200 OK` - Interview added successfully
- `400 Bad Request` - Invalid request body
- `500 Internal Server Error` - Database error

---

### GET /cognitive-graph/history/{user_id}

Get user's interview history from the graph.

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| user_id | string | Yes | User identifier |

**Query Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| limit | integer | No | 100 | Maximum number of interviews to return |

**Response:**
```json
{
  "user_id": "user-123",
  "interviews": [
    {
      "id": "interview-001",
      "title": "Senior Engineer Interview",
      "timestamp": "2024-01-15T14:30:00",
      "duration_ms": 3600000,
      "question_count": 12,
      "companies": ["Google", "Meta"]
    }
  ]
}
```

**Error Codes:**
- `200 OK` - History retrieved successfully
- `400 Bad Request` - Cognitive graph not available
- `404 Not Found` - User not found

---

### GET /cognitive-graph/company/{company_name}

Get insights about questions asked by a specific company.

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| company_name | string | Yes | Company name (e.g., "Google", "Meta") |

**Response:**
```json
{
  "company": "Google",
  "insights": {
    "company": "Google",
    "total_questions": 45,
    "categories": ["technical", "system_design", "behavioral"],
    "common_topics": ["algorithms", "distributed systems", "machine learning"],
    "avg_confidence": 0.78
  }
}
```

**Error Codes:**
- `200 OK` - Insights retrieved successfully
- `400 Bad Request` - Cognitive graph not available
- `404 Not Found` - Company not found

---

### GET /cognitive-graph/skill/{user_id}/{skill_name}

Track user's progression on a specific skill over time.

**Path Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| user_id | string | Yes | User identifier |
| skill_name | string | Yes | Skill name (e.g., "Python", "System Design") |

**Response:**
```json
{
  "user_id": "user-123",
  "skill": "Python",
  "progression": [
    {
      "date": "2024-01-15T14:30:00",
      "proficiency": 0.7,
      "context": "Explain list comprehensions"
    },
    {
      "date": "2024-02-01T10:00:00",
      "proficiency": 0.85,
      "context": "Design a context manager"
    }
  ]
}
```

**Error Codes:**
- `200 OK` - Progression data retrieved successfully
- `400 Bad Request` - Cognitive graph not available
- `404 Not Found` - User or skill not found

---

### GET /cognitive-graph/stats

Get statistics about the cognitive graph.

**Parameters:** None

**Response:**
```json
{
  "interviews": 25,
  "questions": 150,
  "answers": 140,
  "companies": 8,
  "topics": 45,
  "skills": 30
}
```

**Error Codes:**
- `200 OK` - Stats retrieved successfully
- `400 Bad Request` - Cognitive graph not available

---

### POST /cognitive-graph/backfill

Backfill all historical conversations into the cognitive graph.

**Request Body:** None

**Response:**
```json
{
  "backfill_triggered": true,
  "return_code": 0,
  "output": "Processed 25 conversations...",
  "errors": ""
}
```

**Error Response:**
```json
{
  "error": "Backfill failed: timeout"
}
```

**Error Codes:**
- `200 OK` - Backfill completed successfully
- `500 Internal Server Error` - Backfill process failed

---

## Interview Prediction Endpoints

### GET /predict/questions

Get predicted interview questions for a company/role combination.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| company | string | Yes | Company name (e.g., "Google", "Meta") |
| role | string | No | Job role (e.g., "Senior Software Engineer") |
| limit | integer | No | Maximum number of predictions (default: 10) |

**Response:**
```json
{
  "company": "Google",
  "role": "Senior Software Engineer",
  "predictions": [
    {
      "question": "Implement a LRU cache",
      "difficulty": "medium",
      "frequency": 0.9,
      "category": "technical",
      "likelihood": 0.95
    },
    {
      "question": "Design a URL shortener",
      "difficulty": "medium",
      "frequency": 0.85,
      "category": "system_design",
      "likelihood": 0.88
    }
  ],
  "confidence": 0.8,
  "stats": {
    "total_questions_in_db": 45,
    "categories_covered": ["technical", "system_design", "behavioral"],
    "role_pattern_applied": true
  }
}
```

**Error Response:**
```json
{
  "company": "UnknownCorp",
  "role": "Engineer",
  "predictions": [],
  "confidence": 0.0,
  "message": "No data available for this company"
}
```

**Error Codes:**
- `200 OK` - Predictions retrieved successfully
- `400 Bad Request` - Missing required parameters
- `500 Internal Server Error` - Prediction engine error

---

### GET /predict/checklist

Get a preparation checklist for an interview.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| company | string | Yes | Company name |
| role | string | No | Job role |

**Response:**
```json
{
  "company": "Google",
  "role": "Senior Software Engineer",
  "predictions_summary": {
    "company": "Google",
    "role": "Senior Software Engineer",
    "predictions": [...],
    "confidence": 0.8
  },
  "checklist": {
    "technical_prep": [
      "Review data structures: arrays, trees, graphs, hash maps",
      "Practice 5 medium/hard LeetCode problems",
      "Review time/space complexity analysis",
      "Prepare to explain your thought process out loud"
    ],
    "system_design_prep": [
      "Review system design fundamentals (load balancing, caching, databases)",
      "Practice designing a scalable web application",
      "Study trade-offs between different architectures",
      "Prepare diagrams to explain your design"
    ],
    "behavioral_prep": [
      "Prepare 5 STAR-format stories (Situation, Task, Action, Result)",
      "Review leadership principles (if applicable to company)",
      "Prepare questions to ask the interviewer",
      "Research company culture and recent news"
    ],
    "company_specific": [
      "Research Google's products and tech stack",
      "Review Google's engineering blog",
      "Check recent Glassdoor interview experiences"
    ],
    "likely_technical": [
      "Practice: Implement a LRU cache",
      "Practice: Find the k largest elements in an array"
    ],
    "likely_system_design": [
      "Outline: Design a URL shortener"
    ]
  },
  "estimated_prep_time": "4-7 days"
}
```

**Error Codes:**
- `200 OK` - Checklist generated successfully
- `400 Bad Request` - Missing required parameters
- `500 Internal Server Error` - Prediction engine error

---

### GET /predict/companies

Get list of companies with prediction data available.

**Parameters:** None

**Response:**
```json
{
  "companies": [
    "Google", "Meta", "Amazon", "Netflix", "Microsoft",
    "Apple", "Uber", "Airbnb", "LinkedIn", "Twitter",
    "Stripe", "Lyft", "DoorDash", "Instacart", "Coinbase",
    "Robinhood", "OpenAI", "Anthropic", "Snowflake", "Databricks",
    "Salesforce", "Oracle", "Adobe", "Shopify", "Spotify",
    "Dropbox", "Slack", "Zoom", "TikTok", "Snapchat",
    "Pinterest", "Reddit"
  ],
  "total": 32
}
```

**Error Codes:**
- `200 OK` - Company list retrieved successfully
- `500 Internal Server Error` - Prediction module error

---

## Search Endpoints

### GET /cognitive-graph/search

Semantic search across interview history.

**Query Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| q | string | Yes | - | Search query |
| limit | integer | No | 10 | Maximum results to return |

**Response:**
```json
{
  "query": "rate limiter",
  "results": [
    {
      "question_id": "conv-123-q0",
      "question": "How would you design a rate limiter?",
      "answer": "I would use a token bucket algorithm...",
      "category": "system_design",
      "difficulty": "medium",
      "topics": ["distributed systems", "api design"],
      "company": "Google",
      "date": "2024-01-15T14:30:00",
      "relevance": 10
    }
  ],
  "count": 1
}
```

**Scoring Strategy:**
- Question text match: 10 points
- Answer text match: 8 points
- Transcript match: 6 points
- Topic match: 9 points
- Company match: 7 points
- Skill match: 8 points

**Error Codes:**
- `200 OK` - Search completed successfully
- `400 Bad Request` - Missing query parameter or cognitive graph unavailable

---

### GET /cognitive-graph/search/advanced

Advanced search with multiple filters.

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | string | No | Text to search for |
| company | string | No | Filter by company name |
| topic | string | No | Filter by topic |
| category | string | No | Filter by category: `technical`, `behavioral`, `system_design`, `knowledge` |
| difficulty | string | No | Filter by difficulty: `easy`, `medium`, `hard` |
| date_from | string | No | Filter from date (ISO 8601 format) |
| date_to | string | No | Filter to date (ISO 8601 format) |
| limit | integer | No | Maximum results (default: 50) |

**Response:**
```json
{
  "filters": {
    "query": "distributed",
    "company": "Google",
    "topic": null,
    "category": "system_design",
    "difficulty": "hard",
    "date_from": "2024-01-01",
    "date_to": "2024-12-31"
  },
  "results": [
    {
      "question_id": "conv-456-q1",
      "question": "Design a distributed key-value store",
      "answer": "I would consider consistency models...",
      "category": "system_design",
      "difficulty": "hard",
      "topics": ["distributed systems", "databases"],
      "company": "Google",
      "date": "2024-02-15T10:00:00"
    }
  ],
  "count": 1
}
```

**Error Codes:**
- `200 OK` - Search completed successfully
- `400 Bad Request` - Invalid filter parameters

---

## Entity Extraction Endpoints

### POST /extract-entities

Extract entities (companies, topics, skills, roles) from text.

**Request Body:**
```json
{
  "text": "I'm interviewing for a Senior Software Engineer role at Google. The interview focused on Python, system design, and distributed systems."
}
```

**Response:**
```json
{
  "text": "I'm interviewing for a Senior Software Engineer role at Google...",
  "entities": {
    "companies": [
      {"text": "google", "confidence": 0.9}
    ],
    "topics": [
      {"text": "system design", "confidence": 0.85},
      {"text": "distributed system", "confidence": 0.85}
    ],
    "skills": [
      {"text": "python", "confidence": 0.9}
    ],
    "roles": [
      {"text": "senior software engineer", "confidence": 0.85}
    ],
    "category": {
      "label": "general",
      "confidence": 0.5
    },
    "difficulty": null,
    "entities_found": 5
  }
}
```

**Error Codes:**
- `200 OK` - Entities extracted successfully
- `400 Bad Request` - No text provided or entity extraction unavailable

---

### POST /process-transcript

Process a transcript into Q&A pairs with extracted entities.

**Request Body:**
```json
{
  "transcript": "What is your experience with Python?\nI have 5 years of Python experience including Django and Flask.\nCan you explain decorators?\nDecorators are functions that modify other functions..."
}
```

**Response:**
```json
{
  "qa_pairs": [
    {
      "question": "What is your experience with Python?",
      "answer": "I have 5 years of Python experience including Django and Flask.",
      "entities": {
        "companies": [],
        "topics": [],
        "skills": [
          {"text": "python", "confidence": 0.9},
          {"text": "django", "confidence": 0.9},
          {"text": "flask", "confidence": 0.9}
        ],
        "roles": [],
        "category": {"label": "technical", "confidence": 0.6},
        "difficulty": null,
        "entities_found": 3
      }
    }
  ],
  "count": 2,
  "transcript_length": 150
}
```

**Error Codes:**
- `200 OK` - Transcript processed successfully
- `400 Bad Request` - No transcript provided

---

### GET /extract/categorize

Categorize a question (technical, behavioral, system_design, knowledge).

**Query Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| q | string | Yes | Question to categorize |

**Response:**
```json
{
  "question": "Tell me about a time you had to learn something quickly",
  "category": {
    "label": "behavioral",
    "confidence": 0.8
  },
  "difficulty": {
    "label": "medium",
    "confidence": 0.7
  }
}
```

**Categories:**
- `technical` - Coding, algorithms, data structures
- `system_design` - Architecture, scalability
- `behavioral` - Experience, teamwork
- `knowledge` - Concepts, explanations
- `general` - Uncategorized

**Error Codes:**
- `200 OK` - Question categorized successfully
- `400 Bad Request` - Missing question parameter

---

## Export/Import Endpoints

### POST /conversations/export

Export a conversation in various formats.

**Request Body:**
```json
{
  "conversation": {
    "id": "conv-123",
    "title": "Interview",
    "messages": [...],
    "createdAt": 1712345678901,
    "updatedAt": 1712345678901
  },
  "format": "json"
}
```

**Supported Formats:** `json`, `txt`, `markdown`

**Response (JSON format):**
```json
{
  "content": "{...exported JSON...}",
  "filename": "conversation-2024-01-15.json"
}
```

**Response (TXT format):**
```json
{
  "content": "Interview\n=========\n...",
  "filename": "conversation-2024-01-15.txt"
}
```

**Error Codes:**
- `200 OK` - Export successful
- `400 Bad Request` - Invalid format or missing conversation

---

### POST /conversations/import

Import conversations from a JSON file.

**Request Body:** (multipart/form-data)
- `file`: JSON file containing conversation data

**Response:**
```json
{
  "imported": 5,
  "conversations": ["conv-1", "conv-2", "conv-3", "conv-4", "conv-5"],
  "errors": []
}
```

**Error Response:**
```json
{
  "error": "Invalid JSON file",
  "imported": 0,
  "conversations": [],
  "errors": ["Line 45: Invalid character"]
}
```

**Error Codes:**
- `200 OK` - Import successful
- `400 Bad Request` - Invalid file format
- `500 Internal Server Error` - Processing error

---

## Health & Status Endpoints

### GET /health

Check if the backend is running.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T14:30:00Z"
}
```

---

### GET /

Root endpoint returning API information.

**Response:**
```json
{
  "name": "AI Note Taker Backend",
  "version": "1.0.0",
  "status": "running"
}
```

---

## Data Models

### Interview Node

```json
{
  "id": "interview-001",
  "title": "Frontend Interview",
  "timestamp": "2024-01-15T14:30:00",
  "duration_ms": 3600000,
  "user_id": "user-123"
}
```

### Question Node

```json
{
  "id": "q-001",
  "text": "How would you design a rate limiter?",
  "category": "system_design",
  "difficulty": "medium",
  "company_id": "comp-google"
}
```

### Answer Node

```json
{
  "id": "a-001",
  "text": "I would use a token bucket algorithm...",
  "transcript": "Full transcript including thinking process",
  "confidence": 0.85
}
```

### Company Node

```json
{
  "id": "comp-google",
  "name": "Google",
  "industry": "Technology",
  "size": "10000+"
}
```

### Topic Node

```json
{
  "id": "topic-001",
  "name": "distributed systems",
  "category": "technical"
}
```

### Skill Node

```json
{
  "id": "skill-001",
  "name": "Python",
  "proficiency": "expert"
}
```

---

## Neo4j Schema

### Node Types
- `Interview` - Interview session
- `Question` - Interview questions
- `Answer` - User answers
- `Company` - Companies
- `Role` - Job roles
- `Topic` - Technical topics
- `Skill` - Skills demonstrated

### Relationships
- `(Interview)-[:CONTAINS]->(Question)`
- `(Question)-[:ANSWERED_WITH]->(Answer)`
- `(Question)-[:ASKED_BY]->(Company)`
- `(Question)-[:RELATED_TO]->(Topic)`
- `(Answer)-[:DEMONSTRATES]->(Skill)`

### Indexes & Constraints
- Unique constraints on all node IDs
- Indexes on `Interview.timestamp`
- Indexes on `Company.name`
- Indexes on `Topic.name`
- Indexes on `Skill.name`

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEO4J_URI` | Neo4j connection URI | `bolt://localhost:7687` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | `password` |

---

## Error Response Format

All errors follow this format:

```json
{
  "error": "Error message description",
  "detail": "Optional additional details"
}
```

## Common HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200 OK` | Request successful |
| `400 Bad Request` | Invalid request parameters |
| `404 Not Found` | Resource not found |
| `422 Unprocessable Entity` | Validation error |
| `500 Internal Server Error` | Server error |

</details>

<a id="source-api-reference-phase2"></a>

## Source: API_REFERENCE_PHASE2.md

<details>
<summary>Read the original source record</summary>

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

</details>

<a id="source-cognitive-graph-api"></a>

## Source: COGNITIVE_GRAPH_API.md

<details>
<summary>Read the original source record</summary>

# Cognitive Graph API Documentation

## Overview

The Cognitive Graph API provides a personal knowledge graph for interview history. It stores interview sessions, questions, answers, companies, topics, and skills in a Neo4j graph database, enabling semantic search and relationship-based queries.

**Base URL:** `http://localhost:8000/cognitive-graph`

---

## Status Endpoints

### GET `/cognitive-graph/status`

Check if Neo4j cognitive graph is available and connected.

**Response:**
```json
{
  "available": true,
  "connected": true
}
```

**Error Response:**
```json
{
  "available": false,
  "error": "Cognitive graph module not installed"
}
```

---

### POST `/cognitive-graph/initialize`

Initialize the Neo4j schema (constraints and indexes).

**Response:**
```json
{
  "initialized": true
}
```

**Creates:**
- Unique constraints on Interview, Question, Company, Role, Topic, Skill IDs
- Indexes on timestamps, names for faster queries

---

## Search & Query

### GET `/cognitive-graph/search`

Semantic search across interview history.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| q | string | Yes | Search query |
| limit | int | No | Max results (default: 10) |

**Example:**
```
GET /cognitive-graph/search?q=algorithm&limit=5
```

**Response:**
```json
{
  "query": "algorithm",
  "results": [
    {
      "question_id": "q-123",
      "question": "Explain quick sort algorithm",
      "answer": "Quick sort is a divide and conquer algorithm...",
      "topics": ["algorithms", "sorting"],
      "company": "Google"
    }
  ],
  "count": 1
}
```

---

### GET `/cognitive-graph/history/{user_id}`

Get user's interview history from graph.

**Path Parameters:**
| Parameter | Description |
|-----------|-------------|
| user_id | User identifier |

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 100 | Max interviews to return |

**Example:**
```
GET /cognitive-graph/history/user123?limit=10
```

**Response:**
```json
{
  "user_id": "user123",
  "interviews": [
    {
      "id": "int-456",
      "title": "Google Interview",
      "timestamp": "2024-01-15T10:30:00",
      "duration_ms": 3600000,
      "question_count": 5,
      "companies": ["Google"]
    }
  ]
}
```

---

### GET `/cognitive-graph/company/{company_name}`

Get insights about questions asked by a company.

**Example:**
```
GET /cognitive-graph/company/Google
```

**Response:**
```json
{
  "company": "Google",
  "insights": {
    "company": "Google",
    "total_questions": 12,
    "categories": ["technical", "system_design"],
    "common_topics": ["algorithms", "distributed systems"],
    "avg_confidence": 0.75
  }
}
```

---

### GET `/cognitive-graph/skill/{user_id}/{skill_name}`

Track user's progression on a specific skill over time.

**Example:**
```
GET /cognitive-graph/skill/user123/python
```

**Response:**
```json
{
  "user_id": "user123",
  "skill": "python",
  "progression": [
    {
      "date": "2024-01-01",
      "proficiency": 0.6,
      "context": "Explain list comprehensions"
    },
    {
      "date": "2024-02-15",
      "proficiency": 0.85,
      "context": "Implement a decorator"
    }
  ]
}
```

---

## Data Ingestion

### POST `/cognitive-graph/ingest/{conversation_id}`

Ingest a conversation into the cognitive graph.

**Request Body:**
```json
{
  "title": "Google Interview",
  "user_id": "user123",
  "updatedAt": 1705315800000,
  "duration_ms": 3600000,
  "messages": [
    {"role": "interviewer", "content": "Tell me about yourself"},
    {"role": "user", "content": "I have 5 years experience..."}
  ]
}
```

**Response:**
```json
{
  "ingested": true,
  "conversation_id": "conv-789"
}
```

---

### POST `/cognitive-graph/interview`

Add a new interview to the graph.

**Request Body:**
```json
{
  "id": "int-001",
  "title": "Meta Onsite Interview",
  "timestamp": "2024-01-15T14:30:00",
  "duration_ms": 5400000,
  "user_id": "user123"
}
```

**Response:**
```json
{
  "added": true,
  "interview_id": "int-001"
}
```

---

## Entity Extraction Endpoints

### POST `/extract-entities`

Extract entities (companies, topics, skills) from text.

**Request Body:**
```json
{
  "text": "What is your experience with React and Docker at Google?"
}
```

**Response:**
```json
{
  "text": "What is your experience with React and Docker at Google?...",
  "entities": {
    "companies": [{"text": "google", "confidence": 0.9}],
    "topics": [{"text": "docker", "confidence": 0.85}],
    "skills": [
      {"text": "react", "confidence": 0.9},
      {"text": "docker", "confidence": 0.9}
    ],
    "roles": [],
    "category": {"label": "technical", "confidence": 0.7},
    "difficulty": null,
    "entities_found": 3
  }
}
```

---

### POST `/process-transcript`

Process a transcript into Q&A pairs with extracted entities.

**Request Body:**
```json
{
  "transcript": "Interviewer: Tell me about yourself.\nCandidate: I have 5 years of Python experience.\nInterviewer: What's your experience with React?"
}
```

**Response:**
```json
{
  "qa_pairs": [
    {
      "question": "Tell me about yourself.",
      "answer": "I have 5 years of Python experience.",
      "entities": { ... }
    },
    {
      "question": "What's your experience with React?",
      "answer": "",
      "entities": { ... }
    }
  ],
  "count": 2,
  "transcript_length": 145
}
```

---

### GET `/extract/categorize`

Categorize a question (technical, behavioral, system_design, knowledge).

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| q | Yes | Question text to categorize |

**Example:**
```
GET /extract/categorize?q=Design%20a%20URL%20shortener
```

**Response:**
```json
{
  "question": "Design a URL shortener",
  "category": {"label": "system_design", "confidence": 0.9},
  "difficulty": {"label": "hard", "confidence": 0.7}
}
```

---

## Node Types

### InterviewNode
- `id`: Unique identifier
- `title`: Interview title
- `timestamp`: When interview occurred
- `duration_ms`: Duration in milliseconds
- `user_id`: User who conducted interview

### QuestionNode
- `id`: Unique identifier
- `text`: Question text
- `category`: technical, behavioral, system_design, knowledge
- `difficulty`: easy, medium, hard (optional)
- `company_id`: Which company asked (optional)

### AnswerNode
- `id`: Unique identifier
- `text`: Answer text
- `transcript`: Full transcript including thinking process
- `confidence`: Confidence score (0.0-1.0)

### CompanyNode
- `id`: Unique identifier
- `name`: Company name
- `industry`: Industry (optional)
- `size`: Company size (optional)

### RoleNode
- `id`: Unique identifier
- `title`: Role title
- `level`: junior, mid, senior, staff, principal (optional)
- `department`: Department (optional)

### TopicNode
- `id`: Unique identifier
- `name`: Topic name
- `category`: algorithm, database, system-design, etc.

### SkillNode
- `id`: Unique identifier
- `name`: Skill name
- `proficiency`: beginner, intermediate, expert (optional)

---

## Relationship Types

| Relationship | From | To | Description |
|--------------|------|-----|-------------|
| CONTAINS | Interview | Question | Interview contains this question |
| ANSWERED_WITH | Question | Answer | Question was answered with |
| ASKED_BY | Question | Company | Question asked by company |
| RELATED_TO | Question | Topic | Question related to topic |
| FOR_ROLE | Interview | Role | Interview for this role |
| DEMONSTRATES | Answer | Skill | Answer demonstrates skill |

---

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200` - Success
- `400` - Bad Request (missing parameters)
- `500` - Server Error (Neo4j not connected, etc.)

**Common Error Response:**
```json
{
  "error": "Cognitive graph not available",
  "message": "Neo4j connection failed"
}
```

---

## Python Client Example

```python
import requests

BASE_URL = "http://localhost:8000"

# Check status
response = requests.get(f"{BASE_URL}/cognitive-graph/status")
print(response.json())

# Initialize schema
response = requests.post(f"{BASE_URL}/cognitive-graph/initialize")
print(response.json())

# Search
response = requests.get(f"{BASE_URL}/cognitive-graph/search?q=python")
print(response.json())

# Extract entities
text = "What's your experience with Kubernetes at Google?"
response = requests.post(f"{BASE_URL}/extract-entities", json={"text": text})
print(response.json())
```

---

## Environment Variables

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

</details>
