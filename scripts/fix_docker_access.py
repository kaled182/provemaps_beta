#!/usr/bin/env python
"""
Fix Docker Access Issues
Completes first-time setup and configures permissions
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from setup_app.models import FirstTimeSetup
from django.contrib.auth import get_user_model

User = get_user_model()

print("="*60)
print("FIXING DOCKER ACCESS ISSUES")
print("="*60)

# 1. Complete first-time setup
print("\n[1] Checking first-time setup...")
setup, created = FirstTimeSetup.objects.get_or_create(
    id=1,
    defaults={
        'company_name': 'ProveMaps Development',
        'zabbix_url': 'http://zabbix.example.com',
        'auth_type': 'token',
        'zabbix_api_key': 'development-token',
        'maps_api_key': 'development-maps-key',
        'configured': True,
    }
)
if not setup.configured:
    setup.configured = True
    setup.company_name = 'ProveMaps Development'
    setup.save()
    print("✅ First-time setup marked as configured")
else:
    print("✅ First-time setup already configured")

# 2. Ensure admin user exists
print("\n[2] Checking admin user...")
admin_exists = User.objects.filter(username='admin').exists()
if admin_exists:
    print("✅ Admin user exists")
    admin = User.objects.get(username='admin')
    print(f"   - Username: {admin.username}")
    print(f"   - Email: {admin.email}")
    print(f"   - Is superuser: {admin.is_superuser}")
    print(f"   - Is staff: {admin.is_staff}")
    print(f"   - Is active: {admin.is_active}")
else:
    print("⚠️  Admin user not found - creating...")
    admin = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123'
    )
    print("✅ Admin user created")
    print("   - Username: admin")
    print("   - Password: admin123")

# 3. Check database connection
print("\n[3] Checking database connection...")
try:
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    print("✅ Database connection OK")
except Exception as e:
    print(f"❌ Database error: {e}")

# 4. Check static files
print("\n[4] Checking static files...")
from django.conf import settings
static_root = settings.STATIC_ROOT
print(f"   - STATIC_ROOT: {static_root}")
print(f"   - STATIC_URL: {settings.STATIC_URL}")

vue_spa_path = os.path.join(static_root, 'vue-spa', 'assets', 'main.js')
if os.path.exists(vue_spa_path):
    size_kb = os.path.getsize(vue_spa_path) / 1024
    print(f"✅ Frontend assets exist ({size_kb:.1f} KB)")
else:
    print(f"⚠️  Frontend assets not found at {vue_spa_path}")

# 5. Check Redis connection
print("\n[5] Checking Redis connection...")
try:
    from django.core.cache import cache
    cache.set('test_key', 'test_value', 10)
    value = cache.get('test_key')
    if value == 'test_value':
        print("✅ Redis cache OK")
    else:
        print("⚠️  Redis cache not working")
except Exception as e:
    print(f"⚠️  Redis error (non-critical): {e}")

print("\n" + "="*60)
print("SETUP COMPLETE - Try accessing:")
print("  - Backbone dashboard: http://localhost:8000/monitoring/backbone/")
print("  - Admin: http://localhost:8000/admin/")
print("  - Login with: admin / admin123")
print("="*60)
