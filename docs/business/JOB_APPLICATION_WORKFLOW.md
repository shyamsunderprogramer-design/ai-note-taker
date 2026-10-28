# Job applications and browser extension

This guide combines the application workflow, job-portal integration notes, and extension data/permission explanation.

## Workflow

1. [Set up ANT](../../README.md#set-up-from-source), sign in, and keep the backend running.
2. Open Job Tracker from the app menu and organize roles you are considering.
3. Add a listing manually or use the browser extension's save action where supported.
4. Review extracted title, company, location, and description before relying on them.
5. Track application status and use the matching resume/job description for preparation.

Websites change their page layouts. Extraction support for a portal should be checked against a real listing; older “fully supported” tables are historical reports.

## Extension setup

Use the workspace in `apps/ant-chrome-extension/`:

1. Open `chrome://extensions/` in Chrome.
2. Enable Developer Mode and choose **Load unpacked**.
3. Select `apps/ant-chrome-extension/`, which contains the extension manifest.
4. Check its connection to the local backend and complete any authentication the flow requires.

The repository also contains a legacy `chrome-extension/` directory. Use the workspace selected above for this guide rather than mixing files from the two implementations.

## Data and permissions

The documented save workflow reads information from a page the user is viewing and sends listing data to ANT. Inspect the actual [manifest](../../apps/ant-chrome-extension/manifest.json) and [extension workspace](../../apps/ant-chrome-extension/) for host permissions and behavior before deployment.

Read-only page extraction and a user click do not guarantee that a third-party account can never be restricted. The older safety documents made stronger guarantees than the implementation can establish. Captured data goes to the configured backend; a remotely configured backend is not local storage.

## Implementation boundaries

| Area | Reference |
| --- | --- |
| Job-tracker UI | [job-tracker.js](../../apps/web/job-tracker.js) |
| Job routes | [jobs.py](../../backend/routes/jobs.py) |
| Career tools | [career.py](../../backend/routes/career.py) |
| Auto-apply routes | [auto_apply.py](../../backend/routes/auto_apply.py) |
| Resume guidance | [Resume review](resume-builder/README.md) |
| Security boundaries | [Threat model](../devsecops/security/threat-model.md) |

Saving a listing, tailoring a resume, and automatically submitting an application are distinct capabilities. Check the relevant route and UI before treating an integration or automation plan as implemented.

## Troubleshooting

If the save button is missing, check the current page layout and extension permissions. If saving fails, check the backend address, sign-in state, connection status, and required fields. Verify the saved record in Job Tracker after a successful save.

## Historical references

The overlapping source documents are preserved in one [dated reference record](../archive/job-workflow.md). Use that record for original technical examples and planning context, not current setup or status.
