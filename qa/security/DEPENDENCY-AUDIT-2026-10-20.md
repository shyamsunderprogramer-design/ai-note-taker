# Dependency audit — 2026-10-20

The required [CI dependency audit](https://github.com/shyamsunderprogramer-design/ai-note-taker/actions/runs/39514409219/job/118943415297)
reported nine advisories in the existing runtime requirements during the website
artwork update. No audit exclusions or workflow bypasses were added.

| Package | Previous pin | Updated pin | Findings in the audit |
| --- | --- | --- | --- |
| certifi | 2026.2.25 | 2026.10.19 | PYSEC-2026-4320 |
| Pillow | 12.3.0 | 13.0.0 | CVE-2026-112895, CVE-2026-112400, CVE-2026-112397, CVE-2026-112896, CVE-2026-112897, CVE-2026-112395, CVE-2026-112404, CVE-2026-112899 |

The audit identifies these versions as fixes. Verified against the official
[certifi release](https://github.com/certifi/python-certifi/releases/tag/2026.10.19)
and [Pillow 13 release notes](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html).
Pillow 13 supports Python 3.11+, compatible with the repository's Python 3.12.15.
The application does not use the removed Pillow APIs listed in those release notes.

Runtime, cloud and lightweight test requirements now use the patched certifi
version. Runtime and test requirements pin Pillow 13.0.0.

## Compatibility checks

- Installed both new wheels in an isolated temporary overlay.
- Backend suite with those exact versions: **1,653 passed, 59 skipped**.
- Added real PNG, JPEG and WebP decoding through the OCR fallback, including
  grayscale conversion; only the external OCR binary is mocked.
- Loaded the patched certifi CA bundle into a Python SSL context successfully.
- Website image exports use Chromium and are independent of these Python packages.

These pins affect future installs and builds. Existing published desktop installers
were not rebuilt as part of the website update.
