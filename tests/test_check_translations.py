from pathlib import Path

from scripts.check_translations import (
    PORTUGUESE_KEYWORDS,
    scan_paths,
)


def test_scan_paths_detects_non_ascii(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text("texto = 'ação'\n", encoding="utf-8")

    issues = scan_paths([
        file_path,
    ], extensions={".py"}, keywords=PORTUGUESE_KEYWORDS)

    assert any(issue.reason == "non_ascii" for issue in issues)


def test_scan_paths_detects_keywords(tmp_path: Path) -> None:
    file_path = tmp_path / "sample_keyword.py"
    file_path.write_text("descricao_label = 'Description'\n", encoding="utf-8")

    issues = scan_paths([
        file_path,
    ], extensions={".py"}, keywords=PORTUGUESE_KEYWORDS)

    keyword_hits = [
        issue
        for issue in issues
        if issue.reason == "keyword" and "descricao" in issue.hits
    ]
    assert keyword_hits


def test_scan_paths_without_issues(tmp_path: Path) -> None:
    file_path = tmp_path / "clean.py"
    file_path.write_text("value = 'All good here'\n", encoding="utf-8")

    issues = scan_paths([
        file_path,
    ], extensions={".py"}, keywords=PORTUGUESE_KEYWORDS)

    assert issues == []
