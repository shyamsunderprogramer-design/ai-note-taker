# Contributing to ANT (AI Note Taker)

First off, thanks for taking the time to contribute! ANT is a
privacy-first AI notepad that runs locally on your machine. Every
contribution — bug reports, fixes, docs, new features — matters.

## Quick start for contributors

```bash
# 1. Clone
git clone https://github.com/<your-fork>/ai-note-taker.git
cd ai-note-taker

# 2. First-time setup (creates AINT_Venv/ and installs all deps)
make setup

# 3. Activate the venv
source AINT_Venv/bin/activate    # macOS/Linux
# AINT_Venv\Scripts\activate     # Windows

# 4. Verify everything works
make test
make dev     # starts backend + Electron desktop app
```

If you don't have `make` installed, see the platform-specific notes in
[`docs/devops/development/INSTALL.md`](docs/devops/development/INSTALL.md) or read the [`Makefile`](Makefile) for the
exact commands each target runs.

## Project structure (TL;DR)

```
ai-note-taker/
├── backend/          # Python FastAPI server
├── apps/
│   ├── web/          # Vite SPA (deployed to Vercel)
│   ├── landing/      # the landing page
│   └── ant-chrome-extension/  # MV3 Chrome extension
├── electron/         # Desktop shell
├── mobile/           # React Native iOS + Android
├── e2e/              # Playwright e2e tests
├── docker/           # Self-host Dockerfiles
├── infrastructure/   # Terraform (AWS, Azure, GCP)
└── k8s/              # Helm chart for the backend
```

The root [`MONOREPO.md`](MONOREPO.md) explains the npm workspaces setup
in detail. The [`docs/backend/architecture/PROJECT_STRUCTURE.md`](docs/backend/architecture/PROJECT_STRUCTURE.md)
doc has the full Python backend module map.

## Development workflow

1. **Create a branch** from `main`: `git checkout -b fix/short-description`
2. **Make your change.** Run `make test` before pushing.
3. **Write tests.** PRs without tests for new behavior are
   unlikely to land — see [Test coverage](#test-coverage) below.
4. **Run `make verify`** (lint + test + e2e) before opening the PR.
5. **Push** and open a PR. CI will run the same `make verify` gates.

## Test coverage

The backend has 3 tiers of tests:

| Tier | Location | Speed | Purpose |
|------|----------|-------|---------|
| Unit | `backend/tests/test_*.py` | fast (no live server) | Function-level, mocks external services |
| Integration | `backend/tests/test_api_integration.py` | medium (needs uvicorn on :8000) | End-to-end HTTP via the FastAPI app |
| E2E | `e2e/tests/*.spec.js` | slow (boots backend + browser) | Real browser clicking through the UI |

When adding a new feature:
- Add a unit test in `backend/tests/test_<module>.py` (or extend an
  existing file if the module is already tested).
- If the feature is user-facing, add an e2e spec in `e2e/tests/`.

The 3 DOCUMENTED BUG tests in `test_security_validation.py` and
`test_security_encryption.py` are pinned to known issues — if you fix
one of those bugs, the test will fail, which is the signal to also
update the test.

## Coding style

| Language | Style | Tool |
|----------|-------|------|
| Python | PEP 8, type hints, docstrings on public functions | `ruff` (run via `make lint`) |
| JS / TS | Prettier defaults, ES modules, no semicolons | `eslint` (root + per-workspace) |
| Terraform | `terraform fmt` | `terraform validate` |
| YAML | 2-space indent | `yamllint` (if installed) |

We do not enforce strict line length; the linters are configured with
pragmatic defaults. Read existing code in the area you're editing to
match the local style.

## Commit messages

We follow [Conventional Commits](https://www.conventionalcommits.org/)
loosely. Prefix your commit with one of:

- `fix:` — bug fix
- `feat:` — new feature
- `docs:` — documentation only
- `chore:` — tooling, CI, deps
- `refactor:` — code change that doesn't fix a bug or add a feature
- `test:` — adding or fixing tests

Example: `fix: prevent stub recordings from silently loading on app start`

## Pull request process

1. Open a PR against `main`. The CI will run `make verify` (lint,
   test, e2e). All three must pass.
2. Address any review comments. We try to merge within 2-3 days
   of opening.
3. After merge, delete your branch.

## Security

Found a security issue? **Do NOT open a public issue.** Email the
maintainer (or see [`docs/devsecops/security/SECURITY_IMPLEMENTATION_SUMMARY.md`](docs/devsecops/security/SECURITY_IMPLEMENTATION_SUMMARY.md)
for the security contact path). We follow responsible disclosure
and will credit reporters in the CHANGELOG once a fix lands.

## Documentation

- The [`docs/`](docs/) folder is the canonical source for design
  docs, API reference, and architecture. The [`docs/README.md`](docs/README.md)
  index organizes them by role (`backend` / `uiux` / `devops` / `qa` /
  `devsecops`) and by topic (`shared` / `business` / `competitive` /
  `research` / `archive`).
- New features should add an entry to the relevant `docs/` file
  (e.g. new API endpoint → update
  `docs/backend/api/API_REFERENCE.md`; new design token → update
  `docs/uiux/design-system/README.md`).
- README files in subfolders (e.g. `electron/README.md`,
  `apps/web/README.md`) are intended as the first stop for someone
  landing in that folder.

## License

By contributing, you agree that your contributions will be licensed
under the [MIT License](LICENSE).
