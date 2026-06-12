# Pull Request

<!--
Thanks for contributing to ANT (AI Note Taker)!
Please fill out the template below so reviewers have what they need.
-->

## Summary

<!--
One or two sentences on what this PR does and why.
Link the relevant issue with "Fixes #123" or "Closes #456".
-->

- **What:**
- **Why:**
- **Fixes / Closes:**

## Type of change

<!-- Mark the relevant options with an "x". -->

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] Refactor / cleanup (no functional change)
- [ ] CI / CD change
- [ ] Infrastructure (Terraform, K8s, Docker)

## Test plan

<!--
Describe the tests you ran and how to reproduce them.
Include any specific test commands, fixtures, or environments.
-->

- [ ] Backend pytest passes: `cd backend && pytest tests/ -q`
- [ ] Web build passes: `cd apps/web && npm run build`
- [ ] Mobile Jest passes (if mobile changed): `cd mobile && npm test`
- [ ] Electron node:test passes (if electron changed): `cd electron && npm test`
- [ ] E2E smoke passes (if user-facing): `cd e2e && npx playwright test --grep @smoke`
- [ ] Manual testing: describe what you ran

## Checklist

- [ ] My code follows the project's style guide
- [ ] I have added tests for new functionality (or explained why not in the PR description)
- [ ] I have updated the relevant documentation
- [ ] I have added an entry to CHANGELOG.md under `[Unreleased]`
- [ ] I have NOT introduced any new secrets, API keys, or credentials
- [ ] I have verified no `.env`, `*.pem`, or `users.json` files are included
- [ ] My changes generate no new linter warnings
- [ ] Alembic migration is included if I changed a SQLAlchemy model
- [ ] I have read the CONTRIBUTING.md guide

## Screenshots / recordings

<!--
For UI changes: paste a screenshot or short screen recording.
For backend changes: paste a curl output, OpenAPI diff, or test output.
-->

## Related

<!--
Link any related PRs, issues, design docs, or discussion threads.
-->
