#!/usr/bin/env python
"""Verify GIST index creation for Site.location field."""

import os
import sys

import django
from django.db import connection

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()


def verify_gist_index():
    """Check if idx_site_location GIST index exists."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename = 'zabbix_api_site'
            AND indexname = 'idx_site_location'
        """)
        result = cursor.fetchall()

        if result:
            print("✅ GIST Index Found:")
            for row in result:
                print(f"  Name: {row[0]}")
                print(f"  Definition: {row[1]}")
        else:
            print("❌ GIST Index NOT found")

        # Also check all indexes on the table
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'zabbix_api_site'
            ORDER BY indexname
        """)
        all_indexes = cursor.fetchall()
        total = len(all_indexes)
        print(f"\n📊 All indexes on zabbix_api_site ({total} total):")
        for idx_name, _ in all_indexes:
            print(f"  - {idx_name}")


if __name__ == '__main__':
    verify_gist_index()
