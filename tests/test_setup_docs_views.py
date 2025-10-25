# tests/test_setup_docs_views.py
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse, resolve


class DocsViewsSmokeTests(TestCase):
    def setUp(self):
        # Dicionário que a index usa para montar os cards
        self.sample_docs = {
            "README.md": {
                "title": "Guia Principal",
                "summary": "Introdução e visão geral do projeto.",
                "category": "guia",
                "tags": ["intro", "deploy"],
                "size_kb": 42,
                "modified_at": "2025-01-01T12:34:56Z",
                "github_doc_url": "https://github.com/kaled182/mapsprovefiber/blob/main/README.md",
                "views": 10,
            },
            "API_DOCUMENTATION.md": {
                "title": "API — Zabbix e Integrações",
                "summary": "Referência das rotas e contratos.",
                "category": "api",
                "tags": ["api", "zabbix"],
                "size_kb": 88,
                "modified_at": "2025-01-02T09:00:00Z",
                "github_doc_url": "https://github.com/kaled182/mapsprovefiber/blob/main/API_DOCUMENTATION.md",
                "views": 5,
            },
        }

    def test_urls_resolve(self):
        """Confirma que as rotas nomeadas existem no URLConf."""
        idx = reverse("setup_app:docs_index")
        view = reverse("setup_app:docs_view", kwargs={"filename": "README.md"})
        self.assertIsNotNone(resolve(idx))
        self.assertIsNotNone(resolve(view))

    @patch("setup_app.views_docs.get_available_docs")
    def test_docs_index_renders(self, mock_get_docs):
        """A página /docs/ renderiza com os cards e ferramentas."""
        mock_get_docs.return_value = self.sample_docs

        url = reverse("setup_app:docs_index")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # Cabeçalho e elementos de UI
        self.assertContains(resp, "Documentação")
        self.assertContains(resp, 'id="doc-search"')
        self.assertContains(resp, 'id="filter-category"')
        self.assertContains(resp, 'id="doc-list"')

        # Cards (títulos e links)
        self.assertContains(resp, "Guia Principal")
        self.assertContains(resp, "API — Zabbix e Integrações")
        # Link para abrir o documento
        self.assertContains(resp, reverse("setup_app:docs_view", kwargs={"filename": "README.md"}))

    @patch("setup_app.views_docs.get_available_docs")
    @patch("setup_app.views_docs.load_markdown_file")
    def test_docs_view_renders_content_and_toc(self, mock_load_md, mock_get_docs):
        """A página /docs/<filename>/ renderiza o HTML e exibe o TOC/JS."""
        mock_get_docs.return_value = self.sample_docs
        mock_load_md.return_value = """
            <h1>Guia Principal</h1>
            <p>Conteúdo de exemplo.</p>
            <h2>Seção A</h2>
            <p>Detalhes A</p>
            <h2>Seção B</h2>
            <p>Detalhes B</p>
        """

        url = reverse("setup_app:docs_view", kwargs={"filename": "README.md"})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # Título e conteúdo
        self.assertContains(resp, "Guia Principal")
        self.assertContains(resp, "Conteúdo de exemplo")

        # Sidebar/TOC e elementos auxiliares
        self.assertContains(resp, 'id="toc"')
        self.assertContains(resp, 'id="doc-article"')
        self.assertContains(resp, 'id="doc-search"')
        self.assertContains(resp, "Voltar para lista de documentos")

    @patch("setup_app.views_docs.get_available_docs")
    @patch("setup_app.views_docs.load_markdown_file")
    def test_docs_view_handles_missing_file(self, mock_load_md, mock_get_docs):
        """Se o arquivo não existir, a view mostra mensagem de erro estilizada."""
        mock_get_docs.return_value = self.sample_docs
        # Simula retorno do loader para arquivo ausente
        mock_load_md.return_value = """
            <div class="alert alert-warning" role="alert">
                <strong>📄 Arquivo não encontrado:</strong>
            </div>
        """

        url = reverse("setup_app:docs_view", kwargs={"filename": "NAO_EXISTE.md"})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Arquivo não encontrado")

    @patch("setup_app.views_docs.get_available_docs")
    def test_docs_index_empty_state(self, mock_get_docs):
        """Quando não há documentos, exibe estado vazio informativo."""
        mock_get_docs.return_value = {}

        url = reverse("setup_app:docs_index")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Nenhum documento encontrado")
        self.assertContains(resp, "/docs")
