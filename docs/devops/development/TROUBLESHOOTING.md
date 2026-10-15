# Troubleshooting

> Common errors and their fixes for the ANT monorepo. For ops runbook, see [OPERATIONS.md](OPERATIONS.md). For migrations, see [MIGRATIONS.md](MIGRATIONS.md).

---

## Backend (Python)

### `JWT_SECRET_KEY not set` warning

**Symptom:** A warning at startup: `JWT_SECRET_KEY not set — tokens will invalidate on restart`.

**Fix:** Generate one and add to `.env`:

```bash
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))" >> .env
```

In production (Render), set `JWT_SECRET_KEY: generateValue: true` in `render.yaml` so Render creates a strong random secret on first deploy.

---

### `No module named 'generate_ssl'` when running `start_server.py --ssl`

**Symptom:**

```
ModuleNotFoundError: No module named 'generate_ssl'
```

**Cause:** `start_server.py` adds `backend/` and the project root to `sys.path`, but `generate_ssl.py` lives in `backend/core/`. Fixed in 2026-06-07.

**Workaround if you can't upgrade:** `python3 -c "import sys; sys.path.insert(0, 'backend/core'); from start_server import main; main()"`

---

### `No module named 'modules.ai.X'` (circular import)

**Symptom:**

```
ImportError: cannot import name 'X' from 'modules.ai.Y'
```

**Cause:** A new module in `modules/ai/` is being imported from another `modules/ai/` module before its top-level definitions are complete.

**Fix:** Move the import to inside the function that needs it, OR add the new module's name to `modules/ai/__init__.py` so the package is "fully constructed" before the inner import runs.

---

### `AttributeError: 'NoneType' object has no attribute 'X'`

**Symptom:** Backend logs a NoneType error on startup.

**Likely cause:** A config value is None. Check `os.environ.get(...)` returns. Add a default:

```python
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/ainotetaker.db")
```

---

### Alembic: "Can't locate revision identified by 'XXXX'"

**Symptom:** `alembic upgrade head` errors with a "can't locate revision" message.

**Cause:** The `alembic_version` row in the DB points to a revision that doesn't exist in `backend/migrations/versions/`.

**Fix:**

```bash
# Option A: copy the missing file from git
git checkout origin/main -- backend/migrations/versions/<file>.py
alembic upgrade head

# Option B: stamp the DB at head (skips the missing migration — use only if you
# know the schema is already at the right state)
alembic stamp head
```

