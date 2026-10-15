---
name: Feature request
about: Suggest a new feature or improvement
title: "[feature] "
labels: ["enhancement", "needs-triage"]
assignees: []
---

## Primary role owner

<!--
ANT is organized by 5 roles. Pick the role that will own the
implementation. CODEOWNERS routes the issue to that role's GitHub
Team. See OWNERS.{role}.md at the repo root for each role's
charter and docs/{role}/README.md for the role's docs.
-->

- [ ] **backend** — FastAPI, services, DB, AI integration, Neo4j (`backend/`)
- [ ] **uiux** — web SPA, mobile, Chrome extension, Electron UI, design (`apps/`, `mobile/`, `electron/features/`)
- [ ] **devops** — deploy, runtime shell, CI, infra, mobile-native build (`Dockerfile`, `k8s/`, `infrastructure/`, `electron/main.js`/`preload.js`/`stealth.js`, `.github/workflows/`)
- [ ] **qa** — tests, fixtures, e2e, performance (`e2e/`, `qa/`, `backend/tests/`, `mobile/__tests__/`, `electron/tests/`)
- [ ] **devsecops** — security, supply chain, secrets, compliance (`.claude/`, `.pre-commit-config.yaml`, `.github/`, `SECURITY.md`, `backend/security/`)
- [ ] **Cross-cutting** — touches 2+ roles; describe in "Additional context" which secondary roles need to review

## Problem

<!--
What user problem are you trying to solve? Why does it matter?
"Add X" is a solution; describe the underlying pain first.
-->

## Proposed solution

<!-- A clear, concise description of what you want to happen. -->

## Alternatives considered

<!-- What other approaches did you consider, and why is this one better? -->

## Mockups / examples

<!-- Optional: link Figma / sketch / screenshot / competitor screenshot. -->

## Use case

<!-- Who benefits and how? A specific user story ("as a X, I want Y, so Z") helps. -->

## Scope

<!-- Mark one. -->

- [ ] Small — single component / module
- [ ] Medium — multiple modules, no schema change
- [ ] Large — new module / new schema migration / new external dependency
- [ ] Breaking — changes an existing public API or data model

## Additional context

<!-- Anything else: related issues, prior art, etc. -->
