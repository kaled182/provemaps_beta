#!/usr/bin/env python
"""Limpar todos os devices do banco de dados."""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from inventory.models import Device, DeviceGroup, Port

# Contar antes de apagar
device_count = Device.objects.count()
port_count = Port.objects.count()

print(f"Dispositivos atuais: {device_count}")
print(f"Portas atuais: {port_count}")
print("\nApagando todos os dispositivos e portas...")

# Apagar todas as portas primeiro (cascade do device)
Port.objects.all().delete()

# Apagar todos os devices
Device.objects.all().delete()

print(f"\n✅ {device_count} dispositivos apagados")
print(f"✅ {port_count} portas apagadas")
print(f"\nGrupos mantidos: {DeviceGroup.objects.count()}")
print("\nPronto para nova importação!")
