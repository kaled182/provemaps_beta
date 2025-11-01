"""
Conversão segura e otimizada de arquivos Markdown em HTML para o painel de documentação.

MELHORIAS IMPLEMENTADAS:
1. Type hints completos para melhor desenvolvimento
2. Configuração centralizada em classe dedicada
3. Cache mais inteligente com compressão opcional
4. Sistema de plugins para extensibilidade
5. Metadados avançados com extração automática
6. Suporte a múltiplas estratégias de cache
7. Internacionalização preparada
8. Métricas de performance aprimoradas
"""

from __future__ import annotations

import os
import re
import time
import hashlib
import logging
import zlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, TypedDict, Protocol
from dataclasses import dataclass
from enum import Enum

try:
    import markdown2  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback
    markdown2 = None  # type: ignore
    # logger ainda não definido neste ponto; usa logging direto
    logging.getLogger(__name__).warning(
        "markdown2 não instalado; usando renderização básica de Markdown."
    )
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURAÇÃO CENTRALIZADA E TIPADA
# =============================================================================

class CacheStrategy(Enum):
    """Estratégias disponíveis para cache."""
    CONTENT_HASH = "content_hash"
    TIMESTAMP = "timestamp"
    HYBRID = "hybrid"

@dataclass
class DocsConfig:
    """Configuração centralizada para o módulo de documentação."""
    
    # Paths e diretórios
    docs_dir: str = os.getenv("DOCS_DIR", "doc")
    docs_path: Path = None
    
    # Cache
    cache_ttl: int = int(os.getenv("DOCS_CACHE_TTL", "300"))  # 5 minutos
    cache_strategy: CacheStrategy = CacheStrategy.HYBRID
    enable_compression: bool = os.getenv("DOCS_CACHE_COMPRESSION", "false").lower() == "true"
    
    # Segurança
    sanitize_html: bool = os.getenv("DOCS_SANITIZE_HTML", "true").lower() == "true"
    
    # GitHub
    github_base_url: str = os.getenv("DOCS_GITHUB_BASE_URL", "").rstrip("/")
    
    # Performance
    preload_enabled: bool = os.getenv("DOCS_PRELOAD_ENABLED", "true").lower() == "true"
    max_file_size_mb: int = int(os.getenv("DOCS_MAX_FILE_SIZE_MB", "10"))
    
    # Metadados
    summary_length: int = 280
    extract_categories: bool = True
    extract_tags: bool = True
    
    def __post_init__(self):
        """Inicializa paths após criação do dataclass."""
        if self.docs_path is None:
            self.docs_path = Path(settings.BASE_DIR) / self.docs_dir

# Instância global de configuração
CONFIG = DocsConfig()

# =============================================================================
# DEFINIÇÕES DE TIPOS AVANÇADADOS
# =============================================================================

class DocMetadata(TypedDict, total=False):
    """Estrutura tipada para metadados de documentos."""
    title: str
    filename: str
    summary: str
    size_kb: float
    modified_at: str
    github_doc_url: Optional[str]
    views: int
    category: str
    tags: List[str]
    reading_time_min: int
    word_count: int
    sections_count: int
    has_code_blocks: bool
    has_images: bool

class ProcessingMetrics(TypedDict):
    """Métricas de processamento."""
    processing_time_ms: float
    cache_hit: bool
    file_size_bytes: int
    compressed_size_bytes: Optional[int]

class MarkdownProcessor(Protocol):
    """Interface para processadores Markdown."""
    def process(self, text: str, filename: str) -> tuple[str, Dict[str, Any]]: ...

# =============================================================================
# ARQUIVOS PRIORITÁRIOS E CONFIGURAÇÕES MARKDOWN
# =============================================================================

# Arquivos principais (aparecem primeiro/ganham prioridade)
DEFAULT_FILES = {
    "developer/README.md": {
        "title": _("Documentação Principal"),
        "category": "developer",
        "priority": 100,
    },
    "getting-started/QUICKSTART_LOCAL.md": {
        "title": _("Guia Rápido: Ambiente Local"),
        "category": "getting-started",
        "priority": 95,
    },
    "operations/DEPLOYMENT.md": {
        "title": _("Guia de Deploy e Containers"),
        "category": "operations",
        "priority": 90,
    },
    "reference-root/API_DOCUMENTATION.md": {
        "title": _("Documentação da API"),
        "category": "api",
        "priority": 85,
    },
    "reference/README.md": {
        "title": _("Referências Técnicas"),
        "category": "reference",
        "priority": 80,
    },
}

