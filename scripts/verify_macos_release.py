"""Verify the signed, stapled app extracted from the actual macOS release ZIP."""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from verify_desktop_package import verify as verify_runtime


def validate_signature(details, team_id):
    if not re.fullmatch(r"[A-Z0-9]{10}", team_id):
        raise ValueError("A valid APPLE_TEAM_ID is required to verify the release")
    if not re.search(r"^Authority=Developer ID Application: .+", details, re.M):
        raise RuntimeError("The release is not signed with a Developer ID Application certificate")
    if not re.search(rf"^TeamIdentifier={re.escape(team_id)}$", details, re.M):
        raise RuntimeError("The release signature belongs to a different Apple team")
    if not re.search(r"^Timestamp=.+", details, re.M):
        raise RuntimeError("The release signature has no secure timestamp")
    if not re.search(r"^CodeDirectory .*flags=.*\bruntime\b", details, re.M):
        raise RuntimeError("The release does not enable Hardened Runtime")


def verify_archive(archive, team_id):
    def run(*args):
        try:
            result = subprocess.run(args, check=True, capture_output=True, text=True, timeout=300)
        except subprocess.CalledProcessError as error:
            # These commands inspect public artifacts and receive no credentials.
            print((error.stdout or "") + (error.stderr or ""), file=sys.stderr)
            raise
        return result.stdout + result.stderr

    with tempfile.TemporaryDirectory(prefix="ant-notarized-release-") as temporary:
        extracted = Path(temporary)
        run("/usr/bin/ditto", "-x", "-k", str(archive), str(extracted))
        apps = list(extracted.glob("*.app"))
        if len(apps) != 1:
            raise RuntimeError(f"Expected one app in the release ZIP; found {len(apps)}")
        app = apps[0]
        run("/usr/bin/codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app))
        validate_signature(run("/usr/bin/codesign", "--display", "--verbose=4", str(app)), team_id)
        run("/usr/bin/xcrun", "stapler", "validate", str(app))
        assessment = run("/usr/sbin/spctl", "--assess", "--type", "execute", "--verbose=4", str(app))
        if "source=Notarized Developer ID" not in assessment:
            raise RuntimeError("Gatekeeper did not identify the archive as a notarized Developer ID app")
        verify_runtime(app / "Contents/Resources")
        # Smoke tests must not change the signed app's contents.
        run("/usr/bin/codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app))
        print("Release ZIP passed Developer ID, timestamp, Hardened Runtime, staple, Gatekeeper and packaged-runtime checks")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    if sys.platform != "darwin":
        raise RuntimeError("macOS release verification must run on macOS")
    team = os.environ.get("APPLE_TEAM_ID", "")
    if not re.fullmatch(r"[A-Z0-9]{10}", team):
        raise ValueError("A valid APPLE_TEAM_ID is required to verify the release")
    archives = [args.archive] if args.archive else list((Path(__file__).resolve().parent.parent / "electron/dist").glob("*-mac-*.zip"))
    if len(archives) != 1 or not archives[0].is_file():
        raise RuntimeError("Expected exactly one macOS release ZIP")
    verify_archive(archives[0].resolve(), team)
