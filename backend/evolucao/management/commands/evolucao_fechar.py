"""Fecha os itens que o Git diz estarem em produção (ADR 0006 §4.4).

Lê de stdin (ou `--ficheiro`) o JSON que `scripts/evolucao_fechados.sh` produz —
`[{"codigo","commit","mensagem","deploy_em"}]` — e marca cada item `feito` com `fechado_por`.
Idempotente: a primeira observação ganha. Falha em silêncio (sai a 0) por ser chamado por
hook/make; o que fez, diz no stdout.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

from evolucao.usecases import fechar_por_commit


def _deploy_em(valor: str | None) -> datetime:
    if valor:
        try:
            dt = datetime.fromisoformat(valor)
            return dt if dt.tzinfo else timezone.make_aware(dt, timezone.utc)
        except ValueError:
            pass
    return timezone.now()


def aplicar(entradas: list[dict]) -> list[str]:
    fechados: list[str] = []
    for e in entradas:
        codigo = str(e.get("codigo", "")).strip()
        if not codigo:
            continue
        item = fechar_por_commit(
            codigo=codigo,
            commit=str(e.get("commit", "")),
            mensagem=str(e.get("mensagem", "")),
            deploy_em=_deploy_em(e.get("deploy_em")),
        )
        if item is not None:
            fechados.append(codigo)
    return fechados


class Command(BaseCommand):
    help = "Fecha itens da Central a partir do JSON de scripts/evolucao_fechados.sh (stdin)."

    def add_arguments(self, parser):
        parser.add_argument("--ficheiro", default="", help="JSON a ler em vez do stdin.")

    def handle(self, *args, **options):
        try:
            bruto = (
                Path(options["ficheiro"]).read_text(encoding="utf-8")
                if options["ficheiro"]
                else sys.stdin.read()
            )
            entradas = json.loads(bruto or "[]")
            if not isinstance(entradas, list):
                raise ValueError("esperava uma lista JSON")
            fechados = aplicar(entradas)
            self.stdout.write(
                f"{len(fechados)} item(ns) fechado(s)"
                + (f": {', '.join(fechados)}" if fechados else "")
            )
        except Exception as exc:  # fail-silent: um hook que rebenta é desligado
            self.stderr.write(f"evolucao_fechar: {exc}")
