# Neo4j Database Schema Documentation

## Overview

The AI Note Taker uses Neo4j as its graph database to store interview history, questions, answers, and their relationships in a semantic knowledge graph. This document describes the complete database schema including node types, relationships, constraints, indexes, and example queries.

---

## Node Types

### Interview
Represents an interview session.

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Unique identifier (UUID) |
| `title` | String | Interview title |
| `timestamp` | DateTime | When the interview occurred |
| `duration_ms` | Integer | Duration in milliseconds |
| `user_id` | String | Reference to the user |

**Labels:** `:Interview`

---

### Question
Represents a question asked during an interview.

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Unique identifier (UUID) |
| `text` | String | The question text |
| `category` | String | Question category (technical, behavioral, system-design, etc.) |
| `difficulty` | String | Optional difficulty level (easy, medium, hard) |
| `company_id` | String | Optional reference to company ID |

**Labels:** `:Question`

---

### Answer
Represents an answer provided to a question.

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Unique identifier (UUID) |
| `text` | String | The answer text |
| `transcript` | String | Full transcript including thinking process |
| `confidence` | Float | Confidence score (0.0 - 1.0) |

**Labels:** `:Answer`

---

### Company
Represents a company that conducted interviews.

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Unique identifier |
| `name` | String | Company name (unique) |
| `industry` | String | Optional industry sector |
| `size` | String | Optional company size |

**Labels:** `:Company`

---

### Topic
Represents a technical topic related to questions.

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Unique identifier |
| `name` | String | Topic name (unique) |
| `category` | String | Topic category (algorithm, database, system-design, etc.) |

**Labels:** `:Topic`

---

### Skill
Represents a skill demonstrated in answers.

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Unique identifier |
| `name` | String | Skill name (unique) |
| `proficiency` | String | Optional proficiency level (beginner, intermediate, expert) |

**Labels:** `:Skill`

---

### Role
Represents a job role.

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Unique identifier |
| `title` | String | Job title |
| `level` | String | Optional level (junior, mid, senior, staff, principal) |
| `department` | String | Optional department |

**Labels:** `:Role`

---

## Relationships

### Core Relationships

| Relationship | From | To | Description |
|--------------|------|----|-------------|
| `CONTAINS` | Interview | Question | Links interview to its questions |
| `ANSWERED_WITH` | Question | Answer | Links question to its answer |
| `ASKED_BY` | Question | Company | Links question to the asking company |
| `RELATED_TO` | Question | Topic | Links question to related topics |
| `DEMONSTRATES` | Answer | Skill | Links answer to demonstrated skills |
| `FOR_ROLE` | Interview | Role | Links interview to the role being interviewed for |

---

## Constraints

Unique constraints ensure data integrity:

```cypher
// Interview ID uniqueness
CREATE CONSTRAINT interview_id IF NOT EXISTS 
FOR (i:Interview) REQUIRE i.id IS UNIQUE

// Question ID uniqueness
CREATE CONSTRAINT question_id IF NOT EXISTS 
FOR (q:Question) REQUIRE q.id IS UNIQUE

// Company ID uniqueness
CREATE CONSTRAINT company_id IF NOT EXISTS 
FOR (c:Company) REQUIRE c.id IS UNIQUE

// Role ID uniqueness
CREATE CONSTRAINT role_id IF NOT EXISTS 
FOR (r:Role) REQUIRE r.id IS UNIQUE

// Topic ID uniqueness
CREATE CONSTRAINT topic_id IF NOT EXISTS 
FOR (t:Topic) REQUIRE t.id IS UNIQUE

// Skill ID uniqueness
CREATE CONSTRAINT skill_id IF NOT EXISTS 
FOR (s:Skill) REQUIRE s.id IS UNIQUE
```

---

## Indexes

Performance indexes for common queries:

```cypher
// Interview timestamp for chronological queries
CREATE INDEX interview_timestamp IF NOT EXISTS 
FOR (i:Interview) ON (i.timestamp)

// Company name for lookups
CREATE INDEX company_name IF NOT EXISTS 
FOR (c:Company) ON (c.name)

// Topic name for category queries
CREATE INDEX topic_name IF NOT EXISTS 
FOR (t:Topic) ON (t.name)

// Skill name for skill-based queries
CREATE INDEX skill_name IF NOT EXISTS 
FOR (s:Skill) ON (s.name)
```

---

## Example Cypher Queries

### Find All Questions for a Company

```cypher
// Get all questions asked by a specific company
MATCH (c:Company {name: $company_name})<-[:ASKED_BY]-(q:Question)
OPTIONAL MATCH (q)-[:ANSWERED_WITH]->(a:Answer)
OPTIONAL MATCH (q)-[:RELATED_TO]->(t:Topic)
RETURN q.id AS question_id,
       q.text AS question,
       q.category AS category,
       q.difficulty AS difficulty,
       a.text AS answer,
       collect(DISTINCT t.name) AS topics
ORDER BY q.category
```

