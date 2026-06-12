# ANT Documentation

The `docs/` folder is the canonical reference for the ANT (AI Note Taker)
project. Each doc covers one concern; this README is the index.

> **How this is organized** — docs are grouped into 8 categories below.
> Pick a category and the relevant file(s) under it. If a doc spans more
> than one category, we link it from each.

---

## 1. Getting started

| Doc | What it covers |
|---|---|
| [INSTALL.md](INSTALL.md) | End-user install (Win / macOS / Linux) |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Dev setup, conventions, monorepo commands |
| [CONTRIBUTING.md](../CONTRIBUTING.md) (root) | Contribution workflow, code review |

## 2. Backend

| Doc | What it covers |
|---|---|
| [API_REFERENCE.md](API_REFERENCE.md) | Every HTTP endpoint (request, response, errors) |
| [API_REFERENCE_PHASE2.md](API_REFERENCE_PHASE2.md) | Phase 2 endpoints (cognitive graph, study plan, analytics) |
| [COGNITIVE_GRAPH_API.md](COGNITIVE_GRAPH_API.md) | Cognitive-graph-specific endpoint deep-dive |
| [SETUP_COGNITIVE_GRAPH.md](SETUP_COGNITIVE_GRAPH.md) | Neo4j install + first-run setup |
| [architecture/PROJECT_STRUCTURE.md](architecture/PROJECT_STRUCTURE.md) | File layout, package boundaries, data flow |
| [architecture/TECHNICAL_SPECIFICATION.md](architecture/TECHNICAL_SPECIFICATION.md) | Full system design (50+ pages) |
| [database/SCHEMA.md](database/SCHEMA.md) | Every SQLAlchemy model + Alembic migration |

## 3. Devops / release

| Doc | What it covers |
|---|---|
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Deploy to Render (web) + Electron builder (desktop) |
| [OPERATIONS.md](OPERATIONS.md) | Day-2 ops: logs, backups, on-call, scaling |
| [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) | Pre-launch hardening checklist |
| [PRODUCTION_READINESS_ANALYSIS.md](PRODUCTION_READINESS_ANALYSIS.md) | Per-area readiness assessment |
| [PRODUCTION_TASK_BREAKDOWN.md](PRODUCTION_TASK_BREAKDOWN.md) | Granular work items for prod launch |
| [PRODUCTION_DEEP_DIVE_2026.md](PRODUCTION_DEEP_DIVE_2026.md) | April-2026 deep-dive into prod requirements |
| [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) | Per-release QA + signing + GitHub release steps |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Dev workflow + monorepo commands |
| [MIGRATIONS.md](MIGRATIONS.md) | Alembic migration workflow |
| [MOBILE.md](MOBILE.md) | React Native build + deploy (iOS / Android) |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common failures and fixes |
| [INSTALL.md](INSTALL.md) | End-user install (also under "Getting started") |
| [development/DIY_TEST_GUIDE.md](development/DIY_TEST_GUIDE.md) | How to manually test the desktop app |

## 4. Security

| Doc | What it covers |
|---|---|
| [security/SECURITY_IMPLEMENTATION_SUMMARY.md](security/SECURITY_IMPLEMENTATION_SUMMARY.md) | All security features implemented, file by file |
| [../SECURITY.md](../SECURITY.md) (root) | Public security policy + how to report a vuln |
| [../BROWSER_EXTENSION_SAFETY.md](../BROWSER_EXTENSION_SAFETY.md) (root) | Chrome-extension threat model |

## 5. Product / business

| Doc | What it covers |
|---|---|
| [BYOK_BUSINESS_MODEL.md](BYOK_BUSINESS_MODEL.md) | BYOK pricing + cost math + UX rationale |
| [BYOK_MODEL_GUIDE.md](BYOK_MODEL_GUIDE.md) | User-facing guide to BYOK |
| [JOB_APPLICATION_WORKFLOW.md](JOB_APPLICATION_WORKFLOW.md) | Job-app integration end-to-end flow |
| [JOB_PORTAL_GUIDELINES.md](JOB_PORTAL_GUIDELINES.md) | Do's and don'ts for portal integrations |
| [PHASE2_PLAN.md](PHASE2_PLAN.md) | Phase 2 feature plan (real-time, analytics, study plan) |
| [QUESTION_DATABASE_SUMMARY.md](QUESTION_DATABASE_SUMMARY.md) | Question-DB schema + curation |
| [RESUME_REVIEW_HOW_IT_WORKS.md](RESUME_REVIEW_HOW_IT_WORKS.md) | Resume-review product spec |
| [RESUME_BUILDER_COMPETITIVE_ANALYSIS_2025.md](RESUME_BUILDER_COMPETITIVE_ANALYSIS_2025.md) | Resume-builder market scan (2025) |
| [RESUME_BUILDER_DEPLOYMENT_GUIDE.md](RESUME_BUILDER_DEPLOYMENT_GUIDE.md) | Resume-builder deploy notes |
| [RESUME_BUILDER_FEATURE_MATRIX.md](RESUME_BUILDER_FEATURE_MATRIX.md) | Resume-builder feature coverage |
| [RESUME_BUILDER_FREE_STRATEGY.md](RESUME_BUILDER_FREE_STRATEGY.md) | Free-tier strategy |
| [RESUME_BUILDER_IMPLEMENTATION_PLAN.md](RESUME_BUILDER_IMPLEMENTATION_PLAN.md) | Resume-builder build plan |
| [RESUME_BUILDER_IMPLEMENTATION_SUMMARY.md](RESUME_BUILDER_IMPLEMENTATION_SUMMARY.md) | Resume-builder build status |
| [ENTITY_EXTRACTION.md](ENTITY_EXTRACTION.md) | spaCy + rule-based NER pipeline |

