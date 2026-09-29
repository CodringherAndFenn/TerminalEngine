#!/usr/bin/env python3
"""
packaging/release_python.py -- a portable Python for Linux release builds.

A Linux build carries the Python it was built with, and only runs on
systems whose C library (glibc) is at least as new as that Python's. A
rolling-release distro's own Python (e.g. glibc 2.44) makes builds that
won't start on the Steam Deck or older distros. The python-build-standalone
builds target glibc 2.17 (2012), so builds made with them run nearly
anywhere.

    python3 ascii_adventurers/packaging/release_python.py
    ascii_adventurers/.release/venv/bin/python ascii_adventurers/packaging/build.py

Downloads the pinned release below (checked against its published SHA-256
sums) into ascii_adventurers/.release/ (ignored by git), makes a venv from
it and installs requirements-dev.txt. Safe to run again: it skips what's
already there. Linux x86-64 only (Windows Pythons are portable already).
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

PBS_RELEASE = "20260924"            # astral-sh/python-build-standalone release tag
PY_VERSION = "3.14.7"
ASSET = f"cpython-{PY_VERSION}+{PBS_RELEASE}-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"
BASE = f"https://github.com/astral-sh/python-build-standalone/releases/download/{PBS_RELEASE}"

GAME = Path(__file__).resolve().parent.parent
RELEASE = GAME / ".release"
PYTHON = RELEASE / "python" / "bin" / "python3"
VENV = RELEASE / "venv"


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def expected_sha256() -> str:
    sums = _get(f"{BASE}/SHA256SUMS").decode()
    for line in sums.splitlines():
        digest, _, name = line.strip().partition("  ")
        if name == ASSET:
            return digest
    raise SystemExit(f"{ASSET} is not listed in the release's SHA256SUMS")


def fetch_python() -> None:
    if PYTHON.exists():
        print(f"portable Python already there: {PYTHON}")
        return
    RELEASE.mkdir(exist_ok=True)
    print(f"downloading {ASSET} ...")
    blob = _get(f"{BASE}/{ASSET}")
    digest = hashlib.sha256(blob).hexdigest()
    if digest != expected_sha256():
        raise SystemExit("checksum mismatch: download corrupted or tampered with; nothing installed")
    archive = RELEASE / ASSET
    archive.write_bytes(blob)
    with tarfile.open(archive) as tar:
        tar.extractall(RELEASE, filter="data")      # -> .release/python/
    archive.unlink()
    print(f"portable Python: {PYTHON}")


def make_venv() -> None:
    if not (VENV / "bin" / "python").exists():
        subprocess.run([str(PYTHON), "-m", "venv", str(VENV)], check=True)
    subprocess.run([str(VENV / "bin" / "python"), "-m", "pip", "install", "--quiet",
                    "-r", str(GAME / "requirements-dev.txt")], check=True)
    print(f"release venv ready: {VENV}\n"
          f"build with: {VENV / 'bin' / 'python'} {GAME / 'packaging' / 'build.py'}")


def main() -> int:
    if not sys.platform.startswith("linux"):
        print("only needed on Linux: use a python.org Python elsewhere")
        return 0
    fetch_python()
    make_venv()
    return 0


if __name__ == "__main__":
    sys.exit(main())
