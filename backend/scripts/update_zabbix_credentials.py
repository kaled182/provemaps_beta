#!/usr/bin/env python
"""Update FirstTimeSetup record with Zabbix credentials."""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.dev")
django.setup()

from setup_app.models import FirstTimeSetup
from django.conf import settings

print("=" * 80)
print("UPDATING ZABBIX CREDENTIALS IN FIRSTTIMESETUP")
print("=" * 80)

record = FirstTimeSetup.objects.filter(configured=True).order_by("-configured_at").first()

if not record:
    print("❌ No FirstTimeSetup record found!")
    sys.exit(1)

print(f"📝 Current state:")
print(f"   Zabbix URL: {record.zabbix_url}")
print(f"   Zabbix User: {record.zabbix_user or '(empty)'}")
print(f"   Has Password: {bool(record.zabbix_password)}")
print()

# Update with values from settings (which reads from .env)
zabbix_url = getattr(settings, "ZABBIX_API_URL", "")
zabbix_user = getattr(settings, "ZABBIX_API_USER", "")
zabbix_password = getattr(settings, "ZABBIX_API_PASSWORD", "")

if not zabbix_user or not zabbix_password:
    print("❌ ZABBIX_API_USER or ZABBIX_API_PASSWORD not set in .env!")
    print(f"   ZABBIX_API_USER: {zabbix_user or '(empty)'}")
    print(f"   ZABBIX_API_PASSWORD: {'***' if zabbix_password else '(empty)'}")
    sys.exit(1)

print(f"✏️  Updating with:")
print(f"   Zabbix URL: {zabbix_url}")
print(f"   Zabbix User: {zabbix_user}")
print(f"   Has Password: {bool(zabbix_password)}")
print()

# Encrypt password using Fernet
from setup_app.fields import encrypt_string
encrypted_password = encrypt_string(zabbix_password)

record.zabbix_url = zabbix_url
record.zabbix_user = zabbix_user
record.zabbix_password = encrypted_password
record.save(update_fields=["zabbix_url", "zabbix_user", "zabbix_password"])

print("=" * 80)
print("✅ CREDENTIALS UPDATED SUCCESSFULLY!")
print("=" * 80)
print()
print("Verify:")

# Reload and check
from setup_app.services.runtime_settings import get_runtime_config
config = get_runtime_config()

print(f"   URL: {config.zabbix_api_url}")
print(f"   User: {config.zabbix_api_user}")
print(f"   Has Password: {bool(config.zabbix_api_password)}")
print(f"   Configured: {bool(config.zabbix_api_url and config.zabbix_api_user)}")

if config.zabbix_api_url and config.zabbix_api_user:
    print()
    print("✅ Zabbix is NOW CONFIGURED!")
else:
    print()
    print("❌ Still not configured - check values above")
