# setup_app/views_docs.py
from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime

from django.http import Http404
from django.shortcuts import render

from .utils.markdown_loader import (
    load_markdown_file,
    get_available_docs,
    resolve_doc_path,
    normalize_requested_filename,
)


def _meta_for(filename: str) -> dict:
    """Coleta metadados simples do arquivo na pasta doc."""
    try:
        path = resolve_doc_path(filename)
    except ValueError:
        raise Http404

    if not path.exists() or not path.is_file():
        return {}

    stat = path.stat()
    return {
        "title": Path(filename).name,
        "size_kb": round(stat.st_size / 1024, 1),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime(
            "%Y-%m-%d %H:%M"
        ),
    }


def docs_index(request):
    """
    Lista os arquivos .md disponíveis em /docs com metadados.
    Usa os cartões (_doc_card.html).
    """
    available = get_available_docs()  # dict {filename: {...}}
    # Adapta estrutura para o template que já temos
    normalized: dict[str, dict[str, object]] = {}
    for name, meta in available.items():
        last_modified = meta.get("last_modified")
        modified_at = ""
        if isinstance(last_modified, (int, float)):
            modified_at = datetime.fromtimestamp(last_modified).strftime(
                "%Y-%m-%d %H:%M"
            )
        elif isinstance(meta.get("modified_at"), str):
            modified_at = meta["modified_at"]

        raw_tags = meta.get("tags", [])
        if isinstance(raw_tags, str):
            tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
        elif isinstance(raw_tags, (list, tuple, set)):
            tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()]
        else:
            tags = []

        normalized_name = normalize_requested_filename(name)

        normalized[normalized_name] = {
            "title": meta.get("title") or Path(normalized_name).name,
            "summary": meta.get("summary", ""),
            "category": meta.get("category", ""),
            "tags": tags,
            "size_kb": meta.get("size_kb"),
            "modified_at": modified_at,
            "github_doc_url": meta.get("github_doc_url")
            or os.getenv("GITHUB_DOCS_URL", ""),
            "views": meta.get("views", 0),
        }
    context = {
        "available_docs": normalized,
    }
    return render(request, "docs/docs_index.html", context)


def docs_view(request, filename: str = "developer/README.md"):
    """
    Renderiza um Markdown específico em HTML.
    """
    normalized_filename = normalize_requested_filename(filename)

    try:
        path = resolve_doc_path(normalized_filename)
    except ValueError:
        raise Http404

    missing = not (path.exists() and path.is_file())

    html = load_markdown_file(normalized_filename, use_cache=True)
    meta = _meta_for(normalized_filename) if not missing else {}
    available = get_available_docs()

    context = {
        "filename": normalized_filename,
        "content": html,
        "doc_meta": {
            "title": meta.get("title", Path(normalized_filename).name)
        },
        "size_kb": meta.get("size_kb"),
        "modified_at": meta.get("modified_at"),
        "github_doc_url": os.getenv("GITHUB_DOCS_URL", ""),
        "available_docs": available,
        "missing": missing,
    }
    return render(request, "docs/view.html", context)