### Search by Topic

```cypher
// Find all questions related to a specific topic
MATCH (t:Topic {name: $topic_name})<-[:RELATED_TO]-(q:Question)
OPTIONAL MATCH (q)-[:ANSWERED_WITH]->(a:Answer)
OPTIONAL MATCH (q)-[:ASKED_BY]->(c:Company)
OPTIONAL MATCH (i:Interview)-[:CONTAINS]->(q)
RETURN q.text AS question,
       a.text AS answer,
       c.name AS company,
       i.timestamp AS date
ORDER BY i.timestamp DESC
```

### Get Interview History

```cypher
// Get user's interview history with statistics
MATCH (i:Interview {user_id: $user_id})
OPTIONAL MATCH (i)-[:CONTAINS]->(q:Question)
OPTIONAL MATCH (q)-[:ASKED_BY]->(c:Company)
WITH i, count(q) AS question_count, collect(DISTINCT c.name) AS companies
RETURN i.id AS id,
       i.title AS title,
       i.timestamp AS timestamp,
       i.duration_ms AS duration_ms,
       question_count,
       companies
ORDER BY i.timestamp DESC
LIMIT $limit
```

### Get Company Insights

```cypher
// Get insights about questions asked by a company
MATCH (c:Company {name: $company_name})<-[:ASKED_BY]-(q:Question)
OPTIONAL MATCH (q)-[:RELATED_TO]->(t:Topic)
OPTIONAL MATCH (q)-[:ANSWERED_WITH]->(a:Answer)
RETURN c.name AS company,
       count(DISTINCT q) AS total_questions,
       collect(DISTINCT q.category) AS categories,
       collect(DISTINCT t.name) AS common_topics,
       avg(a.confidence) AS avg_confidence
```

### Semantic Search

```cypher
// Search across questions, answers, topics, and companies
CALL {
    // Search in question text (highest score)
    MATCH (q:Question)-[:ANSWERED_WITH]->(a:Answer)
    WHERE q.text CONTAINS $keyword
    WITH q, a, 10 AS score
    RETURN q, a, score
    
    UNION
    
    // Search in answer text
    MATCH (q:Question)-[:ANSWERED_WITH]->(a:Answer)
    WHERE a.text CONTAINS $keyword
    WITH q, a, 8 AS score
    RETURN q, a, score
    
    UNION
    
    // Search in transcript
    MATCH (q:Question)-[:ANSWERED_WITH]->(a:Answer)
    WHERE a.transcript CONTAINS $keyword
    WITH q, a, 6 AS score
    RETURN q, a, score
    
    UNION
    
    // Search by topic
    MATCH (t:Topic)
    WHERE t.name CONTAINS $keyword
    MATCH (t)<-[:RELATED_TO]-(q:Question)-[:ANSWERED_WITH]->(a:Answer)
    WITH q, a, 9 AS score
    RETURN q, a, score
    
    UNION
    
    // Search by company
    MATCH (c:Company)
    WHERE c.name CONTAINS $keyword
    MATCH (c)<-[:ASKED_BY]-(q:Question)-[:ANSWERED_WITH]->(a:Answer)
    WITH q, a, 7 AS score
    RETURN q, a, score
    
    UNION
    
    // Search by skill
    MATCH (s:Skill)
    WHERE s.name CONTAINS $keyword
    MATCH (s)<-[:DEMONSTRATES]-(a:Answer)<-[:ANSWERED_WITH]-(q:Question)
    WITH q, a, 8 AS score
    RETURN q, a, score
}
WITH q, a, max(score) AS relevance
ORDER BY relevance DESC
LIMIT $limit
OPTIONAL MATCH (q)-[:RELATED_TO]->(t:Topic)
OPTIONAL MATCH (q)-[:ASKED_BY]->(c:Company)
OPTIONAL MATCH (i:Interview)-[:CONTAINS]->(q)
RETURN DISTINCT 
    q.id AS question_id,
    q.text AS question,
    a.text AS answer,
    q.category AS category,
    q.difficulty AS difficulty,
    collect(DISTINCT t.name) AS topics,
    c.name AS company,
    i.timestamp AS date,
    relevance
ORDER BY relevance DESC
```

### Get Skill Progression

```cypher
// Track user's progress on a specific skill over time
MATCH (i:Interview {user_id: $user_id})-[:CONTAINS]->(q:Question)
      -[:ANSWERED_WITH]->(a:Answer)-[:DEMONSTRATES]->(s:Skill {name: $skill_name})
RETURN i.timestamp AS date,
       a.confidence AS proficiency,
       q.text AS context
ORDER BY i.timestamp
```

