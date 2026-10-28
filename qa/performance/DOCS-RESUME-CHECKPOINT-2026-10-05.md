# Documentation checkpoint — October 5, 2026

User requested: save and resume later. Work is paused after the documentation edits below.

## Completed locally

- Rewrote root README.md around source setup, local/cloud AI configuration, desktop/browser launch, everyday use, permissions, shortcuts, and troubleshooting.
- Consolidated docs from 160 to 69 Markdown files.
- Removed 107 obsolete paths, including exact/link-only copies and overlapping guides.
- Created or rewrote maintained topic guides for setup/use, API, BYOK, performance, resume tools, jobs/extension, competitive research, Pluely adaptation, roadmap, release readiness, and historical model assignments.
- Preserved 55 unique source chapters in 11 topic records under docs/archive/.
- Rewrote docs/README.md and specialist indexes; updated documentation links, including root README and qa/performance/README.md.
- docs/CONSOLIDATION.md maps all 107 previous paths to maintained guides and preserved source records.

## Validation

- Local Markdown links and maintained guide anchors pass.
- All canonical destinations and preserved source chapter anchors exist.
- Preserved source text matches original content after documented link/path repairs.
- No identical Markdown files remain under docs/.
- git diff --check -- README.md docs passed.
- No application tests were run for this documentation-only task.

Temporary verification helpers, if still present:
- /tmp/check-ant-docs.py
- /tmp/ant-docs-original.json
- /tmp/ant-docs-consolidation-manifest.json

The durable docs and source records are in the original workspace; temporary helpers are not required to read or continue the documentation.

## Git and publication

Documentation changes remain uncommitted in the original ux-sprint workspace, alongside pre-existing unrelated edits. No push, PR, merge, or release was performed in this documentation session.

Earlier application publication work is still described in RESUME-CHECKPOINT-2026-10-05.md. Its prepared app commit a8ff969 and isolated checkout /tmp/ant-publish-20261005 do not contain these later documentation edits. main and ux-sprint have unrelated histories; the target branch decision remains unresolved. Do not force-push or blindly reconcile main.

## Resume next

Read this checkpoint and docs/README.md. If the user wants publication, review and include the documentation edits deliberately while preserving unrelated workspace changes, and resolve the outstanding target-branch decision. The user's current instruction is to pause; do not continue publication work now.
