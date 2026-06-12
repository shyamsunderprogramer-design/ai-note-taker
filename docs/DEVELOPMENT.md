# Development Guide

> Day-to-day dev commands, workflow, and conventions for the ANT monorepo. For ops, see [OPERATIONS.md](OPERATIONS.md). For troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## 1. First-time setup

```bash
git clone https://github.com/shyamsunderprogramer-design/ai-note-taker.git
cd ai-note-taker
make setup           # ~5-10 min: creates AINT_Venv/ + installs Python + JS deps
```

Equivalent to:

```bash
python3 -m venv AINT_Venv
source AINT_Venv/bin/activate
pip install -r backend/requirements.txt -r backend/requirements-test.txt
npm install         # installs all 4 workspaces
```

`make help` lists every available target.

---

## 2. Running the app

| Goal | Command |
|---|---|
| Backend + Electron desktop | `make dev` |
| Backend + Vite web dev | `make dev-web` |
| Backend only | `cd backend && uvicorn core.main:app --reload --port 8000` |
| Mobile (iOS sim) | `make mobile-ios` |
| Mobile (Android emu) | `make mobile-android` |
| Local Docker stack | `make docker-up` |
| Full Docker stack (neo4j+pg+redis+monitoring) | `make docker-up-full` |

---

## 3. Project layout

```
apps/                web, landing, chrome-extension (3 subdirs)
electron/            desktop app (Electron 41)
mobile/              React Native (iOS + Android)
backend/             FastAPI Python server
docker/              Dockerfiles + docker-compose
k8s/                 Helm chart + Argo app manifests
infrastructure/      Terraform stacks (AWS, Azure, GCP)
e2e/                 Playwright e2e tests
docs/                50+ markdown docs
scripts/             repo-helper scripts
```

Workspaces are declared in the root `package.json` (see [MONOREPO.md](../../../MONOREPO.md)). All dev commands can be run from the repo root: `npm run web:dev`, `npm run electron:start`, `npm run mobile:test`, etc.

---

## 4. Backend (Python) conventions

- **Layout:** `core/` (app entry, config, db), `routes/` (FastAPI routers, one per concern), `modules/` (7 sub-packages: agents, ai, crm, interview, platform, video, voice), `security/` (auth, encryption, rate_limit, validation, audit), `lib/` (shared utilities), `migrations/` (Alembic), `tests/`.
- **Style:** Black formatter, isort, mypy strict. `pre-commit-config.yaml` runs them on commit.
- **Imports:** Always use `from core.main import app`, not `from main import app`. The latter works only from inside `backend/` and is fragile.
- **Config:** Read from env vars, not hardcoded. Use the `settings` singleton in `core/config.py`.
- **Tests:** pytest with `asyncio_mode = auto` (set in `backend/pytest.ini`). Place tests in `backend/tests/test_<module>.py` mirroring the source structure.
- **Test coverage target:** > 80% for `security/`, `lib/`, and any new module. Use `pytest --cov=backend` to check.

---

## 5. Frontend (web) conventions

- **Stack:** Vite + vanilla JS (no framework). Multi-page setup with 14 HTML entries (`index.html`, `cognitive-graph.html`, `study-plan.html`, etc.).
- **Style:** Component-scoped CSS variables in `apps/web/css/base/variables.css`. Component files in `apps/web/css/components/`. The legacy `style.css` is the live build target; the modular `css/` tree is a future refactor.
- **JS structure:** `apps/web/js/main.js` is the entry; `js/core/` has utilities (api, auth-helper, config, state, events, window-controls); `js/components/` has React-style class components (CognitiveGraph, DocumentUpload, ExportImport, IntegrationPanel, SettingsPanel, Shell).
- **API contract:** The frontend calls `window.API_BASE` (default `http://127.0.0.1:8000`). Inject a `<script>` tag BEFORE `app.js` to override.
- **No `VITE_*` env vars** — the app doesn't read `.env` at build time. This is intentional; config is injected at runtime.

---

## 6. Electron conventions

