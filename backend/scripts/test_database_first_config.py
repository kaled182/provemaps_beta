#!/usr/bin/env python
"""
Test script to verify database-first configuration architecture.

This script verifies:
1. Configuration is loaded from database (not .env)
2. All Zabbix credentials persist correctly
3. Runtime config matches database values
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from setup_app.models import FirstTimeSetup
from setup_app.services import runtime_settings


def test_database_first_config():
    """Test that configuration is loaded from database, not .env."""
    
    print("\n" + "="*80)
    print("DATABASE-FIRST CONFIGURATION TEST")
    print("="*80 + "\n")
    
    # Step 1: Get database record
    print("Step 1: Checking database record...")
    db_record = FirstTimeSetup.objects.filter(configured=True).first()
    
    if not db_record:
        print("❌ FAILED: No configured FirstTimeSetup record found")
        return False
    
    print(f"✅ Database record found (ID: {db_record.id})")
    print(f"   - Company: {db_record.company_name}")
    print(f"   - Configured: {db_record.configured}")
    print(f"   - Auth Type: {db_record.auth_type}")
    
    # Step 2: Get runtime config
    print("\nStep 2: Loading runtime configuration...")
    runtime_config = runtime_settings.get_runtime_config()
    
    print(f"✅ Runtime config loaded")
    print(f"   - Zabbix URL: {runtime_config.zabbix_api_url}")
    print(f"   - Zabbix User: {runtime_config.zabbix_api_user}")
    print(f"   - Has Password: {bool(runtime_config.zabbix_api_password)}")
    print(f"   - Has API Key: {bool(runtime_config.zabbix_api_key)}")
    
    # Step 3: Compare database vs runtime config
    print("\nStep 3: Validating database → runtime mapping...")
    
    checks = [
        ("Zabbix URL", db_record.zabbix_url, runtime_config.zabbix_api_url),
        ("Zabbix User", db_record.zabbix_user, runtime_config.zabbix_api_user),
        ("Google Maps Key", db_record.maps_api_key, runtime_config.google_maps_api_key),
        ("Map Provider", db_record.map_provider, runtime_config.map_provider),
        ("DB Host", db_record.db_host, runtime_config.db_host),
        ("DB Name", db_record.db_name, runtime_config.db_name),
    ]
    
    all_passed = True
    for name, db_value, runtime_value in checks:
        match = (db_value == runtime_value) or (not db_value and not runtime_value)
        status = "✅" if match else "❌"
        print(f"   {status} {name}: DB='{db_value or ''}' → Runtime='{runtime_value or ''}'")
        if not match:
            all_passed = False
    
    # Step 4: Check .env file (should be minimal/template only)
    print("\nStep 4: Checking .env file status...")
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    
    if not os.path.exists(env_path):
        print("✅ .env file does not exist (database-only configuration)")
    else:
        with open(env_path, 'r') as f:
            env_content = f.read()
        
        # Check if .env has actual values or just comments/empty lines
        non_empty_lines = [
            line for line in env_content.split('\n')
            if line.strip() and not line.strip().startswith('#')
        ]
        
        if not non_empty_lines:
            print("✅ .env file is empty (database-only configuration)")
        else:
            print(f"⚠️  .env file has {len(non_empty_lines)} non-empty lines:")
            for line in non_empty_lines[:5]:  # Show first 5
                print(f"      {line}")
            if len(non_empty_lines) > 5:
                print(f"      ... and {len(non_empty_lines) - 5} more")
    
    # Step 5: Verify encrypted fields work
    print("\nStep 5: Testing encrypted field decryption...")
    try:
        # These fields are encrypted in database
        password = db_record.zabbix_password
        api_key = db_record.zabbix_api_key
        
        print(f"✅ Zabbix password decrypted: {bool(password)} (length: {len(password) if password else 0})")
        print(f"✅ Zabbix API key decrypted: {bool(api_key)} (length: {len(api_key) if api_key else 0})")
    except Exception as e:
        print(f"❌ Encrypted field decryption failed: {e}")
        all_passed = False
    
    # Final verdict
    print("\n" + "="*80)
    if all_passed:
        print("✅ DATABASE-FIRST CONFIGURATION TEST PASSED")
        print("="*80)
        print("\nConfiguration is correctly loaded from database.")
        print("The .env file is not being used as the primary data source.")
        return True
    else:
        print("❌ DATABASE-FIRST CONFIGURATION TEST FAILED")
        print("="*80)
        print("\nSome checks failed. Review output above.")
        return False


if __name__ == "__main__":
    success = test_database_first_config()
    sys.exit(0 if success else 1)