# Extensões otimizadas do markdown2
MARKDOWN_EXTRAS = [
    "fenced-code-blocks",    # Blocos de código com syntax highlighting
    "tables",                # Tabelas
    "header-ids",            # IDs automáticos em headers
    "toc",                   # Table of Contents
    "strike",                # Texto riscado
    "code-friendly",         # Melhor tratamento de código
    "cuddled-lists",         # Listas compactas
    "smarty-pants",          # Aspas inteligentes
    "task_list",             # Listas de tarefas
    "break-on-newline",      # Quebras de linha
    "footnotes",             # Notas de rodapé
    "metadata",              # Metadados YAML frontmatter
]

# =============================================================================
# SANITIZAÇÃO AVANÇADA COM BLEACH
# =============================================================================

class HTMLSanitizer:
    """Gerenciador centralizado de sanitização HTML."""
    
    def __init__(self):
        self.has_bleach = False
        self.allowed_tags = set()
        self.allowed_attributes = {}
        self.allowed_protocols = set()
        
        self._init_bleach()
    
    def _init_bleach(self) -> None:
        """Inicializa configurações do bleach se disponível."""
        try:
            import bleach
            self.has_bleach = True
            
            # Tags base permitidas
            base_tags = set(getattr(bleach.sanitizer, "ALLOWED_TAGS", []))
            self.allowed_tags = base_tags | {
                "p", "pre", "code", "h1", "h2", "h3", "h4", "h5", "h6",
                "table", "thead", "tbody", "tr", "th", "td", 
                "ul", "ol", "li", "a", "strong", "em", "hr", "blockquote", 
                "img", "br", "span", "div", "caption", "colgroup", "col"
            }
            
            # Atributos permitidos
            base_attrs = dict(getattr(bleach.sanitizer, "ALLOWED_ATTRIBUTES", {}))
            self.allowed_attributes = {
                **base_attrs,
                "*": list(set(base_attrs.get("*", [])) | {"class", "id", "title", "style"}),
                "a": list(set(base_attrs.get("a", [])) | {"href", "rel", "target", "title", "name"}),
                "img": list(set(base_attrs.get("img", [])) | {"src", "alt", "title", "width", "height"}),
                "code": list(set(base_attrs.get("code", [])) | {"class", "data-language"}),
                "pre": list(set(base_attrs.get("pre", [])) | {"class"}),
                "table": list(set(base_attrs.get("table", [])) | {"class", "border", "cellspacing", "cellpadding"}),
            }
            
            # Protocolos permitidos
            self.allowed_protocols = set(getattr(bleach.sanitizer, "ALLOWED_PROTOCOLS", {"http", "https", "mailto"})) | {
                "http", "https", "mailto", "data"
            }
            
        except ImportError:
            logger.warning("Bleach não instalado. Sanitização HTML desativada.")
            self.has_bleach = False
    
    def sanitize(self, html: str) -> str:
        """Aplica sanitização HTML se configurado e disponível."""
        if not CONFIG.sanitize_html:
            return html
            
        if not self.has_bleach:
            logger.debug("Bleach não disponível para sanitização")
            return html
            
        try:
            import bleach
            return bleach.clean(
                html,
                tags=list(self.allowed_tags),
                attributes=self.allowed_attributes,
                protocols=self.allowed_protocols,
                strip=False,
                strip_comments=True
            )
        except Exception as e:
            logger.error("Erro na sanitização HTML: %s", e)
            return html  # Fallback: retorna HTML original

# Instância global do sanitizador
SANITIZER = HTMLSanitizer()

# =============================================================================
# SISTEMA DE CACHE INTELIGENTE
# =============================================================================

