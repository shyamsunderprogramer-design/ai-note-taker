# Performance Scripts & Budgets

> **Role tag:** `qa`
> **Owner:** `role-qa`

---

## What goes here

Two related artifacts:

1. **Perf scripts** — k6 (or wrk, or ab) scripts that load-test a
   specific endpoint or user flow.
2. **Perf budgets** — the SLO table for that endpoint or flow. The
   budget is the "if p95 latency exceeds X, the PR is a regression"
   rule that the CI can enforce.

A perf script and its budget live next to each other so that when
the script breaks (because the endpoint changed), the budget is
right there to update.

---

## Folder layout

```
qa/performance/
├── README.md                  # this file
├── backend/                   # perf scripts for backend endpoints
│   ├── auth-login.js          # k6 script
│   └── auth-login.md          # budget + history
├── web/                       # perf scripts for the web app
│   ├── vite-build-time.js     # custom script (Vite build duration)
│   └── vite-build-time.md
└── mobile/                    # perf scripts for the mobile app
    ├── cold-start-time.js     # RN cold-start duration
    └── cold-start-time.md
```

Each perf script has a sibling `.md` with:
- The SLO (p50 / p95 / p99 latency, error rate, throughput)
- The historical numbers (last 10 runs)
- The CI gate (if the budget is exceeded, the PR is blocked)

---

## Conventions

- **One script per endpoint (or user flow).** Don't combine.
- **Script is runnable from CI.** `k6 run qa/performance/backend/auth-login.js` should "just work" once the backend is up.
- **Budget is a hard gate, not a soft target.** If the script exceeds
  the budget, CI fails. Bumping the budget is a PR in itself.
- **History is committed.** `qa/performance/backend/auth-login.md`
  has a table of last 10 runs; the CI appends a row on each run.
- **No real user data in the script.** Use synthetic users from
  `qa/fixtures/`.

---

## Current perf budgets (snapshot 2026-06-11)

| Endpoint / flow | p50 | p95 | p99 | error rate | source |
|---|---|---|---|---|---|
| `POST /auth/login` | 50ms | 200ms | 500ms | <0.1% | `qa/performance/backend/auth-login.md` |
| `POST /agents/sessions` | 100ms | 300ms | 800ms | <0.1% | (TODO) |
| `GET /auth/me` | 10ms | 50ms | 200ms | <0.1% | (TODO) |
| Vite build (full) | 8s | 15s | 30s | 0% | `qa/performance/web/vite-build-time.md` |
| Mobile cold start | 1.5s | 3s | 5s | 0% | `qa/performance/mobile/cold-start-time.md` |

These are *targets*, not measured numbers — the per-script `.md` files
are where the measured numbers live.

---

## Adding a new perf script

1. Add the script in the appropriate subfolder
   (`qa/performance/{backend,web,mobile}/`).
2. Add the budget `.md` next to it.
3. Add the script to `.github/workflows/ci.yml` (under a
   `performance` job that runs on a schedule, or on PR label).
4. Add the script to the table above.
5. Update `qa/README.md` if the script changes the test environment.

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
