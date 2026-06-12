# Cognitive Graph Setup Guide

## Overview

This guide walks you through setting up the Cognitive Graph feature, which uses Neo4j to store and query your interview history.

---

## Prerequisites

- Python 3.8+
- pip package manager
- Java 17+ (for Neo4j local installation)

---

## Option 1: Neo4j Docker (Recommended for Development)

### Install Docker

**Windows:**
```powershell
winget install Docker.DockerDesktop
```

**macOS:**
```bash
brew install --cask docker
```

**Linux:**
```bash
sudo apt-get install docker.io docker-compose
```

### Run Neo4j

```bash
docker run -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

**Access:**
- Browser: http://localhost:7474
- Bolt Port: 7687
- Default Login: `neo4j` / `password`

---

## Option 2: Neo4j Desktop (Recommended for Users)

### Download

1. Go to https://neo4j.com/download/
2. Download Neo4j Desktop
3. Install and create a new project

### Create Database

1. Open Neo4j Desktop
2. Click "New" → "Create a Local Graph"
3. Set password: `password`
4. Start the database

**Default Port:** 7687

---

## Option 3: Neo4j AuraDB (Cloud - No Setup)

### Sign Up

1. Go to https://neo4j.com/cloud/
2. Create free AuraDB account
3. Create new instance

### Get Connection Details

1. In AuraDB console, click "Connect"
2. Copy the Bolt URI
3. Note the username and password

### Configure Environment

```bash
export NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=your-password
```

---

## Option 4: Windows Local Installation

### Install Java

1. Download Java 17+ from https://adoptium.net/
2. Install and set `JAVA_HOME`

### Install Neo4j Community

```powershell
# Download and extract
$url = "https://neo4j.com/artifact.php?name=neo4j-community-5.26.4-windows.zip"
Invoke-WebRequest -Uri $url -OutFile neo4j.zip
Expand-Archive neo4j.zip -DestinationPath C:\neo4j

# Start Neo4j
C:\neo4j\bin\neo4j.bat console
```

---

## Python Dependencies

### Install Required Packages

```bash
pip install neo4j==5.28.1 spacy==3.8.4
```

Or from requirements:
```bash
pip install -r requirements.txt
```

---

## Configuration

### Environment Variables

Create `.env` file or set environment variables:

```bash
# Default (local Neo4j)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# AuraDB (cloud)
# NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
# NEO4J_PASSWORD=your-password
```

### Verify Installation

```python
# test_connection.py
from cognitive_graph import cognitive_graph

# Check connection
if cognitive_graph.driver:
    print("✅ Connected to Neo4j")
else:
    print("❌ Connection failed")
```

---

## Initialize Schema

### Via API

```bash
# Start backend first
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000

# Initialize schema
curl -X POST http://localhost:8000/cognitive-graph/initialize
```

### Via Python

```python
from cognitive_graph import initialize_graph

success = initialize_graph()
print(f"Schema initialized: {success}")
```

**Creates:**
- Unique constraints on all node IDs
- Indexes on timestamps and names

---

## Testing the Connection

### Check Status

```bash
curl http://localhost:8000/cognitive-graph/status
```

**Expected Response:**
```json
{
  "available": true,
  "connected": true
}
```

### Test Search

```bash
curl "http://localhost:8000/cognitive-graph/search?q=test&limit=1"
```

---

## Troubleshooting

### "Unable to determine the path to java.exe"

**Fix:** Install Java 17+ and set JAVA_HOME

```powershell
# Windows
[Environment]::SetEnvironmentVariable("JAVA_HOME", "C:\Program Files\Java\jdk-17", "Machine")
```

### "Failed to establish connection"

**Check:**
1. Is Neo4j running? `docker ps` or check Neo4j Desktop
2. Are ports open? `telnet localhost 7687`
3. Credentials correct?

### "Cognitive graph module not installed"

**Fix:**
```bash
pip install neo4j spacy
```

### "Authentication failed"

**Reset password:**
1. Stop Neo4j
2. Delete `data/dbms/auth` file
3. Restart and use default `neo4j/password`

### Port Already in Use

```bash
# Find process using port 7687
lsof -i :7687  # macOS/Linux
netstat -ano | findstr :7687  # Windows

# Stop Neo4j or use different port
docker run -p 7474:7474 -p 7688:7687 ...  # Use 7688
```

---

## Quick Start Commands

```bash
# 1. Start Neo4j (Docker)
docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest

# 2. Install dependencies
pip install neo4j spacy

# 3. Start backend
cd backend
python -m uvicorn main:app --reload

# 4. Initialize schema
curl -X POST http://localhost:8000/cognitive-graph/initialize

# 5. Test
curl http://localhost:8000/cognitive-graph/status
```

---

## Neo4j Browser

Once Neo4j is running, access the browser interface:

**URL:** http://localhost:7474

### Useful Cypher Queries

```cypher
// View all nodes
MATCH (n) RETURN n LIMIT 25

// View schema
CALL db.schema.visualization()

// Count by type
MATCH (n) RETURN labels(n), count(n)

// Find questions about algorithms
MATCH (q:Question)-[:RELATED_TO]->(t:Topic)
WHERE t.name CONTAINS 'algorithm'
RETURN q.text, t.name

// Company insights
MATCH (c:Company)<-[:ASKED_BY]-(q:Question)
RETURN c.name, count(q) as question_count
ORDER BY question_count DESC
```

---

## Next Steps

1. ✅ Neo4j running
2. ✅ Backend connected
3. ✅ Schema initialized
4. ➡️ [Create Frontend UI](../../../apps/web/cognitive-graph.html)
5. ➡️ [Test Entity Extraction](../../business/ENTITY_EXTRACTION.md)
