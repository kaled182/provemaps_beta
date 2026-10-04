"""Semeia a Central a partir do quadro manual do `CLAUDE.md` (ADR 0006 §4.8).

Idempotente por `codigo`: correr duas vezes não duplica. Sem `--atualizar`, um item que já
exista não é tocado (a triagem feita na Central vence o texto do quadro).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from evolucao.models import EvolucaoContador, EvolucaoItem

_ITEM = re.compile(r"^- `(EV-\d{4})` \*\*(.+?)\*\* · (.*)$")
_PRIORIDADE = re.compile(r"\bP([1-4])\b")
_SECCAO = re.compile(r"^\*\*(A fazer|Entrada|Feito)")
ETIQUETA_MIGRACAO = "migrado-do-claude-md"


def parse_quadro(texto: str) -> list[dict[str, Any]]:
    """Cada linha `- \\`EV-NNNN\\` **título** · …` do bloco EVOLUCAO vira um item; a secção
    (`**A fazer`, `**Entrada`, `**Feito`) decide o estado; `Ideias` no cabeçalho ou `· Ideia ·`
    na linha decide o tipo; `P1..P4` é a prioridade; itens da Entrada são do agente, com a
    linha inteira como evidência."""
    inicio = texto.find("<!-- EVOLUCAO:INICIO")
    fim = texto.find("<!-- EVOLUCAO:FIM")
    bloco = texto[inicio:fim] if inicio >= 0 and fim > inicio else texto
    itens: list[dict[str, Any]] = []
    estado, tipo_seccao = "entrada", "problema"
    for linha in bloco.splitlines():
        m_sec = _SECCAO.match(linha.strip())
        if m_sec:
            estado = {"A fazer": "a_fazer", "Entrada": "entrada", "Feito": "feito"}[m_sec.group(1)]
            tipo_seccao = "ideia" if "Ideias" in linha else "problema"
            continue
        m = _ITEM.match(linha.strip())
        if not m:
            continue
        codigo, titulo, resto = m.groups()
        campos = [c.strip() for c in resto.split(" · ")]
        tipo = "ideia" if tipo_seccao == "ideia" or "Ideia" in campos[:2] else "problema"
        m_p = _PRIORIDADE.search(" ".join(campos[:2]))
        prioridade = int(m_p.group(1)) if m_p else None
        origem = "agente" if estado == "entrada" else "humano"
        item: dict[str, Any] = {
            "codigo": codigo,
            "titulo": titulo.strip()[:200],
            "descricao": resto.strip(),
            "tipo": tipo,
            "estado": estado,
            "prioridade": prioridade,
            "origem": origem,
            "evidencia": (
                {"fonte": "CLAUDE.md", "linha": resto.strip()} if origem == "agente" else None
            ),
            "etiquetas": [ETIQUETA_MIGRACAO],
            "fechado_por": None,
        }
        if estado == "feito":
            m_f = re.search(r"fechado (?:em|no) `?([^`·]+)`?", resto)
            item["fechado_por"] = {
                "commit": "",
                "mensagem": (m_f.group(1).strip() if m_f else resto.strip())[:200],
                "deploy_em": None,
                "fonte": "CLAUDE.md",
            }
        itens.append(item)
    return itens


def semear(itens: list[dict[str, Any]], *, atualizar: bool = False) -> tuple[int, int]:
    """Escreve os itens por `codigo`; devolve (criados, atualizados). Ajusta o contador para
    o maior número visto, para o próximo item novo não colidir."""
    criados = atualizados = 0
    maior = 0
    with transaction.atomic():
        for it in itens:
            maior = max(maior, int(it["codigo"].split("-")[1]))
            existente = EvolucaoItem.objects.filter(codigo=it["codigo"]).first()
            if existente is None:
                EvolucaoItem.objects.create(**it)
                criados += 1
            elif atualizar:
                for k, v in it.items():
                    setattr(existente, k, v)
                existente.save()
                atualizados += 1
        contador, _ = EvolucaoContador.objects.get_or_create(pk=1)
        if contador.ultimo_numero < maior:
            contador.ultimo_numero = maior
            contador.save(update_fields=["ultimo_numero"])
    return criados, atualizados


class Command(BaseCommand):
    help = "Semeia a Central de Evolução a partir do quadro do CLAUDE.md (idempotente por código)."

    def add_arguments(self, parser):
        parser.add_argument("--ficheiro", default=str(Path(settings.BASE_DIR) / "CLAUDE.md"))
        parser.add_argument(
            "--atualizar", action="store_true", help="Sobrescreve itens já existentes."
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        caminho = Path(options["ficheiro"])
        if not caminho.exists():
            raise CommandError(f"Ficheiro não encontrado: {caminho}")
        itens = parse_quadro(caminho.read_text(encoding="utf-8"))
        if not itens:
            raise CommandError("Nenhum item `EV-NNNN` encontrado no bloco EVOLUCAO.")
        if options["dry_run"]:
            for it in itens:
                self.stdout.write(
                    f"{it['codigo']} [{it['estado']}/{it['tipo']}/P{it['prioridade'] or '-'}] {it['titulo'][:70]}"
                )
            return
        criados, atualizados = semear(itens, atualizar=options["atualizar"])
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(itens)} itens lidos: {criados} criados, {atualizados} atualizados."
            )
        )
