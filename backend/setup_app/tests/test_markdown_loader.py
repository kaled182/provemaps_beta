"""Tests for the markdown documentation loader utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from setup_app.utils import markdown_loader

FALLBACK_HTML = "<p>Documento vazio ou n&atilde;o encontrado.</p>"


@pytest.fixture()
def docs_dir(tmp_path: Path):
    """Provide an isolated docs directory and restore global config."""
    docs_path = tmp_path / "docs"
    docs_path.mkdir()

    original_docs_path = markdown_loader.CONFIG.docs_path
    original_docs_dir = markdown_loader.CONFIG.docs_dir

    markdown_loader.CONFIG.docs_path = docs_path
    markdown_loader.CONFIG.docs_dir = docs_path.name

    yield docs_path

    markdown_loader.CONFIG.docs_path = original_docs_path
    markdown_loader.CONFIG.docs_dir = original_docs_dir
    markdown_loader.CACHE_MANAGER.hits = 0
    markdown_loader.CACHE_MANAGER.misses = 0


def test_load_markdown_file_missing_returns_fallback(docs_dir: Path):
    """Missing markdown files should return the fallback HTML message."""
    result = markdown_loader.load_markdown_file("missing.md", use_cache=False)

    assert result == FALLBACK_HTML


def test_load_markdown_file_renders_content(docs_dir: Path):
    """Markdown files inside the configured docs directory render to HTML."""
    markdown_path = docs_dir / "guide.md"
    markdown_path.write_text("# Demo\n\nIt works.", encoding="utf-8")

    html = markdown_loader.load_markdown_file("guide.md", use_cache=False)

    assert "Demo" in html
    assert "It works." in html


def test_get_available_docs_includes_default_metadata(docs_dir: Path):
    """Default metadata entries should be merged when the file exists."""
    developer_dir = docs_dir / "developer"
    developer_dir.mkdir()
    (developer_dir / "README.md").write_text(
        "# Doc\n\nSome notes.",
        encoding="utf-8",
    )

    docs = markdown_loader.get_available_docs()

    key = "developer/README.md"
    assert key in docs

    entry = docs[key]
    assert entry["priority"] == markdown_loader.DEFAULT_FILES[key]["priority"]
    assert entry["category"] == "developer"
    assert "summary" in entry and entry["summary"]
