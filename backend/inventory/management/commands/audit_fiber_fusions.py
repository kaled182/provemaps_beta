import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone


class Command(BaseCommand):
    """Exporta e compara snapshots de fusões de fibra."""

    help = (
        "Exporta um snapshot das fusões (antes da migração) ou compara com um "
        "baseline salvo para verificar se nenhuma fusão foi perdida."
    )

    def add_arguments(self, parser) -> None:  # type: ignore[override]
        parser.add_argument(
            "--baseline-out",
            dest="baseline_out",
            type=str,
            help="Escreve o snapshot atual para o caminho informado (JSON).",
        )
        parser.add_argument(
            "--compare",
            dest="compare_path",
            type=str,
            help="Compara o estado atual com o snapshot JSON informado.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        baseline_out = options.get("baseline_out")
        compare_path = options.get("compare_path")

        if baseline_out and compare_path:
            raise CommandError(
                "Use apenas uma das opções: --baseline-out ou --compare."
            )
        if not baseline_out and not compare_path:
            raise CommandError(
                "Informe --baseline-out para exportar ou "
                "--compare para validar."
            )

        if baseline_out:
            snapshot = collect_snapshot()
            snapshot["generated_at"] = timezone.now().isoformat()
            target = Path(baseline_out)
            target.write_text(
                json.dumps(snapshot, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "Snapshot salvo em "
                    f"{target}. Total de fusões: {snapshot['total_pairs']}"
                )
            )
            return

        assert compare_path is not None
        baseline_file = Path(compare_path)
        if not baseline_file.exists():
            raise CommandError(
                f"Arquivo de baseline não encontrado: {baseline_file}"
            )

        baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
        current = collect_snapshot()

        comparison = compare_snapshots(baseline, current)
        report_comparison(self.stdout, self.style, comparison)


def collect_snapshot() -> dict[str, Any]:
    if legacy_columns_available():
        return snapshot_from_legacy()
    if table_exists("inventory_fiber_fusion"):
        return snapshot_from_fiber_fusion()
    raise CommandError(
        "Não foi possível localizar os campos legados nem a tabela "
        "inventory_fiber_fusion."
    )


def table_exists(table_name: str) -> bool:
    tables = connection.introspection.table_names()
    return table_name in tables


def legacy_columns_available() -> bool:
    if not table_exists("inventory_fiber_strand"):
        return False
    columns = get_columns("inventory_fiber_strand")
    required = {
        "fusion_infrastructure_id",
        "fusion_tray",
        "fusion_slot",
        "fused_to_id",
    }
    return required.issubset(columns)


def get_columns(table_name: str) -> set[str]:
    with connection.cursor() as cursor:
        try:
            description = connection.introspection.get_table_description(
                cursor, table_name
            )
        except Exception:
            return set()
    return {col.name for col in description}


def snapshot_from_legacy() -> dict[str, Any]:
    slots: dict[tuple[int, int | None, int | None], tuple[int, int]] = {}
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                id,
                fused_to_id,
                fusion_infrastructure_id,
                fusion_tray,
                fusion_slot
            FROM inventory_fiber_strand
            WHERE fusion_infrastructure_id IS NOT NULL
            ORDER BY id
            """
        )
        rows = cursor.fetchall()

    for fiber_id, fused_to_id, infra_id, tray, slot in rows:
        if infra_id is None or tray is None or slot is None:
            continue
        slot_key = (infra_id, tray, slot)
        if slot_key in slots:
            continue
        partner_id = fused_to_id or fiber_id
        slots[slot_key] = (fiber_id, partner_id)

    slot_entries: list[dict[str, Any]] = [
        {
            "infrastructure_id": infra,
            "tray": tray,
            "slot": slot,
            "fiber_a_id": pair[0],
            "fiber_b_id": pair[1],
        }
        for (infra, tray, slot), pair in sorted(slots.items())
    ]

    return {
        "source": "legacy_fiber_strand",
        "total_pairs": len(slot_entries),
        "slots": slot_entries,
    }


def snapshot_from_fiber_fusion() -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT infrastructure_id, tray, slot, fiber_a_id, fiber_b_id
            FROM inventory_fiber_fusion
            ORDER BY infrastructure_id, tray, slot
            """
        )
        rows = cursor.fetchall()

    slot_entries = [
        {
            "infrastructure_id": infra,
            "tray": tray,
            "slot": slot,
            "fiber_a_id": fiber_a,
            "fiber_b_id": fiber_b,
        }
        for infra, tray, slot, fiber_a, fiber_b in rows
    ]

    return {
        "source": "fiber_fusion",
        "total_pairs": len(slot_entries),
        "slots": slot_entries,
    }


def normalize_slots(snapshot: dict[str, Any]) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    for entry in snapshot.get("slots", []):
        key = f"{entry['infrastructure_id']}:{entry['tray']}:{entry['slot']}"
        pair = sorted((entry["fiber_a_id"], entry["fiber_b_id"]))
        result[key] = (pair[0], pair[1])
    return result


def compare_snapshots(
    baseline: dict[str, Any], current: dict[str, Any]
) -> dict[str, Any]:
    baseline_slots = normalize_slots(baseline)
    current_slots = normalize_slots(current)

    missing = sorted(set(baseline_slots.keys()) - set(current_slots.keys()))
    extra = sorted(set(current_slots.keys()) - set(baseline_slots.keys()))
    mismatched = sorted(
        key
        for key in baseline_slots.keys() & current_slots.keys()
        if baseline_slots[key] != current_slots[key]
    )

    baseline_total = int(baseline.get("total_pairs") or 0)
    current_total = int(current.get("total_pairs") or 0)

    return {
        "baseline_total": baseline_total,
        "current_total": current_total,
        "total_diff": current_total - baseline_total,
        "missing_slots": missing,
        "extra_slots": extra,
        "mismatched_slots": mismatched,
    }


def report_comparison(
    stdout: Any, style: Any, comparison: dict[str, Any]
) -> None:
    total_diff = comparison["total_diff"]
    baseline_total = comparison["baseline_total"]
    current_total = comparison["current_total"]

    if total_diff == 0:
        stdout.write(
            style.SUCCESS(
                "Totais coincidem: "
                f"{current_total} fusões "
                f"(baseline também tinha {baseline_total})."
            )
        )
    else:
        stdout.write(
            style.WARNING(
                "Diferença de total detectada: "
                f"baseline={baseline_total}, atual={current_total}."
            )
        )

    for label, items in (
        ("Slots ausentes", comparison["missing_slots"]),
        ("Slots extras", comparison["extra_slots"]),
        ("Slots com pares divergentes", comparison["mismatched_slots"]),
    ):
        if items:
            stdout.write(style.ERROR(f"{label}: {items[:20]}"))
        else:
            stdout.write(style.SUCCESS(f"{label}: nenhum."))

