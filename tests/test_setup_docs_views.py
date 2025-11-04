# tests/test_setup_docs_views.py
from typing import Any, Dict
from unittest.mock import Mock, patch
from django.test import TestCase
from django.urls import reverse, resolve


class DocsViewsSmokeTests(TestCase):
    def setUp(self):
        # Dictionary used by the index view to render cards
        self.sample_docs: Dict[str, Dict[str, Any]] = {
            "developer/README.md": {
                "title": "Main Guide",
                "summary": "Project introduction and overview.",
                "category": "guide",
                "tags": ["intro", "deploy"],
                "size_kb": 42,
                "modified_at": "2025-01-01T12:34:56Z",
                "github_doc_url": (
                    "https://github.com/kaled182/provemaps_beta/blob/main/"
                    "README.md"
                ),
                "views": 10,
            },
            "reference-root/API_DOCUMENTATION.md": {
                "title": "API - Zabbix and Integrations",
                "summary": "Reference for routes and contracts.",
                "category": "api",
                "tags": ["api", "zabbix"],
                "size_kb": 88,
                "modified_at": "2025-01-02T09:00:00Z",
                "github_doc_url": (
                    "https://github.com/kaled182/provemaps_beta/blob/main/"
                    "API_DOCUMENTATION.md"
                ),
                "views": 5,
            },
        }

    def test_urls_resolve(self):
        """Ensure the named routes exist in the URLConf."""
        idx = reverse("setup_app:docs_index")
        view = reverse(
            "setup_app:docs_view",
            kwargs={"filename": "developer/README.md"},
        )
        self.assertIsNotNone(resolve(idx))
        self.assertIsNotNone(resolve(view))

    @patch("setup_app.views_docs.get_available_docs")
    def test_docs_index_renders(self, mock_get_docs: Mock) -> None:
        """The /docs/ page renders cards and helper widgets."""
        mock_get_docs.return_value = self.sample_docs

        url = reverse("setup_app:docs_index")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # Header and UI controls
        self.assertContains(resp, "Documentation")
        self.assertContains(resp, 'id="doc-search"')
        self.assertContains(resp, 'id="filter-category"')
        self.assertContains(resp, 'id="doc-list"')

        # Cards (titles and links)
        self.assertContains(resp, "Main Guide")
        self.assertContains(resp, "API - Zabbix and Integrations")
        # Link used to open the document
        self.assertContains(
            resp,
            reverse(
                "setup_app:docs_view",
                kwargs={"filename": "developer/README.md"},
            ),
        )

    @patch("setup_app.views_docs.get_available_docs")
    @patch("setup_app.views_docs.load_markdown_file")
    def test_docs_view_renders_content_and_toc(
        self,
        mock_load_md: Mock,
        mock_get_docs: Mock,
    ) -> None:
        """``/docs/<filename>/`` renders HTML and exposes the TOC/JS."""
        mock_get_docs.return_value = self.sample_docs
        mock_load_md.return_value = """
            <h1>Main Guide</h1>
            <p>Sample content.</p>
            <h2>Section A</h2>
            <p>Details A</p>
            <h2>Section B</h2>
            <p>Details B</p>
        """

        url = reverse(
            "setup_app:docs_view",
            kwargs={"filename": "developer/README.md"},
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # Title and content
        self.assertContains(resp, "Main Guide")
        self.assertContains(resp, "Sample content")

        # Sidebar/TOC and auxiliary elements
        self.assertContains(resp, 'id="toc"')
        self.assertContains(resp, 'id="doc-article"')
        self.assertContains(resp, 'id="doc-search"')
        self.assertContains(resp, "<- Back to document list")

    @patch("setup_app.views_docs.get_available_docs")
    @patch("setup_app.views_docs.load_markdown_file")
    def test_docs_view_handles_missing_file(
        self,
        mock_load_md: Mock,
        mock_get_docs: Mock,
    ) -> None:
        """The view shows a friendly alert when the file is missing."""
        mock_get_docs.return_value = self.sample_docs
        # Simulate loader response for a missing file
        mock_load_md.return_value = """
            <div class="alert alert-warning" role="alert">
                <strong>File not found:</strong>
            </div>
        """

        url = reverse(
            "setup_app:docs_view",
            kwargs={"filename": "NAO_EXISTE.md"},
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "File not found")

    @patch("setup_app.views_docs.get_available_docs")
    def test_docs_index_empty_state(self, mock_get_docs: Mock) -> None:
        """When no documents exist we render an informative empty state."""
        mock_get_docs.return_value = {}

        url = reverse("setup_app:docs_index")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "No documents were found")
        self.assertContains(resp, "/docs")
