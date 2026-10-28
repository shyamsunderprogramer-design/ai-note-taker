# Backend documentation

| Topic | Guide |
| --- | --- |
| Routes, authentication, streaming, and graph API | [API reference](api/API_REFERENCE.md) |
| Architecture and data flow | [Technical specification](architecture/TECHNICAL_SPECIFICATION.md) |
| Source layout | [Project structure](architecture/PROJECT_STRUCTURE.md) |
| Neo4j graph schema | [Graph data model](database/SCHEMA.md) |
| Optional graph service | [Cognitive Graph setup](setup/SETUP_COGNITIVE_GRAPH.md) |
| NLP extraction | [Entity extraction](../business/ENTITY_EXTRACTION.md) |
| Module boundaries | [Module guide](modules/README.md) |
| Relational migrations | [Migration guide](../devops/development/MIGRATIONS.md) |

For local setup, use the [project README](../../README.md). For new API behavior, update the owning route and its schema, then the API topic guide. The original general, Phase 2, and graph API examples are preserved in one [historical API record](../archive/api-reference.md).

Backend ownership is defined in [OWNERS.backend.md](../../OWNERS.backend.md).
