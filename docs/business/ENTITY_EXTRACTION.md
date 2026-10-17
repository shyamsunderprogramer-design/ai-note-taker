# Entity Extraction Documentation

## Overview

The Entity Extraction module provides NLP capabilities to extract structured information from interview transcripts. It uses rule-based extraction (no ML models required) to identify companies, technical topics, skills, roles, and categorize questions.

**File:** `backend/entity_extraction.py`

---

## Features

### Extracted Entity Types

| Entity Type | Description | Examples |
|-------------|-------------|----------|
| **Companies** | Tech companies mentioned | Google, Meta, Amazon, Netflix |
| **Technical Topics** | CS/system design concepts | algorithms, databases, microservices |
| **Skills** | Programming languages, frameworks | Python, React, Kubernetes |
| **Roles** | Job positions | Software Engineer, Product Manager |
| **Categories** | Question classification | technical, behavioral, system_design |
| **Difficulty** | Question difficulty | easy, medium, hard |

---

## Supported Entities

### Companies (100+ supported)

**FAANG + Major Tech:**
- Google, Meta, Facebook, Amazon, Apple, Netflix
- Microsoft, LinkedIn, Twitter/X, Uber, Lyft, Airbnb
- Stripe, Square, Coinbase, Robinhood, DoorDash
- OpenAI, Anthropic, Hugging Face

**Enterprise:**
- Oracle, Salesforce, SAP, Adobe, Cisco
- Snowflake, Databricks, Datadog

**Global:**
- TikTok/ByteDance, Snap, Pinterest, Reddit

### Technical Topics (80+ supported)

**Algorithms:**
- Data structures: arrays, linked lists, trees, graphs
- Techniques: dynamic programming, recursion, BFS, DFS
- Complexity: Big O, time/space complexity

**System Design:**
- Architecture: microservices, distributed systems
- Databases: SQL, NoSQL, sharding, replication
- Caching: Redis, CDN, load balancers
- Messaging: Kafka, RabbitMQ, event-driven
- Cloud: AWS, GCP, Azure, Docker, Kubernetes

**Frontend:**
- Frameworks: React, Vue, Angular
- Core: HTML, CSS, JavaScript, TypeScript

**DevOps:**
- CI/CD: Jenkins, GitHub Actions
- IaC: Terraform, Ansible
- Monitoring: Prometheus, Grafana

### Skills (100+ supported)

**Languages:**
- Python, Java, JavaScript, TypeScript
- C++, Go, Rust, Ruby, Swift, Kotlin
- Scala, Clojure, Haskell, Elixir

**Frameworks:**
- Python: Django, Flask, FastAPI
- JavaScript: Node.js, Express, Next.js
- Java: Spring, Spring Boot
- ML: TensorFlow, PyTorch, scikit-learn

**Tools & Platforms:**
- Git, Docker, Kubernetes
- AWS, GCP, Azure
- Linux, Bash, Vim

### Roles (20+ supported)

- Software Engineer, Senior Software Engineer
- Staff Engineer, Principal Engineer
- Engineering Manager, Tech Lead, CTO
- Product Manager, Data Scientist, ML Engineer
- DevOps Engineer, SRE, Security Engineer
- Frontend Engineer, Backend Engineer, Fullstack Engineer

---

## API Usage

### Extract All Entities

```python
from entity_extraction import extract_entities

text = "What is your experience with React and Docker at Google?"
result = extract_entities(text)

print(result)
```

**Output:**
```json
{
  "companies": [
    {"text": "google", "confidence": 0.9}
  ],
  "topics": [
    {"text": "docker", "confidence": 0.85}
  ],
  "skills": [
    {"text": "react", "confidence": 0.9},
    {"text": "docker", "confidence": 0.9}
  ],
  "roles": [],
  "category": {
    "label": "technical",
    "confidence": 0.7
  },
  "difficulty": null,
  "entities_found": 3
}
```

---

### Process Transcript

