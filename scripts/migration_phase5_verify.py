#!/usr/bin/env python
# Phase 5 verification helper for migration inventory.0004 (route table rename)
# PRE:  python scripts/migration_phase5_verify.py \
#          --phase pre --snapshot pre.json
# MIGRATE: python manage.py migrate
# POST: python scripts/migration_phase5_verify.py \
#          --phase post --compare pre.json

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import django

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.test")
django.setup()

from django.db import connection  # noqa: E402

OLD_TABLES = [
    "routes_builder_route",
    "routes_builder_routesegment",
    "routes_builder_routeevent",
]
NEW_TABLES = [
    "inventory_route",
    "inventory_routesegment",
    "inventory_routeevent",
]


@dataclass
class TableStatus:
    name: str
    exists: bool
    row_count: Optional[int]


def table_names() -> List[str]:
    return connection.introspection.table_names()


def row_count(table: str) -> Optional[int]:
    try:
        with connection.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            val = cur.fetchone()
            return int(val[0]) if val else 0
    except Exception:
        return None


def collect(tables: List[str]) -> Dict[str, TableStatus]:
    existing = set(table_names())
    out: Dict[str, TableStatus] = {}
    for t in tables:
        exists = t in existing
        out[t] = TableStatus(t, exists, row_count(t) if exists else None)
    return out


def header(title: str) -> None:
    print(f"\n{'=' * 50}\n{title}\n{'=' * 50}")


def phase_pre(snapshot_path: str) -> int:
    header("PRE phase")
    old_status = collect(OLD_TABLES)
    new_status = collect(NEW_TABLES)
    for s in old_status.values():
        tag = 'OK' if s.exists else 'MISS'
        print(f"OLD {s.name}: {tag} rows={s.row_count}")
    for s in new_status.values():
        tag = 'OK' if s.exists else 'MISS'
        print(f"NEW {s.name}: {tag} rows={s.row_count}")
    snap = {
        "old": {k: v.row_count for k, v in old_status.items()},
        "new": {k: v.row_count for k, v in new_status.items()},
    }
    with open(snapshot_path, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, indent=2, ensure_ascii=False)
    print(f"Snapshot saved: {snapshot_path}")
    return 0


def phase_post(compare_path: Optional[str]) -> int:
    header("POST phase")
    old_status = collect(OLD_TABLES)
    new_status = collect(NEW_TABLES)
    problems: List[str] = []
    for s in old_status.values():
        if s.exists:
            problems.append(f"Legacy table still present: {s.name}")
    for s in new_status.values():
        if not s.exists:
            problems.append(f"Missing new table: {s.name}")
    if compare_path and os.path.exists(compare_path):
        with open(compare_path, "r", encoding="utf-8") as fh:
            snap = json.load(fh)
        pre_total = sum(v or 0 for v in snap.get("old", {}).values())
        post_total = sum(v.row_count or 0 for v in new_status.values())
        print(f"Rows pre={pre_total} post={post_total}")
        if pre_total != post_total:
            problems.append(
                f"Row count mismatch pre={pre_total} post={post_total}"
            )
    if problems:
        header("FAIL")
        for p in problems:
            print(f" - {p}")
        return 1
    header("OK")
    print("inventory.0004 verified.")
    return 0


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Verify inventory.0004 route table rename"
    )
    parser.add_argument(
        "--phase", required=True, choices=["pre", "post"], help="Phase"
    )
    parser.add_argument("--snapshot", help="Snapshot file (pre phase)")
    parser.add_argument(
        "--compare", help="Snapshot file to compare (post phase)"
    )
    args = parser.parse_args()
    if args.phase == "pre":
        if not args.snapshot:
            print("--snapshot required for pre phase")
            return 1
        return phase_pre(args.snapshot)
    return phase_post(args.compare)


if __name__ == "__main__":
    sys.exit(main())
