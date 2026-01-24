#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from setup_app.models import MessagingGateway
from inventory.models import Site

print("=== CÂMERAS NO BANCO ===")
cameras = MessagingGateway.objects.filter(gateway_type='video')
print(f"Total de câmeras: {cameras.count()}")
print()

for camera in cameras:
    print(f"ID: {camera.id}")
    print(f"Nome: {camera.name}")
    print(f"Site Name: {camera.site_name}")
    print(f"---")

print("\n=== SITES NO INVENTÁRIO ===")
sites = Site.objects.all()
for site in sites[:10]:
    print(f"ID: {site.id}, Nome: {site.name}, Display: {site.display_name}")
