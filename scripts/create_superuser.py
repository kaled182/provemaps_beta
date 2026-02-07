#!/usr/bin/env python
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
os.environ['DB_ENGINE'] = 'sqlite'
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
if not User.objects.filter(username='admin').exists():
    user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('✓ Superuser created: admin/admin123')
else:
    print('✓ Superuser admin already exists')
