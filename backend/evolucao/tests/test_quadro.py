"""Quadro gerado (EV-0027b): render puro, substituição do bloco e o comando `evolucao_quadro`."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from evolucao import usecases as uc
from evolucao.management.commands.evolucao_quadro import linhas_da_base
from evolucao.quadro import MARCADOR_FIM, MARCADOR_INICIO, LinhaQuadro, render, substituir_bloco

AGORA = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def _linha(codigo, **kw):
    base = {
        "titulo": f"t {codigo}",
        "estado": "a_fazer",
        "tipo": "problema",
        "prioridade": None,
        "autor": "paulo",
        "idade_dias": 1,
    }
    base.update(kw)
    return LinhaQuadro(codigo=codigo, **base)


class RenderTests(TestCase):
    def test_vazio(self):
        bloco = render([], agora=AGORA)
        self.assertTrue(bloco.startswith(MARCADOR_INICIO))
        self.assertTrue(bloco.endswith(MARCADOR_FIM))
        self.assertIn("**Nada aberto.**", bloco)
        self.assertIn("2026-10-04", bloco)

    def test_ordem_e_seccoes(self):
        linhas = [
            _linha("EV-0003", prioridade=None),
            _linha("EV-0002", prioridade=2, idade_dias=9),
            _linha("EV-0001", prioridade=2),
            _linha("EV-0004", prioridade=1, tipo="ideia"),
            _linha("EV-0005", estado="entrada", autor="agente"),
            _linha("EV-0006", estado="feito"),
            _linha("EV-0007", estado="feito", deploy_em="2026-10-01T00:00:00+00:00"),
            _linha("EV-0008", estado="recusado"),
        ]
        bloco = render(linhas, agora=AGORA)
        itens = [ln for ln in bloco.splitlines() if ln.startswith("- `EV-")]
        self.assertEqual(
            [ln.split("`")[1] for ln in itens],
            ["EV-0001", "EV-0002", "EV-0003", "EV-0004", "EV-0005", "EV-0006"],
        )
        self.assertIn("**A fazer (4)**", bloco)
        self.assertIn("**Entrada, por triar (1)**", bloco)
        self.assertIn("**Feito — aguarda deploy (1)**", bloco)
        self.assertIn("· P2 · paulo · há 9 dias", bloco)
        self.assertIn("· por triar · agente ·", bloco)
        self.assertNotIn("EV-0007", bloco)  # já em produção
        self.assertNotIn("EV-0008", bloco)  # recusado não é «o que falta»
        # problemas antes das ideias dentro da secção
        self.assertLess(bloco.index("🐛 Problemas"), bloco.index("💡 Ideias"))

    def test_substituir_bloco(self):
        texto = "a\n<!-- EVOLUCAO:INICIO — quadro manual -->\nvelho\n<!-- EVOLUCAO:FIM -->\nz\n"
        novo = substituir_bloco(texto, "NOVO")
        self.assertEqual(novo, "a\nNOVO\nz\n")
        self.assertEqual(substituir_bloco("sem marcadores", "NOVO"), "sem marcadores")
        self.assertEqual(
            substituir_bloco("<!-- EVOLUCAO:FIM --> x <!-- EVOLUCAO:INICIO", "N"),
            "<!-- EVOLUCAO:FIM --> x <!-- EVOLUCAO:INICIO",
        )


class ComandoQuadroTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("paulo", "p@t.com", "p", is_staff=True)
        aberto = uc.criar_item(autor=self.user, tipo="problema", titulo="Mapa", descricao="d")
        uc.triar(aberto, estado="a_fazer", prioridade=1)
        feito = uc.criar_item(
            autor=None,
            tipo="ideia",
            titulo="Ideia feita",
            descricao="d",
            origem="agente",
            evidencia={"f": 1},
        )
        uc.triar(feito, estado="feito")
        no_ar = uc.criar_item(autor=self.user, tipo="problema", titulo="No ar", descricao="d")
        uc.fechar_por_commit(codigo=no_ar.codigo, commit="abc", mensagem="m", deploy_em=AGORA)

    def test_linhas_da_base(self):
        linhas = {ln.codigo: ln for ln in linhas_da_base(AGORA + timedelta(days=3))}
        self.assertEqual(sorted(linhas), ["EV-0001", "EV-0002"])
        self.assertEqual(linhas["EV-0001"].autor, "paulo")
        self.assertEqual(linhas["EV-0002"].autor, "agente")
        self.assertIsNone(linhas["EV-0002"].deploy_em)

    def test_comando_escreve_so_quando_muda(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "CLAUDE.md"
            f.write_text(
                "# x\n\n<!-- EVOLUCAO:INICIO — manual -->\nvelho\n<!-- EVOLUCAO:FIM -->\n\nfim\n",
                encoding="utf-8",
            )
            out = StringIO()
            call_command("evolucao_quadro", ficheiro=str(f), stdout=out)
            self.assertIn("quadro atualizado", out.getvalue())
            texto = f.read_text(encoding="utf-8")
            self.assertIn("EV-0001` **Mapa** · P1 · paulo", texto)
            self.assertIn("**Feito — aguarda deploy (1)**", texto)
            self.assertNotIn("No ar", texto)
            self.assertTrue(texto.startswith("# x\n\n<!-- EVOLUCAO:INICIO — gerado"))
            self.assertTrue(texto.endswith("<!-- EVOLUCAO:FIM -->\n\nfim\n"))
            out = StringIO()
            call_command("evolucao_quadro", ficheiro=str(f), stdout=out)
            self.assertIn("já estava em dia", out.getvalue())

    def test_comando_imprimir_e_ficheiro_inexistente(self):
        out = StringIO()
        call_command("evolucao_quadro", "--imprimir", stdout=out)
        self.assertIn("EV-0001", out.getvalue())
        err = StringIO()
        call_command("evolucao_quadro", ficheiro="/nao/existe.md", stderr=err, stdout=StringIO())
        self.assertIn("não existe", err.getvalue())