### Advanced Search with Filters

```cypher
// Multi-filter search
MATCH (q:Question)-[:ANSWERED_WITH]->(a:Answer)
OPTIONAL MATCH (q)-[:ASKED_BY]->(c:Company)
OPTIONAL MATCH (q)-[:RELATED_TO]->(t:Topic)
OPTIONAL MATCH (i:Interview)-[:CONTAINS]->(q)
WHERE ($query IS NULL OR q.text CONTAINS $query OR a.text CONTAINS $query)
  AND ($company IS NULL OR c.name = $company)
  AND ($topic IS NULL OR t.name = $topic)
  AND ($category IS NULL OR q.category = $category)
  AND ($difficulty IS NULL OR q.difficulty = $difficulty)
  AND ($date_from IS NULL OR i.timestamp >= datetime($date_from))
  AND ($date_to IS NULL OR i.timestamp <= datetime($date_to))
RETURN q.id AS question_id,
       q.text AS question,
       a.text AS answer,
       q.category AS category,
       q.difficulty AS difficulty,
       collect(DISTINCT t.name) AS topics,
       c.name AS company,
       i.timestamp AS date
ORDER BY i.timestamp DESC
LIMIT $limit
```

### Entity Extraction Query

```cypher
// Extract entities mentioned in a question
MATCH (q:Question {id: $question_id})
OPTIONAL MATCH (q)-[:ASKED_BY]->(c:Company)
OPTIONAL MATCH (q)-[:RELATED_TO]->(t:Topic)
OPTIONAL MATCH (q)-[:ANSWERED_WITH]->(a:Answer)
OPTIONAL MATCH (a)-[:DEMONSTRATES]->(s:Skill)
OPTIONAL MATCH (i:Interview)-[:CONTAINS]->(q)
OPTIONAL MATCH (i)-[:FOR_ROLE]->(r:Role)
RETURN {
    question: q.text,
    company: c.name,
    topics: collect(DISTINCT t.name),
    skills: collect(DISTINCT s.name),
    role: r.title,
    category: q.category,
    difficulty: q.difficulty
} AS extracted_entities
```

### Create Interview with Q&A

```cypher
// Create a complete interview record with Q&A
CREATE (i:Interview {
    id: $interview_id,
    title: $title,
    timestamp: datetime(),
    duration_ms: $duration_ms,
    user_id: $user_id
})
WITH i
UNWIND $qa_pairs AS qa
CREATE (q:Question {
    id: qa.question_id,
    text: qa.question_text,
    category: qa.category,
    difficulty: qa.difficulty
})
CREATE (a:Answer {
    id: qa.answer_id,
    text: qa.answer_text,
    transcript: qa.transcript,
    confidence: qa.confidence
})
CREATE (i)-[:CONTAINS]->(q)
CREATE (q)-[:ANSWERED_WITH]->(a)
WITH q, a, qa
CALL apoc.do.when(qa.company_name IS NOT NULL,
    'MERGE (c:Company {name: qa.company_name}) CREATE (q)-[:ASKED_BY]->(c)',
    '',
    {q: q, qa: qa}
) YIELD value
RETURN count(*) AS created
```

---

## Data Class Definitions (Python)

Reference implementation from `backend/cognitive_graph.py`:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class InterviewNode:
    id: str
    title: str
    timestamp: datetime
    duration_ms: int
    user_id: str

@dataclass
class QuestionNode:
    id: str
    text: str
    category: str
    difficulty: Optional[str] = None
    company_id: Optional[str] = None

@dataclass
class AnswerNode:
    id: str
    text: str
    transcript: str
    confidence: float = 0.0

@dataclass
class CompanyNode:
    id: str
    name: str
    industry: Optional[str] = None
    size: Optional[str] = None

@dataclass
class RoleNode:
    id: str
    title: str
    level: Optional[str] = None
    department: Optional[str] = None

@dataclass
class TopicNode:
    id: str
    name: str
    category: str

@dataclass
class SkillNode:
    id: str
    name: str
    proficiency: Optional[str] = None
```

---

## Schema Initialization

To initialize the schema, run:

```python
from backend.cognitive_graph import initialize_graph

# Creates all constraints and indexes
success = initialize_graph()
```

Or execute the constraints and indexes manually via Neo4j Browser.

---

## Notes

- All IDs should be UUIDs or unique strings
- Timestamps use Neo4j's `datetime()` type
- Optional properties may be `NULL` if not provided
- The graph supports bi-directional traversal for all relationships
- Confidence scores range from 0.0 to 1.0
