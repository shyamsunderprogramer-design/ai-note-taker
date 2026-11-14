# Files by role

Use the five existing engineering roles to find files and place new work. Runtime
packages keep their established paths so imports, workspace commands, and deployment
configuration continue to work. Tests stay beside the code they exercise.

| Role | Implementation and tooling | Documentation | Charter |
| --- | --- | --- | --- |
| Backend | `backend/` core, routes, modules, libraries, migrations, and model metadata | [Backend guides](backend/README.md), `docs/architecture/` | [Backend ownership](../OWNERS.backend.md) |
| UI/UX | `apps/`, `mobile/src/`, extension clients, `electron/features/`, `electron/assets/`, `assets/design/` | [UI guides](uiux/README.md) | [UI ownership](../OWNERS.uiux.md) |
| DevOps | `scripts/`, `docker/`, `k8s/`, `infrastructure/`, `.github/workflows/`, Electron runtime/build files, mobile native projects, workspace/deploy manifests | [Operations guides](devops/README.md), `docs/releases/` | [DevOps ownership](../OWNERS.devops.md) |
| QA | `qa/`, `e2e/`, `backend/tests/`, `electron/tests/`, `mobile/__tests__/` | [QA guides](qa/README.md), `docs/qa/reports/` | [QA ownership](../OWNERS.qa.md) |
| DevSecOps | `backend/security/`, security scanning configuration, `vendor/`, `qa/security/` (with QA) | [Security guides](devsecops/README.md), root `SECURITY.md` | [Security ownership](../OWNERS.devsecops.md) |

Extension clients include `apps/ant-chrome-extension/`, `chrome-extension/`,
`browser-extension/`, and `vscode-extension/`. Electron shared runtime helpers live
in `electron/lib/` and belong to DevOps with backend review for IPC contracts.

Each role's agent instructions and memory remain in `agents/<role>/`. The
[agent index](../agents/README.md) explains their scope. Review routing is defined
in [CODEOWNERS](../.github/CODEOWNERS); later, more specific entries override earlier
directory defaults. Role team names use the existing repository convention and
must correspond to configured GitHub teams to receive review requests.

## Placement rules

- Put application code inside its existing package, grouped by feature or function.
- Put maintained engineering guides in `docs/<role>/` and link them from that role's index.
- Put original artwork in `assets/design/artwork/`, reusable design sources in
  `assets/design/source/`, and standalone UI experiments in `assets/design/prototypes/`.
  Production exports stay with the application that loads them.
- Put test evidence and harnesses in `qa/`, and historical QA assessments in
  `docs/qa/reports/`. Keep security evidence under `qa/security/`.
- Keep shared product planning, research, and historical records in `docs/business/`,
  `docs/competitive/`, `docs/research/`, `docs/shared/`, and `docs/archive/`.
- Keep repository entry points and tool-discovered configuration at the root:
  README, license, contribution/security policies, charters, package manifests,
  Dockerfile, Makefile, and hosting configuration.

Local runtime data, virtual environments, dependency installs, caches, and agent
databases remain in their tool-managed locations and are not role documentation.

## Files relocated on 2026-10-29

| Previous location | Current location |
| --- | --- |
| Tracked originals in `Ant Images/` | [`assets/design/artwork/`](../assets/design/artwork/) |
| Ignored local references in `Ant Images/` | `assets/design/local-reference/` (still ignored) |
| `temp_status_bar_logic.js` | [`assets/design/prototypes/status-bar.js`](../assets/design/prototypes/status-bar.js) |
| `testing_operational_maturity_analysis.json` | [QA assessment](qa/reports/testing_operational_maturity_analysis.json) |
| `vercel.json.md` | [Vercel configuration guide](devops/deployment/VERCEL.md) |

Historical audits retain their original paths as dated evidence. Current artwork
export tooling and navigation use the locations above.
