#!/usr/bin/env python
"""
Verifica se STATIC_ASSET_VERSION contém o SHA atual do repositório e imprime status.
Uso:
  powershell> set DJANGO_SETTINGS_MODULE=settings.dev
  powershell> python scripts/verify_asset_version.py

Saída esperada:
  STATIC_ASSET_VERSION=abc123-20251026130522
  GIT_SHA=abc123
  OK: versão contém SHA.
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
    print(f"Erro ao inicializar Django: {e}")
    sys.exit(2)

from django.conf import settings  # noqa: E402


def git_sha() -> str:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
        return sha or "nosha"
    except Exception:
        return "nosha"


def main() -> None:
    sha = git_sha()
    version = getattr(settings, "STATIC_ASSET_VERSION", "undefined")
    print(f"STATIC_ASSET_VERSION={version}")
    print(f"GIT_SHA={sha}")
    if version.startswith(sha):
        print("OK: versão contém SHA.")
    else:
        print("WARN: versão não começa com SHA atual. Reinicie servidor ou verifique se está em detached HEAD.")


if __name__ == "__main__":
    main()
