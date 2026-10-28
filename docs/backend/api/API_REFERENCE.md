# Backend API reference

The running FastAPI schema is the source of truth for enabled routes, authentication, request bodies, and responses. The old general, Phase 2, and Cognitive Graph API documents are consolidated into one reference record with their examples preserved.

## Explore the API

Start the backend using the [setup instructions](../../../README.md#set-up-from-source), then open:

- **Interactive documentation:** http://127.0.0.1:8000/docs
- **OpenAPI schema:** http://127.0.0.1:8000/openapi.json

Use the schema from the environment you are calling. Optional modules and deployed configuration can affect availability. Sign in and provide a bearer token for protected operations.

## Route groups and implementation

| Area | Source |
| --- | --- |
| Application assembly and WebSocket flows | [core/main.py](../../../backend/core/main.py) |
| Authentication | [auth routes](../../../backend/routes/auth.py) |
| Provider configuration and Ollama | [ollama.py](../../../backend/routes/ollama.py) |
| AI requests | [ai.py](../../../backend/routes/ai.py) |
| Transcription | [transcription.py](../../../backend/routes/transcription.py) |
| Conversations | [conversations.py](../../../backend/routes/conversations.py) |
| Answer recovery | [recovery.py](../../../backend/routes/recovery.py) |
| Interview practice | [interview.py](../../../backend/routes/interview.py) |
| Analytics | [analytics.py](../../../backend/routes/analytics.py) |
| Study plans | [study.py](../../../backend/routes/study.py) |
| Jobs and career tools | [jobs.py](../../../backend/routes/jobs.py), [career.py](../../../backend/routes/career.py) |
| Health and modules | [health.py](../../../backend/routes/health.py) |
| Other route families | [routes directory](../../../backend/routes/) |

## Calling and validating routes

1. Confirm the method/path in the running schema.
2. Match the documented input location: query, JSON body, form fields, or multipart upload.
3. Use the authenticated user's identity rather than assuming an arbitrary `user_id` is accepted.
4. Check status codes and structured errors; not every route has the same error envelope.
5. For streaming and WebSocket flows, inspect the owning implementation and test client for event framing, completion, and recovery.

## Cognitive Graph

Neo4j is optional for the core app. Follow the [graph setup guide](../setup/SETUP_COGNITIVE_GRAPH.md) before using graph-dependent endpoints. Read the [graph schema](../database/SCHEMA.md) and [entity extraction guide](../../business/ENTITY_EXTRACTION.md) for data concepts.

The original graph queries, request/response examples, analytics examples, and Phase 2 examples are all available in the dated reference record below. Verify each example against the running schema before use.

## Historical references

The overlapping source documents are preserved in one [dated reference record](../../archive/api-reference.md). Use that record for original technical examples and planning context, not current setup or status.
