from __future__ import annotations

import os
import re
from pathlib import Path
from argparse import ArgumentParser
from typing import Any, Dict, Iterator, List, Optional

from django.core.management.base import BaseCommand, CommandError

BLOCK_HEADER_PATTERN = re.compile(r"^# Time: ")
QUERY_TIME_PATTERN = re.compile(
    r"# Query_time: ([0-9.]+)\s+Lock_time: ([0-9.]+)\s+"
    r"Rows_sent: ([0-9]+)\s+Rows_examined: ([0-9]+)"
)


class Command(BaseCommand):
    help = (
        "Analyze a MariaDB/MySQL slow query log "
        "and display the slowest statements."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--path",
            help=(
                "Absolute path to the slow query log. Defaults to "
                "$MYSQL_SLOW_LOG_PATH when omitted."
            ),
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
            help="Number of slowest entries to display (default: 5).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        path = options.get("path") or os.environ.get("MYSQL_SLOW_LOG_PATH")
        limit = options.get("limit", 5)

        if not path:
            raise CommandError(
                "Provide --path or configure the MYSQL_SLOW_LOG_PATH "
                "environment variable."
            )

        log_path = Path(path)
        if not log_path.exists():
            raise CommandError(f"File {log_path} not found.")

        entries = list(self._parse_slow_log(log_path))
        if not entries:
            self.stdout.write(
                self.style.WARNING("No entries found in the slow query log.")
            )
            return

        entries.sort(key=lambda item: item["query_time"], reverse=True)
        self.stdout.write(
            self.style.NOTICE(f"Total entries found: {len(entries)}")
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Showing top {min(limit, len(entries))} entries:"
            )
        )

        for entry in entries[:limit]:
            self.stdout.write("-" * 80)
            self.stdout.write(f"Time:       {entry['time']}")
            self.stdout.write(
                f"Query_time: {entry['query_time']}s | "
                f"Lock: {entry['lock_time']}s | "
                f"Rows sent/examined: {entry['rows_sent']}/"
                f"{entry['rows_examined']}"
            )
            self.stdout.write("SQL:")
            self.stdout.write(entry["sql"].strip())
            self.stdout.write("")

    def _parse_slow_log(self, path: Path) -> Iterator[Dict[str, Any]]:
        current_block: List[str] = []
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if BLOCK_HEADER_PATTERN.match(line):
                    if current_block:
                        parsed = self._extract_entry(current_block)
                        if parsed:
                            yield parsed
                    current_block = [line]
                else:
                    current_block.append(line)

        if current_block:
            parsed = self._extract_entry(current_block)
            if parsed:
                yield parsed

    def _extract_entry(self, block: List[str]) -> Optional[Dict[str, Any]]:
        header = block[0].strip()
        query_details: Optional[Dict[str, Any]] = None
        sql_lines: List[str] = []

        for line in block[1:]:
            match = QUERY_TIME_PATTERN.search(line)
            if match:
                query_details = {
                    "query_time": float(match.group(1)),
                    "lock_time": float(match.group(2)),
                    "rows_sent": int(match.group(3)),
                    "rows_examined": int(match.group(4)),
                }
                continue

            if line.strip().upper().startswith("SET TIMESTAMP"):
                continue

            if line.startswith("#"):
                continue

            sql_lines.append(line)

        if not query_details:
            return None

        query_details.update(
            {
                "time": header.replace("# Time: ", ""),
                "sql": "".join(sql_lines),
            }
        )
        return query_details