```python
from entity_extraction import process_transcript

transcript = """
Interviewer: Tell me about a time you faced a conflict in your team.
Candidate: I once had a disagreement about code review standards...
Interviewer: How would you optimize a slow database query?
Candidate: I would start by adding indexes...
"""

qa_pairs = process_transcript(transcript)
print(qa_pairs)
```

**Output:**
```json
[
  {
    "question": "Tell me about a time you faced a conflict in your team.",
    "answer": "I once had a disagreement about code review standards...",
    "entities": { ... }
  },
  {
    "question": "How would you optimize a slow database query?",
    "answer": "I would start by adding indexes...",
    "entities": { ... }
  }
]
```

---

### Individual Methods

```python
from entity_extraction import entity_extractor

# Extract specific entity types
companies = entity_extractor.extract_companies(text)
topics = entity_extractor.extract_topics(text)
skills = entity_extractor.extract_skills(text)
roles = entity_extractor.extract_roles(text)

# Categorize question
category, confidence = entity_extractor.categorize_question(
    "Design a distributed cache"
)
# Returns: ("system_design", 0.9)

# Estimate difficulty
difficulty, confidence = entity_extractor.estimate_difficulty(
    "Optimize this complex algorithm"
)
# Returns: ("hard", 0.7)
```

---

## HTTP API Endpoints

### POST `/extract-entities`

Extract entities from text.

**Request:**
```bash
curl -X POST http://localhost:8000/extract-entities \
  -H "Content-Type: application/json" \
  -d '{"text": "Experience with Kubernetes at Google?"}'
```

**Response:**
```json
{
  "text": "Experience with Kubernetes at Google?",
  "entities": { ... }
}
```

---

### POST `/process-transcript`

Process transcript into Q&A pairs.

**Request:**
```bash
curl -X POST http://localhost:8000/process-transcript \
  -H "Content-Type: application/json" \
  -d '{"transcript": "Q: What is Python? A: A programming language."}'
```

**Response:**
```json
{
  "qa_pairs": [...],
  "count": 1,
  "transcript_length": 44
}
```

---

### GET `/extract/categorize`

Categorize a question.

**Request:**
```bash
curl "http://localhost:8000/extract/categorize?q=Design%20a%20chat%20app"
```

**Response:**
```json
{
  "question": "Design a chat app",
  "category": {"label": "system_design", "confidence": 0.9},
  "difficulty": {"label": "hard", "confidence": 0.7}
}
```

---

## Question Categories

| Category | Keywords | Example |
|----------|----------|---------|
| **technical** | algorithm, coding, optimize, complexity | "Implement binary search" |
| **system_design** | design, architecture, scale, distributed | "Design Twitter" |
| **behavioral** | tell me, describe, conflict, leadership | "Tell me about yourself" |
| **knowledge** | what is, how does, explain, difference | "What is REST?" |

---

## Difficulty Indicators

| Difficulty | Keywords |
|------------|----------|
| **easy** | simple, basic, beginner, fundamental |
| **medium** | moderate, typical, standard, average |
| **hard** | difficult, complex, advanced, challenging, optimize, trade-off |

**Auto-detection:** Questions mentioning "optimize", "trade-off", "distributed", or "scale" are marked as hard.

---

## Adding Custom Entities

To add new companies, topics, or skills:

```python
# In entity_extraction.py, add to the sets:

COMPANY_NAMES = {
    # ... existing ...
    "your-company",  # Add here
}

TECHNICAL_TOPICS = {
    # ... existing ...
    "your-topic",
}

SKILLS = {
    # ... existing ...
    "your-skill",
}
```

---

## Performance

- **Extraction Speed:** ~1ms per query (rule-based, no ML inference)
- **Memory:** Minimal (static lookup sets)
- **No GPU Required:** Pure Python regex matching

---

## Future Enhancements

Potential improvements (not yet implemented):

1. **spaCy Integration:** Use spaCy NER for better entity recognition
2. **Custom ML Model:** Train domain-specific model on interview data
3. **Coreference Resolution:** Link "it"/"they" to actual entities
4. **Relationship Extraction:** "Used X for Y" patterns
5. **Sentiment Analysis:** Detect confidence in answers
