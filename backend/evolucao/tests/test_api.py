"""API da Central (EV-0027a): autenticação, visibilidade, triagem só staff, anexos, auditoria."""

from __future__ import annotations

import json

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from evolucao import usecases as uc
from setup_app.models_audit import ConfigurationAudit

BASE = "/api/v1/evolucao"


@override_settings(
    MEDIA_ROOT="/tmp/claude-0/-home-user/38ec594f-35f9-57f7-bf7e-6089ad634c17/scratchpad/media_evolucao"
)
class EvolucaoApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rep", "r@t.com", "p")
        self.staff = User.objects.create_user("tri", "t@t.com", "p", is_staff=True)

    def _post(self, url, body, **kw):
        return self.client.post(url, json.dumps(body), content_type="application/json", **kw)

    def _patch(self, url, body):
        return self.client.patch(url, json.dumps(body), content_type="application/json")

    def test_sem_sessao_e_401(self):
        self.assertEqual(self.client.get(f"{BASE}/itens/").status_code, 401)
        self.assertEqual(self._post(f"{BASE}/itens/", {}).status_code, 401)

    def test_qualquer_autenticado_reporta_e_autor_vem_da_sessao(self):
        self.client.force_login(self.user)
        resp = self._post(
            f"{BASE}/itens/",
            {
                "tipo": "problema",
                "titulo": "Mapa não carrega",
                "descricao": "Em /mapa o OSM fica cinzento",
                "impacto": "bloqueia",
                "contexto": {"rota": "/mapa"},
                "autor": "outro",  # ignorado: a autoria vem da sessão
            },
            HTTP_X_REQUEST_ID="req-1",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        self.assertEqual(data["codigo"], "EV-0001")
        self.assertEqual(data["autor"], "rep")
        self.assertEqual(data["estado"], "entrada")
        self.assertIsNone(data["prioridade"])
        self.assertEqual(data["contexto"]["rota"], "/mapa")
        self.assertIn("request_id", data["contexto"])

    def test_validacao_400(self):
        self.client.force_login(self.user)
        resp = self._post(f"{BASE}/itens/", {"tipo": "bug", "titulo": "ab", "descricao": ""})
        self.assertEqual(resp.status_code, 400)
        for campo in ("tipo", "titulo", "descricao"):
            self.assertIn(campo, resp.json())

    def test_lista_e_detalhe_por_visibilidade(self):
        meu = uc.criar_item(autor=self.user, tipo="problema", titulo="meu", descricao="d")
        outro = uc.criar_item(autor=self.staff, tipo="ideia", titulo="outro", descricao="d")
        self.client.force_login(self.user)
        self.assertEqual(
            [i["codigo"] for i in self.client.get(f"{BASE}/itens/").json()], [meu.codigo]
        )
        self.assertEqual(self.client.get(f"{BASE}/itens/{meu.id}/").status_code, 200)
        self.assertEqual(self.client.get(f"{BASE}/itens/{outro.id}/").status_code, 404)
        self.assertEqual(self.client.get(f"{BASE}/itens/99999/").status_code, 404)
        self.client.force_login(self.staff)
        self.assertEqual(len(self.client.get(f"{BASE}/itens/").json()), 2)
        self.assertEqual(len(self.client.get(f"{BASE}/itens/?tipo=ideia").json()), 1)
        self.assertEqual(self.client.get(f"{BASE}/itens/{meu.id}/").status_code, 200)

    def test_triagem_so_staff_e_auditada(self):
        item = uc.criar_item(autor=self.user, tipo="problema", titulo="x", descricao="d")
        url = f"{BASE}/itens/{item.id}/"
        self.client.force_login(self.user)
        self.assertEqual(self._patch(url, {"estado": "a_fazer"}).status_code, 403)
        self.client.force_login(self.staff)
        resp = self._patch(url, {"estado": "a_fazer", "prioridade": 1, "etiquetas": ["mapa"]})
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertEqual(
            (data["estado"], data["prioridade"], data["etiquetas"]), ("a_fazer", 1, ["mapa"])
        )
        audit = ConfigurationAudit.objects.get()
        self.assertEqual(
            (audit.section, audit.field_name, audit.user), ("Evolução", item.codigo, self.staff)
        )
        self.assertIn("a_fazer", audit.new_value)
        # recusa sem motivo → 400 e sem auditoria nova
        self.assertEqual(self._patch(url, {"estado": "recusado"}).status_code, 400)
        self.assertEqual(ConfigurationAudit.objects.count(), 1)
        self.assertEqual(self._patch(url, {"prioridade": 7}).status_code, 400)
        # prioridade null apaga; sem mudanças não audita
        self.assertIsNone(self._patch(url, {"prioridade": None}).json()["prioridade"])
        self.assertEqual(self._patch(url, {}).status_code, 200)
        self.assertEqual(ConfigurationAudit.objects.count(), 2)
        self.assertEqual(self._patch(f"{BASE}/itens/99999/", {"estado": "feito"}).status_code, 404)

    def test_etiquetas(self):
        item = uc.criar_item(autor=self.user, tipo="problema", titulo="x", descricao="d")
        uc.triar(item, etiquetas=["zabbix", "mapa"])
        self.client.force_login(self.user)
        self.assertEqual(
            self.client.get(f"{BASE}/etiquetas/").json(), {"etiquetas": ["mapa", "zabbix"]}
        )

    def test_anexo_upload_liga_ao_item_e_download_por_visibilidade(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            f"{BASE}/anexos/",
            {"file": SimpleUploadedFile("print.png", b"\x89PNG", content_type="image/png")},
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        anexo_id = resp.json()["id"]
        self.assertEqual(resp.json()["nome_original"], "print.png")
        self.assertEqual(self.client.post(f"{BASE}/anexos/", {}).status_code, 400)
        # o autor vê o anexo ainda sem item; outro utilizador não
        self.assertEqual(self.client.get(f"{BASE}/anexos/{anexo_id}/").status_code, 200)
        resp = self._post(
            f"{BASE}/itens/",
            {"tipo": "problema", "titulo": "com print", "descricao": "ddd", "anexos": [anexo_id]},
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["anexos"][0]["id"], anexo_id)
        resp = self._post(
            f"{BASE}/itens/",
            {"tipo": "problema", "titulo": "sem print", "descricao": "ddd", "anexos": [anexo_id]},
        )
        self.assertEqual(resp.status_code, 400)  # já reclamado
        outro = User.objects.create_user("x", "x@t.com", "p")
        self.client.force_login(outro)
        self.assertEqual(self.client.get(f"{BASE}/anexos/{anexo_id}/").status_code, 404)
        self.client.force_login(self.staff)
        resp = self.client.get(f"{BASE}/anexos/{anexo_id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b"".join(resp.streaming_content), b"\x89PNG")
        self.assertEqual(resp["Content-Type"], "image/png")
