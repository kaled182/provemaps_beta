#!/usr/bin/env python
"""
Check whether STATIC_ASSET_VERSION includes the current repository SHA
and report status.
Usage:
    powershell> set DJANGO_SETTINGS_MODULE=settings.dev
    powershell> python scripts/verify_asset_version.py

Expected output:
    STATIC_ASSET_VERSION=abc123-20251026130522
    GIT_SHA=abc123
    OK: version contains SHA.
"""
from __future__ import annotations
import os
import subprocess
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.dev")

try:
    import django  # type: ignore
    django.setup()
except Exception as e:
    print(f"ERROR initializing Django: {e}")
    sys.exit(2)

from django.conf import settings  # noqa: E402


def git_sha() -> str:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"]
        ).decode().strip()
        return sha or "nosha"
    except Exception:
        return "nosha"


def main() -> None:
    sha = git_sha()
    version = getattr(settings, "STATIC_ASSET_VERSION", "undefined")
    print(f"STATIC_ASSET_VERSION={version}")
    print(f"GIT_SHA={sha}")
    if version.startswith(sha):
        print("OK: Version string contains current SHA")
    else:
        print(
            "WARN: Version does not start with current SHA. Restart the server"
            "or confirm the repository is not in a detached HEAD state."
        )


if __name__ == "__main__":
    main()
