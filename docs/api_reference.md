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
