"""Seed da Central a partir do quadro do CLAUDE.md (EV-0027a): parser e idempotência."""

from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from evolucao.management.commands.evolucao_seed_quadro import (
    ETIQUETA_MIGRACAO,
    parse_quadro,
    semear,
)
from evolucao.models import EvolucaoContador, EvolucaoItem

QUADRO = """
texto antes

<!-- EVOLUCAO:INICIO — quadro manual -->
**A fazer — 🐛 Problemas** (triagem)

- `EV-0012` **Quatro pilhas de mapa** · P2 · `frontend/src/components/MapView.vue` · nota

**Entrada, por triar — 🐛 Problemas** (abertos pelo assistente com prova)

- `EV-0032` **Healthcheck bate em `/healthz/`** · prioridade por triar · `docker/x.yml:43` · prova: 302

**A fazer — 💡 Ideias** (aceitas)

- `EV-0027` **Portar a Central** · **⚠️ não cabe numa sessão** (detalhe)
**Feito — aguarda deploy** (sai daqui quando chegar a produção)

- `EV-0001` **Gráfico óptico aleatório** · P1 · fechado em `fix(charts)` 2026-10-04 — detalhe
- `EV-0026` **Componente único** · Ideia · fechado no mesmo commit — substitui
<!-- EVOLUCAO:FIM -->

- `EV-0999` **fora do bloco** · P1 · ignorado
"""


class ParseQuadroTests(TestCase):
    def test_parse(self):
        itens = {i["codigo"]: i for i in parse_quadro(QUADRO)}
        self.assertEqual(sorted(itens), ["EV-0001", "EV-0012", "EV-0026", "EV-0027", "EV-0032"])
        a = itens["EV-0012"]
        self.assertEqual(
            (a["estado"], a["tipo"], a["prioridade"], a["origem"]),
            ("a_fazer", "problema", 2, "humano"),
        )
        self.assertEqual(a["titulo"], "Quatro pilhas de mapa")
        self.assertTrue(a["descricao"].startswith("P2 · `frontend"))
        e = itens["EV-0032"]
        self.assertEqual((e["estado"], e["prioridade"], e["origem"]), ("entrada", None, "agente"))
        self.assertEqual(e["evidencia"]["fonte"], "CLAUDE.md")
        self.assertEqual(itens["EV-0027"]["tipo"], "ideia")
        self.assertEqual(itens["EV-0027"]["estado"], "a_fazer")
        f = itens["EV-0001"]
        self.assertEqual((f["estado"], f["tipo"], f["prioridade"]), ("feito", "problema", 1))
        self.assertEqual(f["fechado_por"]["mensagem"], "fix(charts)")
        self.assertEqual(itens["EV-0026"]["tipo"], "ideia")
        self.assertEqual(itens["EV-0026"]["estado"], "feito")
        self.assertEqual(itens["EV-0026"]["etiquetas"], [ETIQUETA_MIGRACAO])


class SemearTests(TestCase):
    def test_idempotente_e_contador(self):
        itens = parse_quadro(QUADRO)
        self.assertEqual(semear(itens), (5, 0))
        self.assertEqual(EvolucaoItem.objects.count(), 5)
        self.assertEqual(EvolucaoContador.objects.get(pk=1).ultimo_numero, 32)
        # segunda corrida não duplica nem mexe no que já existe
        EvolucaoItem.objects.filter(codigo="EV-0012").update(prioridade=1)
        self.assertEqual(semear(itens), (0, 0))
        self.assertEqual(EvolucaoItem.objects.get(codigo="EV-0012").prioridade, 1)
        self.assertEqual(semear(itens, atualizar=True), (0, 5))
        self.assertEqual(EvolucaoItem.objects.get(codigo="EV-0012").prioridade, 2)
        # o próximo item novo não colide com os migrados
        from evolucao import usecases as uc

        self.assertEqual(uc.proximo_codigo(), "EV-0033")

    def test_comando_dry_run_e_real(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
            fh.write(QUADRO)
        out = StringIO()
        call_command("evolucao_seed_quadro", ficheiro=fh.name, dry_run=True, stdout=out)
        self.assertIn("EV-0012 [a_fazer/problema/P2]", out.getvalue())
        self.assertEqual(EvolucaoItem.objects.count(), 0)
        out = StringIO()
        call_command("evolucao_seed_quadro", ficheiro=fh.name, stdout=out)
        self.assertIn("5 criados", out.getvalue())
        self.assertEqual(EvolucaoItem.objects.count(), 5)

    def test_comando_ficheiro_inexistente(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("evolucao_seed_quadro", ficheiro="/nao/existe.md")
