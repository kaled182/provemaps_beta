"""Aviso dos 14 dias (EV-0027c): um email ao staff com os itens parados; carimbo só após enviar."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from evolucao import usecases as uc
from evolucao.models import EvolucaoItem
from evolucao.tasks import avisar_parados, avisar_parados_task, compor_aviso, destinatarios_staff


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AvisarParadosTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("tri", "tri@t.com", "p", is_staff=True)
        User.objects.create_user("staff_sem_email", "", "p", is_staff=True)
        User.objects.create_user("inativo", "ina@t.com", "p", is_staff=True, is_active=False)
        self.user = User.objects.create_user("rep", "rep@t.com", "p")
        self.item = uc.criar_item(
            autor=self.user, tipo="problema", titulo="Mapa cinzento", descricao="d"
        )
        EvolucaoItem.objects.filter(pk=self.item.pk).update(
            atualizado_em=timezone.now() - timedelta(days=20)
        )

    def test_destinatarios(self):
        self.assertEqual(destinatarios_staff(), ["tri@t.com"])

    def test_envia_um_email_e_carimba(self):
        agora = timezone.now()
        self.assertEqual(avisar_parados(agora=agora), 1)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ["tri@t.com"])
        self.assertIn("1 item(ns)", msg.subject)
        self.assertIn("EV-0001 [entrada] Mapa cinzento — parado há 20 dias", msg.body)
        self.assertIn("/system/evolucao", msg.body)
        self.item.refresh_from_db()
        self.assertEqual(self.item.alerta_parado_em, agora)
        # segunda corrida: já avisado, nada a enviar
        self.assertEqual(avisar_parados(agora=agora), 0)
        self.assertEqual(len(mail.outbox), 1)

    def test_nada_parado_nao_envia(self):
        EvolucaoItem.objects.filter(pk=self.item.pk).update(atualizado_em=timezone.now())
        self.assertEqual(avisar_parados(), 0)
        self.assertEqual(mail.outbox, [])

    def test_sem_staff_com_email_nao_envia_nem_carimba(self):
        self.staff.email = ""
        self.staff.save()
        self.assertEqual(avisar_parados(), 0)
        self.item.refresh_from_db()
        self.assertIsNone(self.item.alerta_parado_em)

    def test_falha_de_envio_nao_carimba_e_task_nao_morre(self):
        with patch("evolucao.tasks.send_mail", side_effect=OSError("smtp em baixo")):
            resultado = avisar_parados_task()
        self.assertEqual(resultado["avisados"], 0)
        self.assertIn("smtp em baixo", resultado["erro"])
        self.item.refresh_from_db()
        self.assertIsNone(self.item.alerta_parado_em)
        self.assertEqual(avisar_parados_task(), {"avisados": 1})

    def test_compor_aviso(self):
        assunto, corpo = compor_aviso([self.item], agora=timezone.now())
        self.assertIn("Central de Evolução", assunto)
        self.assertIn("EV-0001", corpo)