- **Main process:** `electron/main.js` is the entry. Split into `electron/lib/`, `electron/windows/`, `electron/ipc/`, `electron/backend/` for organization.
- **Security:** All 4 `BrowserWindow` instances have `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`. Never disable these.
- **IPC:** All renderer→main communication goes through `ipcMain.handle` / `ipcRenderer.invoke` with a contextBridge in `preload.js`. Never use `ipcRenderer.send` with a callback.
- **Logging:** Use `electron-log` (already a dep). Logs go to platform-specific locations (see [OPERATIONS.md §3](OPERATIONS.md#3-logs)).

---

## 7. Mobile (React Native) conventions

See [MOBILE.md](MOBILE.md) for the full guide. Quick rules:

- Use `zustand` for state management (lightweight, no boilerplate).
- Use `react-native-audio-recorder-player` for audio capture.
- Use AsyncStorage for simple persistence; `react-native-mmkv` for fast sync access.
- Add per-screen tests in `mobile/__tests__/`.

---

## 8. Adding a new endpoint

1. **Pick a router:** every concern has a file in `backend/routes/`. If the concern is new, create a new file (e.g., `routes/invoices.py`).
2. **Add a Pydantic model** at the top of the file for request/response shapes.
3. **Add a route handler:**
   ```python
   from fastapi import APIRouter, Depends
   from security.auth import require_authentication, User

   router = APIRouter(prefix="/invoices", tags=["invoices"])

   @router.get("/")
   async def list_invoices(user: User = Depends(require_authentication)):
       ...
   ```
4. **Register the router** in `core/main.py:app.include_router()`.
5. **Test it:** add a test file in `backend/tests/test_routes_invoices.py` and exercise the route with `httpx.AsyncClient` + `ASGITransport`.
6. **Document it:** update `docs/backend/api/API_REFERENCE.md` (or `docs/backend/api/API_REFERENCE_PHASE2.md` if it's a Phase 2 feature).

---

## 9. Adding a new model

1. **Add the SQLAlchemy class** to `backend/core/database.py` (or a submodule if it's clearly owned by one).
2. **Generate the migration:** `make alembic-revision MSG="add Invoice table"`.
3. **Review the autogenerated file** — alembic sometimes misses `server_default`, index renames, or type changes.
4. **Apply locally:** `make alembic-upgrade`.
5. **Test the roundtrip:** `cd backend && alembic downgrade base && alembic upgrade head`.
6. **Commit the migration** with the model change. `DatabaseManager.initialize()` will run it on the next deploy.

See [MIGRATIONS.md](MIGRATIONS.md) for the full guide.

---

## 10. Pre-commit

The repo has a `.pre-commit-config.yaml` that runs on every `git commit`:

- `black` + `isort` for Python
- `eslint` for JS/TS
- `prettier` for JSON/YAML/Markdown
- trailing-whitespace, end-of-file-fixer, check-yaml, check-json

Install the hooks once: `pip install pre-commit && pre-commit install`.

---

## 11. Common workflows

### "I added a new Python dep"

```bash
# 1. Add it to backend/requirements.txt (or the appropriate *requirements*.txt)
# 2. Re-install
pip install -r backend/requirements.txt
# 3. Update requirements-test.txt if it's a test dep too
```

### "I added a new npm dep"

```bash
# Add it to the workspace that needs it:
cd electron && npm install <pkg>
# Or from the root for monorepo-shared deps:
npm install -D <pkg> -w <workspace-name>
```

### "I need to query the DB"

```bash
# SQLite (dev)
sqlite3 backend/data/ainotetaker.db

# PostgreSQL (prod)
psql "$DATABASE_URL"
```

### "Tests are flaky"

- Check the pre-existing failures doc: [memory/pre-existing-test-failures.md](memory/pre-existing-test-failures.md).
- Re-run a single test: `pytest tests/test_X.py::TestY::test_z -v`.
- Run with `--count=3` (if `pytest-repeat` is installed) to detect flakiness.

---

## 12. Things NOT to do

- Don't commit `.env`, `users.json`, `*.db`, `*.pem`, or `audit.jsonl`. They're in `.gitignore`.
- Don't disable `contextIsolation` in the Electron main process. It's a security boundary.
- Don't add new `unsafe-inline` or `unsafe-eval` to the CSP. The current CSP allows them only because of a few legacy inline scripts we're planning to remove.
- Don't bypass the Alembic migration path with raw SQL on the production DB. Always use a migration.
- Don't run `pip install --user` — it conflicts with the venv.
