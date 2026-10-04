"""Central de Evolução (EV-0027a): modelo, código sequencial, triagem, fecho por commit, parados."""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from evolucao import usecases as uc
from evolucao.models import EvolucaoContador, EvolucaoItem


class ModeloTests(TestCase):
    def test_codigo_sequencial_e_contador(self):
        self.assertEqual(uc.proximo_codigo(), "EV-0001")
        self.assertEqual(uc.proximo_codigo(), "EV-0002")
        self.assertEqual(EvolucaoContador.objects.get(pk=1).ultimo_numero, 2)

    def test_check_recusa_sem_motivo(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            EvolucaoItem.objects.create(
                codigo="EV-9001", tipo="problema", titulo="t", descricao="d", estado="recusado"
            )

    def test_check_agente_sem_prova(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            EvolucaoItem.objects.create(
                codigo="EV-9002", tipo="problema", titulo="t", descricao="d", origem="agente"
            )

    def test_check_prioridade(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            EvolucaoItem.objects.create(
                codigo="EV-9003", tipo="ideia", titulo="t", descricao="d", prioridade=5
            )

    def test_ordering_prioridade_nulos_no_fim_depois_codigo(self):
        EvolucaoItem.objects.create(codigo="EV-0003", tipo="problema", titulo="c", descricao="d")
        EvolucaoItem.objects.create(
            codigo="EV-0002", tipo="problema", titulo="b", descricao="d", prioridade=2
        )
        EvolucaoItem.objects.create(
            codigo="EV-0001", tipo="problema", titulo="a", descricao="d", prioridade=2
        )
        EvolucaoItem.objects.create(
            codigo="EV-0004", tipo="problema", titulo="e", descricao="d", prioridade=1
        )
        self.assertEqual(
            list(EvolucaoItem.objects.values_list("codigo", flat=True)),
            ["EV-0004", "EV-0001", "EV-0002", "EV-0003"],
        )


class UsecasesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rep", "r@t.com", "p")
        self.staff = User.objects.create_user("tri", "t@t.com", "p", is_staff=True)

    def test_criar_item_nasce_em_entrada_com_autor(self):
        item = uc.criar_item(
            autor=self.user, tipo="problema", titulo=" Mapa  ", descricao=" d ", impacto="atrasa"
        )
        self.assertEqual(item.codigo, "EV-0001")
        self.assertEqual((item.estado, item.titulo, item.descricao), ("entrada", "Mapa", "d"))
        self.assertIsNone(item.prioridade)
        self.assertEqual(item.autor, self.user)
        data = uc.serialize_item(item)
        self.assertEqual(list(data)[:6], ["id", "codigo", "tipo", "titulo", "descricao", "estado"])
        self.assertEqual(data["autor"], "rep")
        self.assertIsNone(data["recusa_motivo"])

    def test_criar_item_agente_exige_evidencia(self):
        with self.assertRaises(uc.EvolucaoError):
            uc.criar_item(autor=None, tipo="problema", titulo="x", descricao="d", origem="agente")
        item = uc.criar_item(
            autor=None,
            tipo="problema",
            titulo="x",
            descricao="d",
            origem="agente",
            evidencia={"ficheiro": "a.py", "linha": 3},
        )
        self.assertIsNone(item.autor)
        self.assertEqual(item.evidencia["linha"], 3)

    def test_criar_item_com_anexos_pendentes(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        anexo = uc.criar_anexo(ficheiro=SimpleUploadedFile("p.png", b"img"), user=self.user)
        self.assertIsNone(anexo.item)
        with self.assertRaises(uc.EvolucaoError):
            uc.criar_item(autor=self.user, tipo="ideia", titulo="x", descricao="d", anexos=[99999])
        item = uc.criar_item(
            autor=self.user, tipo="ideia", titulo="x", descricao="d", anexos=[anexo.id]
        )
        anexo.refresh_from_db()
        self.assertEqual(anexo.item, item)
        self.assertEqual(uc.serialize_item(item)["anexos"][0]["nome_original"], "p.png")

    def test_listar_visibilidade_e_filtros(self):
        meu = uc.criar_item(autor=self.user, tipo="problema", titulo="meu", descricao="d")
        outro = uc.criar_item(autor=self.staff, tipo="ideia", titulo="outro", descricao="d")
        self.assertEqual([i["codigo"] for i in uc.listar_itens(self.user)], [meu.codigo])
        self.assertEqual(len(uc.listar_itens(self.staff)), 2)
        self.assertEqual(
            [i["codigo"] for i in uc.listar_itens(self.staff, tipo="ideia")], [outro.codigo]
        )
        uc.triar(outro, estado="a_fazer")
        self.assertEqual(len(uc.listar_itens(self.staff, estado="entrada")), 1)
        self.assertTrue(uc.pode_ver(self.user, meu))
        self.assertFalse(uc.pode_ver(self.user, outro))

    def test_triar_regras(self):
        item = uc.criar_item(autor=self.user, tipo="problema", titulo="x", descricao="d")
        with self.assertRaises(uc.EvolucaoError):
            uc.triar(item, estado="recusado")
        with self.assertRaises(uc.EvolucaoError):
            uc.triar(item, recusa_motivo="x")  # motivo sem recusa
        mudancas = uc.triar(item, estado="a_fazer", prioridade=2, etiquetas=["b", " a ", "", "a"])
        self.assertEqual(mudancas["estado"], ["entrada", "a_fazer"])
        self.assertEqual(mudancas["prioridade"], [None, 2])
        self.assertEqual(mudancas["etiquetas"], [[], ["a", "b"]])
        self.assertEqual(uc.triar(item, tipo="ideia"), {"tipo": ["problema", "ideia"]})
        # omitido não mexe; `None` explícito apaga
        self.assertEqual(uc.triar(item), {})
        self.assertEqual(uc.triar(item, prioridade=None)["prioridade"], [2, None])
        mudancas = uc.triar(item, estado="recusado", recusa_motivo=" duplicado ")
        item.refresh_from_db()
        self.assertEqual((item.estado, item.recusa_motivo), ("recusado", "duplicado"))
        self.assertIsNotNone(item.recusado_em)
        self.assertEqual(mudancas["recusa_motivo"], "duplicado")

    def test_fechar_por_commit_primeira_observacao_ganha(self):
        item = uc.criar_item(autor=self.user, tipo="problema", titulo="x", descricao="d")
        agora = timezone.now()
        self.assertIsNone(
            uc.fechar_por_commit(codigo="EV-9999", commit="a", mensagem="m", deploy_em=agora)
        )
        fechado = uc.fechar_por_commit(
            codigo=item.codigo, commit="abc1234", mensagem="fix: x" * 60, deploy_em=agora
        )
        self.assertEqual(fechado.estado, "feito")
        self.assertEqual(fechado.fechado_por["commit"], "abc1234")
        self.assertEqual(len(fechado.fechado_por["mensagem"]), 200)
        depois = uc.fechar_por_commit(
            codigo=item.codigo, commit="zzz", mensagem="m", deploy_em=agora + timedelta(days=1)
        )
        self.assertIsNone(depois)
        item.refresh_from_db()
        self.assertEqual(item.fechado_por["commit"], "abc1234")

    def test_itens_parados_e_rearme(self):
        item = uc.criar_item(autor=self.user, tipo="problema", titulo="x", descricao="d")
        feito = uc.criar_item(autor=self.user, tipo="problema", titulo="y", descricao="d")
        uc.triar(feito, estado="feito")
        antigo = timezone.now() - timedelta(days=20)
        EvolucaoItem.objects.filter(pk__in=[item.pk, feito.pk]).update(atualizado_em=antigo)
        agora = timezone.now()
        self.assertEqual([i.pk for i in uc.itens_parados(agora=agora)], [item.pk])
        self.assertEqual(uc.itens_parados(agora=agora, dias=30), [])
        EvolucaoItem.objects.filter(pk=item.pk).update(alerta_parado_em=agora)
        self.assertEqual(uc.itens_parados(agora=agora), [])  # já avisou
        # mexeu depois do aviso e voltou a parar → avisa de novo
        EvolucaoItem.objects.filter(pk=item.pk).update(atualizado_em=agora + timedelta(seconds=1))
        self.assertEqual(len(uc.itens_parados(agora=agora + timedelta(days=15))), 1)

    def test_etiquetas_em_uso(self):
        a = uc.criar_item(autor=self.user, tipo="problema", titulo="x", descricao="d")
        b = uc.criar_item(autor=self.user, tipo="problema", titulo="y", descricao="d")
        uc.triar(a, etiquetas=["dívida", "mapa"])
        uc.triar(b, etiquetas=["mapa", "zabbix"])
        self.assertEqual(uc.etiquetas_em_uso(), ["dívida", "mapa", "zabbix"])
