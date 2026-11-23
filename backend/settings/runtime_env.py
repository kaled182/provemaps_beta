"""Carrega as variáveis de e-mail do `database/runtime.env` (escritas pelo gateway
SMTP em `setup_app`) para o ambiente, sem sobrepor o que já lá está.

Partilhado por `settings.dev` e `settings.prod` (EV-0037): antes só o dev o fazia,
e trocar a produção para `settings.prod` deixaria o e-mail sem configuração.
"""

from __future__ import annotations

import os
from pathlib import Path

EMAIL_KEYS = frozenset(
    {
        "EMAIL_BACKEND",
        "EMAIL_HOST",
        "EMAIL_PORT",
        "EMAIL_HOST_USER",
        "EMAIL_HOST_PASSWORD",
        "EMAIL_USE_TLS",
        "EMAIL_USE_SSL",
        "DEFAULT_FROM_EMAIL",
        "SERVER_EMAIL",
    }
)


def load_runtime_email_env(database_dir: Path) -> None:
    path = os.getenv("ENV_FILE_PATH") or str(Path(database_dir) / "runtime.env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as handler:
        for raw_line in handler:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key not in EMAIL_KEYS or key in os.environ:
                continue
            os.environ[key] = value.strip().strip("\"'").strip()
