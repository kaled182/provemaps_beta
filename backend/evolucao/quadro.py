"""Rende o bloco «QUADRO — o que falta» do `CLAUDE.md` a partir da Central (ADR 0006 §4.5).

Funções PURAS, sem base: a decisão do que mostrar e por que ordem vive aqui e testa-se sem
Postgres. A leitura da base está no comando `evolucao_quadro`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

MARCADOR_INICIO_PREFIXO = "<!-- EVOLUCAO:INICIO"
MARCADOR_INICIO = "<!-- EVOLUCAO:INICIO — gerado por `manage.py evolucao_quadro` (ADR 0006). NÃO editar à mão. -->"
MARCADOR_FIM = "<!-- EVOLUCAO:FIM -->"

#: O quadro é do que falta e do que ainda não chegou a produção; o resto fica na Central.
_SECCOES = (
    ("a_fazer", "A fazer"),
    ("aceite", "Aceites, por priorizar"),
    ("entrada", "Entrada, por triar"),
)
#: Um defeito a morder e uma vontade por fazer não se lêem com a mesma régua: os problemas
#: vêm sempre primeiro.
_TIPOS = (("problema", "🐛 Problemas"), ("ideia", "💡 Ideias"))


@dataclass(frozen=True)
class LinhaQuadro:
    codigo: str
    titulo: str
    estado: str
    tipo: str
    prioridade: int | None
    autor: str
    idade_dias: int
    #: `fechado_por.deploy_em` quando o fecho já foi observado em produção; `None` = aguarda.
    deploy_em: str | None = None


def _ordem(linha: LinhaQuadro) -> tuple[int, str]:
    """A ordem de trabalho: prioridade (nulos no fim) e depois o código menor (o mais velho)."""
    return (linha.prioridade or 99, linha.codigo)


def render(linhas: Sequence[LinhaQuadro], *, agora: datetime) -> str:
    partes: list[str] = [
        MARCADOR_INICIO,
        "## 📌 QUADRO — o que falta",
        "",
        # Data e NÃO minuto: só se grava quando o bloco difere, e um carimbo ao minuto
        # fá-lo diferir sempre.
        f"> Gerado da Central de Evolução a {agora:%Y-%m-%d} (`make evolucao-quadro`). Para mexer, use",
        "> `/system/evolucao` ou a API `/api/v1/evolucao/` — uma edição à mão aqui desaparece na",
        "> próxima geração. A ordem de trabalho é prioridade, depois código; problemas antes de ideias.",
        "",
    ]
    abertas = [x for x in linhas if x.estado in {e for e, _ in _SECCOES}]
    if not abertas:
        partes += ["**Nada aberto.**", ""]
    for estado, titulo in _SECCOES:
        do_estado = [x for x in abertas if x.estado == estado]
        if not do_estado:
            continue
        partes += [f"**{titulo} ({len(do_estado)})**", ""]
        for tipo, rotulo in _TIPOS:
            grupo = sorted((x for x in do_estado if x.tipo == tipo), key=_ordem)
            if not grupo:
                continue
            partes.append(rotulo)
            for x in grupo:
                prio = f"P{x.prioridade}" if x.prioridade else "por triar"
                partes.append(
                    f"- `{x.codigo}` **{x.titulo}** · {prio} · {x.autor} · há {x.idade_dias} dias"
                )
            partes.append("")
    aguardam = sorted(
        (x for x in linhas if x.estado == "feito" and not x.deploy_em), key=lambda x: x.codigo
    )
    if aguardam:
        partes += [
            f"**Feito — aguarda deploy ({len(aguardam)})** (sai daqui quando o commit `fecha` chegar a produção)",
            "",
        ]
        partes += [f"- `{x.codigo}` **{x.titulo}**" for x in aguardam]
        partes.append("")
    partes.append(MARCADOR_FIM)
    return "\n".join(partes)


def substituir_bloco(texto: str, bloco: str) -> str:
    """Troca o que está entre os marcadores (o de início pode ter qualquer sufixo — o quadro
    manual tinha o seu). Sem marcadores, devolve intacto: não se adivinha onde inserir."""
    i = texto.find(MARCADOR_INICIO_PREFIXO)
    j = texto.find(MARCADOR_FIM)
    if i == -1 or j == -1 or j < i:
        return texto
    return texto[:i] + bloco + texto[j + len(MARCADOR_FIM) :]
