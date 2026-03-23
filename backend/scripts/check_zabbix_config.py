#!/usr/bin/env python
"""Quick check of Zabbix runtime configuration."""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.dev")
django.setup()

from setup_app.services.runtime_settings import get_runtime_config

config = get_runtime_config()

print("=" * 80)
print("ZABBIX RUNTIME CONFIGURATION CHECK")
print("=" * 80)
print(f"ZABBIX_API_URL: {config.zabbix_api_url}")
print(f"ZABBIX_API_USER: {config.zabbix_api_user}")
print(f"Has password: {bool(config.zabbix_api_password)}")
print(f"Configured: {bool(config.zabbix_api_url and config.zabbix_api_user)}")
print("=" * 80)

# Test the endpoint logic
if config.zabbix_api_url and config.zabbix_api_user:
    print("✅ Zabbix is CONFIGURED")
else:
    print("❌ Zabbix is NOT CONFIGURED")
    if not config.zabbix_api_url:
        print("   - Missing: ZABBIX_API_URL")
    if not config.zabbix_api_user:
        print("   - Missing: ZABBIX_API_USER")
