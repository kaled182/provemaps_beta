"""Management command to verify GIST index on Site.location field."""

from typing import Any

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    """Verify GIST index creation for Site.location field."""

    help = "Verify GIST index on Site.location field"

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        with connection.cursor() as cursor:
            # Check for idx_site_location
            cursor.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'zabbix_api_site'
                AND indexname = 'idx_site_location'
            """)
            result = cursor.fetchall()

            if result:
                self.stdout.write(
                    self.style.SUCCESS("✅ GIST Index Found:")
                )
                for row in result:
                    self.stdout.write(f"  Name: {row[0]}")
                    self.stdout.write(f"  Definition: {row[1]}")
            else:
                self.stdout.write(
                    self.style.ERROR("❌ GIST Index NOT found")
                )

            # List all indexes
            cursor.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'zabbix_api_site'
                ORDER BY indexname
            """)
            all_indexes = cursor.fetchall()
            total = len(all_indexes)
            self.stdout.write(
                f"\n📊 All indexes on zabbix_api_site ({total} total):"
            )
            for idx_name, idx_def in all_indexes:
                if 'GIST' in idx_def.upper():
                    self.stdout.write(
                        self.style.SUCCESS(f"  - {idx_name} (GIST)")
                    )
                else:
                    self.stdout.write(f"  - {idx_name}")

            # Check Site count with location
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(location) as with_location
                FROM zabbix_api_site
            """)
            row = cursor.fetchone()
            if row:
                total_sites, sites_with_loc = row[0], row[1]
                self.stdout.write(
                    f"\n📍 Sites: {total_sites} total, "
                    f"{sites_with_loc} with location"
                )

