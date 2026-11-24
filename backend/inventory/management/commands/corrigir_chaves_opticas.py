"""EV-0081 — corrige `Device.zabbix_hostid` do OLT BRV e as chaves ópticas das portas.

Por omissão é ENSAIO (não escreve). Com `--aplicar` grava uma cópia JSON dos valores antigos,
escreve numa transação e invalida as caches. A lógica está em `inventory.usecases.optical_keys`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from inventory.usecases.optical_keys import (
    OpticalKeyPlanError,
    apply_optical_key_plan,
    build_optical_key_plan,
)


def _default_backup_dir() -> Path:
    return Path(settings.BASE_DIR) / "backend" / "logs"


class Command(BaseCommand):
    help = (
        "EV-0081: corrige o hostid do device 22 e as chaves RX/TX ópticas das portas "
        "(ensaio por omissão; --aplicar para gravar)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--aplicar",
            action="store_true",
            help="Grava as mudanças (cópia JSON antes, uma transação, caches invalidadas).",
        )
        parser.add_argument(
            "--backup-dir",
            default=None,
            help="Diretório da cópia JSON (padrão: <BASE_DIR>/backend/logs).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        plan = build_optical_key_plan()
        self._print_plan(plan)

        if not options["aplicar"]:
            self.stdout.write(self.style.WARNING("ENSAIO — nada foi escrito. Use --aplicar."))
            return

        backup_dir = Path(options["backup_dir"]) if options["backup_dir"] else None
        try:
            result = apply_optical_key_plan(plan, backup_dir or _default_backup_dir())
        except OpticalKeyPlanError as exc:
            raise CommandError(str(exc)) from exc

        if result["backup_path"]:
            self.stdout.write(f"Cópia dos valores antigos: {result['backup_path']}")
        else:
            self.stdout.write("Nada a mudar — sem cópia, sem escrita.")
        self.stdout.write(
            self.style.SUCCESS(
                f"Aplicado: {result['devices_atualizados']} equipamento(s), "
                f"{result['portas_atualizadas']} porta(s); "
                f"caches invalidadas: {'sim' if result['caches_invalidadas'] else 'não'}"
            )
        )
        if result["conflitos"]:
            self.stdout.write(
                self.style.WARNING(
                    f"{len(result['conflitos'])} linha(s) mudaram desde o ensaio e ficaram "
                    f"como estavam: {result['conflitos']}"
                )
            )

    def _print_plan(self, plan: dict[str, Any]) -> None:
        out = self.stdout
        for err in plan["errors"]:
            out.write(self.style.ERROR(f"ERRO Zabbix: {err}"))
        for note in plan["notes"]:
            out.write(self.style.WARNING(note))

        out.write("== Equipamentos ==")
        for d in plan["devices"]:
            mark = "MUDA" if d["changed"] else "fica"
            out.write(
                f"  [{mark}] device {d['device_id']} «{d['device_name']}» {d['field']}: "
                f"{d['old']!r} → {d['new']!r} ({d['reason']})"
            )

        out.write("== Portas ==")
        current_device = None
        for c in plan["ports"]:
            if c["device_id"] != current_device:
                current_device = c["device_id"]
                out.write(f"  device {c['device_id']} «{c['device_name']}»")
            mark = "MUDA" if c["changed"] else "fica"
            extra = ""
            if c.get("onu"):
                extra += f" ONU {c['onu']}"
            if "value" in c:
                extra += f" valor atual={c['value']}"
            out.write(
                f"    [{mark}] porta {c['port_id']} «{c['port_name']}» {c['rule']}{extra}\n"
                f"        rx: {c['rx_old']!r} → {c['rx_new']!r}\n"
                f"        tx: {c['tx_old']!r} → {c['tx_new']!r}"
            )

        if plan["unmatched"]:
            out.write("== Sem correspondência (não mudam) ==")
            for u in plan["unmatched"]:
                out.write(
                    f"  porta {u['port_id']} «{u['port_name']}» (device {u['device_id']}): "
                    f"{u['reason']} — rx={u['rx_old']!r} tx={u['tx_old']!r}"
                )

        s = plan["summary"]
        out.write("== Resumo ==")
        out.write(f"  equipamentos a mudar: {s['devices_a_mudar']}")
        out.write(
            f"  portas a mudar: {s['portas_a_mudar']} (sem mudança: {s['portas_sem_mudanca']}); "
            f"sem correspondência: {s['sem_correspondencia']}"
        )
        for rule, n in s["por_regra"].items():
            out.write(f"    {rule}: {n}")
        out.write(f"  chamadas ao Zabbix: {plan['zabbix_calls']}; erros: {s['erros']}")
