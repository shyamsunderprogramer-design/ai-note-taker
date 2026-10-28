# Release and production readiness

Use this checklist for a specific candidate build or deployment. The original checklist and readiness reports are historical inputs; their checked boxes, market scores, and old version numbers do not certify a new release.

## 1. Define the candidate

- [ ] Identify the commit, target branch, version, supported OS/architectures, and deployment environment.
- [ ] Describe user-visible changes and known limitations.
- [ ] Confirm which features and integrations are supported in this release.

## 2. Validate the application

- [ ] Install dependencies from the candidate checkout and run relevant backend, desktop, and web checks.
- [ ] Build the web app with `npm run web:build`.
- [ ] Verify sign-in, provider-key save, local/cloud answers, follow-ups, and saved history.
- [ ] Verify microphone, system audio, screenshots, OS permissions, and unsupported-device behavior.
- [ ] Verify stream errors, recovery, shutdown, and data persistence.
- [ ] Record failures and excluded tests; do not report a successful full gate when only focused checks passed.

See the [test strategy](../../qa/test-strategy.md), [manual test guide](../../qa/DIY_TEST_GUIDE.md), and [performance guide](../../business/PERFORMANCE.md).

## 3. Prepare data and deployment

- [ ] Set production signing/encryption keys, database configuration, authentication, and allowed origins.
- [ ] Apply and validate the intended migrations; back up persistent data and test restore.
- [ ] Check user isolation, logging, and credential handling.
- [ ] Validate only the integrations enabled for this environment.
- [ ] Define health/readiness checks, monitoring, and a rollback procedure.

Use the [deployment guide](DEPLOYMENT_GUIDE.md), [migration guide](../development/MIGRATIONS.md), and [operations runbook](../operations/OPERATIONS.md) for their respective procedures.

## 4. Build and test desktop packages

Run the relevant command from the repository root:

```bash
npm run electron:build:win
npm run electron:build:mac
npm run electron:build:linux
```

These are platform targets, not a promise that every target can be built on any host. Prepare the platform-specific Python resources required by [electron/package.json](../../../electron/package.json). Build artifacts are written under `electron/dist/`.

- [ ] Test the actual installer on each supported OS and architecture.
- [ ] Check clean install, upgrade, launch, permissions, bundled Python, and saved-data handling.
- [ ] Verify signing/notarization status and document installation behavior accurately.
- [ ] Generate checksums for the exact artifacts being distributed.
- [ ] Confirm release notes and download links match the tested artifacts.

## 5. Publish and monitor

- [ ] Confirm repository release permissions and the intended tag/target.
- [ ] Draft release notes with changes, installation guidance, known issues, and validation evidence.
- [ ] Publish the verified assets and check a downloaded copy.
- [ ] Monitor issues and deployment health.
- [ ] If a material regression appears, follow the defined rollback or patch procedure and update release notes.

## Evidence record

For each item retain the candidate commit, environment, command or manual procedure, result, and evidence location. Existing April completion reports remain references, not acceptance results for the candidate.

## Historical references

The overlapping source documents are preserved in one [dated reference record](../../archive/release-readiness.md). Use that record for original technical examples and planning context, not current setup or status.
