#!/usr/bin/env python
"""Test backup configuration endpoint"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from setup_app.utils import env_manager
from setup_app.api_views import get_configuration
from django.test import RequestFactory
from django.contrib.auth.models import User
import json

print("=" * 80)
print("1. Testing env_manager.read_values()")
print("=" * 80)

backup_keys = [
    'BACKUP_AUTO_ENABLED',
    'BACKUP_FREQUENCY', 
    'BACKUP_RETENTION_DAYS',
    'BACKUP_CLOUD_UPLOAD',
    'BACKUP_CLOUD_PROVIDER',
    'BACKUP_CLOUD_PATH'
]

vals = env_manager.read_values(backup_keys)
print("From .env file:")
for k, v in vals.items():
    print(f"  {k}: {repr(v)}")

print("\n" + "=" * 80)
print("2. Testing get_configuration endpoint")
print("=" * 80)

# Create fake request
factory = RequestFactory()
req = factory.get('/setup_app/api/config/')

# Get admin user
admin = User.objects.filter(is_staff=True).first()
if not admin:
    print("ERROR: No admin user found")
    sys.exit(1)

req.user = admin

# Call endpoint
response = get_configuration(req)
data = json.loads(response.content)

# Extract BACKUP_* fields
config = data.get('configuration', {})
backup_config = {k: v for k, v in config.items() if k.startswith('BACKUP_')}

print("BACKUP_* fields in API response:")
print(json.dumps(backup_config, indent=2))

print("\n" + "=" * 80)
print("3. Checking editable_keys list")
print("=" * 80)

editable = data.get('editable_keys', [])
backup_editable = [k for k in editable if k.startswith('BACKUP_')]
print(f"BACKUP_* fields in editable_keys: {backup_editable}")

print("\n" + "=" * 80)
print("4. Summary")
print("=" * 80)

missing_in_response = set(backup_keys) - set(backup_config.keys())
if missing_in_response:
    print(f"❌ Missing from API response: {missing_in_response}")
else:
    print("✅ All BACKUP_* fields present in API response")

missing_in_editable = set(backup_keys) - set(backup_editable)
if missing_in_editable:
    print(f"❌ Missing from editable_keys: {missing_in_editable}")
else:
    print("✅ All BACKUP_* fields in editable_keys")