class DocsCacheManager:
    """Gerenciador avançado de cache para documentação."""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
    
    def _compress_data(self, data: str) -> bytes:
        """Comprime dados para economizar cache se habilitado."""
        if not CONFIG.enable_compression:
            return data.encode('utf-8')
        return zlib.compress(data.encode('utf-8'), level=6)
    
    def _decompress_data(self, data: bytes) -> str:
        """Descomprime dados do cache."""
        if not CONFIG.enable_compression:
            return data.decode('utf-8')
        return zlib.decompress(data).decode('utf-8')
    
    def _get_cache_key(self, filename: str, file_hash: str, kind: str = "html") -> str:
        """Gera chave de cache única e padronizada."""
        return f"docs::{kind}::{filename}::{file_hash}"
    
    def get(self, filename: str, file_hash: str) -> tuple[Optional[str], bool]:
        """Recupera dados do cache retornando (dados, cache_hit)."""
        cache_key = self._get_cache_key(filename, file_hash, "html")
        
        try:
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                self.hits += 1
                logger.debug("Cache HIT para %s", filename)
                return self._decompress_data(cached_data), True
        except Exception as e:
            logger.warning("Erro ao acessar cache para %s: %s", filename, e)
        
        self.misses += 1
        return None, False
    
    def set(self, filename: str, file_hash: str, data: str) -> bool:
        """Armazena dados no cache."""
        cache_key = self._get_cache_key(filename, file_hash, "html")
        
        try:
            compressed_data = self._compress_data(data)
            cache.set(cache_key, compressed_data, timeout=CONFIG.cache_ttl)
            logger.debug("Cache SET para %s (%d bytes)", filename, len(compressed_data))
            return True
        except Exception as e:
            logger.error("Erro ao armazenar no cache %s: %s", filename, e)
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache."""
        hit_rate = self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate * 100, 2),
            "total_operations": self.hits + self.misses
        }

# Instância global do gerenciador de cache
CACHE_MANAGER = DocsCacheManager()

# =============================================================================
# PROCESSADOR MARKDOWN AVANÇADO
# =============================================================================

class AdvancedMarkdownProcessor:
    """Processador Markdown com recursos avançados."""
    
    def __init__(self):
        if markdown2 is not None:
            self.markdown = markdown2.Markdown(extras=MARKDOWN_EXTRAS, tab_width=4)
        else:
            self.markdown = None

    def _basic_convert(self, text: str) -> str:
        """Conversão extremamente simples quando markdown2 não está disponível."""
        # Remove fenced code markers but keep content
        text = re.sub(r'```(.*?)```', r'\1', text, flags=re.DOTALL)
        # Convert headers to strong text
        text = re.sub(r'^#{1,6}\s*(.+)$', r'<strong>\1</strong>', text, flags=re.MULTILINE)
        # Emphasis replacements
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
        # Basic links
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        # Line breaks to <br>
        return '<p>' + text.replace('\n\n', '</p><p>').replace('\n', '<br>') + '</p>'
    
    def process(self, text: str, filename: str) -> tuple[str, Dict[str, Any]]:
        """
        Processa texto Markdown retornando HTML e metadados extras.
        
        Returns:
            tuple: (html_rendered, extra_metadata)
        """
        # Extrai metadados do frontmatter YAML se existir
        frontmatter_meta = self._extract_frontmatter(text)
        if frontmatter_meta:
            text = self._remove_frontmatter(text)
        
        # Processa Markdown
        if self.markdown is not None:
            html = self.markdown.convert(text)
        else:
            html = self._basic_convert(text)
        
        # Metadados extras do processamento
        extra_metadata = {
            **frontmatter_meta,
            "word_count": self._count_words(text),
            "reading_time_min": self._calculate_reading_time(text),
            "sections_count": self._count_sections(text),
            "has_code_blocks": "```" in text,
            "has_images": "![" in text,
        }
        
        return html, extra_metadata
    
    def _extract_frontmatter(self, text: str) -> Dict[str, Any]:
        """Extrai metadados do frontmatter YAML."""
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
        if not frontmatter_match:
            return {}
        
        try:
            import yaml
            frontmatter_text = frontmatter_match.group(1)
            return yaml.safe_load(frontmatter_text) or {}
        except ImportError:
            logger.debug("PyYAML não instalado. Frontmatter ignorado.")
        except Exception as e:
            logger.warning("Erro ao processar frontmatter: %s", e)
        
        return {}
    
    def _remove_frontmatter(self, text: str) -> str:
        """Remove frontmatter do texto Markdown."""
        return re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, count=1, flags=re.DOTALL)
    
    def _count_words(self, text: str) -> int:
        """Conta palavras no texto (excluindo código)."""
        # Remove blocos de código para contar apenas texto
        text_no_code = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text_no_code = re.sub(r'`[^`]*`', '', text_no_code)
        words = re.findall(r'\b\w+\b', text_no_code)
        return len(words)
    
    def _calculate_reading_time(self, text: str) -> int:
        """Calcula tempo de leitura em minutos (200 palavras/minuto)."""
        word_count = self._count_words(text)
        return max(1, round(word_count / 200))
    
    def _count_sections(self, text: str) -> int:
        """Conta número de seções (headers) no documento."""
        headers = re.findall(r'^#+\s+.+$', text, re.MULTILINE)
        return len(headers)

# =============================================================================
# UTILITÁRIOS AVANÇADOS
# =============================================================================

def _file_hash(filepath: Path) -> str:
    """Calcula hash MD5 do arquivo com tratamento de erro."""
    try:
        return hashlib.md5(filepath.read_bytes()).hexdigest()
    except Exception as e:
        logger.warning("Erro ao calcular hash para %s: %s", filepath, e)
        return "error"

def _strip_md_for_summary(text: str) -> str:
    """
    Remove marcações Markdown para extrair resumo limpo.
    Versão melhorada com mais padrões.
    """
    # Remove frontmatter primeiro
    text = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, flags=re.DOTALL)
    
    # Remove blocos de código
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    # Remove elementos Markdown sequencialmente
    patterns = [
        (r'`([^`]+)`', r'\1'),                              # Código inline
        (r'^#{1,6}\s+(.*)$', r'\1'),                       # Headers (mantém texto)
        (r'!\[[^\]]*\]\([^)]*\)', ''),                  # Imagens
        (r'\[([^\]]+)\]\([^)]*\)', r'\1'),             # Links
        (r'\*\*([^*]+)\*\*', r'\1'),                    # Negrito
        (r'__(([^_]+))__', r'\1'),                          # Negrito alternativa
        (r'\*([^*]+)\*', r'\1'),                          # Itálico
        (r'_([^_]+)_', r'\1'),                              # Itálico alternativa
        (r'~~([^~]+)~~', r'\1'),                            # Tachado
        (r'`{1,2}([^`]+)`{1,2}', r'\1'),                    # Código inline/backticks múltiplos
    ]

    for pattern, repl in patterns:
        # MULTILINE para alguns padrões que usam ^
        flags = re.MULTILINE if '^' in pattern else 0
        text = re.sub(pattern, repl, text, flags=flags)

    # Remove marcadores de listas e blockquotes residuais
    text = re.sub(r'^[>\-\*\+]\s+', '', text, flags=re.MULTILINE)
    # Remove tabelas simples (linhas com |)
    text = re.sub(r'^\s*\|.*\n', '', text, flags=re.MULTILINE)
    # Remove HTML tags simples
    text = re.sub(r'<[^>]+>', '', text)

    # Normaliza espaços
    text = re.sub(r'\s+', ' ', text).strip()

    # Limita tamanho do resumo
    if len(text) > CONFIG.summary_length:
        text = text[:CONFIG.summary_length].rstrip() + '...'
    return text


def normalize_requested_filename(filename: str) -> str:
    """Normaliza nomes de arquivos recebidos de requisições/URLs."""
    normalized = filename.strip().replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]

    while "//" in normalized:
        normalized = normalized.replace("//", "/")

    return normalized.lstrip("/")


def resolve_doc_path(filename: str) -> Path:
    """Resolve de forma segura o caminho absoluto de um documento."""
    normalized = normalize_requested_filename(filename)
    if not normalized:
        raise ValueError("Nome de arquivo inválido")

    base_path = CONFIG.docs_path.resolve()
    candidate = (base_path / normalized).resolve()

    try:
        candidate.relative_to(base_path)
    except ValueError as exc:
        raise ValueError(
            "Caminho de documento fora do diretório permitido"
        ) from exc

    return candidate


def _generate_title_from_path(relative_path: Path) -> str:
    """Gera título amigável com base no nome do arquivo."""
    stem = relative_path.stem.replace("_", " ").replace("-", " ").strip()
    return stem.title() if stem else relative_path.name


def _derive_category_from_path(relative_path: Path) -> str:
    """Retorna a categoria inferida pelo primeiro segmento do caminho."""
    if not relative_path.parts:
        return ""
    return relative_path.parts[0]


def _extract_summary_from_file(path: Path) -> str:
    """Lê pequeno trecho do arquivo para gerar resumo automático."""
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            snippet = handle.read(2000)
    except Exception as exc:  # pragma: no cover - leitura pode falhar
        logger.debug("Não foi possível extrair resumo de %s: %s", path, exc)
        return ""

    return _strip_md_for_summary(snippet)


def _build_github_url(relative_path: str) -> str:
    """Monta URL para visualização no GitHub se configurado."""
    if not CONFIG.github_base_url:
        return ""
    return f"{CONFIG.github_base_url}/{relative_path}"


# =============================================================================
# FUNÇÕES PRINCIPAIS (RECUPERADAS APÓS CORRUPÇÃO)
# =============================================================================


def _safe_read(path: Path) -> str:
    """Lê arquivo respeitando limite de tamanho configurado."""
    try:
        if not path.exists() or not path.is_file():
            return ""
        max_bytes = CONFIG.max_file_size_mb * 1024 * 1024
        if path.stat().st_size > max_bytes:
            logger.warning(
                "Arquivo %s excede limite de %dMB",
                path.name,
                CONFIG.max_file_size_mb,
            )
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.error("Falha ao ler %s: %s", path, e)
        return ""


def _sanitize_html(html: str) -> str:
    """Sanitiza HTML se bleach disponível e habilitado."""
    if not CONFIG.sanitize_html:
        return html
    try:  # pragma: no cover - sanitização condicional
        import bleach  # type: ignore
    except ModuleNotFoundError:
        logger.info("Bleach não instalado. Sanitização HTML desativada.")
        return html
    allowed_tags = [
        "p",
        "br",
        "strong",
        "em",
        "ul",
        "ol",
        "li",
        "code",
        "pre",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "a",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    ]
    return bleach.clean(html, tags=allowed_tags, strip=True)


def get_available_docs() -> Dict[str, Dict[str, Any]]:
    """Lista documentos Markdown disponíveis com metadados básicos."""
    docs: Dict[str, Dict[str, Any]] = {}
    try:
        base_path = CONFIG.docs_path.resolve()
        for entry in base_path.rglob("*.md"):
            try:
                relative_path = entry.relative_to(base_path)
            except ValueError:
                logger.debug("Ignorando arquivo fora da pasta docs: %s", entry)
                continue

            if any(part.startswith(".") for part in relative_path.parts):
                continue

            rel_key = relative_path.as_posix()

            try:
                stat = entry.stat()
            except OSError as exc:
                logger.warning(
                    "Erro ao coletar metadados de %s: %s",
                    entry,
                    exc,
                )
                continue

            metadata: Dict[str, Any] = {
                "filename": rel_key,
                "size_kb": round(stat.st_size / 1024, 1),
                "last_modified": stat.st_mtime,
                "hash": _file_hash(entry),
                "category": _derive_category_from_path(relative_path),
                "github_doc_url": _build_github_url(rel_key),
            }

            defaults = DEFAULT_FILES.get(rel_key)
            if defaults:
                metadata.update(defaults)

            metadata.setdefault(
                "title", _generate_title_from_path(relative_path)
            )
            metadata.setdefault("summary", _extract_summary_from_file(entry))

            docs[rel_key] = metadata
    except Exception as exc:
        logger.error("Falha ao listar diretório de docs: %s", exc)

    sorted_items = sorted(
        docs.items(),
        key=lambda item: (
            -int(item[1].get("priority", 0)),
            str(item[1].get("title", item[0])).lower(),
        ),
    )
    return {key: value for key, value in sorted_items}


def load_markdown_file(filename: str, use_cache: bool = True) -> str:
    """Carrega e converte Markdown em HTML (com cache)."""
    normalized = normalize_requested_filename(filename)

    try:
        path = resolve_doc_path(normalized)
    except ValueError:
        logger.warning(
            "Caminho de documentação inválido solicitado: %s",
            filename,
        )
        return "<p>Documento vazio ou não encontrado.</p>"

    raw = _safe_read(path)
    if not raw:
        return "<p>Documento vazio ou não encontrado.</p>"

    file_hash = _file_hash(path)

    if use_cache and markdown2 is not None:
        cached, hit = CACHE_MANAGER.get(normalized, file_hash)
        if hit and cached:
            return cached

    processor = AdvancedMarkdownProcessor()
    html, meta = processor.process(raw, normalized)
    html = _sanitize_html(html)

    if use_cache:
        CACHE_MANAGER.set(normalized, file_hash, html)

    return html
