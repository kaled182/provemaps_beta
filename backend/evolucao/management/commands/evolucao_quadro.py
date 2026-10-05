"""Reescreve o bloco EVOLUCAO do `CLAUDE.md` a partir da Central (ADR 0006 §4.5).

Falha em silêncio por desenho (sai a 0 sem tocar em nada) quando não há ficheiro, marcadores
ou base: é chamado por `make evolucao-sync`/hook, e um hook que rebenta é desligado.
`--imprimir` imprime o bloco em vez de escrever.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from evolucao.models import EvolucaoItem
from evolucao.quadro import LinhaQuadro, render, substituir_bloco


def linhas_da_base(agora) -> list[LinhaQuadro]:
    """Itens abertos e os feitos ainda sem `deploy_em`; o histórico já implantado fica fora."""
    qs = EvolucaoItem.objects.exclude(estado="recusado").select_related("autor")
    saida: list[LinhaQuadro] = []
    for item in qs:
        fechado = item.fechado_por or {}
        deploy_em = fechado.get("deploy_em") if item.estado == "feito" else None
        if item.estado == "feito" and deploy_em:
            continue
        saida.append(
            LinhaQuadro(
                codigo=item.codigo,
                titulo=item.titulo,
                estado=item.estado,
                tipo=item.tipo,
                prioridade=item.prioridade,
                autor=item.autor.get_username() if item.autor else item.origem,
                idade_dias=max((agora - item.criado_em).days, 0),
                deploy_em=deploy_em,
            )
        )
    return saida


def escrever(ficheiro: Path, bloco: str) -> bool:
    """Troca o bloco; devolve True só se o ficheiro mudou mesmo (o mtime importa a quem o vigia)."""
    antes = ficheiro.read_text(encoding="utf-8")
    depois = substituir_bloco(antes, bloco)
    if depois == antes:
        return False
    ficheiro.write_text(depois, encoding="utf-8")
    return True


class Command(BaseCommand):
    help = "Regenera o bloco EVOLUCAO do CLAUDE.md a partir da Central de Evolução."

    def add_arguments(self, parser):
        parser.add_argument("--ficheiro", default=str(Path(settings.BASE_DIR) / "CLAUDE.md"))
        parser.add_argument(
            "--imprimir", action="store_true", help="Imprime o bloco em vez de escrever."
        )

    def handle(self, *args, **options):
        try:
            bloco = render(linhas_da_base(timezone.now()), agora=timezone.now())
            if options["imprimir"]:
                self.stdout.write(bloco)
                return
            ficheiro = Path(options["ficheiro"])
            if not ficheiro.is_file():
                self.stderr.write(f"evolucao_quadro: {ficheiro} não existe — nada escrito")
                return
            mudou = escrever(ficheiro, bloco)
            self.stdout.write("quadro atualizado" if mudou else "quadro já estava em dia")
        except Exception as exc:  # fail-silent: um hook que rebenta é desligado
            self.stderr.write(f"evolucao_quadro: {exc}")