See [MIGRATIONS.md §6](MIGRATIONS.md#6-troubleshooting) for more.

---

### Alembic: "Table 'X' already exists" on first run

**Symptom:** `alembic upgrade head` errors because `X` already exists.

**Cause:** The DB was previously created with `Base.metadata.create_all()` (the legacy path).

**Fix:** Drop the tables manually and let alembic re-create them:

```bash
alembic downgrade base    # drops everything
alembic upgrade head      # re-applies all migrations
```

---

### Alembic: "alembic_version is None" after running tests

**Symptom:** Tests pass but `alembic current` returns nothing.

**Cause:** Test fixtures build the DB with `create_all()` only, not `alembic upgrade head`. The pre-existing test failures doc flags this.

**Fix (in your test fixture):**

```python
from alembic.config import Config
from alembic import command
cfg = Config("backend/alembic.ini")
command.upgrade(cfg, "head")
```

OR set `ANT_SKIP_ALEMBIC=1` in the test env and accept that the test DB is unversioned.

---

### Neo4j: "Connection refused" on `bolt://neo4j:7687`

**Symptom:**

```
neo4j.exceptions.ServiceUnavailable: Could not connect to bolt://neo4j:7687
```

**Fix:**

```bash
# Local: start neo4j via docker-compose
make docker-up-full

# Production: check the NEO4J_URI env var matches the deployed Neo4j host
# For Neo4j Aura: use neo4j+s://<id>.databases.neo4j.io:7687
```

---

### bcrypt + passlib incompatibility (login fails)

**Symptom:**

```
ValueError: password cannot be longer than 72 bytes
```

OR the test `test_security_auth.py::TestAccessToken::test_tampered_signature_returns_none` flakes.

**Cause:** `passlib 1.7.4` + `bcrypt >= 4.1` is broken. The error message is misleading — it's not actually a 72-byte issue, it's the bcrypt version pin.

**Fix (in `backend/requirements.txt`):**

```
bcrypt<4.1
```

OR migrate off passlib and use `bcrypt` directly.

This is a known issue. See [memory/bcrypt-passlib-incompatibility.md](memory/bcrypt-passlib-incompatibility.md).

---

### Whisper: "Model 'base' not found"

**Symptom:**

```
ValueError: Model 'base' not found in /path/to/models
```

**Fix:**

```bash
# faster-whisper auto-downloads on first use, but if the download was
# interrupted, delete the partial and re-try:
rm -rf ~/.cache/huggingface/hub/models--Systran--faster-whisper-*
# Then start the app — it'll re-download.
```

---

## Frontend (Web)

### "Network Error" when calling the backend

**Symptom:** Every backend call from the web app fails with "Network Error".

**Cause:** CORS. The backend at `127.0.0.1:8000` is not allowing requests from your web origin.

**Fix:** Check the backend logs for the CORS error. Add the origin to `CORS_ORIGINS` in `.env`:

```bash
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Restart the backend.

---

### "Cannot read properties of null (reading 'X')" on page load

**Symptom:** Console error on page load.

**Cause:** `window.API_BASE` is not set before `app.js` loads. The app falls back to `http://127.0.0.1:8000`, which is wrong in production.

**Fix:** Inject a `<script>` tag in the HTML before `app.js`:

```html
<script>window.API_BASE = 'https://api.your-domain.com';</script>
<script src="app.js"></script>
```

---

## Electron

### Blank white window on startup

**Symptom:** Electron window opens but shows nothing.

**Fix:**

1. Open DevTools: **View → Toggle Developer Tools** (or Ctrl+Shift+I on Windows, Cmd+Option+I on macOS).
2. Check the Console for errors.
3. The most common cause is a CSP violation — check the Network tab for blocked resources.

---

### "App is damaged and can't be opened" on macOS

**Symptom:** macOS Gatekeeper blocks the app from launching.

**Cause:** The app isn't code-signed (the repo has `notarize: false` and `identity: null` for dev).

**Fix (one-time, for the developer who built it):**

```bash
xattr -dr com.apple.quarantine /Applications/ANT.app
```

For production releases, set up code signing with a Developer ID certificate from Apple.

---

### "A JavaScript error occurred in the main process" on Windows

**Symptom:** The app crashes immediately on launch with a dialog: "A JavaScript error occurred in the main process".

**Cause (most common):** `electron/main.js` requires a local module (under `./features/` or `./lib/`) that isn't listed in `electron/package.json` → `build.files`. The packaged `app.asar` doesn't include the folder, so `require()` throws synchronously during module evaluation. The error is invisible in dev mode (`npm start` works because the files are right there on disk) and only surfaces in the packaged build.

**Fix:**
1. Add the missing folder to `build.files`, e.g.:
   ```json
   "files": [
     "main.js",
     "preload.js",
     "stealth.js",
     "features/**",
     "lib/**",
     "assets/**"
   ]
   ```
2. Rebuild with `cd electron && npm run build:win`.
3. Verify with `npx asar list dist/win-unpacked/resources/app.asar | grep -E "^/(features|lib)"` — the files should appear.

**Rule of thumb:** any new top-level folder under `electron/` that's `require()`'d from `main.js` (or `preload.js`) must be listed in `build.files`. `extraResources` is for non-code data and is not on the require() path.

---

### Backend doesn't start when Electron launches

**Symptom:** Electron window opens but the AI chat says "Backend unavailable".

**Cause:** `startBackend()` failed — usually a wrong Python path or a missing venv.

**Fix:** Run the backend manually to see the error:

```bash
cd backend
source ../AINT_Venv/bin/activate
uvicorn core.main:app --reload --port 8000
```

---

### Stealth mode doesn't hide from Zoom

**Symptom:** The app is still visible in Zoom screen share.

**Cause:** `setContentProtection(true)` only works on Windows. On macOS, the equivalent is to use a different approach (set window level, hide from capture APIs).

**Fix:** This is a known platform limitation. On Windows, the protection works as designed. On macOS, the workaround is to position the overlay OUTSIDE the screen region being shared.

---

## Mobile

### "Could not connect to development server"

**Symptom:** Mobile app shows a red screen with "Could not connect to development server".

**Cause:** Metro bundler isn't running, OR the device can't reach the dev machine.

**Fix:**

```bash
# 1. Make sure Metro is running
cd mobile && npm start

# 2. On Android emulator, the default URL should be 10.0.2.2:8081
# 3. On a physical device, use the LAN IP of the dev machine
adb reverse tcp:8081 tcp:8081   # for Android via USB
```

---

### iOS build fails with "No bundle URL present"

**Symptom:** iOS app crashes on launch with "No bundle URL present".

**Cause:** Metro isn't running OR the bundle URL is wrong.

**Fix:**

```bash
cd mobile
npm start
# In another terminal:
npm run ios
```

---

### Android build fails with "SDK location not found"

**Symptom:** Gradle errors with "SDK location not found".

**Fix:**

```bash
# Add to ~/.gradle/gradle.properties or set ANDROID_HOME
export ANDROID_HOME=$HOME/Library/Android/sdk
# or
echo "sdk.dir=/Users/you/Library/Android/sdk" > mobile/android/local.properties
```

---

## CI / CD

### `backend-tests` job fails on GitHub Actions

**Symptom:** PR red because the `backend-tests` job failed.

**Fix:**

1. Check the failing test in the PR's Actions tab.
2. If it's one of the 3 pre-existing failures (`vibevoice_diarizer_fallback`, `test_init_creates_all_tables`, `test_init_stamps_alembic_version`), it's not a regression. Look for a new failure.
3. Re-run the job from the GitHub UI: **Actions → workflow run → Re-run jobs**.

---

### `web-build` job fails

**Symptom:** PR red because the Vite build errored.

**Fix:**

```bash
# Reproduce locally
cd apps/web
npm run build
```

Read the error message. Common causes:
- Syntax error in `app.js` or one of the modular `js/` files
- Missing import
- A `package.json` dep is out of sync

---

### `e2e` job runs out of disk

**Symptom:** The e2e job errors with "no space left on device".

**Cause:** The job installs `faster-whisper`, `spacy`, and other heavy ML deps. GitHub-hosted runners have limited disk.

**Fix:** Document in the YAML. There's a comment at the top of `.github/workflows/ci.yml` already. If it becomes chronic, switch to a self-hosted runner.

---

## Common "I broke it" recovery steps

### "I deleted a migration file"

```bash
git checkout origin/main -- backend/migrations/versions/<file>.py
cd backend && alembic upgrade head
```

### "I committed a secret"

```bash
# 1. Rotate the secret IMMEDIATELY (the old one is in git history forever)
# 2. Use git-filter-repo to scrub it from history
pip install git-filter-repo
git filter-repo --invert-paths --path <file-with-secret>
# 3. Force-push
git push --force
```

### "My local DB is corrupted"

```bash
# Delete the SQLite file — it'll be recreated on next backend start
rm backend/data/ainotetaker.db
# Note: you'll lose any local conversations. Use Postgres for anything important.
```

### "Everything is on fire"

```bash
# Nuke and rebuild
make clean-all
make setup
```
