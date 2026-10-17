# Test Fixtures

> **Role tag:** `qa`
> **Owner:** `role-qa`

---

## What goes here

Test fixtures are *test data* that the test code consumes. They are
distinct from test code:

- **Test code** is the pytest / playwright / jest / node:test
  functions. It lives next to the code: `backend/tests/`, `e2e/tests/`,
  `mobile/__tests__/`, `electron/tests/`.
- **Test fixtures** are the *data* the test code uses: a sample user
  record, a sample audio file, a sample conversation, a sample
  question, a sample answer.

This folder is the home for fixtures that:

1. Are too large to inline in a test file (multi-MB audio, multi-KB
   conversation transcripts)
2. Are reused across multiple test files
3. Need version control (a sample recording that represents a known
   good state)

---

## Conventions

- **Synthetic data only.** No real user data, ever. If you find
  yourself wanting to commit a real `users.json` for a test, *don't*
  — synthesize one with the right shape instead.
- **No real API keys.** All keys are placeholders
  (`sk-test-xxxxxxxx`).
- **No real PII.** Names, emails, and phone numbers in fixtures are
  obviously-fake (`Test User <test@example.com>`).
- **One fixture per file (or folder).** Don't dump 50 sample users in
  one JSON file; split them by feature.
- **Schema-validated.** Fixtures that represent DB rows have a
  corresponding `schema.json` in the same folder that the tests can
  validate against.

---

## Folder layout

```
qa/fixtures/
├── README.md                  # this file
├── users/                     # sample user records
├── conversations/             # sample interview transcripts
├── recordings/                # sample audio files
├── documents/                 # sample uploaded documents
└── api-keys/                  # placeholder BYOK keys
```

Each subfolder has its own README describing the schema and the
"how to use" pattern.

---

## How to load a fixture in a test

### pytest (backend)

```python
# backend/tests/conftest.py
import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[2] / "qa" / "fixtures"

@pytest.fixture
def sample_user():
    return json.loads((FIXTURES / "users" / "sample_user.json").read_text())
```

### Playwright (e2e)

```js
// e2e/tests/...spec.js
import { test, expect } from '@playwright/test';
import path from 'path';

const FIXTURES = path.resolve(__dirname, '../../qa/fixtures');

test('login with sample user', async ({ page }) => {
  const user = require(path.join(FIXTURES, 'users', 'sample_user.json'));
  // ...
});
```

### Jest (mobile)

```js
// mobile/__tests__/...test.js
import sampleUser from '../../qa/fixtures/users/sample_user.json';

test('renders user profile', () => {
  // ...
});
```

---

## Adding a new fixture

1. Decide which subfolder it belongs in.
2. Add the fixture file (JSON, audio, etc.).
3. Add a `README.md` in the same subfolder describing the schema
   (and a `schema.json` if the fixture represents a DB row).
4. Add a usage example to the test file that consumes it.
5. If the fixture changes the test environment, update
   `qa/README.md` and `docs/qa/test-environment.md`.

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
