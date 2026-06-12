"""
Tests for the CI security-scan result parser.

The security-scan job in .github/workflows/ci.yml runs bandit and
pip-audit, then evaluates their JSON output via an inline Python
script. This test file exercises the same parse logic standalone
so we can verify the fail-detection contract without running the
full CI workflow.

The contract:
- bandit-report.json with high-severity + high-confidence findings → exit 1
- bandit-report.json with no high findings → exit 0
- pip-audit-report.json with fixable CVEs → printed but not gating (visibility)
- pip-audit-report.json with no vulns → exit 0
"""

import json
import os
import subprocess
import sys
import tempfile

import pytest

_SCRIPT = r'''
import json, sys, pathlib

failed = False

bp = pathlib.Path("bandit-report.json")
if bp.exists():
    data = json.loads(bp.read_text())
    high = [
        r for r in data.get("results", [])
        if r.get("issue_severity") == "HIGH"
        and r.get("issue_confidence") == "HIGH"
    ]
    if high:
        print(f"::error::bandit found {len(high)} high-severity findings")
        failed = True
    else:
        print("bandit: no high-severity findings")

pp = pathlib.Path("pip-audit-report.json")
if pp.exists():
    data = json.loads(pp.read_text())
    vulns = data.get("dependencies", [])
    fixable = [d for d in vulns if d.get("vulns") and any(
        v.get("fix_versions") for v in d["vulns"]
    )]
    if fixable:
        print(f"::error::pip-audit found {len(fixable)} fixable deps")
    else:
        print("pip-audit: no fixable vulns")

sys.exit(1 if failed else 0)
'''


def _run_parser(tmp_path, bandit_data=None, pip_audit_data=None):
    """Run the parser script in tmp_path with the given JSON inputs."""
    if bandit_data is not None:
        (tmp_path / "bandit-report.json").write_text(json.dumps(bandit_data))
    if pip_audit_data is not None:
        (tmp_path / "pip-audit-report.json").write_text(json.dumps(pip_audit_data))
    result = subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    return result


class TestBanditReport:
    """The parser fails the job on high-severity bandit findings."""

    def test_empty_bandit_report_passes(self, tmp_path):
        result = _run_parser(tmp_path, bandit_data={"results": []})
        assert result.returncode == 0
        assert "no high-severity findings" in result.stdout

    def test_low_severity_bandit_passes(self, tmp_path):
        result = _run_parser(tmp_path, bandit_data={
            "results": [
                {
                    "issue_severity": "LOW",
                    "issue_confidence": "HIGH",
                    "test_id": "B105",
                    "filename": "test.py",
                    "line_number": 1,
                    "issue_text": "hardcoded password",
                }
            ]
        })
        assert result.returncode == 0

    def test_high_severity_bandit_fails(self, tmp_path):
        result = _run_parser(tmp_path, bandit_data={
            "results": [
                {
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "test_id": "B102",
                    "filename": "core/main.py",
                    "line_number": 42,
                    "issue_text": "exec used",
                }
            ]
        })
        assert result.returncode == 1
        assert "high-severity" in result.stdout

    def test_high_severity_low_confidence_passes(self, tmp_path):
        """HIGH severity but LOW confidence — should not fail the build."""
        result = _run_parser(tmp_path, bandit_data={
            "results": [
                {
                    "issue_severity": "HIGH",
                    "issue_confidence": "LOW",
                    "test_id": "B102",
                    "filename": "core/main.py",
                    "line_number": 42,
                    "issue_text": "exec used",
                }
            ]
        })
        assert result.returncode == 0


class TestPipAuditReport:
    """pip-audit findings are reported but don't gate the build."""

    def test_empty_pip_audit_passes(self, tmp_path):
        result = _run_parser(tmp_path, pip_audit_data={"dependencies": []})
        assert result.returncode == 0
        assert "no fixable vulns" in result.stdout

    def test_unfixable_pip_audit_passes(self, tmp_path):
        """A CVE with no fix_versions is just a warning."""
        result = _run_parser(tmp_path, pip_audit_data={
            "dependencies": [
                {
                    "name": "starlette",
                    "version": "0.52.1",
                    "vulns": [
                        {"id": "PYSEC-2026-161", "fix_versions": []}
                    ],
                }
            ]
        })
        # The current implementation prints but does not fail on
        # unfixable vulns. (Pinning the "visibility, not gating" contract.)
        assert result.returncode == 0

    def test_fixable_pip_audit_prints_but_passes(self, tmp_path):
        """Fixable CVEs are reported but don't fail the build."""
        result = _run_parser(tmp_path, pip_audit_data={
            "dependencies": [
                {
                    "name": "urllib3",
                    "version": "2.6.3",
                    "vulns": [
                        {"id": "PYSEC-2026-142", "fix_versions": ["2.7.0"]}
                    ],
                }
            ]
        })
        # Currently non-fatal — visibility only
        assert "fixable deps" in result.stdout


class TestBothReports:
    """Both reports can be parsed together."""

    def test_clean_both_passes(self, tmp_path):
        result = _run_parser(
            tmp_path,
            bandit_data={"results": []},
            pip_audit_data={"dependencies": []},
        )
        assert result.returncode == 0

    def test_high_bandit_fails_even_with_clean_pip_audit(self, tmp_path):
        result = _run_parser(
            tmp_path,
            bandit_data={"results": [{
                "issue_severity": "HIGH",
                "issue_confidence": "HIGH",
                "test_id": "B102",
                "filename": "x.py",
                "line_number": 1,
                "issue_text": "exec",
            }]},
            pip_audit_data={"dependencies": []},
        )
        assert result.returncode == 1

    def test_missing_files_handled_gracefully(self, tmp_path):
        """No bandit/pip-audit reports present → exit 0 (nothing to fail on)."""
        result = _run_parser(tmp_path)
        assert result.returncode == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
