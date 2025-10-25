# setup_app/views_docs.py
from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime

from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from .utils.markdown_loader import load_markdown_file, get_available_docs

DOCS_DIR = Path(settings.BASE_DIR) / "docs"

def _meta_for(filename: str) -> dict:
    """Coleta metadados simples do arquivo no /docs."""
    p = DOCS_DIR / filename
    if not p.exists():
        return {}
    stat = p.stat()
    return {
        "title": filename,
        "size_kb": round(stat.st_size / 1024, 1),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
    }

def docs_index(request):
    """
    Lista os arquivos .md disponíveis em /docs com metadados.
    Usa os cartões (_doc_card.html).
    """
    available = get_available_docs()  # dict {filename: {...}}
    # Adapta estrutura para o template que já temos
    normalized = {}
    for name, meta in available.items():
        normalized[name] = {
            "title": meta.get("title") or name,
            "summary": "",           # opcional: preencher lendo cabeçalho do MD
            "category": "",          # opcional: derivar por pasta—se aplicável
            "tags": [],              # opcional: derivar por front-matter—se existir
            "size_kb": meta.get("size_kb"),
            "modified_at": datetime.fromtimestamp(meta["last_modified"]).strftime("%Y-%m-%d %H:%M"),
            "github_doc_url": os.getenv("GITHUB_DOCS_URL", ""),  # opcional
            "views": 0,
        }
    context = {
        "available_docs": normalized,
    }
    return render(request, "setup/docs/index.html", context)

def docs_view(request, filename: str = "README.md"):
    """
    Renderiza um Markdown específico em HTML.
    """
    # segurança básica: não permitir navegar diretórios
    if "/" in filename or "\\" in filename:
        raise Http404

    path = DOCS_DIR / filename
    if not path.exists() or not path.is_file():
        raise Http404("Documento não encontrado")

    html = load_markdown_file(filename, use_cache=True)
    meta = _meta_for(filename)
    available = get_available_docs()

    context = {
        "filename": filename,
        "content": html,              # já sanitizado no loader (se ativado)
        "doc_meta": {"title": meta.get("title", filename)},
        "size_kb": meta.get("size_kb"),
        "modified_at": meta.get("modified_at"),
        "github_doc_url": os.getenv("GITHUB_DOCS_URL", ""),
        "available_docs": available,
    }
    return render(request, "setup/docs/view.html", context)
