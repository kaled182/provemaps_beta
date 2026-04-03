#!/usr/bin/env python
"""
Gera um snapshot JSON das fusões de fibra antes da migração multi-hop.

Uso:
    python scripts/backup_fiber_fusions.py [--output caminho.json]

O script delega para o comando "audit_fiber_fusions" e salva o arquivo em
"database/backups/" por padrão. Pode ser executado tanto antes quanto depois
Da migração; antes dela, o comando coleta dados a partir dos campos legados
De FiberStrand.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import django
from django.core.management import call_command

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
DEFAULT_OUTPUT_DIR = BASE_DIR / "database" / "backups"
DEFAULT_SETTINGS = os.environ.get("DJANGO_SETTINGS_MODULE", "settings.dev")


def configure_django(settings_module: str) -> None:
    """Prepara o ambiente Django para executar comandos de management."""
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
    django.setup()


def build_default_output() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_OUTPUT_DIR / f"fiber_fusions_snapshot_{timestamp}.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exporta snapshot das fusões para validação pré-migração.",
    )
    parser.add_argument(
        "--output",
        dest="output",
        type=Path,
        help="Caminho do arquivo JSON de saída (default: database/backups/...).",
    )
    parser.add_argument(
        "--settings",
        dest="settings",
        default=DEFAULT_SETTINGS,
        help="Módulo de settings Django (default: settings.dev).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_django(args.settings)

    output_path = args.output or build_default_output()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Gerando snapshot de fusões...")
    call_command("audit_fiber_fusions", baseline_out=str(output_path))
    print(f"Snapshot salvo em {output_path}")


if __name__ == "__main__":
    main()
