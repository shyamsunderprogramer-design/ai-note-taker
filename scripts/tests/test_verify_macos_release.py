import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify_macos_release as verifier

TEAM = "TESTTEAM12"
SIGNATURE = f"""CodeDirectory v=20500 size=123 flags=0x10000(runtime) hashes=1+7 location=embedded
Authority=Developer ID Application: ANT Test ({TEAM})
Authority=Developer ID Certification Authority
TeamIdentifier={TEAM}
Timestamp=18 Oct 2026 at 02:00:00
"""


class SignatureTests(unittest.TestCase):
    def test_developer_id_timestamp_runtime_and_team_are_all_required(self):
        verifier.validate_signature(SIGNATURE, TEAM)
        for details in [
            SIGNATURE.replace("Developer ID Application", "Apple Development"),
            SIGNATURE.replace(f"TeamIdentifier={TEAM}", "TeamIdentifier=OTHERTEAM1"),
            SIGNATURE.replace("Timestamp=", "Signed Time="),
            SIGNATURE.replace("0x10000(runtime)", "0x0(none)"),
        ]:
            with self.subTest(details=details), self.assertRaises(RuntimeError):
                verifier.validate_signature(details, TEAM)
        with self.assertRaises(ValueError):
            verifier.validate_signature(SIGNATURE, "")


class ArchiveTests(unittest.TestCase):
    def run_verification(self, *, fail_at=None, assessment="source=Notarized Developer ID", app_count=1):
        calls = []

        def run(args, **kwargs):
            calls.append(args)
            if args[0] == "/usr/bin/ditto":
                for i in range(app_count):
                    (Path(args[-1]) / f"ANT {i}.app/Contents/Resources").mkdir(parents=True)
            if fail_at == len(calls):
                raise subprocess.CalledProcessError(1, args)
            output = SIGNATURE if "--display" in args else assessment if "--assess" in args else ""
            return subprocess.CompletedProcess(args, 0, "", output)

        with patch.object(verifier.subprocess, "run", side_effect=run), patch.object(verifier, "verify_runtime") as runtime:
            try:
                verifier.verify_archive(Path("release with spaces.zip"), TEAM)
            finally:
                self.calls = calls
                self.runtime_calls = runtime.call_args_list

    def test_checks_extracted_download_and_checks_signature_again_after_runtime_smoke(self):
        self.run_verification()
        self.assertEqual(self.calls[0][3], "release with spaces.zip")
        self.assertIn("--verify", self.calls[1])
        self.assertIn("--display", self.calls[2])
        self.assertIn("stapler", self.calls[3])
        self.assertIn("--assess", self.calls[4])
        self.assertIn("--verify", self.calls[5])
        self.assertEqual(len(self.runtime_calls), 1)
        self.assertEqual(self.runtime_calls[0].args[0], Path(self.calls[1][-1]) / "Contents/Resources")

    def test_any_signature_staple_or_gatekeeper_failure_stops_verification(self):
        for position in [2, 3, 4, 5]:
            with self.subTest(position=position), self.assertRaises(subprocess.CalledProcessError):
                self.run_verification(fail_at=position)
            self.assertEqual(self.runtime_calls, [])
            self.assertEqual(len(self.calls), position)

    def test_post_smoke_signature_failure_is_not_ignored(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_verification(fail_at=6)
        self.assertEqual(len(self.runtime_calls), 1)

    def test_gatekeeper_must_report_notarized_developer_id(self):
        with self.assertRaisesRegex(RuntimeError, "Gatekeeper"):
            self.run_verification(assessment="source=Unnotarized Developer ID")
        self.assertEqual(self.runtime_calls, [])

    def test_empty_or_ambiguous_archive_is_rejected(self):
        for count in [0, 2]:
            with self.subTest(count=count), self.assertRaisesRegex(RuntimeError, "Expected one app"):
                self.run_verification(app_count=count)
            self.assertEqual(self.runtime_calls, [])


if __name__ == "__main__":
    unittest.main()
