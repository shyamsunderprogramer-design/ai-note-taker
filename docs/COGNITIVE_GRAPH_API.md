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
