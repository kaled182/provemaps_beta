from typing import List

from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = (
        "Remove qualquer dado histórico de gráficos do Zabbix persistido no banco local "
        "(remove tabelas legadas de snapshots, caso existam)."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--execute",
            action="store_true",
            help=(
                "Executa a limpeza de fato (DROP TABLE). Sem esta flag, roda em modo dry-run."
            ),
        )

    def handle(self, *args, **options):
        execute: bool = bool(options.get("execute"))

        introspection = connection.introspection
        existing_tables: List[str] = introspection.table_names()

        # Tabelas específicas que já tivemos no passado para snapshots ópticos
        legacy_tables: List[str] = [
            "inventory_optical_power_snapshot",
            "zabbix_api_optical_power_snapshot",
            "optical_power_snapshot",
        ]

        candidates: List[str] = []
        for name in legacy_tables:
            if name in existing_tables:
                candidates.append(name)

        # Varredura adicional por nomes que contenham 'snapshot' relacionados a zabbix/optical/traffic
        for t in existing_tables:
            tl = t.lower()
            if "snapshot" in tl and ("zabbix" in tl or "optical" in tl or "traffic" in tl):
                if t not in candidates:
                    candidates.append(t)

        if not candidates:
            self.stdout.write(
                self.style.SUCCESS(
                    "Nenhuma tabela de snapshot/gráfico do Zabbix encontrada para limpar."
                )
            )
            return

        self.stdout.write(
            f"Encontradas {len(candidates)} tabelas legadas: {', '.join(candidates)}"
        )

        if not execute:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run: nenhuma alteração foi feita. Use --execute para remover as tabelas."
                )
            )
            return

        with connection.cursor() as cursor:
            with transaction.atomic():
                for t in candidates:
                    try:
                        # Compatível com SQLite/PostgreSQL
                        cursor.execute(f'DROP TABLE IF EXISTS "{t}";')
                        self.stdout.write(self.style.WARNING(f"Tabela removida: {t}"))
                    except Exception as exc:  # pragma: no cover
                        self.stderr.write(f"Falha ao remover {t}: {exc}")

        self.stdout.write(self.style.SUCCESS("Limpeza concluída com sucesso."))
