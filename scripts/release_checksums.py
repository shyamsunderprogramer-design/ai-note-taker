"""Require the full desktop artifact set and hash the exact published filenames."""
import hashlib
import sys
from pathlib import Path


def checksums(directory):
    expected = ["*-Setup-*-win-x64.exe", "*-win-x64.exe", "*.AppImage", "*.deb",
                "*-mac-arm64.zip", "*-mac-x64.zip"]
    installers = sorted(p for p in directory.iterdir() if p.suffix in {".exe", ".AppImage", ".deb", ".zip"})
    if len(installers) != 6 or any(not list(directory.glob(pattern)) for pattern in expected):
        raise ValueError("Expected six Windows, Linux, Apple Silicon and Intel Mac installers")
    lines = []
    for installer in installers:
        if not installer.is_file() or installer.is_symlink() or installer.stat().st_size == 0:
            raise ValueError(f"Invalid installer: {installer.name}")
        with installer.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        lines.append(f"{digest}  {installer.name}\n")
    (directory / "SHA256SUMS.txt").write_text("".join(lines))
    print(f"Verified {len(installers)} installers; SHA256SUMS.txt written")


if __name__ == "__main__":
    checksums(Path(sys.argv[1]))
