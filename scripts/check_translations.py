"""Static checker for Portuguese strings in source files.

This helper scans source files for non-ASCII characters or known Portuguese
keywords so we can keep UI strings and identifiers in English. It can be
used locally (`python scripts/check_translations.py`) or inside CI.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence
import re

# Directories that should be ignored when walking the tree.
IGNORE_DIR_NAMES = {
    ".git",
    "__pycache__",
    "legacy_backup",
    "migrations",
    "node_modules",
    "staticfiles",
    "venv",
}

# File extensions inspected by default.
DEFAULT_EXTENSIONS = {
    ".py",
    ".html",
    ".txt",
    ".js",
    ".ts",
    ".tsx",
}

# Plain ASCII keywords that often indicate untranslated Portuguese strings.
PORTUGUESE_KEYWORDS = {
    "descricao",
    "sincronizacao",
    "configuracao",
    "dispositivo",
    "roteador",
    "licenca",
    "atualizacao",
    "mapa",
    "rede",
    "nome",
}

WORD_PATTERN = re.compile(r"[a-z]+", re.IGNORECASE)


@dataclass
class Issue:
    """Represents a potential translation problem."""

    path: Path
    line_no: int
    reason: str
    snippet: str
    hits: tuple[str, ...] = ()


def iter_target_files(
    paths: Sequence[str | Path],
    *,
    extensions: set[str],
) -> Iterator[Path]:
    """Yield files inside the given paths that match the desired extensions."""

    for raw_path in paths:
        root = Path(raw_path).resolve()
        if not root.exists():
            continue
        if root.is_file():
            if root.suffix in extensions:
                yield root
            continue
        for candidate in root.rglob("*"):
            if not candidate.is_file():
                continue
            if candidate.suffix not in extensions:
                continue
            if IGNORE_DIR_NAMES.intersection(candidate.parts):
                continue
            yield candidate


def find_issues(
    content: str,
    *,
    path: Path,
    keywords: set[str],
) -> Iterable[Issue]:
    """Find suspicious lines within a file."""

    for idx, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue

        if any(ord(char) > 127 for char in stripped):
            yield Issue(
                path=path,
                line_no=idx,
                reason="non_ascii",
                snippet=stripped,
            )
            continue

        words = set(word.lower() for word in WORD_PATTERN.findall(stripped))
        hits = tuple(sorted(words.intersection(keywords)))
        if hits:
            yield Issue(
                path=path,
                line_no=idx,
                reason="keyword",
                snippet=stripped,
                hits=hits,
            )


def scan_paths(
    paths: Sequence[str | Path],
    *,
    extensions: set[str] | None = None,
    keywords: set[str] | None = None,
) -> list[Issue]:
    """Collect issues across multiple paths."""

    active_exts = extensions or DEFAULT_EXTENSIONS
    active_keywords = keywords or PORTUGUESE_KEYWORDS

    issues: list[Issue] = []
    for file_path in iter_target_files(paths, extensions=active_exts):
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            issues.append(
                Issue(
                    path=file_path,
                    line_no=0,
                    reason="decode_error",
                    snippet="Unable to decode file as UTF-8",
                )
            )
            continue

        issues.extend(
            find_issues(
                text,
                path=file_path,
                keywords=active_keywords,
            )
        )

    return issues


def format_issue(issue: Issue) -> str:
    """Pretty-print an issue for console output."""

    location = (
        f"{issue.path}:{issue.line_no}"
        if issue.line_no
        else f"{issue.path}"
    )
    if issue.reason == "keyword" and issue.hits:
        hits = ", ".join(issue.hits)
        detail = f"Portuguese keyword(s): {hits}"
    elif issue.reason == "non_ascii":
        detail = "Contains non-ASCII characters"
    elif issue.reason == "decode_error":
        detail = "File is not UTF-8 encoded"
    else:
        detail = issue.reason
    return f"{location} -> {detail} :: {issue.snippet}"


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        default=[
            "inventory",
            "maps_view",
            "routes_builder",
            "setup_app",
            "templates",
        ],
        help="Paths to scan (directories or individual files).",
    )
    parser.add_argument(
        "--fail-on-find",
        action="store_true",
        help="Exit with status 1 if any issue is detected.",
    )
    parser.add_argument(
        "--extensions",
        nargs="*",
        help=(
            "Optional list of file extensions to include "
            "(overrides default)."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry-point for both module import and CLI usage."""

    args = parse_args(argv or sys.argv[1:])
    extensions = (
        {ext if ext.startswith(".") else f".{ext}" for ext in args.extensions}
        if args.extensions
        else DEFAULT_EXTENSIONS
    )

    issues = scan_paths(args.paths, extensions=extensions)

    if issues:
        print("Portuguese strings or non-ASCII characters found:\n")
        for issue in issues:
            print(format_issue(issue))
        print(f"\nTotal issues: {len(issues)}")
        if args.fail_on_find:
            return 1
    else:
        print("No potential translation issues detected.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
