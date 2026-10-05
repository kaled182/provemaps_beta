"""Fecho observado (EV-0027b): o comando `evolucao_fechar` e o script `evolucao_fechados.sh`."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from io import StringIO
from pathlib import Path
from unittest import skipUnless

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from evolucao import usecases as uc
from evolucao.models import EvolucaoItem

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "evolucao_fechados.sh"


class ComandoFecharTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("p", "p@t.com", "p")
        self.item = uc.criar_item(autor=self.user, tipo="problema", titulo="x", descricao="d")

    def _run(self, entradas, **kw):
        out, err = StringIO(), StringIO()
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            json.dump(entradas, fh)
        call_command("evolucao_fechar", ficheiro=fh.name, stdout=out, stderr=err, **kw)
        return out.getvalue(), err.getvalue()

    def test_fecha_e_e_idempotente(self):
        entradas = [
            {
                "codigo": "EV-0001",
                "commit": "abc1234",
                "mensagem": "fix: x — fecha EV-0001",
                "deploy_em": "2026-10-04T10:00:00+00:00",
            },
            {"codigo": "EV-9999", "commit": "zzz", "mensagem": "m", "deploy_em": ""},
        ]
        out, _ = self._run(entradas)
        self.assertIn("1 item(ns) fechado(s): EV-0001", out)
        self.item.refresh_from_db()
        self.assertEqual(self.item.estado, "feito")
        self.assertEqual(self.item.fechado_por["deploy_em"], "2026-10-04T10:00:00+00:00")
        out, _ = self._run(entradas)
        self.assertIn("0 item(ns) fechado(s)", out)

    def test_deploy_em_invalido_usa_agora(self):
        out, _ = self._run(
            [{"codigo": "EV-0001", "commit": "a", "mensagem": "m", "deploy_em": "ontem"}]
        )
        self.assertIn("EV-0001", out)
        self.item.refresh_from_db()
        self.assertTrue(self.item.fechado_por["deploy_em"].startswith("20"))

    def test_json_invalido_cala_e_nao_mexe(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write("{nope")
        err = StringIO()
        call_command("evolucao_fechar", ficheiro=fh.name, stdout=StringIO(), stderr=err)
        self.assertIn("evolucao_fechar:", err.getvalue())
        self.assertEqual(EvolucaoItem.objects.get(pk=self.item.pk).estado, "entrada")


@skipUnless(
    shutil.which("git") and shutil.which("curl") and SCRIPT.exists(),
    "precisa de git, curl e do script",
)
class ScriptFechadosTests(SimpleTestCase):
    def _repo(self, d: Path, mensagens: list[str]) -> str:
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        }
        subprocess.run(["git", "init", "-q", str(d)], check=True, env=env)
        for i, msg in enumerate(mensagens):
            (d / f"f{i}").write_text(str(i))
            subprocess.run(["git", "-C", str(d), "add", "."], check=True, env=env)
            subprocess.run(["git", "-C", str(d), "commit", "-q", "-m", msg], check=True, env=env)
        return subprocess.run(
            ["git", "-C", str(d), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()

    def _correr(self, repo: Path, health: dict) -> tuple[list, str]:
        hf = repo / "health.json"
        hf.write_text(json.dumps(health))
        proc = subprocess.run(
            ["bash", str(SCRIPT)],
            env={
                **os.environ,
                "EVOLUCAO_HEALTH_URL": f"file://{hf}",
                "EVOLUCAO_REPO_DIR": str(repo),
            },
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout), proc.stderr

    def test_fecha_por_verbo_so_commits_alcancaveis(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            sha = self._repo(
                repo,
                [
                    "feat: abre EV-0001 (menciona, não fecha)",
                    "fix(mapa): osm — fecha EV-0002",
                    'fix: aspas "x" — resolve o EV-0003 e closes EV-0004',
                ],
            )
            # um commit DEPOIS do implantado não conta
            self._repo_extra = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "commit",
                    "-q",
                    "--allow-empty",
                    "-m",
                    "fix: fecha EV-0005",
                ],
                env={
                    **os.environ,
                    "GIT_AUTHOR_NAME": "t",
                    "GIT_AUTHOR_EMAIL": "t@t",
                    "GIT_COMMITTER_NAME": "t",
                    "GIT_COMMITTER_EMAIL": "t@t",
                },
                check=True,
            )
            saida, _ = self._correr(
                repo, {"status": "ok", "git_sha": sha, "iniciado_em": "2026-10-04T10:00:00+00:00"}
            )
            codigos = sorted(e["codigo"] for e in saida)
            self.assertEqual(codigos, ["EV-0002", "EV-0003", "EV-0004"])
            e3 = next(e for e in saida if e["codigo"] == "EV-0003")
            self.assertIn('aspas "x"', e3["mensagem"])
            self.assertEqual(e3["deploy_em"], "2026-10-04T10:00:00+00:00")
            self.assertEqual(len(e3["commit"]), 7)

    def test_sem_sha_ou_sha_desconhecido_devolve_vazio(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            self._repo(repo, ["fix: fecha EV-0001"])
            saida, err = self._correr(repo, {"status": "ok"})
            self.assertEqual(saida, [])
            self.assertIn("sem git_sha", err)
            saida, err = self._correr(repo, {"git_sha": "0000000000000000000000000000000000000000"})
            self.assertEqual(saida, [])
            self.assertIn("não existe", err)
