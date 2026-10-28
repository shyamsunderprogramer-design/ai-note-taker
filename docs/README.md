# ANT documentation

Start with the [project README](../README.md) to install ANT and use its desktop or browser interface. This index gives each subject one maintained guide. Original research, plans, and implementation reports are grouped by topic in the [historical references](archive/README.md).

## Setup and everyday use

| What you want to do | Read this |
| --- | --- |
| Install, configure, and launch ANT | [Setup and usage](../README.md#set-up-from-source) |
| Choose local AI or add cloud credentials | [Local AI and API keys](business/BYOK.md) |
| Review a resume or personalize answers | [Resume tools and job context](business/resume-builder/README.md) |
| Save jobs and use the extension | [Job workflow](business/JOB_APPLICATION_WORKFLOW.md) |
| Resolve setup or runtime errors | [Troubleshooting](devops/development/TROUBLESHOOTING.md) |
| Set up the mobile app | [Mobile setup](../mobile/README.md) |
| Enable the optional knowledge graph | [Cognitive Graph setup](backend/setup/SETUP_COGNITIVE_GRAPH.md) |

## Build and maintain

| Topic | Maintained document |
| --- | --- |
| Development workflow | [Development guide](devops/development/DEVELOPMENT.md) |
| API routes and request contracts | [API reference](backend/api/API_REFERENCE.md) |
| Architecture and data flow | [Technical specification](backend/architecture/TECHNICAL_SPECIFICATION.md) |
| Repository structure | [Project structure](backend/architecture/PROJECT_STRUCTURE.md) |
| Graph data model | [Neo4j schema](backend/database/SCHEMA.md) |
| Relational database changes | [Migrations](devops/development/MIGRATIONS.md) |
| Entity extraction | [Extraction guide](business/ENTITY_EXTRACTION.md) |
| Testing | [Test strategy](qa/test-strategy.md) and [manual checks](qa/DIY_TEST_GUIDE.md) |
| Performance | [Measurement and optimization](business/PERFORMANCE.md) |
| Cloud deployment | [Deployment guide](devops/deployment/DEPLOYMENT_GUIDE.md) |
| Release acceptance and packaging | [Release checklist](devops/deployment/RELEASE_CHECKLIST.md) |
| Running a deployment | [Operations runbook](devops/operations/OPERATIONS.md) |
| Containers | [Docker setup](../docker/README.md) |
| Security | [Security index](devsecops/README.md) |
| UI foundations | [UI index](uiux/README.md) |

## Product and research

- [Product roadmap](business/ROADMAP.md) — dependency order and planning context.
- [Competitive research](competitive/README.md) — comparison criteria and product priorities.
- [Pluely adaptation](competitive/pluely/README.md) — desktop architecture tradeoffs and verification.
- [Research index](research/README.md) — distinct competitor records and historical assignments.
- [Interview question catalogue report](business/QUESTION_DATABASE_SUMMARY.md) — dated catalogue details.
- [June project audit](shared/AUDIT_2026-06-05_Project_Audit.md) — historical audit evidence.

## Keep the documentation clear

Update the existing topic guide when behavior changes. Put setup commands in the project README, API contracts in the running schema and API guide, and release evidence in the candidate's validation record. Do not copy a guide into the docs root or publish another overlapping “complete” report.

Historical reference records retain unique examples and proposals with their original context. Their completion claims, prices, timelines, and benchmarks are not current guarantees. See the [consolidation map](CONSOLIDATION.md) to find a document by its previous path.

For ownership and specialist navigation: [backend](backend/README.md), [UI](uiux/README.md), [operations](devops/README.md), [QA](qa/README.md), and [security](devsecops/README.md). Ownership charters remain in `OWNERS.*.md` at the repository root.