## 6. Performance / speed

| Doc | What it covers |
|---|---|
| [SPEED_IMPROVEMENT_SUMMARY.md](SPEED_IMPROVEMENT_SUMMARY.md) | End-to-end speed wins since v0.9 |
| [SPEED_OPTIMIZATION_PLAN.md](SPEED_OPTIMIZATION_PLAN.md) | Future speed roadmap |
| [SPEED_OPTIMIZATIONS_IMPLEMENTED.md](SPEED_OPTIMIZATIONS_IMPLEMENTED.md) | What's already shipped, by release |
| [ANT_MASTER_UPGRADE_PLAN_2026.md](ANT_MASTER_UPGRADE_PLAN_2026.md) | 2026 master upgrade plan (cross-cutting) |

## 7. Research / analysis

| Doc | What it covers |
|---|---|
| [ANALYSIS_2026-04-07_Application_Goals_Competitive_Comparison.md](ANALYSIS_2026-04-07_Application_Goals_Competitive_Comparison.md) | Apr-2026 product goal recheck vs competitors |
| [COMPREHENSIVE_GUIDE.md](COMPREHENSIVE_GUIDE.md) | The full 80+ page everything-doc (canonical) |
| [FULL_IMPLEMENTATION_COMPLETE.md](FULL_IMPLEMENTATION_COMPLETE.md) | Phase-1 completion report |
| [CRITICAL_GAPS_FIXED.md](CRITICAL_GAPS_FIXED.md) | The 60-of-60 audit fixes, summarized |
| [AUDIT_2026-06-05_Project_Audit.md](AUDIT_2026-06-05_Project_Audit.md) | June-2026 project audit (Fix #0 → Fix #50) |
| [COMPETITIVE_ANALYSIS_2026_PRODUCTION_UPGRADE.md](COMPETITIVE_ANALYSIS_2026_PRODUCTION_UPGRADE.md) | Competitor matrix — production upgrade |
| [COMPETITIVE_ANALYSIS_COMPLETE_2026.md](COMPETITIVE_ANALYSIS_COMPLETE_2026.md) | Full competitor matrix (2026) |
| [COMPETITIVE_ARCHITECTURE_COMPARISON_2026.md](COMPETITIVE_ARCHITECTURE_COMPARISON_2026.md) | Competitor architectures |
| [COMPETITIVE_DEEP_DIVE_2026.md](COMPETITIVE_DEEP_DIVE_2026.md) | Top-3 competitor feature deep-dive |
| [COMPETITIVE_GAP_ANALYSIS_2026-04-11.md](COMPETITIVE_GAP_ANALYSIS_2026-04-11.md) | Apr-2026 gap analysis |
| [COMPETITIVE_GAP_ANALYSIS_UPDATED_APRIL_2026.md](COMPETITIVE_GAP_ANALYSIS_UPDATED_APRIL_2026.md) | Updated gap analysis |
| [PLUELY_COMPARISON_2026_COMPLETE.md](PLUELY_COMPARISON_2026_COMPLETE.md) | Pluely (direct competitor) deep-dive |
| [PLUELY_FEATURES_ADAPTATION.md](PLUELY_FEATURES_ADAPTATION.md) | Which Pluely features we should adopt |
| [PLUELY_IMPLEMENTATION_SUMMARY.md](PLUELY_IMPLEMENTATION_SUMMARY.md) | Pluely-feature build status |
| [PLUELY_ROOT_LEVEL_COMPARISON.md](PLUELY_ROOT_LEVEL_COMPARISON.md) | Pluely feature-by-feature comparison |

## 8. Research archive

Older research artifacts (kept for reference, not maintained). See
[research/](research/) for the time-bounded research subfolder.

---

## Doc conventions

- One topic per file; if a doc grows past ~1000 lines, split it.
- Use relative links from inside `docs/` (e.g., `[CHANGELOG](../CHANGELOG.md)`).
- New top-level docs land in the category they fit; if no category fits,
  add one to this README and link it.
- Diagrams: use Mermaid in fenced ```mermaid blocks. No external image
  hosts (offline-first).
- Every doc ends with `*Last Updated: YYYY-MM-DD*`.
