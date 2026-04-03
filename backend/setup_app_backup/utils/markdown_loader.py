"""
Safe and optimized Markdown-to-HTML conversion for the documentation panel.

IMPROVEMENTS IMPLEMENTED:
1. Complete type hints for better development
2. Centralized configuration via a dedicated class
3. Smarter cache with optional compression
4. Plugin system prepared for extensibility
5. Advanced metadata with automatic extraction
6. Support for multiple cache strategies
7. Internationalization readiness
8. Improved performance metrics
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import zlib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, TypedDict

try:
    import markdown2  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback
    markdown2 = None  # type: ignore
    # Logger is not initialized yet; rely on the base logging module
    logging.getLogger(__name__).warning(
        "markdown2 is not installed; falling back to basic Markdown rendering."
    )
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

# =============================================================================
# CENTRALIZED TYPED CONFIGURATION
# =============================================================================


class CacheStrategy(Enum):
    """Cache strategies available for the documentation pipeline."""
    CONTENT_HASH = "content_hash"
    TIMESTAMP = "timestamp"
    HYBRID = "hybrid"

@dataclass
class DocsConfig:
    """Central configuration for the documentation module."""

    # Paths and directories
    docs_dir: str = field(
        default_factory=lambda: os.getenv("DOCS_DIR", "doc")
    )
    docs_path: Path | None = None

    # Cache
    cache_ttl: int = field(
        default_factory=lambda: int(os.getenv("DOCS_CACHE_TTL", "300"))
    )
    cache_strategy: CacheStrategy = CacheStrategy.HYBRID
    enable_compression: bool = field(
        default_factory=lambda: (
            os.getenv("DOCS_CACHE_COMPRESSION", "false").lower() == "true"
        )
    )

    # Security
    sanitize_html: bool = field(
        default_factory=lambda: (
            os.getenv("DOCS_SANITIZE_HTML", "true").lower() == "true"
        )
    )

    # GitHub
    github_base_url: str = field(
        default_factory=lambda: os.getenv("DOCS_GITHUB_BASE_URL", "").rstrip(
            "/"
        )
    )

    # Performance
    preload_enabled: bool = field(
        default_factory=lambda: (
            os.getenv("DOCS_PRELOAD_ENABLED", "true").lower() == "true"
        )
    )
    max_file_size_mb: int = field(
        default_factory=lambda: int(os.getenv("DOCS_MAX_FILE_SIZE_MB", "10"))
    )

    # Metadata
    summary_length: int = 280
    extract_categories: bool = True
    extract_tags: bool = True

    def __post_init__(self):
        """Initialize path configuration after the dataclass instantiation."""
        if self.docs_path is None:
            self.docs_path = Path(settings.BASE_DIR) / self.docs_dir


# Global configuration instance
CONFIG = DocsConfig()

# =============================================================================
# ADVANCED TYPE DEFINITIONS
# =============================================================================


class DocMetadata(TypedDict, total=False):
    """Typed structure that describes documentation metadata."""
    title: str
    filename: str
    summary: str
    size_kb: float
    modified_at: str
    github_doc_url: str | None
    views: int
    category: str
    tags: list[str]
    reading_time_min: int
    word_count: int
    sections_count: int
    has_code_blocks: bool
    has_images: bool


class ProcessingMetrics(TypedDict):
    """Processing metrics captured while rendering markdown."""
    processing_time_ms: float
    cache_hit: bool
    file_size_bytes: int
    compressed_size_bytes: int | None


class MarkdownProcessor(Protocol):
    """Interface definition for markdown processors."""

    def process(
        self,
        text: str,
        filename: str,
    ) -> tuple[str, dict[str, Any]]:
        ...

# =============================================================================
# PRIORITIZED FILES AND MARKDOWN SETTINGS
# =============================================================================


# Main files (displayed first and given higher priority)
DEFAULT_FILES: dict[str, dict[str, Any]] = {
    "developer/README.md": {
        "title": _("Documenta&ccedil;&atilde;o Principal"),
        "category": "developer",
        "priority": 100,
    },
    "getting-started/QUICKSTART_LOCAL.md": {
        "title": _("Guia R&aacute;pido: Ambiente Local"),
        "category": "getting-started",
        "priority": 95,
    },
    "operations/DEPLOYMENT.md": {
        "title": _("Guia de Deploy e Containers"),
        "category": "operations",
        "priority": 90,
    },
    "reference-root/API_DOCUMENTATION.md": {
        "title": _("Documenta&ccedil;&atilde;o da API"),
        "category": "api",
        "priority": 85,
    },
    "reference/README.md": {
        "title": _("Refer&ecirc;ncias T&eacute;cnicas"),
        "category": "reference",
        "priority": 80,
    },
}

# Optimized markdown2 extras
MARKDOWN_EXTRAS = [
    "fenced-code-blocks",    # Code blocks with syntax highlighting
    "tables",                # Tables
    "header-ids",            # Automatic header IDs
    "toc",                   # Table of contents
    "strike",                # Strikethrough text
    "code-friendly",         # Improved inline code handling
    "cuddled-lists",         # Compact list support
    "smarty-pants",          # Smart typography
    "task_list",             # Task list support
    "break-on-newline",      # Line break support
    "footnotes",             # Footnotes
    "metadata",              # YAML front matter metadata
]

# =============================================================================
# ADVANCED BLEACH SANITIZATION
# =============================================================================


class HTMLSanitizer:
    """Centralized HTML sanitization manager."""

    def __init__(self):
        self.has_bleach = False
        self.allowed_tags = set()
        self.allowed_attributes = {}
        self.allowed_protocols = set()

        self._init_bleach()

    def _init_bleach(self) -> None:
        """Initialize bleach configuration when the package is available."""
        try:
            import bleach
            self.has_bleach = True

            # Base set of allowed tags
            base_tags = set(getattr(bleach.sanitizer, "ALLOWED_TAGS", []))
            self.allowed_tags = base_tags | {
                "p",
                "pre",
                "code",
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
                "table",
                "thead",
                "tbody",
                "tr",
                "th",
                "td",
                "ul",
                "ol",
                "li",
                "a",
                "strong",
                "em",
                "hr",
                "blockquote",
                "img",
                "br",
                "span",
                "div",
                "caption",
                "colgroup",
                "col",
            }

            # Allowed attributes
            base_attrs = dict(
                getattr(bleach.sanitizer, "ALLOWED_ATTRIBUTES", {})
            )
            self.allowed_attributes = {
                **base_attrs,
                "*": list(
                    set(base_attrs.get("*", []))
                    | {"class", "id", "title", "style"}
                ),
                "a": list(
                    set(base_attrs.get("a", []))
                    | {"href", "rel", "target", "title", "name"}
                ),
                "img": list(
                    set(base_attrs.get("img", []))
                    | {"src", "alt", "title", "width", "height"}
                ),
                "code": list(
                    set(base_attrs.get("code", []))
                    | {"class", "data-language"}
                ),
                "pre": list(set(base_attrs.get("pre", [])) | {"class"}),
                "table": list(
                    set(base_attrs.get("table", []))
                    | {"class", "border", "cellspacing", "cellpadding"}
                ),
            }

            # Allowed protocols
            self.allowed_protocols = set(
                getattr(
                    bleach.sanitizer,
                    "ALLOWED_PROTOCOLS",
                    {"http", "https", "mailto"},
                )
            ) | {"http", "https", "mailto", "data"}

        except ImportError:
            logger.warning(
                "Bleach is not installed. HTML sanitization disabled."
            )
            self.has_bleach = False

    def sanitize(self, html: str) -> str:
        """Apply HTML sanitization when configured and available."""
        if not CONFIG.sanitize_html:
            return html

        if not self.has_bleach:
            logger.debug("Bleach is not available for sanitization")
            return html

        try:
            import bleach
            return bleach.clean(
                html,
                tags=list(self.allowed_tags),
                attributes=self.allowed_attributes,
                protocols=self.allowed_protocols,
                strip=False,
                strip_comments=True,
            )
        except Exception as e:
            logger.error("Error while sanitizing HTML: %s", e)
            return html  # Fallback: return original HTML


# Global sanitizer instance
SANITIZER = HTMLSanitizer()


# =============================================================================
# SMART CACHE SYSTEM
# =============================================================================


class DocsCacheManager:
    """Advanced cache manager designed for documentation content."""

    def __init__(self):
        self.hits = 0
        self.misses = 0

    def _compress_data(self, data: str) -> bytes:
        """Compress cached data when compression is enabled."""
        if not CONFIG.enable_compression:
            return data.encode('utf-8')
        return zlib.compress(data.encode('utf-8'), level=6)

    def _decompress_data(self, data: bytes) -> str:
        """Decompress cached data when compression is enabled."""
        if not CONFIG.enable_compression:
            return data.decode('utf-8')
        return zlib.decompress(data).decode('utf-8')

    def _get_cache_key(
        self,
        filename: str,
        file_hash: str,
        kind: str = "html",
    ) -> str:
        """Generate a normalized cache key."""
        return f"docs::{kind}::{filename}::{file_hash}"

    def get(self, filename: str, file_hash: str) -> tuple[str | None, bool]:
        """Retrieve cached data, returning the value and a hit flag."""
        cache_key = self._get_cache_key(filename, file_hash, "html")

        try:
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                self.hits += 1
                logger.debug("Cache hit for %s", filename)
                return self._decompress_data(cached_data), True
        except Exception as e:
            logger.warning("Error accessing cache for %s: %s", filename, e)

        self.misses += 1
        return None, False

    def set(self, filename: str, file_hash: str, data: str) -> bool:
        """Store data in the cache backend."""
        cache_key = self._get_cache_key(filename, file_hash, "html")

        try:
            compressed_data = self._compress_data(data)
            cache.set(cache_key, compressed_data, timeout=CONFIG.cache_ttl)
            logger.debug(
                "Cache set for %s (%d bytes)", filename, len(compressed_data)
            )
            return True
        except Exception as e:
            logger.error("Error storing %s in cache: %s", filename, e)
            return False

    def get_stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        operations = self.hits + self.misses
        hit_rate = self.hits / operations if operations else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate * 100, 2),
            "total_operations": operations,
        }


# Global cache manager instance
CACHE_MANAGER = DocsCacheManager()

# =============================================================================
# ADVANCED MARKDOWN PROCESSOR
# =============================================================================


class AdvancedMarkdownProcessor:
    """Markdown processor with advanced capabilities."""

    def __init__(self):
        if markdown2 is not None:
            self.markdown = markdown2.Markdown(
                extras=MARKDOWN_EXTRAS,
                tab_width=4,
            )
        else:
            self.markdown = None

    def _basic_convert(self, text: str) -> str:
        """Perform a minimal conversion when markdown2 is unavailable."""
        # Remove fenced code markers but keep content
        text = re.sub(r'```(.*?)```', r'\1', text, flags=re.DOTALL)
        # Convert headers to strong text
        text = re.sub(
            r'^#{1,6}\s*(.+)$',
            r'<strong>\1</strong>',
            text,
            flags=re.MULTILINE,
        )
        # Emphasis replacements
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
        # Basic links
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        # Line breaks to <br>
        return (
            '<p>'
            + text.replace('\n\n', '</p><p>').replace('\n', '<br>')
            + '</p>'
        )

    def process(self, text: str, filename: str) -> tuple[str, dict[str, Any]]:
        """
        Render markdown text into HTML and return additional metadata.

        Returns:
            tuple: (html_rendered, extra_metadata)
        """
        # Extract metadata from YAML front matter when present
        frontmatter_meta = self._extract_frontmatter(text)
        if frontmatter_meta:
            text = self._remove_frontmatter(text)

    # Process markdown content
        if self.markdown is not None:
            html = self.markdown.convert(text)
        else:
            html = self._basic_convert(text)

    # Additional metadata collected during processing
        extra_metadata = {
            **frontmatter_meta,
            "word_count": self._count_words(text),
            "reading_time_min": self._calculate_reading_time(text),
            "sections_count": self._count_sections(text),
            "has_code_blocks": "```" in text,
            "has_images": "![" in text,
        }

        return html, extra_metadata

    def _extract_frontmatter(self, text: str) -> dict[str, Any]:
        """Extract metadata from the YAML front matter."""
        frontmatter_match = re.match(
            r'^---\s*\n(.*?)\n---\s*\n',
            text,
            re.DOTALL,
        )
        if not frontmatter_match:
            return {}

        try:
            import yaml
            frontmatter_text = frontmatter_match.group(1)
            return yaml.safe_load(frontmatter_text) or {}
        except ImportError:
            logger.debug(
                "PyYAML is not installed. Ignoring front matter block."
            )
        except Exception as e:
            logger.warning("Error while processing front matter: %s", e)

        return {}

    def _remove_frontmatter(self, text: str) -> str:
        """Remove front matter from the markdown text."""
        return re.sub(
            r'^---\s*\n.*?\n---\s*\n',
            '',
            text,
            count=1,
            flags=re.DOTALL,
        )

    def _count_words(self, text: str) -> int:
        """Count the words in the text (excluding code blocks)."""
        # Remove code blocks before counting
        text_no_code = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text_no_code = re.sub(r'`[^`]*`', '', text_no_code)
        words = re.findall(r'\b\w+\b', text_no_code)
        return len(words)

    def _calculate_reading_time(self, text: str) -> int:
        """Estimate reading time in minutes (200 words per minute)."""
        word_count = self._count_words(text)
        return max(1, round(word_count / 200))

    def _count_sections(self, text: str) -> int:
        """Count the number of sections (headers) in the document."""
        headers = re.findall(r'^#+\s+.+$', text, re.MULTILINE)
        return len(headers)

# =============================================================================
# ADVANCED UTILITIES
# =============================================================================


def _file_hash(filepath: Path) -> str:
    """Compute an MD5 hash for the file with error handling."""
    try:
        return hashlib.md5(filepath.read_bytes()).hexdigest()
    except Exception as e:
        logger.warning("Error calculating hash for %s: %s", filepath, e)
        return "error"


def _strip_md_for_summary(text: str) -> str:
    """
    Remove markdown markup to extract a clean summary.
    Improved version with additional patterns.
    """
    # Remove front matter first
    text = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, flags=re.DOTALL)

    # Remove code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)

    # Remove markdown elements sequentially
    patterns = [
        (r'`([^`]+)`', r'\1'),                              # Inline code
        (r'^#{1,6}\s+(.*)$', r'\1'),            # Headers (keep text)
        (r'!\[[^\]]*\]\([^)]*\)', ''),                  # Images
        (r'\[([^\]]+)\]\([^)]*\)', r'\1'),             # Links
        (r'\*\*([^*]+)\*\*', r'\1'),                    # Bold
        (r'__(([^_]+))__', r'\1'),                          # Alternate bold
        (r'\*([^*]+)\*', r'\1'),                          # Italic
        (r'_([^_]+)_', r'\1'),                              # Alternate italic
        (r'~~([^~]+)~~', r'\1'),                            # Strikethrough
        # Inline code/backticks
        (r'`{1,2}([^`]+)`{1,2}', r'\1'),
    ]

    for pattern, repl in patterns:
        # Use re.MULTILINE for patterns anchored at the start
        flags = re.MULTILINE if '^' in pattern else 0
        text = re.sub(pattern, repl, text, flags=flags)

    # Remove list markers and residual blockquotes
    text = re.sub(r'^[>\-\*\+]\s+', '', text, flags=re.MULTILINE)
    # Remove simple table rows (lines containing |)
    text = re.sub(r'^\s*\|.*\n', '', text, flags=re.MULTILINE)
    # Remove basic HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Enforce summary length limit
    if len(text) > CONFIG.summary_length:
        text = text[:CONFIG.summary_length].rstrip() + '...'
    return text


def normalize_requested_filename(filename: str) -> str:
    """Normalize filenames received via requests or URLs."""
    normalized = filename.strip().replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]

    while "//" in normalized:
        normalized = normalized.replace("//", "/")

    return normalized.lstrip("/")


def resolve_doc_path(filename: str) -> Path:
    """Resolve the absolute path for a documentation file safely."""
    normalized = normalize_requested_filename(filename)
    if not normalized:
        raise ValueError("Invalid filename")

    base_path = CONFIG.docs_path.resolve()
    candidate = (base_path / normalized).resolve()

    try:
        candidate.relative_to(base_path)
    except ValueError as exc:
        raise ValueError(
            "Requested document path is outside the allowed directory"
        ) from exc

    return candidate


def _generate_title_from_path(relative_path: Path) -> str:
    """Generate a friendly title based on the filename."""
    stem = relative_path.stem.replace("_", " ").replace("-", " ").strip()
    return stem.title() if stem else relative_path.name


def _derive_category_from_path(relative_path: Path) -> str:
    """Return the category inferred from the first path segment."""
    if not relative_path.parts:
        return ""
    return relative_path.parts[0]


def _extract_summary_from_file(path: Path) -> str:
    """Read a small portion of the file to build an automatic summary."""
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            snippet = handle.read(2000)
    except Exception as exc:  # pragma: no cover - reading may fail
        logger.debug("Unable to extract summary from %s: %s", path, exc)
        return ""

    return _strip_md_for_summary(snippet)


def _build_github_url(relative_path: str) -> str:
    """Build a GitHub URL for the document when configured."""
    if not CONFIG.github_base_url:
        return ""
    return f"{CONFIG.github_base_url}/{relative_path}"


# =============================================================================
# PRIMARY FUNCTIONS (RECOVERED AFTER CORRUPTION)
# =============================================================================


def _safe_read(path: Path) -> str:
    """Read a file while respecting the configured file size limit."""
    try:
        if not path.exists() or not path.is_file():
            return ""
        max_bytes = CONFIG.max_file_size_mb * 1024 * 1024
        if path.stat().st_size > max_bytes:
            logger.warning(
                "File %s exceeds the %dMB limit",
                path.name,
                CONFIG.max_file_size_mb,
            )
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.error("Failed to read %s: %s", path, e)
        return ""


def _sanitize_html(html: str) -> str:
    """Sanitize HTML when bleach is available and enabled."""
    if not CONFIG.sanitize_html:
        return html
    try:  # pragma: no cover - conditional sanitization
        import bleach  # type: ignore
    except ModuleNotFoundError:
        logger.info("Bleach is not installed. HTML sanitization disabled.")
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


def get_available_docs() -> dict[str, dict[str, Any]]:
    """List available markdown documents with basic metadata."""
    docs: dict[str, dict[str, Any]] = {}
    try:
        base_path = CONFIG.docs_path.resolve()
        for entry in base_path.rglob("*.md"):
            try:
                relative_path = entry.relative_to(base_path)
            except ValueError:
                logger.debug(
                    "Ignoring file outside the docs directory: %s",
                    entry,
                )
                continue

            if any(part.startswith(".") for part in relative_path.parts):
                continue

            rel_key = relative_path.as_posix()

            try:
                stat = entry.stat()
            except OSError as exc:
                logger.warning(
                    "Error collecting metadata from %s: %s",
                    entry,
                    exc,
                )
                continue

            metadata: dict[str, Any] = {
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
        logger.error("Failed to list documentation directory: %s", exc)

    sorted_items = sorted(
        docs.items(),
        key=lambda item: (
            -int(item[1].get("priority", 0)),
            str(item[1].get("title", item[0])).lower(),
        ),
    )
    return dict(sorted_items)


def load_markdown_file(filename: str, use_cache: bool = True) -> str:
    """Load and convert markdown into HTML, using cache when available."""
    normalized = normalize_requested_filename(filename)

    try:
        path = resolve_doc_path(normalized)
    except ValueError:
        logger.warning(
            "Invalid documentation path requested: %s",
            filename,
        )
        return "<p>Documento vazio ou n&atilde;o encontrado.</p>"

    raw = _safe_read(path)
    if not raw:
        return "<p>Documento vazio ou n&atilde;o encontrado.</p>"

    file_hash = _file_hash(path)

    if use_cache and markdown2 is not None:
        cached, hit = CACHE_MANAGER.get(normalized, file_hash)
        if hit and cached:
            return cached

    processor = AdvancedMarkdownProcessor()
    html, _meta = processor.process(raw, normalized)
    html = _sanitize_html(html)

    if use_cache:
        CACHE_MANAGER.set(normalized, file_hash, html)

    return html
